import SwiftUI

/// Ports `QuizViewerActivity.fetchQuestions()`: the read-only question browser
/// `QuizManagerActivity` opens for one of the user's own quizzes.
///
/// Android POSTed `get_quiz_questions.php` with a single `quiz_id` form field,
/// read `success` off the envelope, copied the `questions` array into
/// `ArrayList<JSONObject>`, and swapped `emptyText`/`recyclerView` visibility.
/// ``StudyAPI/questions(quizId:)`` performs that exact request; the rows are
/// decoded straight into ``Question``, which already absorbs every column
/// spelling `onBindViewHolder` read by hand (`option_a…option_d`,
/// `correct_option`).
///
/// `QuizViewerActivity` needed no session: `quiz_id` is the only parameter, so
/// this screen takes no `SessionStore` either.
@MainActor
final class QuizViewerViewModel: ObservableObject {

    /// `intent.getIntExtra("QUIZ_ID", 0)`.
    let quizId: Int

    /// `questionList` — the decoded `questions` array, replaced wholesale on
    /// every load exactly as `questionList.clear()` followed by the append loop.
    @Published private(set) var state: LoadState<[Question]> = .idle

    /// Kotlin's `onCreate` called `fetchQuestions()` once and never again.
    private var hasStarted = false

    /// `QuizViewerView(quizId:)`.
    init(quizId: Int) {
        self.quizId = quizId
    }

    /// Ports `onCreate`'s single `fetchQuestions()` call — guarded so a
    /// re-appearing screen does not re-issue the request.
    func load(api: MediGyaanAPI) async {
        guard !hasStarted else { return }
        hasStarted = true
        await fetch(api: api)
    }

    /// Re-runs the request behind `ErrorStateView`'s "Try Again". Android had no
    /// retry affordance at all: a failed fetch left the empty text up forever.
    func reload(api: MediGyaanAPI) async {
        await fetch(api: api)
    }

    /// Ports the Volley `StringRequest` body: POST `quiz_id`, then branch on
    /// `success`. `success: false` and a genuine transport failure both collapse
    /// into `[]` / `.failed` here, because ``StudyAPI/questions(quizId:)``
    /// discards the envelope — see the report's BLOCKERS note.
    private func fetch(api: MediGyaanAPI) async {
        RemoteLogger.log(
            tag: "VIEWER",
            message: "fetchQuestions quiz_id=\(self.quizId)",
            metadata: ["quiz_id": String(self.quizId)]
        )
        state = .loading
        do {
            let rows = try await api.study.questions(quizId: self.quizId)
            state = .loaded(rows)
        } catch {
            let message = LoadState<[Question]>.message(for: error)
            RemoteLogger.log(
                tag: "VIEWER",
                message: "Network error: \(message)",
                metadata: ["quiz_id": String(self.quizId)]
            )
            state = .failed(message)
        }
    }
}

/// Ports `QuizViewerActivity` + `activity_quiz_viewer.xml` + `item_question_view.xml`:
/// the numbered, read-only list of a quiz's questions with the correct answer
/// shown on every card.
///
/// Kotlin reached this screen through
/// `Intent(this, QuizManagerActivity::class.java, QuizViewerActivity::class.java)
/// .putExtra("QUIZ_ID", quizId)`, so the SwiftUI host pushes it with
/// `QuizViewerView(quiz:)`.
struct QuizViewerView: View {

    @Environment(\.api) private var api

    @StateObject private var viewModel: QuizViewerViewModel

    /// Ports the `QUIZ_ID` extra directly.
    init(quizId: Int) {
        _viewModel = StateObject(wrappedValue: QuizViewerViewModel(quizId: quizId))
    }

