"""AISupervisor — UNO Q local AI confidence arbitration (AI plan #146–150).

The UNO Q should never let a probabilistic model (LLM, local classifier,
network prediction) bypass motor/safety control. This supervisor implements
the principle from the UNO Q AI plan:

    AI can recommend. Safety can veto.

Every command candidate arrives tagged with a *source* and a *confidence*
score. The supervisor arbitrates between sources (Jetson command, manual
controller, local command parser, hardware safety, battery prediction) and
enforces:

    1. Hardware-safety sources have absolute veto power (confidence 1.00).
    2. The highest-confidence non-safety source wins the recommendation.
    3. If the winning candidate is rated DANGEROUS by the safety classifier
       and no safety source explicitly allows it, it is downgraded to a
       *needs-approval* verdict (never auto-executed).

This is deliberately deterministic — the arbitration is a small state
machine, not another LLM call — so it can be unit-tested exhaustively and
safely run on the STM32-facing control loop.

See docs/UNOQ_AI_PLAN.md items #146–150 (AI orchestration) and the
supervisor diagram in the plan.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank_os.ai_supervisor")

#: Hard ceiling for any probabilistic source. Hardware-safety sources are
#: the only ones allowed to sit at 1.00 (absolute veto).
MAX_AI_CONFIDENCE = 0.99


class Verdict(str, Enum):
    """Final decision for a command candidate after arbitration."""

    ALLOW = "allow"                 # safe to execute now
    RECOMMEND = "recommend"         # AI suggests it; needs approval path
    NEEDS_APPROVAL = "needs-approval"  # dangerous command, not auto-run
    VETO = "veto"                   # blocked by a safety source
    REJECT = "reject"               # lowest-confidence source loses


class SourceRole(str, Enum):
    """Role of a command source. Safety is special: it can veto."""

    SAFETY = "safety"               # hardware safety / E-STOP (veto power)
    MANUAL = "manual"               # human operator (high trust)
    AI = "ai"                       # LLM / classifier / predictor
    SYSTEM = "system"               # deterministic system policy


@dataclass
class CommandSource:
    """A named source that can propose commands, with a confidence score."""

    name: str
    role: SourceRole
    confidence: float = 0.5
    last_update: float = field(default_factory=time.time)

    def clamp(self) -> None:
        """Keep confidence in [0,1]; non-safety sources can't hit 1.00."""
        if self.role is SourceRole.SAFETY:
            self.confidence = min(1.0, max(0.0, self.confidence))
        else:
            self.confidence = min(MAX_AI_CONFIDENCE, max(0.0, self.confidence))


@dataclass
class ArbitrationResult:
    """Outcome of arbitrating one command candidate."""

    source: str
    command: str
    verdict: Verdict
    confidence: float
    reason: str = ""
    safety_class: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "command": self.command,
            "verdict": self.verdict.value,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "safety_class": self.safety_class,
        }


