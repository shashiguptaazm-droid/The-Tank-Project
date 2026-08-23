"""Robot Constitution — 🌟 the Tank's machine-readable priority policy.

Idea #25 from the originality plan: a set of priorities every AI action
passes through. Plus idea #21 — the AI Debate: multiple lightweight decision
modules (vision / navigation / safety / resource) vote, safety wins, and the
final decision is fully explainable.

THE TANK CONSTITUTION
  1. Protect humans.
  2. Never bypass safety.
  3. Obey authorized human commands.
  4. Preserve hardware.
  5. Complete mission.
  6. Minimize energy consumption.
  7. Ask for help when uncertain.
  8. Report failures honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


class Article(IntEnum):
    """Constitution articles, in priority order (1 = highest)."""

    PROTECT_HUMANS = 1
    NEVER_BYPASS_SAFETY = 2
    OBEY_AUTHORIZED_HUMANS = 3
    PRESERVE_HARDWARE = 4
    COMPLETE_MISSION = 5
    MINIMIZE_ENERGY = 6
    ASK_WHEN_UNCERTAIN = 7
    REPORT_FAILURES_HONESTLY = 8


ARTICLES: Dict[Article, str] = {
    Article.PROTECT_HUMANS: "Protect humans.",
    Article.NEVER_BYPASS_SAFETY: "Never bypass safety.",
    Article.OBEY_AUTHORIZED_HUMANS: "Obey authorized human commands.",
    Article.PRESERVE_HARDWARE: "Preserve hardware.",
    Article.COMPLETE_MISSION: "Complete mission.",
    Article.MINIMIZE_ENERGY: "Minimize energy consumption.",
    Article.ASK_WHEN_UNCERTAIN: "Ask for help when uncertain.",
    Article.REPORT_FAILURES_HONESTLY: "Report failures honestly.",
}


@dataclass
class PolicyVerdict:
    """Outcome of checking an action against the constitution."""

    allowed: bool
    action: str
    article: Optional[Article] = None
    reason: str = ""
    triggers: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "article": int(self.article) if self.article else None,
            "article_text": ARTICLES.get(self.article, "") if self.article else "",
            "reason": self.reason,
            "triggers": self.triggers,
        }


@dataclass
class DebateVote:
    """One module's vote in the AI Debate (idea #21)."""

    module: str
    decision: str          # GO / STOP / LEFT / RIGHT / HOLD ...
    confidence: float
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "module": self.module,
            "decision": self.decision,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


@dataclass
class DebateResult:
    """Aggregated debate outcome — safety wins, fully explainable."""

    votes: List[DebateVote]
    final: str
    winner: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "votes": [v.as_dict() for v in self.votes],
            "final": self.final,
            "winner": self.winner,
            "reason": self.reason,
        }


