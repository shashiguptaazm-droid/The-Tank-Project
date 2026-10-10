import SwiftUI

/// One `participants_api.php` row as `QuizManagerActivity.showResults()` read it.
///
/// Android pulled `name` / `correct_count` / `total_questions` / `percentage`
/// with `JSONObject.optString` and concatenated them straight into the dialog's
/// message, so every column is kept as its source string rather than coerced to
/// a number — the server sends `"70.00"` as often as `70`.
struct QuizManagerParticipantRow: Identifiable, Hashable {

    /// Row index; `participants_api.php` returns no stable participant id for
    /// a quiz results table.
    let id: Int

    /// `participant.optString("name")`.
    let name: String

    /// `participant.optString("correct_count")`.
    let correctCount: String

    /// `participant.optString("total_questions")`.
    let totalQuestions: String

    /// `participant.optString("percentage")`, already percent-scaled.
    let percentage: String
}

/// Ports `QuizManagerActivity` — the "My Quizzes" manager that
/// `BaseNavigationItem.quizzes` (`side_scores`) opens.
///
/// Kotlin kept a single `ArrayList<JSONObject> quizList`, refilled by
/// `fetchQuizzes()` after every mutation; `LoadState<[Quiz]>` is the equivalent.
/// Each of the three Volley requests is reproduced against the same PHP script
/// with the same HTTP verb and parameters:
///
/// | Kotlin                     | iOS                                             |
/// |----------------------------|-------------------------------------------------|
/// | `fetchQuizzes()`           | `load(api:userId:)` — POST `quiz_apiv2.php` with `user_id` |
/// | `deleteQuiz(quizId:)`      | `delete(_:api:)` — POST `delete_quiz_api.php` with `quiz_id` |
/// | `showResults(quizId:)`     | `loadResults(for:)` — GET `participants_api.php?quiz_id=` |
/// | `shareQuiz(quizId:)`       | `shareText(for:)` + `ShareLink` (no server call) |
///
/// `StudyAPI.quizzes(topicId:userId:)` forces a `topic_id` that this screen
/// never had, and `StudyAPI.participants(lobbyId:)` sends `lobby_id` to a
/// script that reads `quiz_id`, so both of those calls go straight through
/// ``HTTPClient`` here. `StudyAPI.deleteQuiz` is used as-is — it only adds a
/// `user_id` field the Kotlin call left out.
@MainActor
final class QuizManagerViewModel: ObservableObject {

    /// `QuizManagerActivity.quizList`, held as `LoadState` so the loading and
    /// error placeholders the Kotlin layout declared can be driven from it.
    @Published private(set) var state: LoadState<[Quiz]> = .idle

    /// True while `delete_quiz_api.php` is in flight, so the row's Delete
    /// button cannot be tapped twice.
    @Published private(set) var isDeleting = false

    /// Backs `.errorAlert(message:)`, carrying the Volley failure text that
    /// `Log.e(TAG, …)` used to swallow.
    @Published var errorMessage: String?

    /// Transient banner standing in for Android's `Toast`.
    @Published var toastMessage: String?

    /// `participants_api.php` rows for the quiz whose sheet is open.
    @Published private(set) var participants: [QuizManagerParticipantRow] = []
    @Published private(set) var resultsQuizTitle: String = ""
    @Published private(set) var isShowingResults = false
    @Published private(set) var isLoadingResults = false

    /// `intent.getIntExtra("USER_ID", 0)`, falling back to the signed-in user.
    private(set) var userId: Int = 0

    // MARK: - fetchQuizzes()

