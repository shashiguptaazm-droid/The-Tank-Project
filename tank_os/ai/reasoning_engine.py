"""TankOS Reasoning Engine — logical decision-making with LLM + memory + fallback.

Takes context, memory, goals, and sensor data, then reasons through
options before acting. Supports multi-step reasoning, confidence
scoring, and graceful fallback when the LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.reasoning")


# ── Data models ─────────────────────────────────────────────────────────

class ReasoningDepth(Enum):
    """Depth of reasoning to apply."""
    QUICK = "quick"          # < 1s, rule-based only
    NORMAL = "normal"        # 1-5s, LLM if available
    DEEP = "deep"            # 5-30s, full LLM + memory retrieval
    CRITICAL = "critical"    # 30s+, exhaustive analysis


@dataclass
class ReasoningContext:
    """Input context for a reasoning request."""
    query: str
    depth: ReasoningDepth = ReasoningDepth.NORMAL
    available_actions: List[str] = field(default_factory=list)
    sensor_data: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    source: str = ""


@dataclass
class ReasoningResult:
    """Output of a reasoning step."""
    decision: str
    confidence: float               # 0.0 - 1.0
    reasoning_path: List[str]       # Chain of thought
    alternatives: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class Decision:
    """A recorded decision for audit and later reflection."""
    id: str
    context: str
    decision: str
    confidence: float
    reasoning_path: List[str]
    outcome: str = "pending"    # "pending", "success", "failure"
    timestamp: float = field(default_factory=time.time)


# ── Rules ───────────────────────────────────────────────────────────────

class ReasoningRule:
    """A simple if-then reasoning rule for quick decisions."""
    def __init__(self, name: str, condition: Callable[[ReasoningContext], bool],
                 conclusion: str, confidence: float = 0.8):
        self.name = name
        self.condition = condition
        self.conclusion = conclusion
        self.confidence = confidence

    def evaluate(self, ctx: ReasoningContext) -> Optional[Tuple[str, float, str]]:
        """Evaluate rule; returns (conclusion, confidence, rule_name) or None."""
        try:
            if self.condition(ctx):
                return (self.conclusion, self.confidence, self.name)
        except Exception as e:
            logger.warning("Rule '%s' failed: %s", self.name, e)
        return None


# ── Built-in safety rules ───────────────────────────────────────────────

_builtin_rules = [
    ReasoningRule(
        "estop_override", lambda ctx: any("estop" in a for a in ctx.available_actions),
        "Emergency stop — immediate halt", 1.0,
    ),
    ReasoningRule(
        "low_battery_safety",
        lambda ctx: ctx.sensor_data.get("battery_pct", 100) < 15,
        "Low battery — return to dock and charge", 0.95,
    ),
    ReasoningRule(
        "collision_avoidance",
        lambda ctx: ctx.sensor_data.get("obstacle_distance", 10) < 0.3,
        "Obstacle too close — stop and replan", 0.9,
    ),
    ReasoningRule(
        "high_temp_safety",
        lambda ctx: ctx.sensor_data.get("cpu_temp", 40) > 80,
        "CPU temperature critical — reduce load", 0.85,
    ),
    ReasoningRule(
        "no_op_when_charging",
        lambda ctx: ctx.sensor_data.get("charging", False),
        "Currently charging — postpone non-critical actions", 0.9,
    ),
]


# ── Reasoning Engine ────────────────────────────────────────────────────

class ReasoningEngine:
    """Central reasoning engine — makes decisions using rules, LLM, and memory.

    Uses a layered approach:
    1. Safety rules (always checked first, highest priority)
    2. Quick rules (pattern-based, no LLM needed)
    3. LLM reasoning (deep analysis with chain-of-thought)
    4. Memory-informed decisions (retrieves similar past situations)

    Usage:
        engine = ReasoningEngine()
        engine.initialize()

        ctx = ReasoningContext(
            query="Should I patrol the house?",
            available_actions=["patrol", "dock", "charge"],
            sensor_data={"battery_pct": 65, "obstacle_distance": 5.0},
        )
        result = engine.reason(ctx)
    """

    _instance: Optional["ReasoningEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._rules = list(_builtin_rules)
                cls._instance._decisions: List[Decision] = []
                cls._instance._learned_rules: List[ReasoningRule] = []
                cls._instance._llm_available = False
                cls._instance._store_path = None
            return cls._instance

    def initialize(self) -> None:
        """Initialize the reasoning engine."""
        self._check_llm()
        self._bus.on("reasoning_request", self._on_reasoning_request)
        self._bus.on("decision_outcome", self._on_decision_outcome)
        logger.info("ReasoningEngine initialized (%d rules, LLM=%s)",
                     len(self._rules), self._llm_available)

    def _check_llm(self) -> None:
        """Check if a local LLM is available for deep reasoning."""
        try:
            # Check for llama-cpp-python or similar
            import importlib
            self._llm_available = importlib.util.find_spec("llama_cpp") is not None
        except Exception:
            self._llm_available = False

    def add_rule(self, rule: ReasoningRule) -> None:
        """Add a custom reasoning rule."""
        self._rules.append(rule)

    # ── Core reasoning ────────────────────────────────────────────────

    def reason(self, ctx: ReasoningContext) -> ReasoningResult:
        """Run reasoning on a context and return a decision.

        Layers checked in order: safety → rules → LLM → memory.
        Returns as soon as a high-confidence decision is reached.
        """
        start = time.time()

        # Layer 1: Safety rules (always checked, highest priority)
        for rule in self._rules:
            result = rule.evaluate(ctx)
            if result:
                conclusion, confidence, rule_name = result
                if confidence >= 0.9:  # Safety-critical threshold
                    elapsed = (time.time() - start) * 1000
                    return ReasoningResult(
                        decision=conclusion,
                        confidence=confidence,
                        reasoning_path=[f"Safety rule '{rule_name}' triggered"],
                        duration_ms=elapsed,
                    )

        # Layer 2: Quick rule-based reasoning
        candidates = []
        for rule in self._rules:
            result = rule.evaluate(ctx)
            if result:
                candidates.append(result)
        if candidates:
            candidates.sort(key=lambda x: -x[1])  # Sort by confidence
            best = candidates[0]
            if best[1] >= 0.8:
                elapsed = (time.time() - start) * 1000
                return ReasoningResult(
                    decision=best[0],
                    confidence=best[1],
                    reasoning_path=[f"Rule '{best[2]}' matched"],
                    duration_ms=elapsed,
                )

        # Layer 3: LLM deep reasoning (best quality)
        if self._llm_available and ctx.depth in (ReasoningDepth.DEEP, ReasoningDepth.CRITICAL):
            try:
                return self._llm_reason(ctx, start)
            except Exception as e:
                logger.warning("LLM reasoning failed: %s", e)

        # Layer 4: Memory-informed decision (fallback)
        memory_decision = self._memory_reason(ctx)
        if memory_decision:
            elapsed = (time.time() - start) * 1000
            memory_decision.duration_ms = elapsed
            return memory_decision

        # Layer 5: Default safe decision
        elapsed = (time.time() - start) * 1000
        return ReasoningResult(
            decision=f"Unable to determine best action for: {ctx.query[:50]}",
            confidence=0.3,
            reasoning_path=["No rules matched, LLM unavailable, no relevant memories"],
            alternatives=ctx.available_actions[:3],
            risks=["Default decision — confidence is low"],
            duration_ms=elapsed,
        )

    def _llm_reason(self, ctx: ReasoningContext, start: float) -> ReasoningResult:
        """Use LLM for deep reasoning (requires loaded model)."""
        if not self._llm_available:
            return self._memory_reason(ctx)
        try:
            from llama_cpp import Llama
            # Find best available GGUF model
            from pathlib import Path
            llm_dir = Path("/var/lib/tank_os/models/llm")
            models = list(llm_dir.glob("*.gguf"))
            if not models:
                return self._memory_reason(ctx)

            model_path = str(models[0])
            llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)

            prompt = f"""Analyze this situation and decide the best action.

