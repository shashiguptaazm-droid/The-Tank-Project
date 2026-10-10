import Foundation

// MARK: - Difficulty

enum DifficultyLevel: String, Codable, CaseIterable, Identifiable {
    case beginner
    case intermediate
    case advanced

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .beginner: return "Beginner"
        case .intermediate: return "Intermediate"
        case .advanced: return "Advanced"
        }
    }

    var symbolName: String {
        switch self {
        case .beginner: return "1.circle"
        case .intermediate: return "2.circle"
        case .advanced: return "3.circle"
        }
    }
}

// MARK: - Training location

enum TrainingLocation: String, Codable, CaseIterable, Identifiable {
    case home
    case gym
    case outdoor

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .home: return "Home"
        case .gym: return "Gym"
        case .outdoor: return "Outdoors"
        }
    }
}

// MARK: - Impact level

enum ImpactLevel: String, Codable, CaseIterable {
    case low
    case moderate
    case high
}

// MARK: - Review status (content governance)

enum ReviewStatus: String, Codable {
    case draft
    case inReview = "in_review"
    case approved
    case published
    case archived
}

// MARK: - Primary goals

enum TrainingGoal: String, Codable, CaseIterable, Identifiable {
    case generalFitness = "general_fitness"
    case strength
    case muscleGrowth = "muscle_growth"
    case endurance
    case flexibility
    case weightManagement = "weight_management"
    case mobility
    case stressReduction = "stress_reduction"
    case danceFitness = "dance_fitness"
    case healthyAging = "healthy_aging"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .generalFitness: return "General fitness"
        case .strength: return "Strength"
        case .muscleGrowth: return "Muscle growth"
        case .endurance: return "Endurance"
        case .flexibility: return "Flexibility"
        case .weightManagement: return "Weight management"
        case .mobility: return "Mobility"
        case .stressReduction: return "Stress reduction"
        case .danceFitness: return "Dance fitness"
        case .healthyAging: return "Healthy aging"
        }
    }
}

// MARK: - Equipment

enum Equipment: String, Codable, CaseIterable, Identifiable {
    case none
    case bodyweight
    case dumbbells
    case barbell
    case kettlebell
    case resistanceBands = "resistance_bands"
    case bench
    case pullUpBar = "pull_up_bar"
    case dipStation = "dip_station"
    case machine
    case cable
    case suspensionTrainer = "suspension_trainer"
    case medicineBall = "medicine_ball"
    case householdObject = "household_object"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .none: return "None"
        case .bodyweight: return "Bodyweight"
        case .dumbbells: return "Dumbbells"
        case .barbell: return "Barbell"
        case .kettlebell: return "Kettlebell"
        case .resistanceBands: return "Resistance bands"
        case .bench: return "Bench"
        case .pullUpBar: return "Pull-up bar"
        case .dipStation: return "Dip station"
        case .machine: return "Machine"
        case .cable: return "Cable"
        case .suspensionTrainer: return "Suspension trainer"
        case .medicineBall: return "Medicine ball"
        case .householdObject: return "Household object"
        }
    }
}

// MARK: - Muscle groups

enum MuscleGroup: String, Codable, CaseIterable, Identifiable {
    case chest
    case back
    case shoulders
    case arms
    case core
    case glutes
    case quadriceps
    case hamstrings
    case calves
    case hipFlexors = "hip_flexors"
    case adductors
    case forearms
    case rotatorCuff = "rotator_cuff"
    case fullBody = "full_body"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .chest: return "Chest"
        case .back: return "Back"
        case .shoulders: return "Shoulders"
        case .arms: return "Arms"
        case .core: return "Core"
        case .glutes: return "Glutes"
        case .quadriceps: return "Quadriceps"
        case .hamstrings: return "Hamstrings"
        case .calves: return "Calves"
        case .hipFlexors: return "Hip flexors"
        case .adductors: return "Adductors"
        case .forearms: return "Forearms"
        case .rotatorCuff: return "Rotator cuff"
        case .fullBody: return "Full body"
        }
    }

    var systemImage: String {
        switch self {
        case .chest: return "figure.strengthtraining.traditional"
        case .back: return "figure.archery"
        case .shoulders: return "figure.arms.open"
        case .arms: return "figure.strengthtraining.functional"
        case .core: return "figure.core.training"
        case .glutes, .quadriceps, .hamstrings, .calves, .hipFlexors, .adductors:
            return "figure.walk"
        case .forearms, .rotatorCuff: return "hand.raised.fill"
        case .fullBody: return "figure.mixed.cardio"
        }
    }
}

// MARK: - Movement patterns

enum MovementPattern: String, Codable, CaseIterable {
    case push
    case pull
    case squat
    case hinge
    case lunge
    case carry
    case rotate
    case brace
    case jump
    case locomotion
}
