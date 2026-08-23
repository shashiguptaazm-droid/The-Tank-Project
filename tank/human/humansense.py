"""
TankOS HumanSense
===================
Human Detection & Interaction Engine.

Pipeline: Detect -> Track -> Understand Intent -> Coordinate -> Respond -> Remember

Principle: Detect -> Understand -> Respect -> Respond -> Verify -> Remember
"""

from __future__ import annotations
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("tank.human")


class HumanState(Enum):
    UNKNOWN = "unknown"
    DETECTED = "detected"
    OBSERVING = "observing"
    APPROACHING = "approaching"
    AVAILABLE = "available"
    INTERACTING = "interacting"
    BUSY = "busy"
    LEAVING = "leaving"


class InteractionType(Enum):
    NONE = "none"
    VOICE = "voice"
    GESTURE = "gesture"
    REMOTE = "remote"
    PROXIMITY = "proximity"
    COMMAND = "command"


class GestureType(Enum):
    NONE = "none"
    WAVE = "wave"
    POINT = "point"
    STOP = "stop"
    CONFIRM = "confirm"
    REJECT = "reject"
    DIRECTION = "direction"
    SELECT = "select"


@dataclass
class HumanDetection:
    """Single human detection."""
    detection_id: str = ""
    position: dict = field(default_factory=lambda: {"x": 0, "y": 0, "z": 0})
    distance: float = 0.0
    direction: str = "unknown"
    velocity: dict = field(default_factory=lambda: {"vx": 0, "vy": 0})
    motion: str = "stationary"  # stationary, walking, running, approaching, departing
    state: HumanState = HumanState.DETECTED
    gesture: GestureType = GestureType.NONE
    interaction_probability: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class InteractionSession:
    """Active interaction with a human."""
    session_id: str = ""
    human_id: str = ""
    interaction_type: InteractionType = InteractionType.NONE
    start_time: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)
    status: str = "active"


