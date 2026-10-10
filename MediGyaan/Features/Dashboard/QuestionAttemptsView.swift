import SwiftUI

/// Navigation payload for ``QuestionAttemptsView``.
///
/// Ports the two values `QuestionAttemptsActivity.onCreate` pulled off its
/// intent: `intent.getIntExtra("question_id", 0)` and the `userId` that
/// `SharedQuestionsActivity` had in hand when it built the
/// `Intent(this, QuestionAttemptsActivity::class.java)` that carried
/// `putExtra("question_id", questionId)`.
///
/// Android passed the question id alone and recomputed the rest of the screen's
/// arguments itself; this type makes the pair explicit so a
/// `NavigationStack` destination can carry it. See the orchestrator note in
/// `DashboardView` for the `DrawerDestination` case that adopts it.
struct QuestionAttemptsRoute: Hashable {

    /// `question_id` — the shared question whose peer attempts are listed.
    let questionId: Int

    /// `user_id` — the signed-in user whose shared-question view is drilled into.
    let userId: Int

    init(questionId: Int, userId: Int) {
        self.questionId = questionId
        self.userId = userId
    }
}

/// Ports `QuestionAttemptsActivity.loadAttempts()` — the single
/// `JsonObjectRequest` GET against
/// `https://medigyaan.com/Neurons/attempts_api.php?question_id=$questionId&user_id=$userId`
/// that reads `attempts[]` out of the response.
///
/// Android drove the request straight from the activity and mutated its
/// `ArrayList<AttemptModel>` on the Volley worker thread before calling
/// `adapter.notifyDataSetChanged()`; the replacement here keeps the fetch on the
/// main actor and publishes the parsed rows into a `LoadState`, which is what
/// the shared `LoadingStateView` / `EmptyStateView` / `errorAlert` trio reads.
///
/// The wire shape is unchanged: each element of `attempts` decodes through
/// ``QuestionAttemptPeer`` (a port of Android's `AttemptModel`), which takes
/// `temporary_user_id`, `user_answer`, `is_correct`, `name` and `created_at`.
/// The endpoint is the same `APIConfig.Endpoint.attempts` case
/// (`attempts_api.php`) that `SocialAPI.questionAttempts` already speaks to,
/// and the query keys stay `question_id` and `user_id`.
@MainActor
final class QuestionAttemptsViewModel: ObservableObject {

    /// `intent.getIntExtra("question_id", 0)`.
    let questionId: Int

    /// The attempt rows, or `nil` while the first fetch is in flight and after a
    /// failure. `LoadState` is what `LoadingStateView` and `EmptyStateView` hang
    /// off; Android had neither, leaving a blank list until Volley answered.
    @Published private(set) var state: LoadState<[QuestionAttemptPeer]> = .idle

    /// Ports the Volley `ErrorListener` arm of `loadAttempts`, which showed
    /// `Toast.makeText(this, "Error loading attempts", Toast.LENGTH_SHORT)`.
    /// iOS has no Toast, so the text is surfaced through `.errorAlert(message:)`
    /// and the message is whatever `LoadState.message(for:)` derives from the
    /// thrown `APIError`.
    @Published var errorMessage: String?

    init(questionId: Int) {
        self.questionId = questionId
    }

    /// `list` in the Kotlin activity, exposed for previews and tests.
    var attempts: [QuestionAttemptPeer] {
        state.value ?? []
    }

    /// Fetches the attempts for ``questionId``.
    ///
    /// Mirrors `loadAttempts(questionId, userId)`: one GET, no retry loop, no
    /// pagination. Android caught nothing — a non-2xx reply or a JSON object
    /// missing the `attempts` key both fell into the same Toast — so this does
    /// the same and reports the failure once.
    func load(userId: Int, api: MediGyaanAPI) async {
        RemoteLogger.log(
            tag: "QuestionAttempts_Load",
            message: "Fetching peer attempts for question \(questionId)"
        )
        errorMessage = nil
        state = .loading
        do {
            let items = try await api.social.questionAttempts(
                questionId: questionId,
                userId: userId
            )
            state = .loaded(items)
        } catch {
            state = .idle
            errorMessage = LoadState<Never>.message(for: error)
        }
    }
}

/// Ports `QuestionAttemptsActivity.kt` — the per-question peer-attempts list
/// behind `SharedQuestionsActivity`'s "Peer Breakdown" tap.
///
/// * `setContentView(R.layout.activity_attempts)` — a bold "Attempts" heading,
///   a padded `RecyclerView` and the shared bottom navigation pinned to the
///   bottom, with `setupAppBottomNavigation(bottomNavigation, R.id.nav_home)`
///   marking Home as selected.
/// * `loadAttempts()` — see ``QuestionAttemptsViewModel``.
/// * `AttemptAdapter` / `item_attempt.xml` — one card per attempt, rendered by
///   the shared ``AttemptRow``.
///
/// Android's layout supplied its own bottom bar; here the screen is pushed
/// inside the Home tab's `NavigationStack` so ``BottomNavBar`` stays visible, and
/// the `"Attempts"` `TextView` becomes the navigation title.
struct QuestionAttemptsView: View {

    /// `user_id` when the caller already knows it (`QuestionAttemptsRoute`);
    /// `nil` falls back to `SessionStore.userId`, standing in for the placeholder
    /// the Kotlin activity shipped with — `val userId = "YOUR_USER_ID"`.
    private let userIdOverride: Int?

    @Environment(\.api) private var api
    @EnvironmentObject private var session: SessionStore

    @StateObject private var viewModel: QuestionAttemptsViewModel

    init(questionId: Int, userId: Int? = nil) {
        self.userIdOverride = userId
        _viewModel = StateObject(wrappedValue: QuestionAttemptsViewModel(questionId: questionId))
    }

    var body: some View {
        content
            .screenBackground()
            .navigationTitle("Attempts")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task { await reload() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .foregroundStyle(AppTheme.Palette.primary)
                    }
                    .accessibilityLabel("Reload attempts")
                }
            }
            .errorAlert(message: $viewModel.errorMessage)
            .task {
                await reload()
            }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .idle, .loading:
            LoadingStateView(message: "Loading attempts…")

        case let .failed(message):
            ErrorStateView(message: message) {
                Task { await reload() }
            }

        case let .loaded(attempts):
            if attempts.isEmpty {
                EmptyStateView(
                    title: "No Attempts Yet",
                    message: "Share this question with your study group to see who has attempted it.",
                    systemImage: "person.crop.circle.badge.questionmark"
                )
            } else {
                attemptsList(attempts)
            }
        }
    }

    private func attemptsList(_ attempts: [QuestionAttemptPeer]) -> some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: AppTheme.Spacing.md) {
                ForEach(attempts) { attempt in
                    AttemptRow(attempt: attempt)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
            .padding(.vertical, AppTheme.Spacing.md)
        }
        .refreshable {
            await reload()
        }
    }

    @MainActor
    private func reload() async {
        await viewModel.load(userId: userIdOverride ?? session.userId, api: api)
    }
}