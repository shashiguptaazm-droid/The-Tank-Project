"""HumanCoordination — 👤 human-coordination subsystem (100-feature plan).

The robot understands who is commanding it, what humans are doing around it,
where they are, what they want, and when it should ask for permission instead
of acting autonomously.

Implements:
- Human presence & awareness (§1): person registry, distance/direction/velocity,
  approach/departure/stationary states, proximity zones, confidence.
- Human–robot interaction (§2): interaction state machine (FOLLOW, STOP,
  ESCORT, MAINTAIN_DISTANCE, MEET, RETURN_TO_OWNER, ...).
- Human intent AI (§5): intent classification, confidence, ambiguous-command
  detection, "Ask the human" clarification decisions.
- Human control arbitration (§6): CONTROL AUTHORITY (safety > human > mission
  > autonomy), current-controller indicator, command queue.
- Human + AI collaboration (§7): AI proposes → human APPROVE / MODIFY /
  REJECT → safety → robot. Human-in-the-loop autonomy.

Pure logic + tiny state machine — no GUI, deterministic, unit-testable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class InteractionMode(str, Enum):
    """Human–robot interaction mode (plan §2 #21–40)."""

    IDLE = "idle"
    FOLLOW = "follow"
    STOP = "stop"
    MAINTAIN_DISTANCE = "maintain-distance"
    MAINTAIN_ANGLE = "maintain-angle"
    ESCORT = "escort"
    LEAD = "lead"
    MEET = "meet"
    RETURN_TO_OWNER = "return-to-owner"
    HUMAN_GUIDED = "human-guided"


class PresenceState(str, Enum):
    """Human presence state (§1 #7–9)."""

    APPROACHING = "approaching"
    DEPARTING = "departing"
    STATIONARY = "stationary"
    CROSSING = "crossing"
    UNKNOWN = "unknown"


class ControlAuthority(str, Enum):
    """Who currently controls the robot (§6 #71–80)."""

    SAFETY = "safety"
    HUMAN = "human"
    MISSION = "mission"
    AUTONOMY = "autonomy"
    NONE = "none"


#: Explicit command chain — every action has a visible source (§22).
COMMAND_CHAIN = [
    "EMERGENCY STOP",
    "SAFETY CONTROLLER",
    "HUMAN",
    "MISSION EXECUTIVE",
    "AI",
    "AUTOMATION",
]

#: Interaction modes that keep the robot with a person.
FOLLOW_MODES = {InteractionMode.FOLLOW, InteractionMode.ESCORT,
                InteractionMode.LEAD, InteractionMode.MAINTAIN_DISTANCE}

PROXIMITY_ZONES = [("danger", 0.5), ("warning", 1.5), ("comfort", 3.0)]

#: Default safety confidence for human-vs-autonomy arbitration (1.00 = armed).
DEFAULT_SAFETY_CONF = 0.0


@dataclass
class Person:
    """One tracked human (§1 #2–6, #18)."""

    id: int
    distance_m: float = 5.0
    direction_deg: float = 0.0
    velocity_ms: float = 0.0
    confidence: float = 0.5
    presence: PresenceState = PresenceState.UNKNOWN
    status: str = "IDLE"
    zone: str = "outside"
    last_seen: float = field(default_factory=time.time)
    history: List[tuple] = field(default_factory=list)  # (t, distance)

    def update(self, distance_m: float, direction_deg: float,
               confidence: float, dt: float = 1.0) -> None:
        self.history.append((time.time(), self.distance_m))
        if len(self.history) > 200:
            self.history.pop(0)
        # Velocity signed toward the robot: negative = approaching.
        vel = (distance_m - self.distance_m) / max(dt, 0.01)
        self.velocity_ms = vel
        self.distance_m = distance_m
        self.direction_deg = direction_deg
        self.confidence = max(0.0, min(1.0, confidence))
        if vel < -0.15:
            self.presence = PresenceState.APPROACHING
        elif vel > 0.15:
            self.presence = PresenceState.DEPARTING
        else:
            self.presence = PresenceState.STATIONARY
        self.zone = next((z for z, dist in PROXIMITY_ZONES if distance_m <= dist),
                         "outside")
        self.last_seen = time.time()

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "distance_m": round(self.distance_m, 2),
            "direction_deg": round(self.direction_deg, 1),
            "velocity_ms": round(self.velocity_ms, 2),
            "confidence": round(self.confidence, 3),
            "presence": self.presence.value,
            "status": self.status,
            "zone": self.zone,
        }


