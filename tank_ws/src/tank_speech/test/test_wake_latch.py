"""pytest cases for the wake-latch state machine.

Run with::

    colcon build --packages-select tank_speech
    . install/setup.bash
    python3 -m pytest src/tank_speech/test/test_wake_latch.py
"""
import pytest

from tank_speech.wake_state import WakeLatch, WakeLatchConfig


def make_latch(threshold=0.5, cooldown=2.0, window=5.0):
    return WakeLatch(WakeLatchConfig(
        threshold=threshold, cooldown_sec=cooldown, window_sec=window,
    ))


def test_idle_when_no_signal_above_threshold():
    latch = make_latch()
    for t in range(0, 10):
        assert latch.step(0.10, float(t)) == "idle"


def test_fires_once_at_threshold():
    latch = make_latch(cooldown=10.0, window=0.5)
    assert latch.step(0.6, 1.0) == "wake"
    # Should be latched for the entire window now
    assert latch.step(0.10, 1.1) == "wake"


def test_cooldown_blocks_repeat_fires():
    # window=0.5 so the latch genuinely holds for half a second before releasing;
    # calling step() with window=0.0 runs straight through (the latch fires and
    # the next call immediately expires it). Test the realistic case here.
    latch = make_latch(threshold=0.5, cooldown=2.0, window=0.5)
    assert latch.step(0.6, 1.0) == "wake"   # first fire; latch goes high
    assert latch.step(0.0, 1.1) == "wake"   # inside the 0.5 s window
    assert latch.step(0.0, 1.6) == "idle"   # window expired (1.6 - 1.0 > 0.5)
    assert latch.step(0.6, 1.7) == "idle"   # cooldown blocks re-fire (until 3.0)
    assert latch.step(0.6, 3.1) == "wake"   # past cooldown + not latched -> fires


def test_window_keeps_latch_high_after_threshold_briefly_drops():
    latch = make_latch(threshold=0.5, cooldown=10.0, window=2.0)
    assert latch.step(0.6, 1.0) == "wake"
    assert latch.step(0.0,  1.5) == "wake"  # score below threshold but latched
    assert latch.step(0.0,  3.2) == "idle"  # window has expired


def test_reset_clears_state():
    latch = make_latch(cooldown=10.0, window=10.0)
    latch.step(0.9, 1.0)
    assert latch.is_latched
    latch.reset()
    assert not latch.is_latched
    assert latch.last_trigger_at == 0.0


def test_threshold_is_inclusive():
    latch = make_latch(threshold=0.5, cooldown=10.0, window=10.0)
    assert latch.step(0.5, 1.0) == "wake"
