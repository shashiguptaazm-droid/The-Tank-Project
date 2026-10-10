import Foundation
import Observation

/// Stores the user profile and onboarding flag locally. Server sync joins later (M3/M8).
@Observable
final class ProfileStore {
    private static let profileKey = "fitworld.profile.v1"
    private static let onboardingKey = "fitworld.onboarding.complete"

    private let defaults: UserDefaults

    var profile: UserProfile {
        didSet { persist() }
    }

    private(set) var hasCompletedOnboarding: Bool

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: Self.profileKey),
           let decoded = try? JSONDecoder().decode(UserProfile.self, from: data) {
            self.profile = decoded
        } else {
            self.profile = UserProfile()
        }
        self.hasCompletedOnboarding = defaults.bool(forKey: Self.onboardingKey)
    }

    func markOnboardingComplete() {
        hasCompletedOnboarding = true
        defaults.set(true, forKey: Self.onboardingKey)
    }

    func update(_ mutate: (inout UserProfile) -> Void) {
        var copy = profile
        mutate(&copy)
        profile = copy
    }

    /// Account deletion / data reset support (§22 of master spec).
    func eraseProfile() {
        profile = UserProfile()
        hasCompletedOnboarding = false
        defaults.removeObject(forKey: Self.profileKey)
        defaults.removeObject(forKey: Self.onboardingKey)
    }

    private func persist() {
        if let data = try? JSONEncoder().encode(profile) {
            defaults.set(data, forKey: Self.profileKey)
        }
    }
}
