import SwiftUI

// MARK: - Step 5: Body metrics (fully optional)

struct BodyStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Body metrics (optional)")
                    .font(.title2.bold())
                Text("Only used to personalize intensity. Skip freely — never a judgment.")
                    .foregroundStyle(.secondary)

                Picker("Units", selection: $profile.profile.usesMetric) {
                    Text("Metric (kg/cm)").tag(true)
                    Text("Imperial (lb/in)").tag(false)
                }
                .pickerStyle(.segmented)

                HStack {
                    Text("Height \(profile.profile.usesMetric ? "(cm)" : "(in)")")
                    Spacer()
                    TextField("—", value: $profile.profile.heightCm,
                              format: .number)
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 80)
                }

                HStack {
                    Text("Weight \(profile.profile.usesMetric ? "(kg)" : "(lb)")")
                    Spacer()
                    TextField("—", value: $profile.profile.weightKg,
                              format: .number)
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 80)
                }

                Picker("Age range", selection: $profile.profile.ageRange) {
                    Text("Skip").tag(AgeRange?.none)
                    ForEach(AgeRange.allCases) { range in
                        Text(range.displayName).tag(AgeRange?.some(range))
                    }
                }
            }
            .padding()
        }
    }
}

// MARK: - Step 6: Preferences

struct PreferencesStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Preferences")
                    .font(.title2.bold())

                TextField("Allergies (comma separated)",
                          text: Binding(
                            get: { profile.profile.allergies.joined(separator: ", ") },
                            set: { profile.profile.allergies = $0.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty } }))
                    .textFieldStyle(.roundedBorder)

                TextField("Dietary preferences (comma separated)",
                          text: Binding(
                            get: { profile.profile.dietaryPreferences.joined(separator: ", ") },
                            set: { profile.profile.dietaryPreferences = $0.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty } }))
                    .textFieldStyle(.roundedBorder)
            }
            .padding()
        }
    }
}

// MARK: - Step 7: Accessibility

struct AccessibilityStepView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Accessibility")
                    .font(.title2.bold())
                Text("The app adapts to how you like to train and read.")
                    .foregroundStyle(.secondary)

                Toggle("Prefer seated workouts", isOn: $profile.profile.prefersSeatedWorkouts)
                Toggle("Prefer low-impact options", isOn: $profile.profile.prefersLowImpact)
                Toggle("Show captions", isOn: $profile.profile.prefersCaptions)
                Toggle("Spoken guidance during workouts", isOn: $profile.profile.prefersAudioGuidance)
                Toggle("Reduce motion", isOn: $profile.profile.prefersReducedMotion)
            }
            .padding()
        }
    }
}

// MARK: - Step 8: Summary

struct SummaryStepView: View {
    @Environment(ProfileStore.self) private var profile
    let onFinish: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("You're set!")
                    .font(.title2.bold())

                let p = profile.profile
                summaryRow("Goal", p.primaryGoal?.displayName)
                summaryRow("Level", p.fitnessLevel.displayName)
                summaryRow("Location", p.trainingLocation?.displayName)
                summaryRow("Weekly minutes", String(p.weeklyAvailabilityMinutes.reduce(0, +)))
                summaryRow("Equipment",
                           p.availableEquipment.isEmpty ? "Bodyweight" :
                            p.availableEquipment.map(\.displayName).joined(separator: ", "))
                summaryRow("Seated / low-impact",
                           (p.prefersSeatedWorkouts || p.prefersLowImpact) ? "Yes" : "No")

                Text("Your plan updates from feedback as you train — nothing here is set in stone.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                Button("Start training", action: onFinish)
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 8)
            }
            .padding()
        }
    }

    @ViewBuilder
    private func summaryRow(_ label: String, _ value: String?) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value ?? "—")
        }
    }
}
