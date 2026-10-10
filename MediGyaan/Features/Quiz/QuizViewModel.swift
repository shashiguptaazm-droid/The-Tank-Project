import Foundation
import AVFoundation
import UIKit

/// Identifies a fixed "single player test mode" series.
///
/// Ports the intent extras read by `SinglePlayerTestModeActivity.onCreate`:
/// `UNIQUE_ID` (int), `SUBJECT` falling back to `SELECTED_SUBJECT` (string) and
/// `QUIZ_TYPE` (string).
struct SinglePlayerSeries: Equatable, Hashable {

    /// `intent.getIntExtra("UNIQUE_ID", 0)`.
    let uniqueId: Int

    /// `intent.getStringExtra("SUBJECT") ?: intent.getStringExtra("SELECTED_SUBJECT") ?: ""`.
    let subject: String

    /// `intent.getStringExtra("QUIZ_TYPE") ?: ""`.
    let quizType: String

    init(uniqueId: Int, subject: String = "", quizType: String = "") {
        self.uniqueId = uniqueId
        self.subject = subject
        self.quizType = quizType
    }
}

/// The pure, side-effect-free half of `SinglePlayer.kt`: the scoring constants,
/// the `UNIQUE_ID` normaliser, the `get_test_structure.php` reader and the
/// review-JSON builder `appendReviewJson()` used to assemble.
///
/// Kept out of ``QuizViewModel`` so none of it inherits main-actor isolation.
private enum SinglePlayerSupport {

    /// `xpPerCorrect` — awarded on every correct answer.
    static let xpPerCorrect = 10

    /// `totalQuestions` — the hard cap applied to the fetched id list.
    static let questionCap = 200

    /// `maxScore` — 800, i.e. `questionCap * correctPoints`.
    static let maxScore = 800

    /// `correctPoints` — `+4`.
    static let correctPoints = 4

    /// `wrongPoints` — `-1`.
    static let wrongPoints = -1

    /// The `delay(1100)` in `LaunchedEffect(showFeedback)` before auto-advancing.
    static let feedbackDelay: UInt64 = 1_100_000_000

    /// Ports `SinglePlayerTestModeActivity.normalizeUniqueId`: ids above 100 are
    /// left alone (they are already subject-scoped), everything else is folded
    /// into `1...50` with `0` mapped to `1`.
    static func normalizeUniqueId(_ id: Int) -> Int {
        if id > 100 { return id }
        let safe = ((id % 50) + 50) % 50
        return safe == 0 ? 1 : safe
    }

    /// Ports the `when (selected.uppercase())` letter tables scattered through
    /// `appendReviewJson` and `FeedbackCard`.
    static func letter(for index: Int) -> String {
        let letters = ["A", "B", "C", "D", "E"]
        return letters.indices.contains(index) ? letters[index] : ""
    }

    /// Inverse of ``letter(for:)``, used when restoring a previously answered
    /// question from the review list.
    static func index(forLetter letter: String) -> Int? {
        let upper = letter.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard upper.unicodeScalars.count == 1,
              let scalar = upper.unicodeScalars.first,
              scalar.value >= 65, scalar.value <= 90 else { return nil }
        return Int(scalar.value - 65)
    }

    /// `optInt(i, -1)` over a `JSONArray` that may hold ints, doubles or strings.
    static func integer(from value: Any) -> Int? {
        if let value = value as? Int { return value }
        if let value = value as? Double { return Int(value) }
        if let value = value as? String { return Int(value) }
        return nil
    }

    /// Ports `fetchQuestionIdsLegacyByUniqueId`:
    /// `GET api/get_test_structure.php?unique_id=&subject=&quiz_type=`, keeping
    /// only positive ids.
    ///
    /// The response is read defensively because the script has shipped both a
    /// bare `question_ids` array and a `data`-wrapped one.
    static func fetchQuestionIds(uniqueId: Int, subject: String, quizType: String) async throws -> [Int] {
        let object = try await HTTPClient.shared.getObject(.testStructure, query: [
            "unique_id": String(normalizeUniqueId(uniqueId)),
            "subject": subject,
            "quiz_type": quizType
        ])

        var payload: Any?
        for key in ["question_ids", "questionIds", "ids", "questions", "data"] {
            if let value = object[key], !(value is NSNull) {
                payload = value
                break
            }
        }
        guard let payload else { return [] }

        var rawItems: [Any] = []
        if let array = payload as? [Any] {
            rawItems = array
        } else if let nested = payload as? [String: Any] {
            for key in ["question_ids", "questionIds", "ids"] {
                if let array = nested[key] as? [Any] {
                    rawItems = array
                    break
                }
            }
        }

        return rawItems.compactMap { integer(from: $0) }.filter { $0 > 0 }
    }

