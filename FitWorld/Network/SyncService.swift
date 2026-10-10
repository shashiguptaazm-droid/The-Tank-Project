import Foundation
import Observation

// MARK: - Sync DTOs (mirror plan §5 API contract)

struct SyncSessionDTO: Codable {
    let id: UUID
    let workoutSlug: String
    let startedAt: Date
    let endedAt: Date?
    let entries: [SetEntry]
    let feel: SessionFeel?
}

struct SyncPushResponse: Codable {
    let accepted: [UUID]
    let conflicts: [UUID]
}

struct SyncPullResponse: Codable {
    let sessions: [SyncSessionDTO]
}

// MARK: - Service

/// Opportunistic two-way sync. Local store is always the source of truth for
/// reads; the server merges. Conflict policy: last write wins per session
/// (each device stamps its own completed entries, so real conflicts are rare).
@Observable
final class SyncService {
    private let apiClient: APIClient
    private let sessionStoreProvider: () -> SessionStore?

    var lastSyncAt: Date?
    var lastError: String?
    var isSyncing = false

    init(apiClient: APIClient, sessionStoreProvider: @escaping () -> SessionStore?) {
        self.apiClient = apiClient
        self.sessionStoreProvider = sessionStoreProvider
    }

    /// Push unsynced local sessions then pull anything newer than lastSync.
    func syncNow() async {
        guard !isSyncing else { return }
        guard let store = sessionStoreProvider() else { return }
        isSyncing = true
        defer { isSyncing = false }

        do {
            let local = await MainActor.run { store.fetchAll() }
            let outgoing = local.compactMap { session -> SyncSessionDTO? in
                guard session.endedAt != nil else { return nil } // never push partials
                return SyncSessionDTO(id: session.id,
                                      workoutSlug: session.workoutSlug,
                                      startedAt: session.startedAt,
                                      endedAt: session.endedAt,
                                      entries: session.entries,
                                      feel: session.feel)
            }
            if !outgoing.isEmpty {
                let _: SyncPushResponse = try await apiClient.post(
                    "api/v1/sync/sessions", body: outgoing)
            }

            let since = lastSyncAt.map { [URLQueryItem(name: "since", value: ISO8601DateFormatter().string(from: $0))] } ?? []
            let pull: SyncPullResponse = try await apiClient.get("api/v1/sync/sessions", query: since)
            for dto in pull.sessions {
                let domain = WorkoutSession(id: dto.id,
                                            workoutSlug: dto.workoutSlug,
                                            workoutName: dto.workoutSlug,
                                            startedAt: dto.startedAt,
                                            endedAt: dto.endedAt,
                                            entries: dto.entries,
                                            feel: dto.feel)
                await MainActor.run { store.save(domain) }
            }
            lastSyncAt = Date()
            lastError = nil
        } catch APIError.offline {
            // Normal state; nothing to do until connectivity returns.
        } catch {
            lastError = error.localizedDescription
        }
    }
}
