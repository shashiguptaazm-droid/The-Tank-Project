import Foundation

/// Backs `DashboardView`. Replaces `DashboardActivity`'s inline Volley calls.
///
/// The API client and user id arrive through `load(api:userId:)` rather than
/// `init`, because a `@StateObject`'s wrapped value is get-only — the view
/// cannot rebuild the model once the SwiftUI environment (and therefore the
/// session) becomes available.
@MainActor
final class DashboardViewModel: ObservableObject {

    @Published private(set) var state: LoadState<DashboardStats> = .idle
    @Published private(set) var attempts: [AttemptSummary] = []

    /// Loads the summary and recent attempts concurrently; the summary is the
    /// only one whose failure is fatal to the screen.
    func load(api: MediGyaanAPI, userId: Int) async {
        guard userId > 0 else {
            state = .failed("You need to be signed in to view your dashboard.")
            return
        }

        async let statsResult = fetchStats(api: api, userId: userId)
        async let attemptsResult = fetchAttempts(api: api, userId: userId)

        state = await statsResult
        attempts = await attemptsResult
    }

    private func fetchStats(api: MediGyaanAPI, userId: Int) async -> LoadState<DashboardStats> {
        var state: LoadState<DashboardStats> = .loading
        await state.load { try await api.study.dashboard(userId: userId) }
        return state
    }

    private func fetchAttempts(api: MediGyaanAPI, userId: Int) async -> [AttemptSummary] {
        (try? await api.study.attempts(userId: userId)) ?? []
    }
}
