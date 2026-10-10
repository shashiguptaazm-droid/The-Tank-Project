import SwiftUI

// MARK: - Step 1: Primary goal

struct GoalStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {

        // Bindings over @Observable environment values:
        @Bindable var profile = profile
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("What's your main focus?")
                    .font(.title2.bold())
                Text("Pick one. You can change it any time.")
                    .foregroundStyle(.secondary)

                Picker("Goal", selection: $profile.profile.primaryGoal) {
                    Text("Skip").tag(TrainingGoal?.none)
                    ForEach(TrainingGoal.allCases) { goal in
                        Text(goal.displayName).tag(TrainingGoal?.some(goal))
                    }
                }
                .pickerStyle(.inline)
            }
            .padding()
        }
    }
}

// MARK: - Step 2: Fitness level

struct LevelStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {

        // Bindings over @Observable environment values:
        @Bindable var profile = profile
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Your current level")
                    .font(.title2.bold())
                Text("Be honest — the plan adapts as you train.")
                    .foregroundStyle(.secondary)

                Picker("Level", selection: $profile.profile.fitnessLevel) {
                    ForEach(DifficultyLevel.allCases) { level in
                        Text(level.displayName).tag(level)
                    }
                }
                .pickerStyle(.segmented)
            }
            .padding()
        }
    }
}

// MARK: - Step 3: Location + equipment

struct LocationStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {

        // Bindings over @Observable environment values:
        @Bindable var profile = profile
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Where will you train?")
                    .font(.title2.bold())

                Picker("Location", selection: $profile.profile.trainingLocation) {
                    Text("Skip").tag(TrainingLocation?.none)
                    ForEach(TrainingLocation.allCases) { loc in
                        Text(loc.displayName).tag(TrainingLocation?.some(loc))
                    }
                }
                .pickerStyle(.segmented)

                Text("Equipment available")
                    .font(.headline)

                EquipmentPicker(selection: $profile.profile.availableEquipment)
            }
            .padding()
        }
    }
}

// MARK: - Step 4: Weekly availability

struct AvailabilityStepView: View {
    private static let dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    // @State belongs on the struct, never inside body (illegal placement was
    // the "type '()' cannot conform to 'View'" CI error).
    @State private var availabilityStore = AvailabilityDraft()

    var body: some View {

        // Bindings over @Observable environment values:
        @Bindable var profile = profile
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Weekly availability")
                    .font(.title2.bold())
                Text("Rough minutes per day is fine.")
                    .foregroundStyle(.secondary)

                ForEach(0..<7, id: \.self) { day in
                    HStack {
                        Text(Self.dayNames[day])
                            .frame(width: 44, alignment: .leading)
                        Stepper("\(availabilityStore.minutes[day])m",
                                value: $availabilityStore.minutes[day],
                                in: 0...120, step: 5)
                            .font(.subheadline.monospacedDigit())
                    }
                }
            }
            .padding()
        }
        .onAppear { availabilityStore.loadFromProfile() }
        .onDisappear { availabilityStore.saveToProfile() }
    }
}

/// Bridges the slider UI to the profile's weekly availability array.
@Observable
final class AvailabilityDraft {
    var minutes: [Int] = Array(repeating: 30, count: 7)

    func loadFromProfile() {
        // ProfileStore is fetched through environment on save; keep in sync here.
        minutes = AvailabilityDraft.sharedProfile?.weeklyAvailabilityMinutes
            ?? Array(repeating: 30, count: 7)
    }

    func saveToProfile() {
        AvailabilityDraft.sharedProfile?.update {
            $0.weeklyAvailabilityMinutes = minutes
        }
    }

    // Set by MainTabView/AppModel wiring at boot.
    static weak var sharedProfile: ProfileStore?
}
