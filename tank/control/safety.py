"""Tank — Safety Controller.

Software safety mechanisms: E-stop, command timeout, max duration,
invalid command rejection, sensor failure, watchdog, safe defaults.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional

from ..core.state_machine import State, StateMachine
from ..core.event_bus import EventType, get_event_bus

logger = logging.getLogger("tank.safety")


class SafetyController:
    def __init__(self, state_machine: StateMachine, timeout: float = 2.0) -> None:
        self._sm = state_machine
        self._bus = get_event_bus()
        self._timeout = timeout
        self._last_action_time = 0.0
        self._emergency = False
        self._watchdog_last = time.time()

    def check(self) -> bool:
        """Run safety checks. Returns True if safe to continue."""
        if self._emergency:
            return False

        # Watchdog: if no activity for timeout, safe stop
        if time.time() - self._watchdog_last > self._timeout:
            logger.warning("Watchdog timeout — triggering SAFE_STOP")
            self._sm.transition(State.SAFE_STOP, reason="watchdog_timeout")
            self._bus.emit(EventType.WATCHDOG_TIMEOUT, source="safety")
            return False

        # State guard: never act from unsafe states
        if self._sm.state in (State.SAFE_STOP, State.ERROR):
            return False

        return True

    def action_timeout(self) -> bool:
        """Check if current action has exceeded max duration."""
        if self._sm.state == State.ACTING:
            if time.time() - self._last_action_time > self._timeout:
                logger.warning("Action timeout — triggering SAFE_STOP")
                self._sm.transition(State.SAFE_STOP, reason="action_timeout")
                return True
        return False

    def emergency_stop(self) -> None:
        """Hardware E-stop triggered."""
        logger.critical("EMERGENCY STOP ACTIVATED")
        self._emergency = True
        self._sm.force(State.SAFE_STOP, reason="emergency_stop")
        self._bus.emit(EventType.SAFETY_STOP, source="estop")

    def reset_emergency(self) -> None:
        self._emergency = False
        self._sm.transition(State.IDLE, reason="emergency_reset")

    def feed_watchdog(self) -> None:
        self._watchdog_last = time.time()

    def on_action_start(self) -> None:
        self._last_action_time = time.time()
        self.feed_watchdog()

    def on_action_complete(self) -> None:
        self.feed_watchdog()

    def sensor_failure(self, sensor_name: str) -> None:
        logger.warning(f"Sensor failure: {sensor_name} — continuing with degraded mode")
        self._bus.emit(EventType.SENSOR_DISCONNECTED, source=sensor_name, data={"reason": "failure"})

    def health(self) -> Dict:
        return {
            "emergency": self._emergency,
            "watchdog_age": round(time.time() - self._watchdog_last, 2),
            "timeout": self._timeout,
            "state": self._sm.state.value,
        }
