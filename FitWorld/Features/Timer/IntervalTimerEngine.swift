import Foundation
import Observation
import AVFoundation

/// Phase of the interval timer.
enum TimerPhase: Equatable {
    case warmUp
    case exercise
    case rest(seconds: Int)
    case transition
    case coolDown
    case finished
}

/// Snapshot consumed by the UI every tick.
struct TimerSnapshot: Equatable {
    var phase: TimerPhase = .finished
    var secondsRemaining: Int = 0
    var currentSet: Int = 0
    var totalSets: Int = 0
    var blockIndex: Int = 0
    var totalBlocks: Int = 0
    var isRunning: Bool = false
}

/**
 * IntervalTimerEngine — the accuracy-critical component (master spec §5).
 *
 * Design: all time math is anchored to wall-clock dates. A paused-at moment is
 * recorded as a Date and restored against Date() on resume; backgrounding,
 * an incoming call, or a locked screen therefore cannot drift or lose time.
 * The displayed countdown is computed from `phaseEnd` minus `Date()`, never
 * from accumulated increments.
 */
@Observable
final class IntervalTimerEngine {
    // MARK: Configuration inputs

    struct Config {
        var warmUpSeconds: Int = 60
        var workSeconds: Int?          // nil => untimed (reps-based, advance manually)
        var restSeconds: Int = 60
        var transitionSeconds: Int = 10
        var coolDownSeconds: Int = 60
        var sets: Int = 1
        var blocks: Int = 1
    }

    private(set) var snapshot = TimerSnapshot()
    var onPhaseChange: ((TimerPhase) -> Void)?
    var onSpokenCue: ((String) -> Void)?

    // MARK: State

    private var config = Config()
    private var phaseEnd: Date = .distantFuture
    private var unsavedPausedRemaining: Int = 0
    private var timer: Timer?

    private(set) var isPaused = false
    private var lastCueSecond: Int = -1

    // MARK: Lifecycle

    func start(config: Config) {
        self.config = config
        snapshot = TimerSnapshot(phase: .warmUp,
                                 totalSets: config.sets,
                                 totalBlocks: config.blocks,
                                 isRunning: true)
        enter(phase: .warmUp, duration: config.warmUpSeconds)
        scheduleTicks()
    }

    /// Untimed work phase (reps-based): user advances manually.
    func startRepBasedSet() {
        recomputeSnapshot { snap in
            snap.phase = .exercise
            snap.secondsRemaining = -1 // sentinel: no countdown display
        }
        phaseEnd = .distantFuture
        scheduleTicks()
        speak("Begin")
    }

    func pause() {
        guard !isPaused else { return }
        isPaused = true
        // Freeze the remaining wall-clock budget; timer stops ticking.
        if phaseEnd != .distantFuture {
            unsavedPausedRemaining = max(0, Int(phaseEnd.timeIntervalSinceNow.rounded()))
        }
        timer?.invalidate()
        timer = nil
        updateRunning(false)
    }

    func resume() {
        guard isPaused else { return }
        isPaused = false
        if phaseEnd != .distantFuture {
            phaseEnd = Date().addingTimeInterval(TimeInterval(unsavedPausedRemaining))
        }
        scheduleTicks()
        updateRunning(true)
    }

    func skipPhase() {
        advance()
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isPaused = false
        snapshot.phase = .finished
        snapshot.isRunning = false
    }

    // MARK: Internals

    private func enter(phase: TimerPhase, duration: Int) {
        phaseEnd = Date().addingTimeInterval(TimeInterval(duration))
        updateSnapshot(phase: phase, secondsRemaining: duration)
        lastCueSecond = -1

        switch phase {
        case .warmUp: speak("Warm up")
        case .exercise: speak("Work")
        case .rest: speak("Rest")
        case .transition: speak("Get ready")
        case .coolDown: speak("Cool down")
        case .finished: break
        }
        onPhaseChange?(phase)
    }

    private func scheduleTicks() {
        timer?.invalidate()
        let t = Timer(timeInterval: 0.25, repeats: true) { [weak self] _ in
            self?.tick()
        }
        // Coalesce while the app is backgrounded; phases stay date-anchored,
        // so missed ticks self-correct on the next rendered frame.
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    private func tick() {
        guard !isPaused else { return }
        guard phaseEnd != .distantFuture else { return }

        let remaining = max(0, Int(phaseEnd.timeIntervalSinceNow.rounded(.up)))
        updateSnapshot(secondsRemaining: remaining)
        emitCountdownCues(remaining)

        if remaining == 0 { advance() }
    }

    private func emitCountdownCues(_ remaining: Int) {
        guard remaining <= 3, remaining >= 1, remaining != lastCueSecond else { return }
        lastCueSecond = remaining
        speak("\(remaining)")
    }

    private func advance() {
        switch snapshot.phase {
        case .warmUp, .coolDown, .finished, .transition:
            beginSet()
        case .exercise:
            // Rest between sets/blocks, or move on when last set of last block.
            let isLastSet = snapshot.currentSet >= config.sets
            let isLastBlock = snapshot.blockIndex >= config.blocks
            if isLastSet && isLastBlock {
                enterCoolDown()
            } else {
                enter(phase: .rest(seconds: config.restSeconds),
                      duration: config.restSeconds)
            }
        case .rest:
            beginSet()
        }
    }

    private func beginSet() {
        // Progress set/block bookkeeping on entry.
        if snapshot.phase == .rest || snapshot.phase == .transition {
            if snapshot.currentSet >= config.sets {
                snapshot.currentSet = 1
                snapshot.blockIndex += 1
                if snapshot.blockIndex > config.blocks {
                    enterCoolDown()
                    return
                }
            } else {
                snapshot.currentSet += 1
            }
        } else {
            snapshot.currentSet = max(1, snapshot.currentSet == 0 ? 1 : snapshot.currentSet)
        }

        if config.workSeconds == nil {
            startRepBasedSet()
        } else {
            enter(phase: .exercise, duration: config.workSeconds!)
        }
        updateRunning(true)
    }

    private func enterCoolDown() {
        guard config.coolDownSeconds > 0 else {
            finish(); return
        }
        enter(phase: .coolDown, duration: config.coolDownSeconds)
    }

    private func finish() {
        timer?.invalidate(); timer = nil
        snapshot.phase = .finished
        snapshot.isRunning = false
        speak("Done. Great work.")
        onPhaseChange?(.finished)
    }

    private func updateSnapshot(phase: TimerPhase? = nil, secondsRemaining: Int? = nil) {
        if let phase { snapshot.phase = phase }
        if let secondsRemaining { snapshot.secondsRemaining = secondsRemaining }
    }

    private func recomputeSnapshot(_ mutate: (inout TimerSnapshot) -> Void) {
        var copy = snapshot
        mutate(&copy)
        snapshot = copy
    }

    private func updateRunning(_ running: Bool) {
        recomputeSnapshot { $0.isRunning = running }
    }

    private func speak(_ text: String) {
        onSpokenCue?(text)
    }
}

// MARK: - Voice output

/// Voice cues via AVSpeechSynthesizer. Disabled when profile.audioGuidance is
/// off; respects silent-mode-resistant playback for workout audio.
final class VoiceCueSpeaker {
    private let synthesizer = AVSpeechSynthesizer()
    var isEnabled: Bool = true

    func speak(_ text: String) {
        guard isEnabled else { return }
        let utterance = AVSpeechUtterance(string: text)
        utterance.rate = 0.5
        synthesizer.stopSpeaking(at: .immediate)
        synthesizer.speak(utterance)
    }
}