class RobotConstitution:
    """Policy engine — every AI action passes through the constitution."""

    _instance: Optional["RobotConstitution"] = None

    def __new__(cls) -> "RobotConstitution":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._audit: List[dict] = []
        return cls._instance

    # ------------------------------------------------------------ policy
    def check(self, action: str, *, human_near: bool = False,
              obstacle_m: Optional[float] = None,
              battery_pct: Optional[int] = None,
              low_confidence: bool = False,
              authorized_human: bool = False,
              collision_risk: Optional[float] = None) -> PolicyVerdict:
        """Evaluate an action against the constitution articles."""
        triggers: List[str] = []

        if human_near or (obstacle_m is not None and obstacle_m < 0.5):
            triggers.append("Article 1 — Protect humans")
            if action.lower().startswith(("move", "drive", "forward", "reverse")):
                return PolicyVerdict(
                    False, action, Article.PROTECT_HUMANS,
                    "Human detected / obstacle < 0.5 m — motion vetoed.",
                    triggers)

        if collision_risk is not None and collision_risk >= 0.5:
            triggers.append("Article 2 — Never bypass safety")
            return PolicyVerdict(
                False, action, Article.NEVER_BYPASS_SAFETY,
                f"Collision probability {collision_risk:.0%} ≥ 50% — safety veto.",
                triggers)

        if battery_pct is not None and battery_pct <= 10 and \
                action.lower().startswith(("move", "drive", "mission")):
            triggers.append("Article 4 — Preserve hardware")
            return PolicyVerdict(
                False, action, Article.PRESERVE_HARDWARE,
                f"Battery {battery_pct}% critical — hardware protection stop.",
                triggers)

        if low_confidence and action.lower().startswith(("move", "drive")):
            triggers.append("Article 7 — Ask for help when uncertain")
            return PolicyVerdict(
                False, action, Article.ASK_WHEN_UNCERTAIN,
                "AI confidence too low — must ask the human first.",
                triggers)

        if not authorized_human and action.lower().startswith("sudo"):
            triggers.append("Article 3 — Obey authorized human commands")
            return PolicyVerdict(
                False, action, Article.OBEY_AUTHORIZED_HUMANS,
                "Command requires authorized human — rejected.",
                triggers)

        return PolicyVerdict(True, action, reason="All articles satisfied.")

    def audit(self, verdict: PolicyVerdict) -> None:
        self._audit.append({**verdict.as_dict(), "t": __import__("time").time()})
        if len(self._audit) > 200:
            self._audit.pop(0)

    def audit_log(self, limit: int = 30) -> List[dict]:
        return list(self._audit[-limit:])

    # -------------------------------------------------------- AI debate
    def debate(self, action: str, *, vision_go: bool = True,
               nav_go: bool = True, safety_go: bool = True,
               battery_ok: bool = True,
               vision_conf: float = 0.9, nav_conf: float = 0.85,
               safety_conf: float = 1.0, battery_conf: float = 0.91) -> DebateResult:
        """Run the multi-module debate (idea #21). Safety wins."""
        votes = [
            DebateVote("VISION", "GO" if vision_go else "STOP", vision_conf,
                       "detections clear" if vision_go else "obstacle in view"),
            DebateVote("NAVIGATION", "GO" if nav_go else "STOP", nav_conf,
                       "path free" if nav_go else "no valid path"),
            DebateVote("SAFETY", "GO" if safety_go else "STOP", safety_conf,
                       "all clear" if safety_go else "collision risk ≥ 50%"),
            DebateVote("BATTERY", "GO" if battery_ok else "STOP", battery_conf,
                       "energy sufficient" if battery_ok else "battery critical"),
        ]
        stops = [v for v in votes if v.decision == "STOP"]
        if stops:
            winner = max(stops, key=lambda v: v.confidence)
            return DebateResult(
                votes, "STOP", winner.module,
                f"{winner.module} vetoes — {winner.reason} (conf {winner.confidence:.2f}). "
                "Safety wins over action.")
        # All GO — the highest-confidence module's plan wins.
        best = max(votes, key=lambda v: v.confidence)
        return DebateResult(
            votes, f"GO ({action})", best.module,
            f"All modules agree — highest confidence {best.module} "
            f"({best.confidence:.2f}) leads.")

    def command_chain_for(self, source: str) -> str:
        """Idea #22 — make authority explicit: this action came from …"""
        mapping = {
            "safety": "EMERGENCY STOP → SAFETY CONTROLLER",
            "human": "HUMAN → SAFETY CONTROLLER",
            "mission": "MISSION EXECUTIVE → HUMAN → SAFETY CONTROLLER",
            "ai": "AI → MISSION EXECUTIVE → HUMAN → SAFETY CONTROLLER",
            "automation": "AUTOMATION → AI → MISSION EXECUTIVE → HUMAN → SAFETY CONTROLLER",
        }
        return mapping.get(source, f"{source.upper()} → SAFETY CONTROLLER")

    def reset(self) -> None:
        self._audit.clear()
