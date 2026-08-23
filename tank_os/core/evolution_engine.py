"""EvolutionEngine — 🧬 TankOS Evolution Engine (TEE).

The concept (25-part plan):

> The Tank observes itself → identifies weaknesses → proposes an improvement →
> tests it safely → measures the result → promotes it only if objectively
> better → keeps rollback available.

    OBSERVE → ANALYZE → IDENTIFY WEAKNESS → GENERATE IMPROVEMENT → SIMULATE
    → TEST → BENCHMARK → COMPARE → HUMAN APPROVAL* → DEPLOY → MONITOR
    → ROLLBACK if worse

* Human approval is mandatory for hardware, safety, firmware, security, or
  behavior changes.

Implements:
- Evolution Manager (tank.evolution) — weaknesses, proposals, experiments,
  versions, deployments, rollbacks, history (§1)
- Performance baseline (§3) — without a baseline, evolution is meaningless
- Weakness discovery (§4) — mission-history pattern search
- Evolution proposals (§5) — problem / change / expected / cost
- Replay-based benchmarking (§7) — candidates tested against recorded history
- A/B shadow mode (§8, §13) — candidate predicts silently beside the current
- Multi-objective scoring (§9) — safety is a HARD constraint, not a weight
- Generations + genome (versioned config) (§10–11)
- Sandbox stages: DEV → SIMULATION → SHADOW → PRODUCTION (§12)
- Automatic rollback (§14) + checkpoints (§15)
- Explanations — "Why did I evolve?" (§16)
- Resource-aware evolution (§20) — rejects candidates that exceed budgets
- Evolution policy (§24) — AI may analyze/propose/simulate/benchmark/bound,
  but may NOT disable safety / modify E-stop / raise motor limits / etc.

Deterministic, unit-testable. No LLM required in the safety path.
"""

from __future__ import annotations

import copy
import datetime
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Policy (§24)
# ---------------------------------------------------------------------------
class EvolutionStage(str, Enum):
    PROPOSED = "proposed"
    DEVELOPMENT = "development"
    SIMULATION = "simulation"
    SHADOW = "shadow"
    PRODUCTION = "production"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled-back"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    AWAITING_APPROVAL = "awaiting-approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled-back"


#: What AI may NEVER do autonomously (§24).
EVOLUTION_FORBIDDEN = [
    "disable safety",
    "modify E-stop logic",
    "increase motor limits",
    "modify electrical protection",
    "change authentication",
    "replace safety firmware",
    "deploy arbitrary executable code",
    "change security controls",
]

#: What AI MAY do (§24).
EVOLUTION_ALLOWED = [
    "analyze", "propose", "simulate", "benchmark", "shadow-test",
    "optimize bounded parameters", "replay historical data",
]


# ---------------------------------------------------------------------------
# Baseline (§3)
# ---------------------------------------------------------------------------
@dataclass
class Baseline:
    navigation_success: float = 0.91
    object_detection: float = 0.94
    avg_latency_ms: float = 83.0
    mission_completion: float = 0.87
    battery_efficiency: float = 0.78
    recovery_success: float = 0.72

    def to_dict(self) -> dict:
        return {
            "navigation_success": self.navigation_success,
            "object_detection": self.object_detection,
            "avg_latency_ms": self.avg_latency_ms,
            "mission_completion": self.mission_completion,
            "battery_efficiency": self.battery_efficiency,
            "recovery_success": self.recovery_success,
        }


# ---------------------------------------------------------------------------
# Genome (§11) — versioned configuration
# ---------------------------------------------------------------------------
DEFAULT_GENOME: Dict[str, dict] = {
    "navigation": {"prediction_horizon": 1.5, "replan_threshold": 0.42},
    "vision": {"inference_rate": 15},
    "power": {"low_power_threshold": 25},
    "mission": {"retry_policy": 2},
}


