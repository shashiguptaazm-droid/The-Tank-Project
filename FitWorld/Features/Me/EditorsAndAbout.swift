import SwiftUI

/// Edits core profile fields later via the Me tab.
struct ProfileEditorView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        Form {
            Picker("Goal", selection: $profile.profile.primaryGoal) {
                Text("None").tag(TrainingGoal?.none)
                ForEach(TrainingGoal.allCases) { goal in
                    Text(goal.displayName).tag(TrainingGoal?.some(goal))
                }
            }
            Picker("Level", selection: $profile.profile.fitnessLevel) {
                ForEach(DifficultyLevel.allCases) { level in
                    Text(level.displayName).tag(level)
                }
            }
            Picker("Location", selection: $profile.profile.trainingLocation) {
                Text("None").tag(TrainingLocation?.none)
                ForEach(TrainingLocation.allCases) { loc in
                    Text(loc.displayName).tag(TrainingLocation?.some(loc))
                }
            }
            HeightWeightSection()
        }
        .navigationTitle("Edit profile")
    }
}

struct HeightWeightSection: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        Section("Body (optional)") {
            HStack {
                Text("Height (cm)")
                Spacer()
                TextField("—", value: $profile.profile.heightCm, format: .number)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 80)
            }
            HStack {
                Text("Weight (kg)")
                Spacer()
                TextField("—", value: $profile.profile.weightKg, format: .number)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 80)
            }
        }
    }
}

struct PreferencesEditorView: View {
    @Environment(ProfileStore.self) private var profile

    var body: some View {
        @Bindable var profile = profile

        Form {
            Section("Training style") {
                Toggle("Seated workouts", isOn: $profile.profile.prefersSeatedWorkouts)
                Toggle("Low-impact options", isOn: $profile.profile.prefersLowImpact)
            }
            Section("Instruction & cues") {
                Toggle("Captions", isOn: $profile.profile.prefersCaptions)
                Toggle("Spoken guidance", isOn: $profile.profile.prefersAudioGuidance)
                Toggle("Reduce motion", isOn: $profile.profile.prefersReducedMotion)
            }
            Section("Dietary") {
                TextField("Allergies (comma separated)",
                          text: Binding(
                            get: { profile.profile.allergies.joined(separator: ", ") },
                            set: { profile.profile.allergies = $0.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) } }))
                TextField("Dietary preferences",
                          text: Binding(
                            get: { profile.profile.dietaryPreferences.joined(separator: ", ") },
                            set: { profile.profile.dietaryPreferences = $0.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) } }))
            }
        }
        .navigationTitle("Preferences")
    }
}

/// Mandatory safety/about screen (§ "acceptance criteria" — safety text must ship).
struct AboutSafetyView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text("Safety first").font(.title2.bold())
                Text("""
                FitWorld provides general fitness education, not medical advice. \
                Nothing here diagnoses conditions, prescribes treatment, or replaces \
                professional medical care.
                """)
                Text("""
                Stop immediately and seek medical help if you experience chest pain, \
                severe shortness of breath, sudden weakness, loss of balance, or any \
                rapid worsening of symptoms during exercise.
                """)
                Text("""
                Persistent, recurrent, or unexplained pain should be reviewed by a \
                qualified healthcare professional. If a clinician has given you \
                restrictions, those take precedence over anything in this app.
                """)
                Text("Data & privacy").font(.title2.bold())
                Text("""
                Your profile and workout history stay on this device in Phase 1. \
                Account deletion and data export are available in Settings; health \
                data is never sold or shared for advertising.
                """)
                Text("Version").font(.title2.bold())
                Text("Phase 1 — Core Engine (development)")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("About & safety")
        .navigationBarTitleDisplayMode(.inline)
    }
}
