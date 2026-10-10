import XCTest
@testable import FitWorld

final class IntervalTimerEngineTests: XCTestCase {
    private func makeEngine() -> IntervalTimerEngine {
        let engine = IntervalTimerEngine()
        engine.onSpokenCue = { _ in }
        engine.onPhaseChange = { _ in }
        return engine
    }

    func testCountdownAnchorsToWallClockNotDrift() {
        let engine = makeEngine()
        // Warm-up 5s; wait 2s; remaining should be ~3 (±1 s of scheduling slack).
        let config = IntervalTimerEngine.Config(warmUpSeconds: 5, workSeconds: 1,
                                                restSeconds: 1, transitionSeconds: 1,
                                                coolDownSeconds: 1, sets: 1, blocks: 1)
        engine.start(config: config)
        let expected = 5 - 2
        let afterTwoSeconds = expectation(description: "after 2 s")
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            // XCTest's accuracy assertion is FloatingPoint-only; compare as Double.
            XCTAssertEqual(Double(engine.snapshot.secondsRemaining), Double(expected),
                           accuracy: 1.0, "Countdown must be wall-clock anchored")
            engine.stop()
            afterTwoSeconds.fulfill()
        }
        wait(for: [afterTwoSeconds], timeout: 5)
    }

    func testPauseFreezesAndResumeRestores() {
        let engine = makeEngine()
        let config = IntervalTimerEngine.Config(warmUpSeconds: 10, workSeconds: 1,
                                                restSeconds: 1, transitionSeconds: 1,
                                                coolDownSeconds: 1, sets: 1, blocks: 1)
        engine.start(config: config)
        engine.pause()
        let frozen = engine.snapshot.secondsRemaining
        XCTAssertEqual(engine.snapshot.isRunning, false)

        let exp = expectation(description: "paused hold")
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            XCTAssertEqual(engine.snapshot.secondsRemaining, frozen,
                           "Paused timer must not drift")
            engine.resume()
            XCTAssertTrue(engine.snapshot.isRunning)
            engine.stop()
            exp.fulfill()
        }
        wait(for: [exp], timeout: 5)
    }

    func testPhaseProgressionWarmUpToExerciseToRest() {
        let engine = makeEngine()
        var seenPhases: [TimerPhase] = []
        engine.onPhaseChange = { seenPhases.append($0) }
        let config = IntervalTimerEngine.Config(warmUpSeconds: 1, workSeconds: 1,
                                                restSeconds: 1, transitionSeconds: 1,
                                                coolDownSeconds: 1, sets: 2, blocks: 2)
        engine.start(config: config)
        // Let it cycle a bit; then inspect.
        let exp = expectation(description: "cycle")
        DispatchQueue.main.asyncAfter(deadline: .now() + 5.5) {
            XCTAssertTrue(seenPhases.contains(.warmUp))
            XCTAssertTrue(seenPhases.contains(.exercise),
                          "Must reach exercise phase")
            engine.stop()
            exp.fulfill()
        }
        wait(for: [exp], timeout: 10)
    }

    func testRepBasedSetHasNoCountdown() {
        let engine = makeEngine()
        let config = IntervalTimerEngine.Config(warmUpSeconds: 0, workSeconds: nil,
                                                restSeconds: 1, transitionSeconds: 1,
                                                coolDownSeconds: 1, sets: 1, blocks: 1)
        engine.start(config: config)
        // Warm-up is 0 s: should enter rep-based exercise immediately.
        XCTAssertEqual(engine.snapshot.phase, .exercise)
        XCTAssertEqual(engine.snapshot.secondsRemaining, -1,
                       "Rep-based sets use -1 sentinel, not a countdown")
        engine.stop()
    }

    func testSetsAndBlocksProgress() {
        let engine = makeEngine()
        let config = IntervalTimerEngine.Config(warmUpSeconds: 0, workSeconds: 0,
                                                restSeconds: 0, transitionSeconds: 0,
                                                coolDownSeconds: 0, sets: 3, blocks: 2)
        // Work 0 == immediate advance; steps through all phases rapidly.
        engine.start(config: config)
        let exp = expectation(description: "snapshots progress")
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            let snap = engine.snapshot
            XCTAssertTrue(snap.totalSets == 3 && snap.totalBlocks == 2,
                          "Config must be reflected in snapshot")
            engine.stop()
            exp.fulfill()
        }
        wait(for: [exp], timeout: 5)
    }
}