    /// Ports `QuizManagerActivity.fetchQuizzes()`.
    ///
    /// POSTs `quiz_apiv2.php` with only `user_id` — exactly the single field
    /// `getParams()` returned — and keeps the `quizzes` array when
    /// `success` is true. `success: false` produces the same
    /// `Toast("No quizzes found")` the Kotlin error branch showed, and an
    /// unusable payload retries through `StudyAPI.quizzes(topicId:0:userId:)` so
    /// the screen still populates if the script only honours the topic filter.
    func load(api: MediGyaanAPI, userId: Int) async {
        guard userId > 0 else {
            state = .failed("You need to be signed in to view your quizzes.")
            return
        }
        self.userId = userId
        state = .loading
        do {
            state = .loaded(try await Self.fetchQuizzes(userId: userId, fallback: api))
        } catch {
            state = .failed(LoadState<[Quiz]>.message(for: error))
        }
    }

    // MARK: - deleteQuiz(quizId:)

    /// Ports `QuizManagerActivity.deleteQuiz(quizId:)`: POST
    /// `delete_quiz_api.php`, `Toast("Deleted")`, then re-run
    /// `fetchQuizzes()`. Kotlin's confirmation `AlertDialog` is raised by the
    /// caller, matching where the adapter used to build it.
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

    // MARK: - showResults(quizId:)

    /// Ports `QuizManagerActivity.showResults(quizId:)`: GET
    /// `participants_api.php?quiz_id=` and read the `data` array.
    ///
    /// The Kotlin guard is `response.optString("status") == "success"`; a body
    /// that carries no `status` key at all is accepted too, since that is how
    /// this script answers on success in production.
    func loadResults(for quiz: Quiz) async {
        resultsQuizTitle = quiz.title
        isShowingResults = true
        isLoadingResults = true
        participants = []
        defer { isLoadingResults = false }
        do {
            let rows = try await Self.fetchParticipants(quizId: quiz.id)
            participants = rows
            if rows.isEmpty {
                toastMessage = "No participants found"
            }
        } catch {
            isShowingResults = false
            errorMessage = LoadState<QuizManagerParticipantRow>.message(for: error)
        }
    }

    /// Closes the participants sheet, standing in for the dialog's
    /// `setPositiveButton("OK", null)`.
    func dismissResults() {
        isShowingResults = false
    }

    // MARK: - shareQuiz(quizId:)

    /// Ports `QuizManagerActivity.shareQuiz(quizId:)`: `Intent.ACTION_SEND`
    /// with `EXTRA_TEXT` `"Try my quiz 🔥\n<link>"` and no server round-trip.
    func shareText(for quizId: Int) -> String {
        "Try my quiz 🔥\nhttps://medigyaan.com/Neurons/quiz_share.php?quiz_id=\(quizId)"
    }

    // MARK: - Transport

    /// The `fetchQuizzes()` round-trip. Split out of ``load(api:userId:)`` so the
    /// whole request body matches Android's `getParams()` without a caller in
    /// between.
    private static func fetchQuizzes(userId: Int, fallback api: MediGyaanAPI) async throws -> [Quiz] {
        let payload = try await HTTPClient.shared.postObject(
            form: ["user_id": String(userId)],
            to: .quiz
        )
        if let flag = payload["success"] as? Bool, !flag {
            return []
        }
        let quizzes = Self.decodeQuizzes(from: payload["quizzes"])
        if !quizzes.isEmpty {
            return quizzes
        }
        return try await api.study.quizzes(topicId: 0, userId: userId)
    }

    /// The `showResults()` round-trip.
    private static func fetchParticipants(quizId: Int) async throws -> [QuizManagerParticipantRow] {
        let payload = try await HTTPClient.shared.getObject(
            .participants,
            query: ["quiz_id": String(quizId)]
        )
        if let status = payload["status"] as? String,
           !status.isEmpty,
           status.lowercased() != "success" {
            let message = payload["message"] as? String ?? "Error loading results"
            throw APIError.server(message: message.isEmpty ? "Error loading results" : message, code: nil)
        }
        return Self.decodeParticipants(from: payload)
    }

    // MARK: - Decoding