class HumanSense:
    """Main human interaction engine."""

    # Safety zones (meters)
    INTERACTION_ZONE = 2.0
    CAUTION_ZONE = 1.0
    CRITICAL_ZONE = 0.5

    def __init__(self):
        self._detections: list[HumanDetection] = []
        self._tracked: dict[str, HumanDetection] = {}
        self._sessions: list[InteractionSession] = []
        self._active_session: Optional[InteractionSession] = None
        self._interaction_count = 0

    def process_frame(self, detections: list[dict]) -> list[HumanDetection]:
        """Process vision detections and update human state."""
        result = []
        seen_ids = set()

        for det in detections:
            hd = HumanDetection(
                detection_id=det.get("id", f"h{len(result)}"),
                position=det.get("position", {}),
                distance=det.get("distance", 0),
                direction=det.get("direction", "unknown"),
                velocity=det.get("velocity", {}),
                motion=self._classify_motion(det),
                confidence=det.get("confidence", 0.8)
            )
            hd.state = self._determine_state(hd)
            hd.gesture = self._detect_gesture(det)
            hd.interaction_probability = self._estimate_interaction(hd)

            result.append(hd)
            seen_ids.add(hd.detection_id)
            self._tracked[hd.detection_id] = hd

        # Mark missing detections as leaving
        for hid, tracked in list(self._tracked.items()):
            if hid not in seen_ids:
                tracked.state = HumanState.LEAVING
                tracked.timestamp = time.time()

        self._detections = result
        return result

    def get_nearest_human(self) -> Optional[HumanDetection]:
        if not self._detections:
            return None
        return min(self._detections, key=lambda d: d.distance)

    def get_human_count(self) -> int:
        return len([d for d in self._detections
                   if d.state != HumanState.LEAVING])

    def get_interaction_state(self) -> dict:
        nearest = self.get_nearest_human()
        return {
            "humans_detected": self.get_human_count(),
            "nearest_distance": nearest.distance if nearest else None,
            "nearest_direction": nearest.direction if nearest else None,
            "interaction_active": self._active_session is not None,
            "interaction_count": self._interaction_count,
            "any_approaching": any(d.state == HumanState.APPROACHING
                                  for d in self._detections),
            "any_gesture": any(d.gesture != GestureType.NONE
                              for d in self._detections),
        }

    def should_offer_interaction(self) -> bool:
        """Determine if robot should proactively offer interaction."""
        nearest = self.get_nearest_human()
        if not nearest:
            return False
        if (nearest.interaction_probability > 0.7 and
            nearest.distance < self.INTERACTION_ZONE and
            nearest.state in (HumanState.AVAILABLE, HumanState.APPROACHING)):
            return True
        return False

    def start_interaction(self, human_id: str = "auto") -> InteractionSession:
        session = InteractionSession(
            session_id=f"int-{self._interaction_count}",
            human_id=human_id
        )
        self._active_session = session
        self._sessions.append(session)
        self._interaction_count += 1
        return session

    def end_interaction(self):
        if self._active_session:
            self._active_session.status = "completed"
            self._active_session = None

    def handle_gesture(self, gesture: GestureType) -> dict:
        """Interpret a gesture into a robot command."""
        gesture_commands = {
            GestureType.WAVE: {"action": "greet", "voice": "Hello!"},
            GestureType.STOP: {"action": "stop", "priority": "high"},
            GestureType.CONFIRM: {"action": "confirm", "voice": "Acknowledged"},
            GestureType.REJECT: {"action": "cancel", "voice": "Cancelled"},
            GestureType.POINT: {"action": "look_at_direction"},
            GestureType.DIRECTION: {"action": "navigate_direction"},
        }
        return gesture_commands.get(gesture, {"action": "none"})

    def get_safety_status(self) -> dict:
        """Check if any human is in a safety-critical zone."""
        for det in self._detections:
            if det.distance < self.CRITICAL_ZONE:
                return {
                    "safe": False,
                    "reason": f"Human at {det.distance:.1f}m (critical zone)",
                    "human_id": det.detection_id
                }
        return {"safe": True, "reason": "No humans in critical zone"}

    def _classify_motion(self, det: dict) -> str:
        vel = det.get("velocity", {})
        speed = (vel.get("vx", 0)**2 + vel.get("vy", 0)**2) ** 0.5
        if speed < 0.1:
            return "stationary"
        elif speed < 1.0:
            return "walking"
        else:
            return "running"

    def _determine_state(self, hd: HumanDetection) -> HumanState:
        if hd.distance < self.INTERACTION_ZONE and hd.interaction_probability > 0.6:
            return HumanState.AVAILABLE
        if hd.motion == "approaching" or (hd.velocity.get("vy", 0) < -0.3):
            return HumanState.APPROACHING
        if hd.motion in ("walking", "running") and hd.velocity.get("vy", 0) > 0.3:
            return HumanState.LEAVING
        if hd.distance < self.INTERACTION_ZONE:
            return HumanState.OBSERVING
        return HumanState.DETECTED

    def _detect_gesture(self, det: dict) -> GestureType:
        gesture_str = det.get("gesture", "none").lower()
        try:
            return GestureType(gesture_str)
        except ValueError:
            return GestureType.NONE

    def _estimate_interaction(self, hd: HumanDetection) -> float:
        prob = 0.0
        if hd.distance < self.INTERACTION_ZONE:
            prob += 0.3
        if hd.motion == "approaching":
            prob += 0.3
        if hd.gesture != GestureType.NONE:
            prob += 0.2
        if hd.distance < self.CAUTION_ZONE:
            prob += 0.2
        return min(1.0, prob)

    def get_status(self) -> dict:
        return {
            "humans_detected": self.get_human_count(),
            "tracked_total": len(self._tracked),
            "interaction_active": self._active_session is not None,
            "total_interactions": self._interaction_count,
            "safety": self.get_safety_status(),
        }


# Global singleton
HUMANSENSE = HumanSense()
