"""Tank — State Machine.

Deterministic state transitions for the robot's cognitive loop.
States: IDLE → OBSERVING → DETECTING → ANALYZING → TRACKING → ACTING → VERIFYING
Safety: SAFE_STOP, ERROR, OFFLINE
"""
from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("tank.state")


class State(Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    DETECTING = "DETECTING"
    ANALYZING = "ANALYZING"
    TRACKING = "TRACKING"
    ACTING = "ACTING"
    VERIFYING = "VERIFYING"
    SAFE_STOP = "SAFE_STOP"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


# Valid transitions: from_state → set of allowed to_states
TRANSITIONS: Dict[State, Set[State]] = {
    State.IDLE: {State.OBSERVING, State.IDLE, State.SAFE_STOP, State.OFFLINE},
    State.OBSERVING: {State.DETECTING, State.ANALYZING, State.OBSERVING, State.IDLE, State.SAFE_STOP, State.OFFLINE},
    State.DETECTING: {State.ANALYZING, State.OBSERVING, State.SAFE_STOP, State.ERROR},
    State.ANALYZING: {State.TRACKING, State.ACTING, State.DETECTING, State.OBSERVING, State.SAFE_STOP, State.ERROR},
    State.TRACKING: {State.ACTING, State.ANALYZING, State.OBSERVING, State.SAFE_STOP, State.ERROR},
    State.ACTING: {State.VERIFYING, State.OBSERVING, State.SAFE_STOP, State.ERROR},
    State.VERIFYING: {State.OBSERVING, State.TRACKING, State.SAFE_STOP, State.ERROR},
    State.SAFE_STOP: {State.IDLE, State.OBSERVING, State.ERROR},
    State.ERROR: {State.IDLE, State.SAFE_STOP},
    State.OFFLINE: {State.IDLE},
}


class StateMachine:
    def __init__(self, on_transition: Optional[callable] = None) -> None:
        self._state = State.IDLE
        self._previous = State.IDLE
        self._entered_at = time.time()
        self._on_transition = on_transition
        self._transition_log: List[Dict] = []

    @property
    def state(self) -> State:
        return self._state

    @property
    def previous(self) -> State:
        return self._previous

    @property
    def time_in_state(self) -> float:
        return time.time() - self._entered_at

    def can_transition(self, target: State) -> bool:
        return target in TRANSITIONS.get(self._state, set())

    def transition(self, target: State, reason: str = "") -> bool:
        if not self.can_transition(target):
            logger.warning(f"Invalid transition: {self._state.value} → {target.value} (reason: {reason})")
            return False

        old = self._state
        self._previous = old
        self._state = target
        self._entered_at = time.time()

        entry = {
            "from": old.value,
            "to": target.value,
            "reason": reason,
            "time": self._entered_at,
        }
        self._transition_log.append(entry)
        if len(self._transition_log) > 500:
            self._transition_log = self._transition_log[-500:]

        logger.info(f"State: {old.value} → {target.value} ({reason})")

        if self._on_transition:
            try:
                self._on_transition(old, target, reason)
            except Exception as e:
                logger.error(f"on_transition callback error: {e}")

        return True

    def force(self, target: State, reason: str = "force") -> None:
        """Force transition (bypasses validation — for emergency use only)."""
        old = self._state
        self._previous = old
        self._state = target
        self._entered_at = time.time()
        self._transition_log.append({"from": old.value, "to": target.value, "reason": f"FORCE: {reason}", "time": self._entered_at})
        logger.warning(f"FORCED: {old.value} → {target.value} ({reason})")

    def history(self, limit: int = 50) -> List[Dict]:
        return self._transition_log[-limit:]
