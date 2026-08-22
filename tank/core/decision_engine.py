"""Tank — Decision Engine.

AI recommendations pass through: VALIDATION → SAFETY CHECK → DECISION → ACTION
AI must NEVER directly execute arbitrary commands.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .event_bus import Event, EventType, get_event_bus
from .state_machine import State, StateMachine

logger = logging.getLogger("tank.decision")


class ActionType(Enum):
    TRACK = "TRACK"
    APPROACH = "APPROACH"
    RETREAT = "RETREAT"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    STOP = "STOP"
    PATROL = "PATROL"
    REPORT = "REPORT"
    IDLE = "IDLE"
    SAFE_STOP = "SAFE_STOP"


@dataclass
class AIResult:
    object_name: str = "unknown"
    confidence: float = 0.0
    distance_m: float = 0.0
    situation: str = "unknown"
    recommended_action: str = "idle"
    priority: str = "normal"
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    action: ActionType
    reason: str
    confidence: float
    source: str
    timestamp: float = field(default_factory=time.time)
    params: Dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    def __init__(self, state_machine: StateMachine) -> None:
        self._sm = state_machine
        self._bus = get_event_bus()
        self._decision_history: List[Decision] = []
        self._max_history = 500

    def process(self, ai_result: AIResult) -> Optional[Decision]:
        # 1. Validate AI result
        if not self._validate(ai_result):
            logger.warning(f"AI result validation failed: {ai_result}")
            return None

        # 2. Safety check
        if not self._safety_check(ai_result):
            logger.warning(f"Safety check failed — issuing SAFE_STOP")
            self._sm.transition(State.SAFE_STOP, reason="safety_check_failed")
            return Decision(ActionType.SAFE_STOP, "safety check failed", 1.0, "safety")

        # 3. Generate decision
        decision = self._decide(ai_result)

        # 4. Log and emit
        self._decision_history.append(decision)
        if len(self._decision_history) > self._max_history:
            self._decision_history = self._decision_history[-self._max_history:]

        self._bus.emit(
            EventType.DECISION_CREATED,
            source="decision_engine",
            confidence=decision.confidence,
            data={"action": decision.action.value, "reason": decision.reason},
        )

        return decision

    def _validate(self, result: AIResult) -> bool:
        if result.confidence < 0.0 or result.confidence > 1.0:
            return False
        if result.distance_m < 0:
            return False
        if not result.object_name:
            return False
        return True

    def _safety_check(self, result: AIResult) -> bool:
        # Never approach unknown objects at very close range
        if result.object_name == "unknown" and result.distance_m < 0.3 and result.distance_m > 0:
            return False
        return True

    def _decide(self, result: AIResult) -> Decision:
        state = self._sm.state

        # State-dependent decisions
        if state in (State.SAFE_STOP, State.ERROR, State.OFFLINE):
            return Decision(ActionType.IDLE, "system not active", 1.0, "state_guard")

        if result.recommended_action == "track":
            return Decision(ActionType.TRACK, f"tracking {result.object_name}", result.confidence, "ai")
        elif result.recommended_action == "approach":
            return Decision(ActionType.APPROACH, f"approaching {result.object_name}", result.confidence, "ai")
        elif result.recommended_action == "retreat":
            return Decision(ActionType.RETREAT, f"retreating from {result.object_name}", result.confidence, "ai")
        elif result.recommended_action == "stop":
            return Decision(ActionType.STOP, "stop requested", result.confidence, "ai")
        else:
            return Decision(ActionType.IDLE, f"no action for {result.situation}", result.confidence, "default")

    def history(self, limit: int = 50) -> List[Decision]:
        return self._decision_history[-limit:]