    /// Convenience entry point for ``ScoresView``'s `onOpenQuiz` seam, which
    /// hands over the whole ``Quiz`` rather than its id.
    init(quiz: Quiz) {
        self.init(quizId: quiz.id)
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                heading
                content
            }
        }
        .task {
            await viewModel.load(api: api)
        }
        .baseScreen("QuizViewerActivity", style: .material)
        .toolbar(.hidden, for: .tabBar)
    }

    // MARK: - Chrome

    /// The `@+id/title` `TextView` from `activity_quiz_viewer.xml`: a hardcoded
    /// "Quiz Questions" at 20sp bold with 16dp padding. The activity declared no
    /// `ActionBar` title, so the label sits in the scroll content here too.
    private var heading: some View {
        Text("Quiz Questions")
            .font(AppTheme.Font.title2)
            .foregroundStyle(AppTheme.Palette.textPrimary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AppTheme.Spacing.lg)
    }

    // MARK: - List

    /// Ports the `emptyText` / `recyclerView` visibility swap. Kotlin showed the
    /// empty label for an empty `questions` array, a `success: false` envelope
    /// and both error callbacks alike; the retry affordance is the one addition,
    /// since iOS has no permanent-blank fallback.
    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Loading questions…")
                .frame(minHeight: 240)

        case .failed(let message):
            ErrorStateView(message: message) {
                Task { await viewModel.reload(api: api) }
            }
            .frame(minHeight: 240)

        case .loaded(let questions):
            if questions.isEmpty {
                EmptyStateView(
                    title: "No questions found",
                    systemImage: "questionmark.square.dashed"
                )
                .frame(minHeight: 240)
            } else {
                LazyVStack(spacing: AppTheme.Spacing.md) {
                    ForEach(Array(questions.enumerated()), id: \.offset) { index, question in
                        QuizViewerQuestionRow(position: index, question: question)
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, AppTheme.Spacing.xl)
            }
        }
    }
}

/// Ports `QuestionAdapter` + `item_question_view.xml`: the numbered question,
/// the A–D option block, and the green "Correct: X" line.
///
/// Read-only, as on Android — the card exposes no answer selection and the
/// `btnDeleteQuestion` button declared in the layout was never given a click
/// listener by `onBindViewHolder`, so it is not ported either.
private struct QuizViewerQuestionRow: View {

    /// Adapter position; Kotlin wrote `"\(position + 1). \(question)"`.
    let position: Int
    let question: Question

    var body: some View {
        CardContainer {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                // `item_question_view.xml` declared no `ImageView`; the rows are
                // rendered only when the row carries one.
                if let imageURL = question.imageURL {
                    AsyncImage(url: imageURL) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(maxWidth: .infinity, minHeight: 120)
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(maxWidth: .infinity, maxHeight: 220)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                        case .failure:
                            Label("Image could not be loaded", systemImage: "photo.badge.exclamationmark")
                                .font(AppTheme.Font.caption)
                                .foregroundStyle(AppTheme.Palette.textSecondary)
                                .frame(maxWidth: .infinity, minHeight: 60)
                        @unknown default:
                            EmptyView()
                        }
                    }
                }

                Text("\(position + 1). \(question.text.isEmpty ? "Question" : question.text)")
                    .font(AppTheme.Font.bodyBold)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineSpacing(2)
                    .fixedSize(horizontal: false, vertical: true)

                Rectangle()
                    .fill(AppTheme.Palette.optionStroke)
                    .frame(height: 1)

                VStack(spacing: 0) {
                    ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                        OptionRow(
                            text: option,
                            index: index,
                            isSelected: false,
                            reviewState: .neutral,
                            action: {}
                        )
                    }
                }

                Text("Correct: \(self.correctLetter)")
                    .font(AppTheme.Font.callout.weight(.bold))
                    .foregroundStyle(AppTheme.Palette.success)
            }
        }
    }

    /// Kotlin interpolated the raw `correct_option` string; ``Question`` has
    /// already folded that column into an index, so the A–F label is re-derived.
    private var correctLetter: String {
        let letters = ["A", "B", "C", "D", "E", "F"]
        guard question.correctIndex >= 0, question.correctIndex < letters.count else { return "—" }
        return letters[question.correctIndex]
    }
}