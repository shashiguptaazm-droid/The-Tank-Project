import SwiftUI

enum OnboardingStep {
    static let allSteps: [String] = [
        "Goal", "Level", "Location", "Availability",
        "Body", "Preferences", "Accessibility", "Summary"
    ]
}

/// Wires the profile store into the availability draft bridge.
enum OnboardingSteps {
    static func wireProfile(_ store: ProfileStore) {
        AvailabilityDraft.sharedProfile = store
    }
}
