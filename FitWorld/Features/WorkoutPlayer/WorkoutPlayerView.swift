import SwiftUI

/// Live workout screen (§5): animation + timer + current set + target reps +
/// rest countdown + form reminders, without clutter. Sessions save locally on
/// finish or abort — never lost to an interruption.
struct WorkoutPlayerView: View {
    @Environment(ContentStore.self) private var content
    @Environment(ProfileStore.self) private var profile
    @Environment(AppModel.self) private var appModel
    @Environment(\.dismiss) private var dismiss

    let workout: Workout

    @State private var engine = IntervalTimerEngine()
    @State private var speaker = VoiceCueSpeaker()
    @State private var session: WorkoutSession
    @State private var showFeelPicker = false
    @State private var savedToHistory = false
    @State private var resolved: (warmUp: [Exercise], blocks: [Exercise], coolDown: [Exercise]) = ([], [], [])

    init(workout: Workout) {
        self.workout = workout
        _session = State(initialValue: WorkoutSession(
            id: UUID(), workoutSlug: workout.slug, workoutName: workout.name,
            startedAt: Date(), endedAt: nil, entries: [], feel: nil))
    }

    var body: some View {
        VStack(spacing: 12) {
            demoArea
            timerArea
            setControls
        }
        .padding()
        .navigationTitle(workout.name)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Finish") { finishSession(manually: true) }
            }
        }        .onAppear(perform: start)
        .onDisappear { engine.stop() }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.willTerminateNotification)) { _ in
            // Safe state on abnormal exit: the record persists with what we have.
            finishSession(manually: true)
        }
        .sheet(isPresented: $showFeelPicker, onDismiss: dismissAfterSave) {
            SessionFeelSheet(feel: $session.feel)
        }
    }

    // MARK: Demo area

    @ViewBuilder
    private var demoArea: some View {
        let currentExercise = currentExercise()
        VStack(spacing: 4) {
            if let ex = currentExercise {
                LottieDemoPlayer(exercise: ex,
                                 gender: .male,
                                 view: .front,
                                 speed: 1.0)
            }
            Text(currentExercise?.name ?? "Workout complete")
                .font(.headline)
            if let cue = currentExercise?.formCues.first {
                Text(cue).font(.caption).foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: Timer area

    private var timerArea: some View {
        VStack(spacing: 4) {
            TimerRing(snapshot: engine.snapshot)
                .frame(height: 160)
            HStack {
                Text("Set \(engine.snapshot.currentSet)/\(engine.snapshot.totalSets) · Block \(engine.snapshot.blockIndex + 1)/\(engine.snapshot.totalBlocks)")
                    .font(.subheadline.monospacedDigit())
                Spacer()
                if let block = workout.blocks[safe: engine.snapshot.blockIndex] {
                    Text(block.targetDisplay).font(.subheadline)
                }
            }
        }
    }

    // MARK: Controls

    private var setControls: some View {
        HStack(spacing: 16) {
            Button("Pause") { engine.pause() }
            Button("Resume") { engine.resume() }
            Button("Skip") { engine.skipPhase() }
            Spacer()
            Button {
                recordSetCompletion()
                engine.skipPhase()
            } label: {
                Label("Set done", systemImage: "checkmark.circle.fill")
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: Logic

    private func start() {
        speaker.isEnabled = profile.profile.prefersAudioGuidance
        engine.onSpokenCue = { text in speaker.speak(text) }
        resolved = content.resolve(workout: workout)
        let config = IntervalTimerEngine.Config(
            warmUpSeconds: resolved.warmUp.isEmpty ? 30 : 60,
            workSeconds: nil, // reps-based for Phase 1 simplicity; timed sets later
            restSeconds: workout.blocks.first?.restSeconds ?? 60,
            transitionSeconds: 10,
            coolDownSeconds: 45,
            sets: workout.blocks.first?.sets ?? 1,
            blocks: workout.blocks.count)
        engine.start(config: config)
    }

    private func currentExercise() -> Exercise? {
        let index = min(engine.snapshot.blockIndex, max(0, resolved.blocks.count - 1))
        return resolved.blocks.indices.contains(engine.snapshot.blockIndex)
            ? resolved.blocks[index]
            : resolved.blocks.first
    }

    private func recordSetCompletion() {
        let blockIndex = engine.snapshot.blockIndex
        let setNumber = engine.snapshot.currentSet
        let entry = SetEntry(blockIndex: blockIndex,
                             setNumber: setNumber,
                             reps: nil,
                             weightKg: nil,
                             durationSeconds: nil,
                             completed: true)
        session.entries.append(entry)
    }

    private func finishSession(manually: Bool) {
        session.endedAt = Date()
        // Persist BEFORE showing the feel sheet — the record must survive
        // even if the app is killed while the sheet is open (plan §8 M7 rule).
        appModel.sessionStore?.save(session)
        savedToHistory = true
        showFeelPicker = true
    }

    private func dismissAfterSave() {
        guard savedToHistory else { return }
        // Feel was captured on the sheet's dismiss via the binding write.
        appModel.sessionStore?.save(session)
        dismiss()
    }
}

// MARK: - Timer ring

struct TimerRing: View {
    let snapshot: TimerSnapshot

    var body: some View {
        ZStack {
            Circle().stroke(Color(.tertiarySystemFill), lineWidth: 10)
            if snapshot.secondsRemaining >= 0 {
                Text("\(snapshot.secondsRemaining)")
                    .font(.system(size: 56, weight: .heavy, design: .rounded))
                    .monospacedDigit()
            } else {
                Text("GO")
                    .font(.system(size: 48, weight: .heavy, design: .rounded))
            }
        }
        .accessibilityLabel(accessibilityText)
    }

    private var accessibilityText: String {
        switch snapshot.phase {
        case .warmUp: return "Warm-up, \(snapshot.secondsRemaining) seconds"
        case .exercise: return "Working"
        case .rest: return "Rest, \(snapshot.secondsRemaining) seconds"
        case .transition: return "Get ready"
        case .coolDown: return "Cool-down"
        case .finished: return "Finished"
        }
    }
}

// MARK: - Feel sheet

struct SessionFeelSheet: View {
    @Binding var feel: SessionFeel?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 16) {
            Text("How did that feel?")
                .font(.title3.bold())
            Text("Honest feedback tunes the next session. No wrong answers.")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                ForEach(SessionFeel.allCases, id: \.self) { option in
                    Button(labelFor(option)) {
                        feel = option
                        dismiss()
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding()
        .presentationDetents([.height(200)])
    }

    private func labelFor(_ feel: SessionFeel) -> String {
        switch feel {
        case .easy: return "Easy"
        case .justRight: return "Just right"
        case .hard: return "Hard"
        }
    }
}

// MARK: - Safe index helper

extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