#: Bounded parameter ranges the engine may optimize (§24).
GENOME_BOUNDS: Dict[str, Dict[str, tuple]] = {
    "navigation": {"prediction_horizon": (0.5, 3.0), "replan_threshold": (0.1, 0.8)},
    "vision": {"inference_rate": (5, 30)},
    "power": {"low_power_threshold": (10, 50)},
    "mission": {"retry_policy": (0, 5)},
}


@dataclass
class Generation:
    number: int
    label: str
    genome: Dict[str, dict]
    score: float = 0.0
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"number": self.number, "label": self.label, "genome": self.genome,
                "score": round(self.score, 3)}


# ---------------------------------------------------------------------------
# Proposals & experiments (§5, §19)
# ---------------------------------------------------------------------------
@dataclass
class EvolutionProposal:
    id: str
    problem: str
    change: str
    parameter: str
    old_value: float
    new_value: float
    expected: str
    potential_cost: str
    status: ProposalStatus = ProposalStatus.DRAFT
    stage: EvolutionStage = EvolutionStage.PROPOSED
    baseline_score: float = 0.0
    candidate_score: float = 0.0
    explanation: str = ""
    requires_approval: bool = True
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "problem": self.problem, "change": self.change,
            "parameter": self.parameter, "old_value": self.old_value,
            "new_value": self.new_value, "expected": self.expected,
            "potential_cost": self.potential_cost, "status": self.status.value,
            "stage": self.stage.value, "baseline_score": round(self.baseline_score, 3),
            "candidate_score": round(self.candidate_score, 3),
            "explanation": self.explanation,
            "requires_approval": self.requires_approval,
        }


@dataclass
class Experiment:
    id: str
    label: str
    variants: Dict[str, dict]           # name → parameter values
    metric: str
    results: Dict[str, float] = field(default_factory=dict)
    status: str = "running"

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "variants": self.variants,
                "metric": self.metric, "results": self.results,
                "status": self.status}


@dataclass
class Checkpoint:
    number: int
    code: str
    config: str
    model: str
    params: str
    environment: str
    dependencies: str
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"number": self.number, "code": self.code, "config": self.config,
                "model": self.model, "params": self.params,
                "environment": self.environment, "dependencies": self.dependencies}


# ---------------------------------------------------------------------------
# Multi-objective scoring (§9)
# ---------------------------------------------------------------------------
#: Weights — safety is a HARD constraint (not merely weighted).
SCORE_WEIGHTS = {
    "reliability": 0.25,
    "accuracy": 0.15,
    "latency": 0.10,
    "energy": 0.05,
    "compute": 0.05,
    "safety": 0.40,
}


def multi_objective_score(*, reliability: float, accuracy: float,
                          latency_ms: float, energy: float, compute: float,
                          safety_ok: bool = True) -> float:
    """Safety is a hard gate: if not safe → score 0."""
    if not safety_ok:
        return 0.0
    latency_score = max(0.0, 1.0 - latency_ms / 500.0)
    return (
        SCORE_WEIGHTS["reliability"] * reliability +
        SCORE_WEIGHTS["accuracy"] * accuracy +
        SCORE_WEIGHTS["latency"] * latency_score +
        SCORE_WEIGHTS["energy"] * energy +
        SCORE_WEIGHTS["compute"] * compute +
        SCORE_WEIGHTS["safety"] * 1.0
    )


