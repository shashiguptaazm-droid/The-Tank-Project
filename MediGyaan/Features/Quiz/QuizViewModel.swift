import Foundation

/// Drives a quiz attempt: question delivery, timing, scoring, and sync.
///
/// Consolidates the logic spread across the Android `QuizManagerActivity`,
/// `QuizViewerActivity`, `MCQActivity`, and `TestActivity`.
///
/// The API client and user id arrive through `start(api:userId:)` rather than
/// `init`, because a `@StateObject` is constructed before the SwiftUI
/// environment (and therefore the session) is available.
@MainActor
final class QuizViewModel: ObservableObject {

    @Published private(set) var state: LoadState<QuizSession> = .idle
    @Published private(set) var currentIndex: Int = 0
    @Published private(set) var answers: [Int: AttemptAnswer] = [:]
    @Published private(set) var secondsRemaining: Int = 0
    @Published private(set) var isSubmitting = false
    @Published private(set) var result: QuizAttempt?

    private let quiz: Quiz
    private var api: MediGyaanAPI = .live
    private var userId: Int = 0
    private var startedAt = Date()
    private var timerTask: Task<Void, Never>?

    init(quiz: Quiz) {
        self.quiz = quiz
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

    // MARK: - Lifecycle

    /// Fetches the questions and starts the countdown.
    func start(api: MediGyaanAPI, userId: Int) async {
        self.api = api
        self.userId = userId

        await state.load { [api, quiz] in
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
        // Fall back to a minute per question when the quiz has no time limit.
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

    // MARK: - Answering

    /// Records an answer for a question.
    func answer(selectedIndex: Int, question: Question) {
        answers[question.id] = AttemptAnswer(
            questionId: question.id,
            selectedIndex: selectedIndex,
            correctIndex: question.correctIndex
        )
    }

    func goToNext() {
        guard !isLastQuestion else { return }
        currentIndex += 1
    }

    func goToPrevious() {
        guard currentIndex > 0 else { return }
        currentIndex -= 1
    }

    func jump(to index: Int) {
        guard questions.indices.contains(index) else { return }
        currentIndex = index
    }

    // MARK: - Submission

    /// Builds the attempt, shows the result, and syncs it to the backend.
    func finish() async {
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

        // A failed sync must not block the result screen; the Android app also
        // treated this as best-effort.
        _ = try? await api.study.syncAttempt(attempt)
    }

    deinit {
        timerTask?.cancel()
    }
}
