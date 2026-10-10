import Foundation
import Observation
import SwiftData

/// Persists executed workouts locally. Writes complete before any network
/// activity is attempted — losing a workout to a network error is a bug (§22).
/// Whole class is main-actor-isolated: SwiftData containers/contexts are
/// main-actor-only in Swift 6 concurrency, and every UI caller is on the main
/// actor anyway (View lifecycle, sheet dismissals, subscriptions).
@MainActor @Observable
final class SessionStore {
    static func makeContainer() throws -> ModelContainer {
        let schema = Schema([WorkoutSessionRecord.self])
        let config = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
        return try ModelContainer(for: config)
    }

    private let container: ModelContainer
    /// Granularity: days with ≥1 finished session count as "active".
    var daysActive: Set<CalendarDay> = []

    init(container: ModelContainer) {
        self.container = container
        recomputeDaysActive()
    }

    // MARK: Record wrapper (SwiftData model)

    @Model
    final class WorkoutSessionRecord {
        @Attribute(.unique) var sessionID: UUID
        var workoutSlug: String
        var workoutName: String
        var startedAt: Date
        var endedAt: Date?
        var entriesJSON: Data
        var feelRaw: String?

        init(session: WorkoutSession) {
            self.sessionID = session.id
            self.workoutSlug = session.workoutSlug
            self.workoutName = session.workoutName
            self.startedAt = session.startedAt
            self.endedAt = session.endedAt
            self.entriesJSON = (try? JSONEncoder().encode(session.entries)) ?? Data()
            self.feelRaw = session.feel?.rawValue
        }

        func toSession() -> WorkoutSession? {
            let entries = (try? JSONDecoder().decode([SetEntry].self, from: entriesJSON)) ?? []
            return WorkoutSession(id: sessionID,
                                  workoutSlug: workoutSlug,
                                  workoutName: workoutName,
                                  startedAt: startedAt,
                                  endedAt: endedAt,
                                  entries: entries,
                                  feel: feelRaw.flatMap(SessionFeel.init(rawValue:)))
        }
    }

    // MARK: Queries

    func fetchAll() -> [WorkoutSession] {
        let context = container.mainContext
        let descriptor = FetchDescriptor<WorkoutSessionRecord>(
            sortBy: [SortDescriptor(\.startedAt, order: .reverse)])
        let records = (try? context.fetch(descriptor)) ?? []
        return records.compactMap { $0.toSession() }
    }

    func sessions(in interval: Interval) -> [WorkoutSession] {
        fetchAll().filter { $0.startedAt >= interval.start && $0.startedAt <= interval.end }
    }

    struct Interval {
        let start: Date
        let end: Date
    }

    // MARK: Writes

    func save(_ session: WorkoutSession) {
        let context = container.mainContext
        let existing = try? context.fetch(descriptor(for: session.id)).first
        if let existing = existing {
            existing.endedAt = session.endedAt
            existing.entriesJSON = (try? JSONEncoder().encode(session.entries)) ?? Data()
            existing.feelRaw = session.feel?.rawValue
        } else {
            context.insert(WorkoutSessionRecord(session: session))
        }
        try? context.save()
        recomputeDaysActive()
    }

    private func descriptor(for id: UUID) -> FetchDescriptor<WorkoutSessionRecord> {
        FetchDescriptor(predicate: #Predicate { $0.sessionID == id })
    }

    func delete(sessionID: UUID) {
        let context = container.mainContext
        if let record = try? context.fetch(descriptor(for: sessionID)).first {
            context.delete(record)
            try? context.save()
            recomputeDaysActive()
        }
    }

    // MARK: Derived

    private func recomputeDaysActive() {
        var set: Set<CalendarDay> = []
        for session in fetchAll() where session.endedAt != nil {
            set.insert(CalendarDay(date: session.startedAt))
        }
        daysActive = set
    }

    var currentStreak: Int {
        StreakCalculator.currentStreak(daysActive: daysActive)
    }
}