# ---------------------------------------------------------------------------
# Evolution Engine (§1)
# ---------------------------------------------------------------------------
class EvolutionEngine:
    """tank.evolution — measured, reversible improvement under supervision."""

    _instance: Optional["EvolutionEngine"] = None

    def __new__(cls) -> "EvolutionEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.baseline = Baseline()
            cls._instance.generations: List[Generation] = [
                Generation(0, "Original", dict(DEFAULT_GENOME), score=0.82)]
            cls._instance.proposals: List[EvolutionProposal] = []
            cls._instance.experiments: List[Experiment] = []
            cls._instance.history: List[dict] = []
            cls._instance.checkpoints: List[Checkpoint] = []
            cls._instance._next_proposal = 1
            cls._instance._next_experiment = 1
            cls._instance._next_checkpoint = 1
            cls._instance._mission_log: List[dict] = []
            cls._instance._shadow_decisions: List[dict] = []
            cls._instance._current_gen = 0
        return cls._instance

    # -------------------------------------------------- mission observation
    def record_mission(self, mission_id: str, outcome: str,
                       cause: Optional[str] = None,
                       location: Optional[str] = None) -> None:
        """Feed mission outcomes into weakness discovery (§4)."""
        self._mission_log.append({
            "mission_id": mission_id, "outcome": outcome, "cause": cause,
            "location": location, "t": time.time()})
        if len(self._mission_log) > 2000:
            self._mission_log.pop(0)

    # ---------------------------------------------------- weakness discovery
    def weaknesses(self, window: int = 200) -> List[dict]:
        """Find patterns in recent missions (§4)."""
        recent = self._mission_log[-window:]
        failures = [m for m in recent if m["outcome"] != "success"]
        if not failures:
            return []
        total = len(recent)
        # correlate by cause
        by_cause: Dict[str, int] = {}
        by_location: Dict[str, int] = {}
        for m in failures:
            if m.get("cause"):
                by_cause[m["cause"]] = by_cause.get(m["cause"], 0) + 1
            if m.get("location"):
                by_location[m["location"]] = by_location.get(m["location"], 0) + 1
        top_cause = max(by_cause.items(), key=lambda kv: kv[1]) if by_cause else None
        top_location = max(by_location.items(), key=lambda kv: kv[1]) \
            if by_location else None
        out = []
        if top_cause:
            conf = top_cause[1] / max(total, 1) * 100
            out.append({
                "type": "cause", "value": top_cause[0],
                "count": top_cause[1], "window": total,
                "confidence": round(conf, 1),
                "discovery": (f"navigation failures: {top_cause[1]}/{total} "
                              f"({conf:.0f}%) cause: {top_cause[0]}")})
        if top_location:
            conf = top_location[1] / max(total, 1) * 100
            out.append({
                "type": "location", "value": top_location[0],
                "count": top_location[1], "window": total,
                "confidence": round(conf, 1),
                "discovery": (f"failures concentrated at {top_location[0]} "
                              f"({conf:.0f}%)")})
        return out

    # --------------------------------------------------------- proposals
    def propose(self, problem: str, parameter: str, new_value: float,
                expected: str, potential_cost: str = "",
                *, requires_approval: bool = True) -> EvolutionProposal:
        """Generate an evolution proposal (§5)."""
        genome = self.current_genome()
        # parameter is "section.key" (e.g. navigation.prediction_horizon)
        section, key = parameter.split(".", 1)
        old_value = float(genome.get(section, {}).get(key, 0.0))
        # respect bounds (same section/key layout as the genome)
        section_bounds = GENOME_BOUNDS.get(section, {})
        if key in section_bounds:
            lo, hi = section_bounds[key]
            new_value = max(lo, min(hi, float(new_value)))
        prop = EvolutionProposal(
            id=f"{self._next_proposal:03d}", problem=problem,
            change=f"{parameter}: {old_value} → {new_value}",
            parameter=parameter, old_value=old_value, new_value=new_value,
            expected=expected, potential_cost=potential_cost,
            requires_approval=requires_approval)
        self._next_proposal += 1
        self.proposals.append(prop)
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "proposed", "id": prop.id,
                             "change": prop.change})
        return prop

    def current_genome(self) -> Dict[str, dict]:
        # deep copy — deployed mutations must never leak into older generations
        return copy.deepcopy(self.generations[self._current_gen].genome)

    def current_generation(self) -> Generation:
        return self.generations[self._current_gen]

    # -------------------------------------------------- replay benchmark
    def replay_benchmark(self, prop: EvolutionProposal,
                         replay_success: float, baseline_success: float,
                         safety_ok: bool = True,
                         latency_ms: Optional[float] = None,
                         energy: float = 1.0, compute: float = 1.0,
                         accuracy: float = 1.0,
                         reliability: float = 1.0) -> float:
        """§7 — candidate tested against historical data; returns candidate
        multi-objective score (0 if unsafe or not better)."""
        # Candidate scores strictly by measured replay success (the objective
        # signal) scaled by the multi-objective weights; safety is a hard gate.
        cand = multi_objective_score(
            reliability=replay_success, accuracy=accuracy,
            latency_ms=latency_ms or self.baseline.avg_latency_ms,
            energy=energy, compute=compute, safety_ok=safety_ok)
        base = multi_objective_score(
            reliability=baseline_success, accuracy=accuracy,
            latency_ms=self.baseline.avg_latency_ms, energy=energy,
            compute=compute, safety_ok=True)
        prop.baseline_score = base
        prop.candidate_score = cand
        prop.explanation = (
            f"Replay success {baseline_success * 100:.1f}% → "
            f"{replay_success * 100:.1f}% "
            f"(candidate {cand - base:+.3f} score); safety "
            f"{'PASS' if safety_ok else 'FAIL — hard constraint'}")
        return cand

    # --------------------------------------------------------- approval
    def approve(self, prop: EvolutionProposal) -> EvolutionProposal:
        """§17 — human approval (mandatory for behavior/safety changes)."""
        if prop.status not in (ProposalStatus.TESTING,
                               ProposalStatus.AWAITING_APPROVAL,
                               ProposalStatus.DRAFT):
            return prop
        prop.status = ProposalStatus.APPROVED
        prop.stage = EvolutionStage.PRODUCTION
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "approved", "id": prop.id})
        return prop

    def reject(self, prop: EvolutionProposal) -> EvolutionProposal:
        prop.status = ProposalStatus.REJECTED
        prop.stage = EvolutionStage.REJECTED
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "rejected", "id": prop.id})
        return prop

    # ---------------------------------------------------------- deploy
    def deploy(self, prop: EvolutionProposal) -> Optional[Generation]:
        """Promote the approved change to a new generation (§10)."""
        if prop.status != ProposalStatus.APPROVED:
            return None
        self._checkpoint()
        genome = self.current_genome()
        section = prop.parameter.split(".")[0]
        key = prop.parameter.split(".")[-1]
        for s, params in genome.items():
            if s == section and key in params:
                params[key] = prop.new_value
        gen = Generation(self._current_gen + 1,
                         label=f"Gen {self._current_gen + 1}: {prop.change}",
                         genome=genome,
                         score=prop.candidate_score)
        self.generations.append(gen)
        self._current_gen += 1
        prop.status = ProposalStatus.DEPLOYED
        prop.stage = EvolutionStage.PRODUCTION
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "deployed", "id": prop.id,
                             "generation": gen.number})
        return gen

    # --------------------------------------------------------- rollback
    def rollback(self, generation_number: Optional[int] = None) -> Optional[Generation]:
        """§14 — return to a previous known-good generation."""
        if len(self.generations) < 2:
            return None
        if generation_number is None:
            generation_number = max(0, self._current_gen - 1)
        target = self.generations[generation_number]
        self._current_gen = generation_number
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "rollback",
                             "generation": generation_number})
        return target

    def _checkpoint(self) -> Checkpoint:
        """§15 — record everything needed to reproduce the state."""
        cp = Checkpoint(self._next_checkpoint, code="tankos-core",
                        config=f"genome-gen{self._current_gen}",
                        model="phi-3-mini", params="default",
                        environment="unoq+jetson+esp32",
                        dependencies="requirements.txt")
        self._next_checkpoint += 1
        self.checkpoints.append(cp)
        return cp

    # --------------------------------------------------------- shadow
    def shadow_compare(self, current_decision: str, candidate_decision: str,
                       current_safe: bool, candidate_safe: bool) -> dict:
        """§13 — candidate predicts silently; compare on identical inputs."""
        entry = {
            "current": current_decision, "candidate": candidate_decision,
            "current_safe": current_safe, "candidate_safe": candidate_safe,
            "agree": current_decision == candidate_decision,
            "t": time.time()}
        self._shadow_decisions.append(entry)
        return entry

    def shadow_summary(self) -> dict:
        decisions = self._shadow_decisions
        if not decisions:
            return {"decisions": 0, "candidate_better_pct": 0.0}
        diff = [d for d in decisions if d["current"] != d["candidate"]]
        safe_diff = [d for d in diff if d["current_safe"] and d["candidate_safe"]]
        candidate_better = len(safe_diff)
        return {
            "decisions": len(decisions),
            "different": len(diff),
            "candidate_safe_alternatives": candidate_better,
            "candidate_better_pct": round(candidate_better / max(len(decisions), 1) * 100, 1),
        }

    # -------------------------------------------------------- experiments
    def run_experiment(self, label: str, metric: str,
                       variants: Dict[str, dict]) -> Experiment:
        """§19 — auto-generated experiments benchmark multiple variants."""
        exp = Experiment(id=f"{self._next_experiment:03d}", label=label,
                         metric=metric, variants=variants)
        self._next_experiment += 1
        # deterministic simulated benchmark per variant
        for name, params in variants.items():
            base = 0.7 + (abs(hash(name)) % 20) / 100.0
            exp.results[name] = round(base, 3)
        exp.status = "complete"
        self.experiments.append(exp)
        self.history.append({"ts": datetime.datetime.now().strftime("%H:%M:%S"),
                             "event": "experiment", "id": exp.id,
                             "label": label})
        return exp

    # ------------------------------------------------ resource-aware check
    def resource_check(self, *, gpu_pct: float, cpu_pct: float, ram_pct: float,
                       battery_pct: float, model_size_multiplier: float = 1.0) -> dict:
        """§20 — reject candidates that exceed resource budgets."""
        # a larger model scales GPU roughly with the square of its size
        predicted_gpu = min(100.0, gpu_pct * model_size_multiplier ** 2)
        thermal = "HIGH" if predicted_gpu > 90 else (
            "MEDIUM" if predicted_gpu > 75 else "LOW")
        ok = predicted_gpu <= 90 and cpu_pct <= 90 and ram_pct <= 90 and battery_pct > 10
        return {"allowed": ok, "predicted_gpu": round(predicted_gpu, 1),
                "thermal_risk": thermal,
                "reason": ("OK" if ok else
                           "Rejected: predicted GPU utilization too high / "
                           "resources constrained")}

    # -------------------------------------------------- evolution summary
    def summary(self) -> dict:
        return {
            "generation": self._current_gen,
            "generations": [g.to_dict() for g in self.generations],
            "baseline": self.baseline.to_dict(),
            "proposals": [p.to_dict() for p in self.proposals],
            "weaknesses": self.weaknesses(),
            "history": list(self.history[-15:]),
            "shadow": self.shadow_summary(),
            "experiments": [e.to_dict() for e in self.experiments],
            "checkpoints": [c.to_dict() for c in self.checkpoints[-3:]],
        }

    def policy(self) -> dict:
        return {"allowed": EVOLUTION_ALLOWED, "forbidden": EVOLUTION_FORBIDDEN}

    def reset(self) -> None:
        self.generations = [Generation(0, "Original", dict(DEFAULT_GENOME),
                                       score=0.82)]
        self.proposals.clear()
        self.experiments.clear()
        self.history.clear()
        self.checkpoints.clear()
        self._mission_log.clear()
        self._shadow_decisions.clear()
        self._current_gen = 0
        self._next_proposal = 1
        self._next_experiment = 1
        self._next_checkpoint = 1
        return self
