import Foundation

/// Backs `DashboardView`. Replaces `DashboardActivity`'s inline Volley calls.
@MainActor
final class DashboardViewModel: ObservableObject {

    @Published private(set) var state: LoadState<DashboardStats> = .idle
    @Published private(set) var attempts: [AttemptSummary] = []

    private let api: MediGyaanAPI
    private let userId: Int

    init(api: MediGyaanAPI, userId: Int) {
        self.api = api
        self.userId = userId
    }

    /// Loads the summary and recent attempts concurrently; the summary is the
    /// only one whose failure is fatal to the screen.
    func load() async {
        guard userId > 0 else {
            state = .failed("You need to be signed in to view your dashboard.")
            return
        }

        async let statsResult = fetchStats()
        async let attemptsResult = fetchAttempts()

        let stats = await statsResult
        state = stats
        attempts = await attemptsResult
    }

    private func fetchStats() async -> LoadState<DashboardStats> {
        var state: LoadState<DashboardStats> = .loading
        await state.load { [api, userId] in
            try await api.study.dashboard(userId: userId)
        }
        return state
    }

    private func fetchAttempts() async -> [AttemptSummary] {
        (try? await api.study.attempts(userId: userId)) ?? []
    }
}
