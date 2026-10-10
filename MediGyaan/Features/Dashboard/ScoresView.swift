import SwiftUI

/// Ports `QuizManagerActivity`: the "My Quizzes" manager reached from the
/// `side_scores` drawer row (`R.id.side_scores`), which Android launched as
/// `Intent(this, QuizManagerActivity::class.java)` with the `USER_ID` extra.
///
/// The Kotlin class held a single `ArrayList<JSONObject> quizList`, refilled on
/// every mutation; `LoadState<[Quiz]>` is the equivalent, and `.failed` doubles
/// as the `Toast`/`Log.e` channel the three Volley error callbacks wrote to.
@MainActor
final class ScoresViewModel: ObservableObject {

    /// `quiz_apiv2.php` results, keyed by `quiz_id`.
    @Published private(set) var state: LoadState<[Quiz]> = .idle

    /// True while `delete_quiz_api.php` is in flight, so the row's Delete
    /// button cannot be tapped twice.
    @Published private(set) var isDeleting = false

    /// Backs `.errorAlert(message:)`, and carries the row id of the quiz whose
    /// participants sheet is open — `nil` when the sheet is closed.
    @Published var errorMessage: String?

    /// Transient banner standing in for Android's `Toast`.
    @Published var toastMessage: String?

    /// `participants_api.php` rows for the quiz whose sheet is open.
    @Published private(set) var participants: [Participant] = []
    @Published private(set) var resultsQuizTitle: String = ""
    @Published private(set) var isShowingResults = false
    @Published private(set) var isLoadingResults = false

    /// `intent.getIntExtra("USER_ID", 0)`.
    private(set) var userId: Int = 0

    /// Ports `QuizManagerActivity.onCreate()`'s `fetchQuizzes()`:
    /// POST `quiz_apiv2.php` with `user_id`, keep the `quizzes` array on
    /// `success`, otherwise show the empty state.
    func load(api: MediGyaanAPI, userId: Int) async {
        guard userId > 0 else {
            state = .failed("You need to be signed in to view your quizzes.")
            return
        }
        self.userId = userId
        state = .loading
        do {
            let quizzes = try await api.study.quizzes(topicId: 0, userId: userId)
            state = .loaded(quizzes)
        } catch {
            state = .failed(LoadState<[Quiz]>.message(for: error))
        }
    }

    /// Ports `deleteQuiz(quizId:)`: POST `delete_quiz_api.php` with `quiz_id`,
    /// then re-run `fetchQuizzes()`. Kotlin raised its confirmation
    /// `AlertDialog` in the adapter; that prompt lives in the view.
    func delete(_ quizId: Int, api: MediGyaanAPI) async {
        guard !isDeleting else { return }
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await api.study.deleteQuiz(quizId: quizId, userId: userId)
            toastMessage = "Deleted"
            await load(api: api, userId: userId)
        } catch {
            errorMessage = "Delete failed"
        }
    }

    /// Ports `showResults(quizId:)`: GET `participants_api.php` and render the
    /// `data` array as the "Quiz Participants" dialog body.
    ///
    /// Kotlin read `name` / `correct_count` / `total_questions` / `percentage`
    /// with `optString` off `?quiz_id=`. `StudyAPI.participants` targets the same
    /// script through its lobby path and returns the shared ``Participant``
    /// model, so `correct_count` surfaces as that model's `score` and the
    /// `total`/`percentage` columns are dropped.
    func loadResults(for quiz: Quiz, api: MediGyaanAPI) async {
        resultsQuizTitle = quiz.title
        isShowingResults = true
        isLoadingResults = true
        participants = []
        defer { isLoadingResults = false }
        do {
            let rows = try await api.study.participants(lobbyId: String(quiz.id))
            participants = rows
            if rows.isEmpty {
                toastMessage = "No participants found"
            }
        } catch {
            isShowingResults = false
            errorMessage = LoadState<[Quiz]>.message(for: error)
        }
    }

    /// Closes the participants sheet, standing in for the dialog's
    /// `setPositiveButton("OK", null)`.
    func dismissResults() {
        isShowingResults = false
    }

    /// Ports `shareQuiz(quizId:)`. Kotlin fired
    /// `Intent.ACTION_SEND` with `EXTRA_TEXT` and no server round-trip; the
    /// `shareQuiz` endpoint is deliberately not called here.
    func shareText(for quizId: Int) -> String {
        "Try my quiz 🔥\nhttps://medigyaan.com/Neurons/quiz_share.php?quiz_id=\(quizId)"
    }
}

