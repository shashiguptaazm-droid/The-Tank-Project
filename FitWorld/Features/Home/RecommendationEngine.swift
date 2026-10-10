import Foundation

/// Phase 1 rule-based recommender. AI coach personalization arrives in Phase 5;
/// these rules adapt to equipment, level and goal without pretending to be clever.
enum RecommendationEngine {
    static func suggestWorkout(content: ContentStore, profile: UserProfile) -> Workout? {
        let candidates = content.workouts

        guard !candidates.isEmpty else { return nil }

        // Scoring: goal match > level match > equipment availability > shortest fit
        let goal = profile.primaryGoal
        let level = profile.fitnessLevel
        let preferredMinutes = averageAvailability(profile)

        func score(_ workout: Workout) -> Int {
            var s = 0
            if workout.goal == goal { s += 40 }
            if workout.level == level { s += 30 }
            if workout.sessionLengthMinutes <= max(10, preferredMinutes) { s += 20 }
            // Favor equipment the user actually has.
            if let location = profile.trainingLocation, workout.locationHint == location { s += 10 }
            return s
        }

        return candidates.max { score($0) < score($1) }
    }

    static func averageAvailability(_ profile: UserProfile) -> Int {
        guard !profile.weeklyAvailabilityMinutes.isEmpty else { return 30 }
        return profile.weeklyAvailabilityMinutes.reduce(0, +) / profile.weeklyAvailabilityMinutes.count
    }
}
