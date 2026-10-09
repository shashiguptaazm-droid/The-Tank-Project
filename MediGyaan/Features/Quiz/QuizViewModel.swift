import Foundation
import AVFoundation
import UIKit

/// Drives an MCQ practice / quiz session: question delivery, timing, instant scoring,
/// audio reading (TTS), combo streaks, and backend synchronization.
/// Ports the full behavior of Android's `MCQActivity.kt`.
@MainActor
final class QuizViewModel: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {

    @Published private(set) var state: LoadState<QuizSession> = .idle
    @Published private(set) var currentIndex: Int = 0
    @Published private(set) var answers: [Int: AttemptAnswer] = [:]
    @Published private(set) var secondsRemaining: Int = 0
    @Published private(set) var isSubmitting = false
    @Published private(set) var result: QuizAttempt?

    // Gamification & instant feedback (mirrors MCQActivity.kt)
    @Published private(set) var combo: Int = 0
    @Published private(set) var expEarned: Int = 0
    @Published private(set) var isAnswerRevealed: Bool = false
    @Published private(set) var isSpeaking: Bool = false

    // Topic selector & Question pool (matching Android MCQActivity.kt topicSpinner & all_question_ids)
    @Published var selectedTopic: String = "All Topics"
    @Published private(set) var topicsList: [String] = ["All Topics"]
    @Published private(set) var allQuestionIds: [Int] = []
    @Published private(set) var isLoadingQuestion: Bool = false

    private let quiz: Quiz
    private var currentSubject: String
    private var api: MediGyaanAPI = .live
    private var userId: Int = 0
    private var startedAt = Date()
    private var timerTask: Task<Void, Never>?
    private var speechSynthesizer: AVSpeechSynthesizer?

    init(quiz: Quiz) {
        self.quiz = quiz
        self.currentSubject = quiz.subject.isEmpty ? "NEET PG" : quiz.subject
        if !quiz.topic.isEmpty {
            self.selectedTopic = quiz.topic
        }
        super.init()
    }

    // MARK: - Derived state

    var questions: [Question] { state.value?.questions ?? [] }

    var currentQuestion: Question? {
        guard questions.indices.contains(currentIndex) else { return nil }
        return questions[currentIndex]
    }

    var isLastQuestion: Bool {
        if !allQuestionIds.isEmpty {
            return currentIndex >= allQuestionIds.count - 1
        }
        return currentIndex >= questions.count - 1
    }

    var totalQuestionsCount: Int {
        if !allQuestionIds.isEmpty {
            return allQuestionIds.count
        }
        return questions.count
    }

    var hasStarted: Bool {
        if case .idle = state { return false }
        return true
    }

    var progress: Double {
        let total = totalQuestionsCount
        guard total > 0 else { return 0 }
        return Double(currentIndex + 1) / Double(total)
    }

    var answeredCount: Int { answers.count }