    /// Ports `appendReviewJson(q, selected, isCorrect)`: the flat option fields,
    /// the two resolved answer texts and the `+4` / `-1` score change.
    static func reviewItem(question: Question, selectedIndex: Int, isCorrect: Bool) -> ReviewQuestionItem {
        let option: (Int) -> String = { question.options.indices.contains($0) ? question.options[$0] : "" }
        return ReviewQuestionItem(
            question_id: question.id,
            question: question.text,
            option_a: option(0),
            option_b: option(1),
            option_c: option(2),
            option_d: option(3),
            option_e: option(4),
            selected_option: letter(for: selectedIndex),
            correct_option: letter(for: question.correctIndex),
            selected_answer_text: option(selectedIndex),
            correct_answer_text: option(question.correctIndex),
            score_change: isCorrect ? correctPoints : wrongPoints,
            explanation: question.explanation,
            image_url: question.imageURL?.absoluteString ?? "",
            is_correct: isCorrect ? 1 : 0
        )
    }
}

/// Drives an MCQ practice / quiz session: question delivery, timing, instant scoring,
/// audio reading (TTS), combo streaks, and backend synchronization.
///
/// Also carries the fixed-series **single player test mode** ported from
/// `SinglePlayer.kt` (`SinglePlayerTestModeActivity` /
/// `SinglePlayerTestModeScreen`), which is selected by passing a
/// ``SinglePlayerSeries``. In that mode the MCQ timer, combo streak and topic
/// switcher are inert and the `+4` / `-1`, 800-point, 200-question,
/// background-penalty rules apply instead.
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

    // MARK: - Single player test mode (SinglePlayer.kt)

    /// `questionIds` after the 200-item cap.
    @Published private(set) var seriesQuestionIds: [Int] = []
    /// The normalised `UNIQUE_ID` the series is addressed by.
    @Published private(set) var seriesUniqueId: Int = 0
    @Published private(set) var isLoadingSeriesIds: Bool = false
    @Published private(set) var isLoadingSeriesQuestion: Bool = false
    @Published private(set) var seriesQuestion: Question?
    /// `selectedOption` — the unsubmitted pick, held separately from `answers`.
    @Published private(set) var seriesDraftIndex: Int?
    /// `answerLocked` — once true the options are frozen and the review state paints.
    @Published private(set) var isSeriesAnswerLocked: Bool = false
    /// `isQuestionPenalized` — guards the one-per-question background deduction.
    @Published private(set) var isSeriesPenalized: Bool = false
    @Published private(set) var seriesScore: Int = 0
    @Published private(set) var seriesCorrectCount: Int = 0
    @Published private(set) var seriesWrongCount: Int = 0
    @Published private(set) var seriesAttemptedCount: Int = 0
    /// `currentExp`, seeded from `SharedPreferences("MY_APP")["user_exp"]`.
    @Published private(set) var seriesExp: Int = RankProgressStore.exp()
    @Published private(set) var isSeriesFeedbackVisible: Bool = false
    @Published private(set) var seriesFeedbackIsCorrect: Bool = false
    @Published private(set) var seriesFeedbackTitle: String = ""
    @Published private(set) var seriesFeedbackText: String = ""
    /// `finished` — swaps the runner for ``SinglePlayerResultView``.
    @Published private(set) var isSeriesFinished: Bool = false
    /// `showBattleSummary` — the collapsible stats card, collapsed by default.
    @Published private(set) var isSeriesSummaryExpanded: Bool = false
    /// `reviewQuestions` — the flat review rows built by `appendReviewJson`.
    @Published private(set) var seriesReviewItems: [ReviewQuestionItem] = []
    /// Stands in for the `Toast` the restart button raised on Android.
    @Published var seriesRestartNotice: Bool = false
    /// Drives `.errorAlert(...)`; Kotlin raised a `Toast` at each of these points.
    @Published var seriesErrorMessage: String?

    private let quiz: Quiz
    private let singlePlayerSeries: SinglePlayerSeries?
    private var currentSubject: String
    private var api: MediGyaanAPI = .live
    private var userId: Int = 0
    private var startedAt = Date()
    private var timerTask: Task<Void, Never>?
    private var seriesFeedbackTask: Task<Void, Never>?
    /// `finishEarly` — forces the next advance to end the session.
    private var seriesFinishRequested = false
    /// Kotlin's `LaunchedEffect(Unit)` guard, so history is written exactly once.
    private var seriesHistorySaved = false
    /// `"Mock Test $uniqueId"`, used as the topic label and the stats bucket.
    private var seriesTopicLabel: String = ""
    private var speechSynthesizer: AVSpeechSynthesizer?

    init(quiz: Quiz, singlePlayerSeries: SinglePlayerSeries? = nil) {
        self.quiz = quiz
        self.singlePlayerSeries = singlePlayerSeries
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

    /// The question the chrome (TTS, share, Ask AI) should act on. Single-player
    /// runs hold exactly one question at a time, outside the `QuizSession`.
    var activeQuestion: Question? {
        singlePlayerSeries != nil ? seriesQuestion : currentQuestion
    }

    var isSinglePlayerMode: Bool { singlePlayerSeries != nil }

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

    // MARK: - Single player scoring constants

    /// `maxScore` — 800.
    var seriesMaxScore: Int { SinglePlayerSupport.maxScore }
    /// `totalQuestions` — the 200-item cap.
    var seriesQuestionCap: Int { SinglePlayerSupport.questionCap }
    /// `correctPoints` — `+4`.
    var seriesCorrectPoints: Int { SinglePlayerSupport.correctPoints }
    /// `wrongPoints` — `-1`.
    var seriesWrongPoints: Int { SinglePlayerSupport.wrongPoints }
    /// `xpPerCorrect` — 10 per correct answer.
    var seriesXpPerCorrect: Int { SinglePlayerSupport.xpPerCorrect }

    /// `scoreRatio`, clamped to `0...1` exactly as Kotlin's `.coerceIn(0f, 1f)`.
    var seriesScoreRatio: Double {
        guard SinglePlayerSupport.maxScore > 0 else { return 0 }
        return min(max(Double(seriesScore) / Double(SinglePlayerSupport.maxScore), 0), 1)
    }

    /// The result screen's percentage, clamped to `0...100`.
    var seriesPercentage: Double {
        guard SinglePlayerSupport.maxScore > 0 else { return 0 }
        return min(max(Double(seriesScore) / Double(SinglePlayerSupport.maxScore) * 100, 0), 100)
    }

    /// `progressText` — `"Q n / 200"`, or `"Finished"` once the session ends.
    var seriesProgressText: String {
        guard !isSeriesFinished else { return "Finished" }
        return "Q \(min(currentIndex + 1, SinglePlayerSupport.questionCap)) / \(SinglePlayerSupport.questionCap)"
    }

    /// `totalQuestions - attemptedCount`, floored at zero.
    var seriesRemainingCount: Int {
        max(0, SinglePlayerSupport.questionCap - seriesAttemptedCount)
    }

    /// Kotlin swaps Submit for Next when `answerLocked && currentIndex < attemptedCount`.
    var seriesOffersNextButton: Bool {
        isSeriesAnswerLocked && currentIndex < seriesAttemptedCount
    }

    // MARK: - Lifecycle

    func start(api: MediGyaanAPI, userId: Int) async {
        self.api = api
        self.userId = userId

        if singlePlayerSeries != nil {
            await startSeriesSession()
            return
        }

        // Fetch curriculum topics for subject matching Android's fetchTopics()
        await loadTopics()

        // Fetch initial question and pool of question IDs
        await loadInitialQuestionSession()
    }

    // MARK: - Single player session (SinglePlayer.kt)

    /// Ports `LaunchedEffect(uniqueId)`: resolve the id list, cap it at 200, then
    /// load question zero — or jump straight to the result screen when the series
    /// is empty.
    private func startSeriesSession() async {
        guard let series = singlePlayerSeries else { return }

        state = .loading
        isLoadingSeriesIds = true
        seriesErrorMessage = nil
        seriesUniqueId = series.uniqueId
        seriesTopicLabel = "Mock Test \(series.uniqueId)"
        if !series.subject.isEmpty {
            currentSubject = series.subject
        }
        seriesExp = RankProgressStore.exp()
        startedAt = Date()

        var ids: [Int] = []
        do {
            ids = try await SinglePlayerSupport.fetchQuestionIds(
                uniqueId: series.uniqueId,
                subject: series.subject,
                quizType: series.quizType
            )
        } catch {
            RemoteLogger.log(
                tag: "SINGLE_PLAYER",
                message: "Test structure fetch failed for unique_id=\(series.uniqueId): \(error.localizedDescription)"
            )
            seriesErrorMessage = "Question list failed"
        }

        seriesQuestionIds = Array(ids.prefix(SinglePlayerSupport.questionCap))
        isLoadingSeriesIds = false
        state = .loaded(QuizSession(
            quizId: quiz.id,
            title: seriesTopicLabel,
            questions: [],
            durationSeconds: 0,
            topic: series.quizType
        ))

        if seriesQuestionIds.isEmpty {
            finishSeries()
            return
        }

        currentIndex = 0
        await loadSeriesQuestion(at: 0)
    }

    /// Ports `loadQuestionByIndex`: fetch one question and either restore the
    /// locked state from the review list or reset for a fresh attempt.
    private func loadSeriesQuestion(at index: Int) async {
        guard seriesQuestionIds.indices.contains(index) else { return }
        let questionId = seriesQuestionIds[index]
        let existing = seriesReviewItems.first { $0.question_id == questionId }

        isLoadingSeriesQuestion = true
        defer { isLoadingSeriesQuestion = false }

        guard let question = try? await api.study.question(id: questionId) else {
            RemoteLogger.log(tag: "SINGLE_PLAYER", message: "Unable to load question #\(questionId)")
            seriesErrorMessage = "Unable to load question"
            return
        }
        seriesQuestion = question

        if let existing {
            seriesDraftIndex = SinglePlayerSupport.index(forLetter: existing.selected_option)
            isSeriesAnswerLocked = true
        } else {
            seriesDraftIndex = nil
            isSeriesAnswerLocked = false
            isSeriesPenalized = false
        }
    }

    /// Selects an option without grading it — the runner separates picking from
    /// submitting, unlike the MCQ flow.
    func selectSeriesOption(index: Int) {
        guard singlePlayerSeries != nil, !isSeriesAnswerLocked else { return }
        seriesDraftIndex = index
    }

    /// Ports `onToggle` on `BattleSummaryCard`.
    func toggleSeriesSummary() {
        guard singlePlayerSeries != nil else { return }
        isSeriesSummaryExpanded.toggle()
    }

    /// Ports `submitAnswer()`: lock, tally, score, record the answer, award XP
    /// on a hit and queue the review row.
    func submitSeriesAnswer() async {
        guard singlePlayerSeries != nil,
              !isSeriesAnswerLocked,
              let question = seriesQuestion,
              let selectedIndex = seriesDraftIndex else { return }

        let isCorrect = selectedIndex == question.correctIndex

        isSeriesAnswerLocked = true
        seriesAttemptedCount += 1
        DailyStatsManager.shared.recordAnswer(topic: seriesTopicLabel, isCorrect: isCorrect)

        if isCorrect {
            seriesCorrectCount += 1
            seriesScore += SinglePlayerSupport.correctPoints
            seriesFeedbackTitle = "Correct"
            let explanation = question.explanation.trimmingCharacters(in: .whitespacesAndNewlines)
            seriesFeedbackText = explanation.isEmpty ? "Great answer." : question.explanation
            awardSeriesExperience(SinglePlayerSupport.xpPerCorrect)
        } else {
            seriesWrongCount += 1
            seriesScore += SinglePlayerSupport.wrongPoints
            seriesFeedbackTitle = "Incorrect"
            let correctLetter = SinglePlayerSupport.letter(for: question.correctIndex)
            let explanation = question.explanation.trimmingCharacters(in: .whitespacesAndNewlines)
            var text = "Correct answer: \(correctLetter.isEmpty ? "N/A" : correctLetter)"
            if !explanation.isEmpty {
                text += "\n\n\(explanation)"
            }
            seriesFeedbackText = text
        }

        seriesFeedbackIsCorrect = isCorrect
        isSeriesFeedbackVisible = true
        seriesReviewItems.append(
            SinglePlayerSupport.reviewItem(question: question, selectedIndex: selectedIndex, isCorrect: isCorrect)
        )

        scheduleSeriesAdvance()
    }

    /// Ports `syncExpToServer` + `saveLocalExp`: bump `user_exp` locally so
    /// `RankView` sees it, then fire the `sync_game_stats.php` POST and forget it.
    private func awardSeriesExperience(_ amount: Int) {
        seriesExp += amount
        RankProgressStore.setExp(seriesExp)

        let form: [String: String] = [
            "user_id": String(userId),
            "score": String(amount),
            "total_questions": "1",
            "hp": "0",
            "is_win": "false",
            "challenge_id": "0"
        ]
        Task {
            _ = try? await HTTPClient.shared.postObject(form: form, to: .syncGameStats)
        }
    }

    /// Ports `LaunchedEffect(showFeedback)`: hold the verdict for 1.1s, then
    /// clear it and advance.
    private func scheduleSeriesAdvance() {
        seriesFeedbackTask?.cancel()
        seriesFeedbackTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: SinglePlayerSupport.feedbackDelay)
            } catch {
                return
            }
            guard let self, !Task.isCancelled else { return }
            self.isSeriesFeedbackVisible = false
            self.advanceSeriesQuestionOrFinish()
        }
    }

    /// Ports `goToNextQuestionOrFinish()`.
    private func advanceSeriesQuestionOrFinish() {
        if seriesFinishRequested {
            finishSeries()
            return
        }
        let nextIndex = currentIndex + 1
        if nextIndex < seriesQuestionIds.count && nextIndex < SinglePlayerSupport.questionCap {
            currentIndex = nextIndex
            Task { [weak self] in
                guard let self else { return }
                await self.loadSeriesQuestion(at: nextIndex)
            }
        } else {
            finishSeries()
        }
    }

    /// The Previous button. Kotlin increments past the end unchecked; iOS clamps
    /// so the run cannot walk off the id list.
    func goToPreviousSeriesQuestion() {
        guard singlePlayerSeries != nil, currentIndex > 0, !isSeriesAnswerLocked else { return }
        seriesFeedbackTask?.cancel()
        isSeriesFeedbackVisible = false
        currentIndex -= 1
        let index = currentIndex
        Task { [weak self] in
            guard let self else { return }
            await self.loadSeriesQuestion(at: index)
        }
    }

    /// The Next button shown once an answer is locked and still ahead of the
    /// attempts counter.
    func goToNextSeriesQuestion() {
        guard singlePlayerSeries != nil else { return }
        guard currentIndex + 1 < seriesQuestionIds.count else { return }
        seriesFeedbackTask?.cancel()
        isSeriesFeedbackVisible = false
        currentIndex += 1
        let index = currentIndex
        Task { [weak self] in
            guard let self else { return }
            await self.loadSeriesQuestion(at: index)
        }
    }

    /// The header close button and the "Finish Early" link both land here.
    func finishSeriesEarly() {
        guard singlePlayerSeries != nil else { return }
        seriesFinishRequested = true
        finishSeries()
    }

    /// Ports the `if (finished)` branch: write the `FINAL_TEST` history row once,
    /// then reveal the result screen.
    private func finishSeries() {
        guard !isSeriesFinished else { return }
        isSeriesFinished = true
        seriesFeedbackTask?.cancel()
        isSeriesFeedbackVisible = false

        guard !seriesHistorySaved else { return }
        seriesHistorySaved = true

        let reviewJson = (try? JSONEncoder().encode(seriesReviewItems))
            .flatMap { String(data: $0, encoding: .utf8) } ?? "[]"
        QuizHistoryManager.shared.saveHistory(
            userId: userId,
            mode: "FINAL_TEST",
            title: "Final Mock Test",
            topic: seriesTopicLabel,
            score: seriesScore,
            totalQuestions: SinglePlayerSupport.questionCap,
            correctAnswers: seriesCorrectCount,
            wrongAnswers: seriesWrongCount,
            reviewJson: reviewJson
        )
        RemoteLogger.log(
            tag: "SINGLE_PLAYER",
            message: "Session finished: score=\(seriesScore) correct=\(seriesCorrectCount) wrong=\(seriesWrongCount)"
        )
    }

    /// Ports the `LifecycleEventObserver` registered by `DisposableEffect`: coming
    /// back to the foreground mid-question costs one point, once per question.
    func registerSeriesBackgroundResume() {
        guard singlePlayerSeries != nil, !isSeriesFinished else { return }
        guard !isSeriesAnswerLocked,
              !isSeriesPenalized,
              !isLoadingSeriesQuestion,
              seriesQuestion != nil else { return }
        seriesScore -= 1
        isSeriesPenalized = true
        RemoteLogger.log(tag: "SINGLE_PLAYER", message: "Background penalty applied at question \(currentIndex + 1)")
    }

    // MARK: - Topic catalogue

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

        RemoteLogger.log(
            tag: "Quiz_Answer",
            message: "User answered Q#\(question.id) with index \(index) (Correct: \(isCorrect))"
        )

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
        } else if let q = activeQuestion {
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
        guard !isSinglePlayerMode else { return }
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
        seriesFeedbackTask?.cancel()
    }
}