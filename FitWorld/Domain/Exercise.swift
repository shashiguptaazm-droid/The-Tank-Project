import Foundation

// MARK: - Demo asset reference

struct DemoAsset: Codable, Hashable {
    /// e.g. "bodyweight-squat-male-front-b.lottie.json"
    let assetID: String
    let view: DemoView
    let difficulty: DifficultyLevel

    enum DemoView: String, Codable, Hashable {
        case front
        case side
        case rear
    }
}

// MARK: - Common mistake / correction pair

struct ExerciseMistake: Codable, Hashable, Identifiable {
    let mistake: String
    let correction: String

    var id: String { mistake }
}

// MARK: - Sets/reps guidance per difficulty level

struct SetsRepsGuidance: Codable, Hashable {
    var sets: Int
    var repsMin: Int?
    var repsMax: Int?
    /// For timed exercises (planks, holds).
    var durationSeconds: Int?
    var restSeconds: Int
    var loadGuidance: String?

    var repsDisplay: String? {
        if let d = durationSeconds { return "\(d)s hold" }
        guard let min = repsMin else { return nil }
        if let max = repsMax, max != min { return "\(min)–\(max) reps" }
        return "\(min) reps"
    }
}

// MARK: - Exercise demo block

struct ExerciseDemo: Codable, Hashable {
    /// Lottie assets; UI falls back to a "demo pending" placeholder when missing.
    var male: [DemoAsset]
    var female: [DemoAsset]
}

// MARK: - The canonical Exercise model (mirrors the API schema in the plan)

struct Exercise: Identifiable, Codable, Hashable {
    let id: String
    let slug: String
    let name: String
    let altNames: [String]
    let primaryMuscles: [MuscleGroup]
    let secondaryMuscles: [MuscleGroup]
    let movementPattern: MovementPattern
    let category: String
    let difficulty: DifficultyLevel
    let equipment: [Equipment]
    let impactLevel: ImpactLevel
    let spaceRequired: String
    let startPosition: String
    let steps: [String]
    let formCues: [String]
    let breathing: String
    let setsReps: [DifficultyLevel: SetsRepsGuidance]
    let commonMistakes: [ExerciseMistake]
    let easierVariantSlug: String?
    let harderVariantSlug: String?
    let contraindications: [String]
    let substitutionSlugs: [String]
    let demo: ExerciseDemo
    let reviewStatus: ReviewStatus
    let reviewedBy: String?
    let reviewDate: Date?

    // MARK: Convenience

    var displayName: String { name }

    var musclesSummary: String {
        let primary = primaryMuscles.map(\.displayName).joined(separator: ", ")
        let secondary = secondaryMuscles.map(\.displayName).joined(separator: ", ")
        if primary.isEmpty { return secondary }
        if secondary.isEmpty { return primary }
        return "\(primary) · \(secondary)"
    }

    var equipmentSummary: String {
        guard !equipment.isEmpty else { return "No equipment" }
        return equipment.map(\.displayName).joined(separator: ", ")
    }

    func guidance(for level: DifficultyLevel) -> SetsRepsGuidance? {
        setsReps[level] ?? setsReps[.beginner]
    }

    /// Assets available for a chosen demonstrator, for a chosen view.
    func assets(for gender: DemonstratorGender, view: DemoAsset.DemoView) -> [DemoAsset] {
        let list = gender == .male ? demo.male : demo.female
        return list.filter { $0.view == view }
    }
}

// MARK: - Demonstrator selection

enum DemonstratorGender: String, CaseIterable, Identifiable {
    case male
    case female

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .male: return "Male"
        case .female: return "Female"
        }
    }
}