@dataclass
class PermissionRequest:
    """AI proposes → human approves/rejects/modifies (§7 #81–90)."""

    id: int
    command: str
    reason: str
    proposer: str = "ai"
    status: str = "pending"          # pending / approved / rejected / modified
    modified_command: Optional[str] = None
    created: float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "command": self.command,
            "modified_command": self.modified_command,
            "reason": self.reason,
            "proposer": self.proposer,
            "status": self.status,
        }


@dataclass
class Clarification:
    """'Ask the human' — low-confidence ambiguity (§5 #63, #70)."""

    id: int
    question: str
    options: List[str]
    confidence: float
    context: str = ""
    answer: Optional[str] = None
    created: float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "confidence": round(self.confidence, 3),
            "context": self.context,
            "answer": self.answer,
        }


class HumanCoordination:
    """Singleton coordinator: people, interaction, authority, requests."""

    _instance: Optional["HumanCoordination"] = None

    def __new__(cls) -> "HumanCoordination":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._people: Dict[int, Person] = {}
            cls._instance._next_person = 1
            cls._instance._mode = InteractionMode.IDLE
            cls._instance._designated_id: Optional[int] = None
            cls._instance._authority = ControlAuthority.AUTONOMY
            cls._instance._requests: List[PermissionRequest] = []
            cls._instance._clarifications: List[Clarification] = []
            cls._instance._next_req = 1
            cls._instance._next_clar = 1
            cls._instance._interaction_history: List[str] = []
        return cls._instance

    # ------------------------------------------------------------ people
    def track_person(self, distance_m: float, direction_deg: float,
                     confidence: float, dt: float = 1.0) -> Person:
        """Register or update a person; returns the (possibly new) Person."""
        p = self._people.get(self._next_person)
        if p is None:
            p = Person(id=self._next_person)
            self._people[self._next_person] = p
        p.update(distance_m, direction_deg, confidence, dt)
        self._designated_id = self._designated_id or p.id
        return p

    def people(self) -> Dict[int, Person]:
        return dict(self._people)

    def nearest_person(self) -> Optional[Person]:
        if not self._people:
            return None
        return min(self._people.values(), key=lambda p: p.distance_m)

    def set_status(self, person_id: int, status: str) -> None:
        if person_id in self._people:
            self._people[person_id].status = status

    # ------------------------------------------------------- interaction
    def set_mode(self, mode: InteractionMode, person_id: Optional[int] = None) -> None:
        self._mode = mode
        if person_id is not None:
            self._designated_id = person_id
        if mode in FOLLOW_MODES and self._designated_id is None:
            self._designated_id = self._nearest_id()
        self._interaction_history.append(
            f"{time.strftime('%H:%M:%S')} mode -> {mode.value}")
        if len(self._interaction_history) > 100:
            self._interaction_history.pop(0)

    def mode(self) -> InteractionMode:
        return self._mode

    def designated_person(self) -> Optional[Person]:
        if self._designated_id is None:
            return None
        return self._people.get(self._designated_id)

    def _nearest_id(self) -> Optional[int]:
        p = self.nearest_person()
        return p.id if p else None

    # -------------------------------------------------------- arbitration
    def set_authority(self, authority: ControlAuthority) -> None:
        self._authority = authority
        self._interaction_history.append(
            f"{time.strftime('%H:%M:%S')} authority -> {authority.value}")

    def authority(self) -> ControlAuthority:
        return self._authority

    def controller_priority(self) -> List[ControlAuthority]:
        """Command chain in priority order (plan §22 / §6)."""
        return [ControlAuthority.SAFETY, ControlAuthority.HUMAN,
                ControlAuthority.MISSION, ControlAuthority.AUTONOMY]

    def human_takes_control(self) -> None:
        """§89 — human takes control."""
        self.set_authority(ControlAuthority.HUMAN)

    def autonomy_resumes(self) -> None:
        """§90 — AI hands control back."""
        self.set_authority(ControlAuthority.AUTONOMY)

    def mission_priority(self) -> None:
        self.set_authority(ControlAuthority.MISSION)

    def emergency_stop(self) -> None:
        """§75 — E-stop priority."""
        self.set_authority(ControlAuthority.SAFETY)
        self.set_mode(InteractionMode.STOP)

    # ------------------------------------------------------ collaboration
    def ai_propose(self, command: str, reason: str) -> PermissionRequest:
        """§81 — AI proposes an action; waits for human approval."""
        req = PermissionRequest(id=self._next_req, command=command, reason=reason)
        self._next_req += 1
        self._requests.append(req)
        self._interaction_history.append(
            f"{time.strftime('%H:%M:%S')} AI proposes: {command}")
        return req

    def pending_requests(self) -> List[PermissionRequest]:
        return [r for r in self._requests if r.status == "pending"]

    def approve(self, req_id: int) -> Optional[PermissionRequest]:
        """§82 — human approves."""
        for r in self._requests:
            if r.id == req_id and r.status == "pending":
                r.status = "approved"
                self._interaction_history.append(
                    f"{time.strftime('%H:%M:%S')} HUMAN approves: {r.command}")
                return r
        return None

    def reject(self, req_id: int) -> Optional[PermissionRequest]:
        """§83 — human rejects."""
        for r in self._requests:
            if r.id == req_id and r.status == "pending":
                r.status = "rejected"
                self._interaction_history.append(
                    f"{time.strftime('%H:%M:%S')} HUMAN rejects: {r.command}")
                return r
        return None

    def modify(self, req_id: int, new_command: str) -> Optional[PermissionRequest]:
        """§86 — human modifies the AI plan."""
        for r in self._requests:
            if r.id == req_id and r.status == "pending":
                r.status = "modified"
                r.modified_command = new_command
                self._interaction_history.append(
                    f"{time.strftime('%H:%M:%S')} HUMAN modifies: {new_command}")
                return r
        return None

    # ------------------------------------------------------ ask-the-human
    def ask_human(self, question: str, options: List[str], confidence: float,
                  context: str = "") -> Clarification:
        """§70 — when AI confidence is low, ask instead of guessing."""
        c = Clarification(id=self._next_clar, question=question,
                          options=options, confidence=confidence, context=context)
        self._next_clar += 1
        self._clarifications.append(c)
        self._interaction_history.append(
            f"{time.strftime('%H:%M:%S')} ASK HUMAN: {question}")
        return c

    def open_clarifications(self) -> List[Clarification]:
        return [c for c in self._clarifications if c.answer is None]

    def answer_clarification(self, clar_id: int, answer: str) -> Optional[Clarification]:
        for c in self._clarifications:
            if c.id == clar_id and c.answer is None:
                c.answer = answer
                self._interaction_history.append(
                    f"{time.strftime('%H:%M:%S')} HUMAN answers: {answer}")
                return c
        return None

    def resolve_route_ambiguity(self, confidence: float,
                                options: Optional[List[str]] = None) -> Clarification:
        """The signature demo: two possible routes, low AI confidence → ask."""
        return self.ask_human(
            "I found two possible routes. Which should I take?",
            options or ["LEFT", "RIGHT"],
            confidence=confidence,
            context="route-ambiguity")

    def human_priority_check(self, human_conf: float, ai_conf: float,
                             safety_conf: float = DEFAULT_SAFETY_CONF) -> str:
        """§68/§69 — human-vs-autonomy arbitration summary."""
        if safety_conf >= 0.99:
            return "safety-veto"
        if human_conf >= ai_conf:
            return "human"
        return "autonomy"

    def interaction_history(self, limit: int = 30) -> List[str]:
        return list(self._interaction_history[-limit:])

    # ----------------------------------------------------------- reset
    def reset(self) -> None:
        self._people.clear()
        self._requests.clear()
        self._clarifications.clear()
        self._mode = InteractionMode.IDLE
        self._authority = ControlAuthority.AUTONOMY
        self._designated_id = None