    var formattedTimeRemaining: String {
        let minutes = secondsRemaining / 60
        let seconds = secondsRemaining % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    func selectedIndex(for question: Question) -> Int? {
        answers[question.id]?.selectedIndex
    }

    func isQuestionAnswered(_ question: Question) -> Bool {
        answers[question.id] != nil
    }

    // MARK: - Lifecycle

    func start(api: MediGyaanAPI, userId: Int) async {
        RemoteLogger.log(
            tag: "QuizViewModel_start",
            message: "Starting Quiz - subject: \(currentSubject), topic: \(selectedTopic), quizId: \(quiz.id), userId: \(userId)"
        )
        self.api = api
        self.userId = userId

        // Fetch curriculum topics for subject matching Android's fetchTopics()
        await loadTopics()

        // Fetch initial question and pool of question IDs
        await loadInitialQuestionSession()
    }

    /// Fetches all topics for the subject from api/getTopics.php (matching MCQActivity.kt fetchTopics)
    func loadTopics() async {
        RemoteLogger.log(tag: "QuizViewModel_loadTopics", message: "Fetching topics for \(currentSubject)")
        do {
            let fetchedTopics = try await api.study.topics(subject: currentSubject)
            var names = ["All Topics"]
            names.append(contentsOf: fetchedTopics.map { $0.name }.filter { !$0.isEmpty })
            var seen = Set<String>()
            self.topicsList = names.filter { seen.insert($0).inserted }
            RemoteLogger.log(tag: "QuizViewModel_loadTopics_success", message: "Loaded \(self.topicsList.count) topics")
        } catch {
            RemoteLogger.log(tag: "QuizViewModel_loadTopics_error", message: "Failed: \(error.localizedDescription)")
            self.topicsList = ["All Topics"]
        }
    }

    /// Loads the question stream and question ID pool matching Android's fetchQuestion(null)
    func loadInitialQuestionSession() async {
        RemoteLogger.log(
            tag: "QuizViewModel_loadSession",
            message: "Loading session for \(currentSubject) | \(selectedTopic)"
        )
        state = .loading
        isLoadingQuestion = true
        defer { isLoadingQuestion = false }

        do {
            // First check if fixed quiz has questions
            if quiz.id > 0 {
                let quizQuestions = (try? await api.study.questions(quizId: quiz.id)) ?? []
                if !quizQuestions.isEmpty {
                    applyLoadedQuestions(quizQuestions)
                    return
                }
            }

            // Otherwise, stream from getQuestions.php?subject=<subject>&topic=<topic>&user_id=<userId>
            let (question, rawIds) = try await api.study.fetchQuestions(
                subject: currentSubject,
                topic: selectedTopic == "All Topics" ? nil : selectedTopic,
                userId: userId
            )

            RemoteLogger.log(
                tag: "QuizViewModel_fetchQuestions_success",
                message: "Fetched \(rawIds.count) ids. Has first question: \(question != nil)"
            )

            self.allQuestionIds = rawIds
            if let firstQuestion = question {
                if let img = firstQuestion.imageURL {
                    RemoteLogger.log(tag: "Question_Image", message: "Q#\(firstQuestion.id) image URL: \(img.absoluteString)")
                }
                applyLoadedQuestions([firstQuestion])
            } else if let firstId = rawIds.first {
                let singleQ = try await api.study.question(id: firstId)
                if let img = singleQ.imageURL {
                    RemoteLogger.log(tag: "Question_Image", message: "Q#\(singleQ.id) image URL: \(img.absoluteString)")
                }
                applyLoadedQuestions([singleQ])
            } else {
                state = .loaded(QuizSession(
                    quizId: quiz.id,
                    title: quiz.title.isEmpty ? selectedTopic : quiz.title,
                    questions: [],
                    durationSeconds: quiz.durationSeconds,
                    topic: selectedTopic
                ))
            }
        } catch {
            RemoteLogger.log(
                tag: "QuizViewModel_loadSession_error",
                message: "Error loading session: \(error.localizedDescription)"
            )
            state = .failed(error.localizedDescription)
        }
    }

    private func applyLoadedQuestions(_ loaded: [Question]) {
        state = .loaded(QuizSession(
            quizId: quiz.id,
            title: quiz.title.isEmpty ? (selectedTopic.isEmpty ? "Practice" : selectedTopic) : quiz.title,
            questions: loaded,
            durationSeconds: quiz.durationSeconds,
            topic: selectedTopic
        ))

        startedAt = Date()
        currentIndex = 0
        answers = [:]
        combo = 0
        expEarned = 0
        isAnswerRevealed = false

        if quiz.durationSeconds > 0 {
            secondsRemaining = quiz.durationSeconds
            startTimer()
        } else {
            secondsRemaining = 0
            timerTask?.cancel()
        }
    }

    /// User switches topic from the in-session topic dropdown (matching Android MCQActivity onItemSelected)
    func selectTopic(_ topic: String) async {
        guard topic != selectedTopic else { return }
        selectedTopic = topic
        stopAudio()
        await loadInitialQuestionSession()
    }

    private func startTimer() {
        guard secondsRemaining > 0 else { return }
        timerTask?.cancel()
        timerTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let self else { return }
                if self.secondsRemaining <= 1 {
                    self.secondsRemaining = 0
                    await self.finish()
                    return
                }
                self.secondsRemaining -= 1
            }
        }
    }

    // MARK: - Answering & Instant Review (MCQActivity style)

    /// Submits an answer with immediate validation, combo increment, and haptic feedback.
    func selectOption(index: Int, question: Question) {
        guard answers[question.id] == nil else { return } // Already answered

        let isCorrect = (index == question.correctIndex)
        answers[question.id] = AttemptAnswer(
            questionId: question.id,
            selectedIndex: index,
            correctIndex: question.correctIndex
        )
        isAnswerRevealed = true

        // Gamification logic matching MCQActivity.kt
        if isCorrect {
            combo += 1
            expEarned += 10 + (combo * 2)
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        } else {
            combo = 0
            UINotificationFeedbackGenerator().notificationOccurred(.error)
        }

        // Background sync to submitAnswerx1.php (fire-and-forget)
        Task {
            let optionLetters = ["A", "B", "C", "D", "E"]
            let letter = optionLetters.indices.contains(index) ? optionLetters[index] : "\(index + 1)"
            _ = try? await api.study.submitAnswer(questionId: question.id, answer: letter, userId: userId)
        }
    }

    func goToNext() {
        stopAudio()
        guard !isLastQuestion else { return }
        currentIndex += 1
        ensureQuestionLoaded(at: currentIndex)
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
    }

    func goToPrevious() {
        stopAudio()
        guard currentIndex > 0 else { return }
        currentIndex -= 1
        ensureQuestionLoaded(at: currentIndex)
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
    }

    func jump(to index: Int) {
        stopAudio()
        guard index >= 0 && index < totalQuestionsCount else { return }
        currentIndex = index
        ensureQuestionLoaded(at: currentIndex)
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
    }

    private func ensureQuestionLoaded(at index: Int) {
        guard !questions.indices.contains(index) else { return }
        guard allQuestionIds.indices.contains(index) else { return }
        let questionId = allQuestionIds[index]
        isLoadingQuestion = true
        Task { [weak self] in
            guard let self else { return }
            defer { self.isLoadingQuestion = false }
            if let fetched = try? await self.api.study.question(id: questionId) {
                if let img = fetched.imageURL {
                    RemoteLogger.log(tag: "Question_Image", message: "Q#\(fetched.id) (index \(index)) image URL: \(img.absoluteString)")
                }
                var currentList = self.questions
                while currentList.count <= index {
                    if currentList.count == index {
                        currentList.append(fetched)
                    } else {
                        // placeholder
                        currentList.append(fetched)
                    }
                }
                currentList[index] = fetched
                if let currentSession = self.state.value {
                    self.state = .loaded(QuizSession(
                        id: currentSession.id,
                        quizId: currentSession.quizId,
                        title: currentSession.title,
                        questions: currentList,
                        durationSeconds: currentSession.durationSeconds,
                        topic: currentSession.topic
                    ))
                }
            }
        }
    }

    // MARK: - Audio Reader (TTS)

    func toggleAudio() {
        if isSpeaking {
            stopAudio()
        } else if let q = currentQuestion {
            speak(question: q)
        }
    }

    private func speak(question: Question) {
        stopAudio()
        let cleanText = question.text.replacingOccurrences(of: #"^\d+[.\s\-)\]]+\s*"#, with: "", options: .regularExpression)
        var speech = "Question: \(cleanText). "
        let letters = ["A", "B", "C", "D", "E"]
        for (i, opt) in question.options.enumerated() {
            let l = letters.indices.contains(i) ? letters[i] : "\(i + 1)"
            speech += "Option \(l): \(opt). "
        }

        let utterance = AVSpeechUtterance(string: speech)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        if speechSynthesizer == nil {
            let synth = AVSpeechSynthesizer()
            synth.delegate = self
            speechSynthesizer = synth
        }
        speechSynthesizer?.speak(utterance)
        isSpeaking = true
    }

    func stopAudio() {
        if let synth = speechSynthesizer, synth.isSpeaking {
            synth.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            self.isSpeaking = false
        }
    }

    // MARK: - Submission

    func finish() async {
        stopAudio()
        guard result == nil, !isSubmitting else { return }
        isSubmitting = true
        timerTask?.cancel()
        defer { isSubmitting = false }

        let attempt = QuizAttempt(
            quizId: quiz.id,
            quizTitle: quiz.title,
            userId: userId,
            answers: questions.compactMap { answers[$0.id] },
            startedAt: startedAt,
            finishedAt: Date()
        )
        result = attempt
        _ = try? await api.study.syncAttempt(attempt)
    }

    deinit {
        timerTask?.cancel()
    }
}
