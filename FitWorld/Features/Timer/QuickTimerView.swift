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
                workStepper
                restStepper
                setsStepper
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

    private var workStepper: some View {
        VStack {
            Text("Work").font(.caption)
            Stepper("\(workSeconds)s", value: $workSeconds, in: 5...600, step: 5)
                .font(.subheadline.monospacedDigit())
        }
    }

    private var restStepper: some View {
        VStack {
            Text("Rest").font(.caption)
            Stepper("\(restSeconds)s", value: $restSeconds, in: 5...300, step: 5)
                .font(.subheadline.monospacedDigit())
        }
    }

    private var setsStepper: some View {
        VStack {
            Text("Sets").font(.caption)
            Stepper("\(sets)", value: $sets, in: 1...30, step: 1)
                .font(.subheadline.monospacedDigit())
        }
    }
}