Query: {ctx.query}
Available actions: {', '.join(ctx.available_actions)}
Sensors: {json.dumps(ctx.sensor_data, default=str)}
Goals: {', '.join(ctx.goals)}
Constraints: {', '.join(ctx.constraints)}

Output JSON only: {{"decision": "...", "confidence": 0.0-1.0, "reasoning": ["..."], "risks": ["..."]}}
"""
            output = llm.create_completion(prompt, max_tokens=256, temperature=0.1)
            text = output.get("choices", [{}])[0].get("text", "")

            # Try to parse JSON from output
            import re
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                data = json.loads(json_match.group())
                elapsed = (time.time() - start) * 1000
                return ReasoningResult(
                    decision=data.get("decision", "No decision"),
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning_path=data.get("reasoning", ["LLM reasoning"]),
                    risks=data.get("risks", []),
                    duration_ms=elapsed,
                )
        except Exception as e:
            logger.warning("LLM reasoning failed: %s", e)

        return self._memory_reason(ctx)

    def _memory_reason(self, ctx: ReasoningContext) -> Optional[ReasoningResult]:
        """Use historical decisions to inform reasoning."""
        try:
            from tank_os.core.memory_manager import MemoryManager
            mem = MemoryManager()
            similar = mem.recall(ctx.query, limit=5)
            if similar:
                decisions = []
                for entry in similar:
                    if entry.tags and "decision" in entry.tags:
                        decisions.append(entry.content)
                if decisions:
                    return ReasoningResult(
                        decision=f"Based on past experience: {decisions[0][:100]}",
                        confidence=0.6,
                        reasoning_path=["Retrieved from memory", f"Found {len(decisions)} relevant decisions"],
                        duration_ms=0,
                    )
        except Exception:
            pass
        return None

    # ── Event handlers ────────────────────────────────────────────────

    def _on_reasoning_request(self, event: Event) -> None:
        """Handle reasoning requests from the EventBus."""
        ctx_data = event.data
        ctx = ReasoningContext(
            query=ctx_data.get("query", ""),
            depth=ReasoningDepth(ctx_data.get("depth", "normal")),
            available_actions=ctx_data.get("available_actions", []),
            sensor_data=ctx_data.get("sensor_data", {}),
            goals=ctx_data.get("goals", []),
            constraints=ctx_data.get("constraints", []),
            source=event.source,
        )
        result = self.reason(ctx)

        # Log the decision
        decision = Decision(
            id=str(uuid.uuid4())[:8],
            context=ctx.query[:100],
            decision=result.decision[:100],
            confidence=result.confidence,
            reasoning_path=result.reasoning_path,
        )
        self._decisions.append(decision)

        self._bus.emit(Event("reasoning_result", {
            "id": decision.id,
            "decision": result.decision,
            "confidence": result.confidence,
            "reasoning": result.reasoning_path,
            "risks": result.risks,
            "duration_ms": result.duration_ms,
        }, source="reasoning_engine", priority=Priority.HIGH))

    def _on_decision_outcome(self, event: Event) -> None:
        """Record the outcome of a previous decision (for learning)."""
        decision_id = event.data.get("decision_id", "")
        outcome = event.data.get("outcome", "unknown")
        for d in self._decisions:
            if d.id == decision_id:
                d.outcome = outcome
                break

    # ── Queries ───────────────────────────────────────────────────────

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent decisions for audit."""
        recent = sorted(self._decisions, key=lambda d: d.timestamp, reverse=True)[:limit]
        return [{"id": d.id, "context": d.context, "decision": d.decision,
                 "confidence": d.confidence, "outcome": d.outcome} for d in recent]

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        total = len(self._decisions)
        succeeded = sum(1 for d in self._decisions if d.outcome == "success")
        failed = sum(1 for d in self._decisions if d.outcome == "failure")
        return {
            "total_decisions": total,
            "success_rate": round(succeeded / total, 2) if total else 0,
            "failed_count": failed,
            "rule_count": len(self._rules),
            "llm_available": self._llm_available,
        }