class AISupervisor:
    """Confidence-arbitration layer between AI sources and STM32 control.

    Usage::

        sup = AISupervisor()
        sup.register("jetson", SourceRole.AI, 0.94)
        sup.register("manual", SourceRole.MANUAL, 0.99)
        sup.register("local-parser", SourceRole.AI, 0.87)
        sup.register("hardware-safety", SourceRole.SAFETY, 1.00)
        sup.register("battery-pred", SourceRole.AI, 0.91)

        verdict = sup.arbitrate("forward 0.5", "local-parser")  # ALLOW etc.
    """

    _instance: Optional["AISupervisor"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AISupervisor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._sources: Dict[str, CommandSource] = {}
                cls._instance._safety_classifier = None
                cls._instance._history: List[ArbitrationResult] = []
            return cls._instance

    # ── Configuration ─────────────────────────────────────────────────

    def configure(self, *, safety_classifier=None) -> None:
        """Inject a safety classifier (callable: str -> SafetyClass)."""
        self._safety_classifier = safety_classifier

    def _classify(self, command: str) -> str:
        """Classify a command via the injected classifier, else 'unknown'."""
        if self._safety_classifier is None:
            return "unknown"
        try:
            cls = self._safety_classifier(command)
            return cls.name.lower() if hasattr(cls, "name") else str(cls)
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("safety classify failed: %s", exc)
            return "unknown"

    # ── Source registry (plan #149 — AI confidence arbitration) ───────

    def register(self, name: str, role: SourceRole,
                 confidence: float = 0.5) -> CommandSource:
        """Register (or update) a command source with a confidence score."""
        with self._lock:
            src = self._sources.get(name) or CommandSource(name=name, role=role)
            src.role = role
            src.confidence = confidence
            src.last_update = time.time()
            src.clamp()
            self._sources[name] = src
            return src

    def update_confidence(self, name: str, confidence: float) -> Optional[CommandSource]:
        """Update a source's confidence (e.g. battery predictor re-scores)."""
        with self._lock:
            src = self._sources.get(name)
            if src is None:
                return None
            src.confidence = confidence
            src.last_update = time.time()
            src.clamp()
            return src

    def sources(self) -> Dict[str, CommandSource]:
        with self._lock:
            return dict(self._sources)

    # ── Arbitration (plan #149) ───────────────────────────────────────

    def arbitrate(self, command: str, source: str) -> ArbitrationResult:
        """Decide whether ``command`` from ``source`` may reach STM32 control.

        Rules (deterministic):
          1. Unknown sources are REJECTed (never trust a stranger).
          2. A SAFETY source with confidence >= 1.0 can ALLOW or VETO.
          3. DANGEROUS commands from non-safety sources -> NEEDS_APPROVAL.
          4. Otherwise the highest-confidence non-safety source wins and
             the proposing source is compared against it.
        """
        src = self._sources.get(source)
        if src is None:
            return ArbitrationResult(source, command, Verdict.REJECT, 0.0,
                                     reason="unknown source")
        src.clamp()
        safety_class = self._classify(command)

        # 2) Safety source has absolute power (veto / explicit allow).
        if src.role is SourceRole.SAFETY:
            if src.confidence >= 1.0:
                verdict = Verdict.ALLOW if safety_class != "blocked" else Verdict.VETO
                reason = "hardware safety authorizes" if verdict is Verdict.ALLOW \
                    else "hardware safety veto"
                return self._record(ArbitrationResult(
                    source, command, verdict, src.confidence, reason, safety_class))

        # 3) Dangerous / blocked commands never auto-execute from AI.
        if safety_class in ("dangerous", "blocked"):
            verdict = Verdict.NEEDS_APPROVAL
            reason = f"classified {safety_class} — needs operator approval"
            return self._record(ArbitrationResult(
                source, command, verdict, src.confidence, reason, safety_class))

        # 4) Compare against the best other source; manual > AI on ties.
        best = self._best_source(exclude=source)
        if best is None:
            verdict = Verdict.ALLOW
            reason = "sole source, within trust budget"
        elif src.confidence >= best.confidence:
            verdict = Verdict.ALLOW
            reason = f"highest confidence ({best.name} {best.confidence:.2f})"
        else:
            verdict = Verdict.RECOMMEND
            reason = f"lower confidence than {best.name} ({best.confidence:.2f})"
        return self._record(ArbitrationResult(
            source, command, verdict, src.confidence, reason, safety_class))

    def _best_source(self, *, exclude: str) -> Optional[CommandSource]:
        """Highest-confidence non-safety source, ties to MANUAL first."""
        candidates = [
            s for n, s in self._sources.items()
            if n != exclude and s.role is not SourceRole.SAFETY
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda s: (s.confidence, s.role is SourceRole.MANUAL),
        )

    def _record(self, result: ArbitrationResult) -> ArbitrationResult:
        with self._lock:
            self._history.append(result)
            if len(self._history) > 200:
                self._history = self._history[-200:]
        return result

    # ── Reporting ─────────────────────────────────────────────────────

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.as_dict() for r in self._history[-limit:]]

    def report(self) -> Dict[str, Any]:
        """Confidence table — the arbitration board from the plan."""
        rows = sorted(self._sources.values(),
                      key=lambda s: s.confidence, reverse=True)
        return {
            "sources": [
                {"name": s.name, "role": s.role.value,
                 "confidence": round(s.confidence, 3),
                 "last_update": round(s.last_update, 1)}
                for s in rows
            ],
            "rule": "AI can recommend. Safety can veto.",
            "max_ai_confidence": MAX_AI_CONFIDENCE,
        }

    def safety_veto_active(self) -> bool:
        """True if a safety source is latched at veto confidence."""
        return any(
            s.role is SourceRole.SAFETY and s.confidence >= 1.0
            for s in self._sources.values()
        )
