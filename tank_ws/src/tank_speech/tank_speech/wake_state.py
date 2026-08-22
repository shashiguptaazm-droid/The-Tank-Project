"""Pure-Python wake-latch state machine.

Lifted out of the ROS2 node so it can be unit-tested without bringing up
a ROS environment and reused by the standalone CLI.

The state machine transitions:

    idle --(score >= threshold AND cooldown elapsed)--> wake
    wake --(now - wake_at > window_sec)--> idle

The cooldown is applied to the moment a wake fires (latched). The window
is how long the latch stays high so downstream ASR knows when to listen.

A ``reset()`` is exposed so the host (typically the ROS node) can flush
state when it has honoured the wake event (e.g. after ASR has captured
the audio clip).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WakeLatchConfig:
    threshold:    float = 0.55
    cooldown_sec: float = 2.0
    window_sec:   float = 5.0


class WakeLatch:
    def __init__(self, config: WakeLatchConfig) -> None:
        self._cfg = config
        self._cooldown_until = 0.0
        self._latched = False
        self._wake_at = 0.0

    def step(self, score: float, now_sec: float) -> str:
        """Feed the latest wake-word score (0..1) and the monotonic clock.

        Returns ``"wake"`` if the latch is high (we're inside the
        window after a recent firing), ``"idle"`` otherwise.

        The latch flips to True exactly when``score >= threshold`` AND
        ``now >= cooldown_until``. The latch flips back to False when
        ``now - wake_at > window_sec``.
        """
        if (
            not self._latched
            and score >= self._cfg.threshold
            and now_sec >= self._cooldown_until
        ):
            self._latched = True
            self._wake_at = now_sec
            self._cooldown_until = now_sec + self._cfg.cooldown_sec
        if self._latched and (now_sec - self._wake_at) > self._cfg.window_sec:
            self._latched = False
            return "idle"
        return "wake" if self._latched else "idle"

    def reset(self) -> None:
        """Force the latch off and reset the cooldown."""
        self._latched = False
        self._cooldown_until = 0.0
        self._wake_at = 0.0

    @property
    def is_latched(self) -> bool:
        return self._latched

    @property
    def last_trigger_at(self) -> float:
        return self._wake_at
