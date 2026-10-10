import SwiftUI

/// Customizable standalone timer (§5): user-defined work/rest/sets, Tabata preset.
struct QuickTimerView: View {
    @State private var workSeconds = 40
    @State private var restSeconds = 20
    @State private var sets = 8
    @State private var engine = IntervalTimerEngine()
    @State private var speaker = VoiceCueSpeaker()

    var body: some View {
        VStack(spacing: 20) {
            TimerRing(snapshot: engine.snapshot)
                .frame(height: 220)

            HStack(spacing: 12) {
                stepper("Work", value: $workSeconds, bounds: 5...600, step: 5)
                stepper("Rest", value: $restSeconds, bounds: 5...300, step: 5)
                stepper("Sets", value: $sets, bounds: 1...30, step: 1)
            }

            HStack(spacing: 16) {
                Button("Start") {
                    speaker.isEnabled = true
                    engine.onSpokenCue = { speaker.speak($0) }
                    engine.start(config: .init(
                        warmUpSeconds: 15,
                        workSeconds: workSeconds,
                        restSeconds: restSeconds,
                        transitionSeconds: 10,
                        coolDownSeconds: 45,
                        sets: sets,
                        blocks: 1))
                }
                .buttonStyle(.borderedProminent)
                .disabled(engine.snapshot.isRunning)

                Button("Pause") { engine.pause() }.disabled(!engine.snapshot.isRunning)
                Button("Resume") { engine.resume() }
                Button("Stop") { engine.stop() }
            }
        }
        .padding()
        .navigationTitle("Quick timer")
    }

    private func stepper(_ label: String, value: Binding<Int>,
                         bounds: ClosedRange<Int>, step: Int) -> some View {
        VStack {
            Text(label).font(.caption)
            Stepper("\(value.wrappedValue)s", value: value,
                    in: bounds, step: step)
                .font(.subheadline.monospacedDigit())
        }
    }
}
