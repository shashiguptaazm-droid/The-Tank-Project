import Foundation

/// Everything collected during onboarding (§2 of the master spec).
/// Optional questions are genuinely optional — nil means "user skipped".
struct UserProfile: Codable, Hashable {
    var ageRange: AgeRange?
    var country: String?
    var preferredLanguage: String?
    var usesMetric: Bool

    var heightCm: Double?
    var weightKg: Double?

    var primaryGoal: TrainingGoal?
    var secondaryGoals: [TrainingGoal]?
    var fitnessLevel: DifficultyLevel

    var trainingLocation: TrainingLocation?
    var availableEquipment: [Equipment]

    /// Minutes available per weekday, index 0 = Monday … 6 = Sunday. 0 = unavailable.
    var weeklyAvailabilityMinutes: [Int]

    var dietaryPreferences: [String]
    var allergies: [String]

    // Accessibility preferences (§20)
    var prefersSeatedWorkouts: Bool
    var prefersLowImpact: Bool
    var prefersCaptions: Bool
    var prefersAudioGuidance: Bool
    var prefersReducedMotion: Bool

    // Reserved for the subscriptions phase; no StoreKit in Phase 1.
    var entitlements: [String]

    init() {
        self.ageRange = nil
        self.country = nil
        self.preferredLanguage = nil
        self.usesMetric = true
        self.heightCm = nil
        self.weightKg = nil
        self.primaryGoal = nil
        self.secondaryGoals = nil
        self.fitnessLevel = .beginner
        self.trainingLocation = nil
        self.availableEquipment = [.bodyweight]
        self.weeklyAvailabilityMinutes = Array(repeating: 30, count: 7)
        self.dietaryPreferences = []
        self.allergies = []
        self.prefersSeatedWorkouts = false
        self.prefersLowImpact = false
        self.prefersCaptions = false
        self.prefersAudioGuidance = true
        self.prefersReducedMotion = false
        self.entitlements = ["free"]
    }
}

enum AgeRange: String, Codable, CaseIterable, Identifiable {
    case under18 = "under_18"
    case range18to29 = "18_29"
    case range30to44 = "30_44"
    case range45to59 = "45_59"
    case over60 = "over_60"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .under18: return "Under 18"
        case .range18to29: return "18–29"
        case .range30to44: return "30–44"
        case .range45to59: return "45–59"
        case .over60: return "60+"
        }
    }

    /// Minors never get adult weight-loss targets or unsupervised advanced plans (§20).
    var isMinor: Bool { self == .under18 }
}
