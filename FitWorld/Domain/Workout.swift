import Foundation

/// A single exercise assignment inside a workout.
struct ExerciseBlock: Codable, Hashable, Identifiable {
    let exerciseSlug: String
    var sets: Int
    var repsMin: Int?
    var repsMax: Int?
    /// Timed exercises instead of reps.
    var durationSeconds: Int?
    var restSeconds: Int
    var tempo: String?
    var notes: String?

    var id: String {
        var key = exerciseSlug
        if let repsMin { key += "-r\(repsMin)" }
        if let repsMax { key += "-R\(repsMax)" }
        if let durationSeconds { key += "-d\(durationSeconds)" }
        return key
    }

    var targetDisplay: String {
        if let d = durationSeconds { return "\(d)s × \(sets)" }
        switch (repsMin, repsMax) {
        case let (min?, max?) where min != max: return "\(min)–\(max) × \(sets)"
        case let (min?, _): return "\(min) × \(sets)"
        default: return "\(sets) sets"
        }
    }
}

/// A named, authored session made of blocks.
struct Workout: Identifiable, Codable, Hashable {
    let id: String
    let slug: String
    let name: String
    let goal: TrainingGoal?
    let level: DifficultyLevel
    let sessionLengthMinutes: Int
    let locationHint: TrainingLocation?
    let blocks: [ExerciseBlock]
    let warmUpSlugs: [String]
    let coolDownSlugs: [String]
    let reviewStatus: ReviewStatus
}

/// A generated calendar program made of weekly templates.
struct Program: Identifiable, Codable, Hashable {
    enum Duration: String, Codable, CaseIterable {
        case days7 = "7"
        case days14 = "14"
        case days30 = "30"
        case days60 = "60"
        case days90 = "90"

        var dayCount: Int { Int(rawValue) ?? 7 }
    }

    struct ProgramDay: Codable, Hashable, Identifiable {
        let dayIndex: Int
        /// Nil workoutSlug == recovery/rest day.
        let workoutSlug: String?
        let isDeload: Bool

        var id: Int { dayIndex }
        var isRestDay: Bool { workoutSlug == nil }
    }

    struct ProgramWeek: Codable, Hashable {
        let weekIndex: Int
        let days: [ProgramDay]
        let isDeload: Bool
    }

    let id: String
    let slug: String
    let name: String
    let goal: TrainingGoal
    let level: DifficultyLevel
    let duration: Duration
    let locationHint: TrainingLocation?
    let weeks: [ProgramWeek]
    let progressionRules: String
    let reviewStatus: ReviewStatus

    var trainingDaysPerWeek: Int {
        guard let first = weeks.first else { return 0 }
        return first.days.filter { !$0.isRestDay }.count
    }
}
