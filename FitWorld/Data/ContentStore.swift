import Foundation
import Observation

/// Holds all library content in memory and provides searching/filtering.
/// Loaded from bundled seed in Phase 1; API-synced snapshots merge in later.
@Observable
final class ContentStore {
    private(set) var exercises: [Exercise] = []
    private(set) var workouts: [Workout] = []
    private(set) var programs: [Program] = []

    private var exercisesBySlug: [String: Exercise] = [:]
    private var workoutsBySlug: [String: Workout] = [:]

    enum ContentError: LocalizedError {
        case loadFailed(underlying: Error)

        var errorDescription: String? {
            switch self {
            case .loadFailed(let e): return "Could not load exercise library: \(e.localizedDescription)"
            }
        }
    }

    private let loader: BundledContentLoader

    init(loader: BundledContentLoader) {
        self.loader = loader
    }

    /// Call once from the app's startup path.
    func loadBundledContent() throws {
        do {
            let exercises = try loader.loadExercises()
            let workouts = try loader.loadWorkouts()
            let programs = try loader.loadPrograms()
            install(exercises: exercises, workouts: workouts, programs: programs)
        } catch {
            throw ContentError.loadFailed(underlying: error)
        }
    }

    func install(exercises: [Exercise], workouts: [Workout], programs: [Program]) {
        self.exercises = exercises
        self.workouts = workouts
        self.programs = programs
        exercisesBySlug = Dictionary(exercises.map { ($0.slug, $0) },
                                     uniquingKeysWith: { first, _ in first })
        workoutsBySlug = Dictionary(workouts.map { ($0.slug, $0) },
                                    uniquingKeysWith: { first, _ in first })
    }

    func exercise(slug: String) -> Exercise? { exercisesBySlug[slug] }
    func workout(slug: String) -> Workout? { workoutsBySlug[slug] }

    func resolve(workout: Workout) -> (warmUp: [Exercise], blocks: [Exercise], coolDown: [Exercise]) {
        let warm = workout.warmUpSlugs.compactMap { exercise(slug: $0) }
        let blocks = workout.blocks.compactMap { exercise(slug: $0.exerciseSlug) }
        let cool = workout.coolDownSlugs.compactMap { exercise(slug: $0) }
        return (warm, blocks, cool)
    }

    // MARK: Search & filter

    struct ExerciseFilter {
        var searchText: String = ""
        var muscles: Set<MuscleGroup> = []
        var level: DifficultyLevel?
        var equipment: Equipment?
        var maxImpact: ImpactLevel?
        var excludeContraindicatedFor: Set<String> = []

        var isEmpty: Bool {
            searchText.isEmpty && muscles.isEmpty && level == nil
                && equipment == nil && maxImpact == nil
        }
    }

    func filteredExercises(_ filter: ExerciseFilter) -> [Exercise] {
        exercises.filter { ex in
            if !filter.searchText.isEmpty {
                let q = filter.searchText.lowercased()
                let hay = (ex.name + " " + ex.altNames.joined(separator: " ")).lowercased()
                if !hay.contains(q) { return false }
            }
            if !filter.muscles.isEmpty {
                let overlap = ex.primaryMuscles.contains(where: filter.muscles.contains)
                    || ex.secondaryMuscles.contains(where: filter.muscles.contains)
                if !overlap { return false }
            }
            if let level = filter.level, ex.difficulty != level { return false }
            if let equipment = filter.equipment {
                // "none"/"bodyweight" exercises match anything the user owns.
                let needsNone = ex.equipment.isEmpty
                    || ex.equipment == [.bodyweight]
                    || ex.equipment.contains(.bodyweight)
                if !needsNone && !(ex.equipment.contains(equipment)) { return false }
            }
            if let maxImpact = filter.maxImpact {
                if impactRank(ex.impactLevel) > impactRank(maxImpact) { return false }
            }
            return true
        }
        .sorted { $0.name < $1.name }
    }

    private func impactRank(_ impact: ImpactLevel) -> Int {
        switch impact {
        case .low: return 0
        case .moderate: return 1
        case .high: return 2
        }
    }

    var muscleGroupCounts: [MuscleGroup: Int] {
        var result: [MuscleGroup: Int] = [:]
        for ex in exercises {
            for m in ex.primaryMuscles {
                result[m, default: 0] += 1
            }
        }
        return result
    }
}
