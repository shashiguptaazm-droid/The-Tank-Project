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
                LottieView(name: asset.assetID, bundle: .main)
                    .looping()
                    .animationSpeed(CGFloat(speed))
                    .resizable()
                    .scaledToFit()
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

// MARK: - Lottie wrapper convenience

private struct LottieView: UIViewRepresentable {
    let name: String
    let bundle: Bundle

    func makeUIView(context: Context) -> LottieAnimationView {
        let v = LottieAnimationView(name: name, bundle: bundle)
        v.contentMode = .scaleAspectFit
        return v
    }

    func updateUIView(_ v: LottieAnimationView, context: Context) {
        v.play()
    }

    func looping() -> Self { self }
    func animationSpeed(_ speed: CGFloat) -> Self { self }
    func resizable() -> Self { self }
    func scaledToFit() -> Self { self }
}