/// Ports `activity_quiz_manager.xml` + `item_quiz.xml` + `QuizManagerActivity`:
/// the Material-themed "My Quizzes" list, one `CardView` per quiz with the
/// View / Delete / Share / Results button row.
///
/// `onOpenQuiz` replaces `Intent(this, QuizViewerActivity::class.java)
/// .putExtra("QUIZ_ID", quizId)`; the hosting navigation stack owns that
/// destination, so the button is disabled when no handler is supplied.
struct ScoresView: View {

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore

    @StateObject private var viewModel = ScoresViewModel()

    /// The `USER_ID` extra passed by whoever pushed this screen; `nil` falls
    /// back to the signed-in user, matching Android's `getIntExtra(.., 0)`
    /// followed by the backend's own user-1 default.
    private let requestedUserId: Int?

    private let onOpenQuiz: ((Quiz) -> Void)?

    init(userId: Int? = nil, onOpenQuiz: ((Quiz) -> Void)? = nil) {
        self.requestedUserId = userId
        self.onOpenQuiz = onOpenQuiz
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                heading
                content
            }
        }
        .task {
            await viewModel.load(api: api, userId: requestedUserId ?? session.userId)
        }
        .baseScreen("QuizManagerActivity", style: .material)
        .overlay(alignment: .bottom) { toast }
        .confirmationDialog(
            "Delete Quiz",
            isPresented: Binding(
                get: { pendingDelete != nil },
                set: { if !$0 { pendingDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Yes", role: .destructive) {
                guard let quiz = pendingDelete else { return }
                pendingDelete = nil
                Task { await viewModel.delete(quiz.id, api: api) }
            }
            Button("No", role: .cancel) { pendingDelete = nil }
        } message: {
            Text("Are you sure?")
        }
        .sheet(isPresented: $viewModel.isShowingResults) {
            resultsSheet
        }
        .errorAlert(message: $viewModel.errorMessage)
    }

    // MARK: - Chrome

    /// The `@+id/title` `TextView` from `activity_quiz_manager.xml`: 20sp bold
    /// with 16dp padding.
    private var heading: some View {
        Text("My Quizzes")
            .font(AppTheme.Font.title2)
            .foregroundStyle(AppTheme.Palette.textPrimary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(AppTheme.Spacing.lg)
    }

    // MARK: - List

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Loading quizzes…")
                .frame(minHeight: 240)
        case .failed(let message):
            ErrorStateView(message: message) {
                Task { await viewModel.load(api: api, userId: requestedUserId ?? session.userId) }
            }
            .frame(minHeight: 240)
        case .loaded(let quizzes):
            if quizzes.isEmpty {
                // Kotlin never un-hid `R.id.emptyText`, so the list simply went
                // blank; the string it declared is what this shows.
                EmptyStateView(
                    title: "No quizzes found",
                    message: "Create a quiz from a topic to see it here.",
                    systemImage: "square.stack.3d.up.slash"
                )
                .frame(minHeight: 240)
            } else {
                LazyVStack(spacing: AppTheme.Spacing.sm) {
                    ForEach(quizzes) { quiz in
                        quizCard(quiz)
                    }
                }
                .padding(.horizontal, AppTheme.Spacing.xl)
                .padding(.bottom, AppTheme.Spacing.xl)
            }
        }
    }

    /// Ports `QuizAdapter.onBindViewHolder` + `item_quiz.xml`: bold 16sp title
    /// capped at two lines, a 1dp divider, then four equal-width buttons.
    private func quizCard(_ quiz: Quiz) -> some View {
        CardContainer(padding: AppTheme.Spacing.md) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.md) {
                Text(quiz.title.isEmpty ? "Quiz Name" : quiz.title)
                    .font(AppTheme.Font.bodyBold)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                Rectangle()
                    .fill(AppTheme.Palette.optionStroke)
                    .frame(height: 1)

                HStack(spacing: AppTheme.Spacing.sm) {
                    actionButton(title: "View", tint: AppTheme.Palette.primary) {
                        onOpenQuiz?(quiz)
                    }
                    .disabled(onOpenQuiz == nil)
                    .opacity(onOpenQuiz == nil ? 0.4 : 1)

                    actionButton(title: "Delete", tint: AppTheme.Palette.danger) {
                        pendingDelete = quiz
                    }
                    .disabled(viewModel.isDeleting)

                    ShareLink(item: viewModel.shareText(for: quiz.id)) {
                        actionButtonLabel(title: "Share", tint: AppTheme.Palette.info)
                    }

                    actionButton(title: "Results", tint: AppTheme.Palette.success) {
                        Task { await viewModel.loadResults(for: quiz, api: api) }
                    }
                }
            }
        }
    }

    /// `android:layout_height="40dp"`, `android:textSize="12sp"`.
    private static let actionHeight: CGFloat = 40

    private func actionButton(
        title: String,
        tint: Color,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            actionButtonLabel(title: title, tint: tint)
        }
    }

    private func actionButtonLabel(title: String, tint: Color) -> some View {
        Text(title)
            .font(AppTheme.Font.caption)
            .foregroundStyle(tint)
            .frame(maxWidth: .infinity)
            .frame(height: Self.actionHeight)
            .background(
                RoundedRectangle(
                    cornerRadius: AppTheme.Radius.button,
                    style: .continuous
                )
                .fill(tint.opacity(0.12))
            )
    }

    // MARK: - Participants sheet

    /// Ports the `AlertDialog` titled "Quiz Participants" that
    /// `showResults()` built from its `data` rows. Android concatenated the rows
    /// into one monospaced message string; a list is the readable iOS
    /// equivalent of the same data.
    private var resultsSheet: some View {
        NavigationStack {
            Group {
                if viewModel.isLoadingResults {
                    LoadingStateView(message: "Loading participants…")
                } else if viewModel.participants.isEmpty {
                    EmptyStateView(
                        title: "No participants found",
                        systemImage: "person.2.slash"
                    )
                } else {
                    List(viewModel.participants) { participant in
                        participantRow(participant)
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle(viewModel.resultsQuizTitle.isEmpty ? "Quiz Participants" : viewModel.resultsQuizTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("OK") { viewModel.dismissResults() }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func participantRow(_ participant: Participant) -> some View {
        HStack(spacing: AppTheme.Spacing.md) {
            AvatarView(url: participant.avatarURL, name: participant.name, size: 36)
            VStack(alignment: .leading, spacing: 2) {
                Text(participant.name.isEmpty ? "—" : participant.name)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text("Score: \(participant.score)")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    // MARK: - Toast

    /// iOS has no `Toast`; this is the `Toast.makeText(...)` feedback
    /// "Deleted" / "No participants found" produced.
    private var toast: some View {
        Group {
            if let message = viewModel.toastMessage {
                Text(message)
                    .font(AppTheme.Font.callout)
                    .foregroundStyle(AppTheme.Palette.onPrimary)
                    .padding(.horizontal, AppTheme.Spacing.lg)
                    .padding(.vertical, AppTheme.Spacing.md)
                    .background(
                        Capsule().fill(AppTheme.Palette.primaryDark)
                    )
                    .padding(.bottom, AppTheme.Spacing.xl)
                    .transition(.opacity)
                    .task(id: message) {
                        try? await Task.sleep(nanoseconds: 2_000_000_000)
                        if viewModel.toastMessage == message {
                            viewModel.toastMessage = nil
                        }
                    }
            }
        }
        .animation(.easeOut(duration: 0.2), value: viewModel.toastMessage)
    }

    // MARK: - State

    /// The quiz awaiting `AlertDialog.Builder(...).setTitle("Delete Quiz")`.
    @State private var pendingDelete: Quiz?
}
