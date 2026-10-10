import SwiftUI

/// 8-step onboarding (master spec §2). All optional questions are skippable.
struct OnboardingContainerView: View {
    @Environment(AppModel.self) private var app
    @Environment(ProfileStore.self) private var profileStore

    @State private var stepIndex = 0

    private let totalSteps = OnboardingStep.allSteps.count

    var body: some View {
        VStack(spacing: 0) {
            // Progress header
            HStack {
                Text("Step \(stepIndex + 1) of \(totalSteps)")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Skip") {
                    finish()
                }
                .font(.subheadline)
            }
            .padding()

            ProgressView(value: Double(stepIndex + 1), total: Double(totalSteps))
                .padding(.horizontal)

            // Steps are independent views bound to the shared profile draft.
            TabView(selection: $stepIndex) {
                GoalStepView().tag(0)
                LevelStepView().tag(1)
                LocationStepView().tag(2)
                AvailabilityStepView().tag(3)
                BodyStepView().tag(4)
                PreferencesStepView().tag(5)
                AccessibilityStepView().tag(6)
                SummaryStepView(onFinish: finish).tag(7)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(.default, value: stepIndex)
            .onAppear {
                OnboardingSteps.wireProfile(profileStore)
            }

            // Footer navigation
            HStack {
                Button {
                    if stepIndex > 0 { stepIndex -= 1 }
                } label: {
                    Image(systemName: "chevron.left")
                }
                .disabled(stepIndex == 0)

                Spacer()

                Button(stepIndex == totalSteps - 1 ? "Finish" : "Next") {
                    if stepIndex < totalSteps - 1 {
                        stepIndex += 1
                    } else {
                        finish()
                    }
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
        }
    }

    private func finish() {
        app.completeOnboarding()
    }
}
