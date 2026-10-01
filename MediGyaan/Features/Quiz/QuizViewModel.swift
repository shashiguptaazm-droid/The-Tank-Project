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

    private let quiz: Quiz
    private var api: MediGyaanAPI = .live
    private var userId: Int = 0
    private var startedAt = Date()
    private var timerTask: Task<Void, Never>?
    private let speechSynthesizer = AVSpeechSynthesizer()

    init(quiz: Quiz) {
        self.quiz = quiz
        super.init()
        speechSynthesizer.delegate = self
    }

    // MARK: - Derived state

    var questions: [Question] { state.value?.questions ?? [] }

    var currentQuestion: Question? {
        guard questions.indices.contains(currentIndex) else { return nil }
        return questions[currentIndex]
    }

    var isLastQuestion: Bool { currentIndex >= questions.count - 1 }

    var hasStarted: Bool {
        if case .idle = state { return false }
        return true
    }

    var progress: Double {
        guard !questions.isEmpty else { return 0 }
        return Double(currentIndex + 1) / Double(questions.count)
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
        self.api = api
        self.userId = userId

        state = await LoadState.result { [api, quiz] in
            let questions = try await api.study.questions(quizId: quiz.id)
            return QuizSession(
                quizId: quiz.id,
                title: quiz.title,
                questions: questions,
                durationSeconds: quiz.durationSeconds,
                topic: quiz.topic
            )
        }

        guard let session = state.value, !session.questions.isEmpty else { return }
        startedAt = Date()
        currentIndex = 0
        answers = [:]
        combo = 0
        expEarned = 0
        isAnswerRevealed = false

        secondsRemaining = session.durationSeconds > 0
            ? session.durationSeconds
            : session.questions.count * 60
        startTimer()
    }

    private func startTimer() {
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
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
    }

    func goToPrevious() {
        stopAudio()
        guard currentIndex > 0 else { return }
        currentIndex -= 1
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
    }

    func jump(to index: Int) {
        stopAudio()
        guard questions.indices.contains(index) else { return }
        currentIndex = index
        isAnswerRevealed = (currentQuestion.flatMap { answers[$0.id] } != nil)
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
        speechSynthesizer.speak(utterance)
        isSpeaking = true
    }

    func stopAudio() {
        if speechSynthesizer.isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
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
        speechSynthesizer.stopSpeaking(at: .immediate)
    }
}
