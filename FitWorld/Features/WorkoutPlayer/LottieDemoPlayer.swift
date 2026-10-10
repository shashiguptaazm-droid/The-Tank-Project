import SwiftUI
import Lottie

/// Renders a Lottie animation demo for an exercise, or a clear labeled
/// placeholder when no asset exists yet — never a fake animation (plan §4).
struct LottieDemoPlayer: View {
    let exercise: Exercise
    let gender: DemonstratorGender
    let view: DemoAsset.DemoView
    let speed: Double

    var body: some View {
        Group {
            if let asset = pickAsset() {
                LottieLoopPlayer(assetName: asset.assetID, speed: speed)
                    .accessibilityLabel("\(gender.displayName) demonstration, \(exercise.name)")
            } else {
                PlaceholderDemo(gender: gender)
            }
        }
        .id("\(assetKey() ?? "none")-\(speed)")
    }

    private func pickAsset() -> DemoAsset? {
        let forGender = gender == .male ? exercise.demo.male : exercise.demo.female
        // Exact view match first; fall back to any view so the user still sees motion.
        return forGender.first { $0.view == view } ?? forGender.first
    }

    private func assetKey() -> String? { pickAsset()?.assetID }
}

/// UIViewRepresentable wrapper around LottieAnimationView with looping + speed
/// handled inside (no fake fluent modifiers — those don't type-check).
struct LottieLoopPlayer: UIViewRepresentable {
    let assetName: String
    let speed: Double

    func makeUIView(context: Context) -> LottieAnimationView {
        let v = LottieAnimationView(name: assetName, bundle: .main)
        v.contentMode = .scaleAspectFit
        v.animationSpeed = CGFloat(speed)
        v.loopMode = .loop
        v.play()
        return v
    }

    func updateUIView(_ v: LottieAnimationView, context: Context) {
        v.animationSpeed = CGFloat(speed)
        if !v.isAnimationPlaying {
            v.play()
        }
    }
}

/// Visible, honest placeholder that explains itself.
struct PlaceholderDemo: View {
    let gender: DemonstratorGender

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "figure.person.crop.rectangle")
                .font(.system(size: 56))
                .foregroundStyle(.tertiary)
            Text("Animation demo in production")
                .font(.subheadline)
            Text("Reviewed \(gender == .male ? "male" : "female") demonstration coming for this exercise. Text instructions below are complete.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Animation demo not yet available. Use the written instructions below.")
    }
}
