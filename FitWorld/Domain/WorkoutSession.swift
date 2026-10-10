import Foundation

/// One logged set.
struct SetEntry: Codable, Hashable, Identifiable {
    let blockIndex: Int
    let setNumber: Int
    var reps: Int?
    var weightKg: Double?
    var durationSeconds: Int?
    var completed: Bool

    var id: String { "\(blockIndex)-\(setNumber)" }
}

/// Overall session feel, self-reported at the end.
enum SessionFeel: String, Codable, CaseIterable {
    case easy
    case justRight = "just_right"
    case hard
}

/// A recorded workout execution. Saved locally first (SwiftData), synced later.
struct WorkoutSession: Identifiable, Codable, Hashable {
    let id: UUID
    let workoutSlug: String
    let workoutName: String
    let startedAt: Date
    var endedAt: Date?
    var entries: [SetEntry]
    var feel: SessionFeel?

    var duration: TimeInterval? {
        guard let end = endedAt else { return nil }
        return max(0, end.timeIntervalSince(startedAt))
    }

    var completedSets: Int {
        entries.filter(\.completed).count
    }

    /// Rough training volume in kg·reps where weight is known; nil if none recorded.
    var volumeKg: Double? {
        let sum = entries
            .filter(\.completed)
            .compactMap { (entry: SetEntry) -> Double? in
                guard let reps = entry.reps else { return nil }
                // reps is Int — widen to Double explicitly (annotation noted line 47)
                return Double(reps) * (entry.weightKg ?? 0)
            }
            .reduce(0.0, +)
        return sum > 0 ? sum : nil
    }
}

// MARK: - Streaks (consistency, celebrated fairly — never used to shame)

enum StreakCalculator {
    /// Counts consecutive days ending today (or yesterday, so today can still be trained)
    /// that contain at least one completed session. A missed day breaks the streak;
    /// the UI must never frame that as failure (master spec §14).
    static func currentStreak(daysActive: Set<CalendarDay>, today: Date = Date(),
                              calendar: Calendar = .current) -> Int {
        var day = today
        // If today has no activity yet, the streak may still be alive from yesterday.
        if !daysActive.contains(CalendarDay(date: day, calendar: calendar)) {
            guard let yesterday = calendar.date(byAdding: .day, value: -1, to: day) else { return 0 }
            guard daysActive.contains(CalendarDay(date: yesterday, calendar: calendar)) else { return 0 }
            day = yesterday
        }

        var streak = 0
        while let candidate = daysActive.contains(
            CalendarDay(date: day, calendar: calendar)) ? day : nil {
            streak += 1
            guard let previous = calendar.date(byAdding: .day, value: -1, to: candidate) else { break }
            day = previous
        }
        return streak
    }
}

/// Calendar-day value usable as a Set member (year/month/day normalized).
struct CalendarDay: Hashable {
    let year: Int
    let month: Int
    let day: Int

    init(date: Date, calendar: Calendar = .current) {
        let c = calendar.dateComponents([.year, .month, .day], from: date)
        self.year = c.year ?? 0
        self.month = c.month ?? 0
        self.day = c.day ?? 0
    }
}