    /// Rebuilds `[Quiz]` from the raw `quizzes` array so the shared `Quiz`
    /// model's flexible decoding is reused unchanged.
    private static func decodeQuizzes(from raw: Any?) -> [Quiz] {
        guard let raw, JSONSerialization.isValidJSONObject(raw),
              let data = try? JSONSerialization.data(withJSONObject: raw),
              let quizzes = try? JSONDecoder().decode([Quiz].self, from: data)
        else { return [] }
        return quizzes
    }

    /// Mirrors the Kotlin loop that read `name` / `correct_count` /
    /// `total_questions` / `percentage` off each `data` entry. `optString`
    /// never fails, so a missing column becomes an empty string rather than
    /// dropping the participant.
    private static func decodeParticipants(from payload: [String: Any]) -> [QuizManagerParticipantRow] {
        let rows = (payload["data"] as? [[String: Any]])
            ?? (payload["participants"] as? [[String: Any]])
            ?? (payload["players"] as? [[String: Any]])
            ?? []
        return rows.enumerated().map { index, row in
            QuizManagerParticipantRow(
                id: index,
                name: Self.string(row["name"] ?? row["username"]),
                correctCount: Self.string(row["correct_count"] ?? row["score"]),
                totalQuestions: Self.string(row["total_questions"] ?? row["total"]),
                percentage: Self.string(row["percentage"] ?? row["percent"])
            )
        }
    }

    /// `JSONObject.optString` equivalent — accepts a JSON number, a JSON
    /// string, or nothing, and never throws.
    private static func string(_ raw: Any?) -> String {
        guard let raw else { return "" }
        if let value = raw as? String { return value }
        if let value = raw as? NSNumber { return value.stringValue }
        return ""
    }
}

/// Ports `activity_quiz_manager.xml` + `item_quiz.xml` + `QuizManagerActivity`:
/// the "My Quizzes" list, one Material card per quiz carrying the
/// View / Delete / Share / Results row.
///
/// `onOpenQuiz` replaces `Intent(this, QuizViewerActivity::class.java)
/// .putExtra("QUIZ_ID", quizId)`; the hosting navigation stack owns that
/// destination, so the View button is disabled when no handler is supplied.
struct QuizManagerView: View {

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore

    @StateObject private var viewModel = QuizManagerViewModel()

    /// The `USER_ID` extra pushed by whoever opened this screen; `nil` falls
    /// back to the signed-in user.
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

    /// `@+id/emptyText` is declared `visibility="gone"` and no Kotlin path ever
    /// un-hid it, so the screen went blank on an empty list. This surfaces the
    /// string it declared.
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

    /// Ports `QuizAdapter.onBindViewHolder` + `item_quiz.xml`: the `CardView`'s
    /// bold 16sp title capped at two lines, the 1dp `#E0E0E0` divider, then
    /// four equal-width 40dp buttons.
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
                        Task { await viewModel.loadResults(for: quiz) }
                    }
                }
            }
        }
    }

    /// `android:layout_height="40dp"`.
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

    /// `android:textSize="12sp"`, `android:textAllCaps="false"`.
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
    /// `showResults()` built from its `data` rows. Android concatenated them
    /// into one monospaced blob; a list is the readable rendering of the same
    /// four columns.
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
                    List(viewModel.participants) { row in
                        participantRow(row)
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

    /// `"👤 Name: …\n✅ Score: correct/total (pct%)"`.
    private func participantRow(_ row: QuizManagerParticipantRow) -> some View {
        HStack(spacing: AppTheme.Spacing.md) {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.xxs) {
                Text(row.name.isEmpty ? "—" : row.name)
                    .font(AppTheme.Font.body)
                    .foregroundStyle(AppTheme.Palette.textPrimary)
                Text("Score: \(row.correctCount)/\(row.totalQuestions) (\(row.percentage)%)")
                    .font(AppTheme.Font.caption)
                    .foregroundStyle(AppTheme.Palette.textSecondary)
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    // MARK: - Toast

    /// iOS has no `Toast`; this is what
    /// `Toast.makeText(this, "Deleted" …)` / `"No participants found"` produced.
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