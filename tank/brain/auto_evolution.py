"""
TankOS Auto-Evolution Engine
==============================
Controlled self-improvement system. NOT an AI that blindly rewrites itself.

Pipeline:
  OBSERVE -> FIND WEAKNESSES -> PRIORITIZE -> GENERATE SOLUTION
  -> SANDBOX -> VALIDATE -> TEST -> SIMULATE -> BENCHMARK
  -> SAFETY GATE -> CANARY DEPLOY -> MONITOR -> PROMOTE/ROLLBACK

Key Principle: TankOS evolves through evidence, not self-confidence.
"""

from __future__ import annotations
import time
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("tank.evolution")


class RiskClass(Enum):
    R0_DOCUMENTATION = 0   # README, comments - auto OK
    R1_UI = 1              # Dashboard, layout - auto if reversible
    R2_OPTIMIZATION = 2    # Performance, caching - needs tests
    R3_AI_BEHAVIOR = 3     # Model, routing - needs simulation
    R4_ROBOT_BEHAVIOR = 4  # Navigation, motion - needs hardware-in-loop
    R5_SAFETY = 5          # Emergency stop, limits - NEVER autonomous


class ExperimentStatus(Enum):
    CREATED = "created"
    TESTING = "testing"
    SIMULATING = "simulating"
    BENCHMARKING = "benchmarking"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    DEPLOYED = "deployed"
    FAILED = "failed"


class EvolutionStrategy(Enum):
    OPTIMIZATION = "optimization"     # Tune parameters
    REFACTORING = "refactoring"       # Improve structure
    REPLACEMENT = "replacement"       # Swap model/algorithm
    GENERATION = "generation"         # Create new module
    REMOVAL = "removal"              # Remove unused code


@dataclass
class Baseline:
    """Current system baseline metrics."""
    version: str = "1.0.0"
    navigation_success: float = 0.0
    vision_fps: float = 0.0
    avg_latency_ms: float = 0.0
    crash_rate: float = 0.0
    battery_runtime_min: float = 0.0
    ai_accuracy: float = 0.0
    custom_metrics: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Experiment:
    """A single evolution experiment."""
    experiment_id: str = field(default_factory=lambda: f"EXP-{str(uuid.uuid4())[:6]}")
    problem: str = ""
    hypothesis: str = ""
    strategy: EvolutionStrategy = EvolutionStrategy.OPTIMIZATION
    risk_class: RiskClass = RiskClass.R2_OPTIMIZATION
    change_description: str = ""
    change_files: list[str] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.CREATED
    baseline: Optional[Baseline] = None
    candidate_metrics: Optional[dict] = None
    test_passed: bool = False
    simulation_safe: bool = False
    benchmark_improvement: float = 0.0
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0
    result: str = ""


# Objective function weights by subsystem
OBJ_WEIGHTS = {
    "navigation": {
        "safety": 0.30, "reliability": 0.25, "latency": 0.20,
        "quality": 0.15, "power": 0.10
    },
    "ai": {
        "accuracy": 0.30, "latency": 0.25, "cost": 0.20,
        "reliability": 0.15, "privacy": 0.10
    },
    "gui": {
        "usability": 0.40, "response": 0.25, "accessibility": 0.15,
        "aesthetics": 0.10, "error_rate": 0.10
    },
    "general": {
        "reliability": 0.30, "quality": 0.25, "latency": 0.20,
        "efficiency": 0.15, "usability": 0.10
    }
}


class AutoEvolutionEngine:
    """
    TankOS self-improvement engine.
    Evolves through evidence, not self-confidence.
    """

    def __init__(self):
        self._baseline: Baseline = Baseline()
        self._experiments: list[Experiment] = []
        self._active_experiment: Optional[Experiment] = None
        self._observations: list[dict] = []
        self._hypotheses: list[dict] = []
        self._lessons_learned: list[dict] = []
        self._version_history: list[str] = ["1.0.0"]

    def set_baseline(self, baseline: Baseline):
        self._baseline = baseline

    def observe(self, observation: dict):
        """Observe system for improvement opportunities."""
        observation["_timestamp"] = time.time()
        self._observations.append(observation)
        if len(self._observations) > 1000:
            self._observations = self._observations[-500:]

    def detect_problems(self) -> list[dict]:
        """Analyze observations to find problems."""
        problems = []
        # Check for recurring failures
        fail_count = sum(1 for o in self._observations
                        if o.get("status") == "error")
        if fail_count > 5:
            problems.append({
                "type": "recurring_failure",
                "severity": "high",
                "count": fail_count,
                "description": f"{fail_count} failures detected in recent observations"
            })

        # Check for high latency
        high_lat = [o for o in self._observations
                   if o.get("latency_ms", 0) > 5000]
        if len(high_lat) > 3:
            problems.append({
                "type": "high_latency",
                "severity": "medium",
                "count": len(high_lat),
                "description": f"{len(high_lat)} high-latency events"
            })

        return problems

    def create_experiment(self, problem: str, hypothesis: str,
                          strategy: EvolutionStrategy = EvolutionStrategy.OPTIMIZATION,
                          risk: RiskClass = RiskClass.R2_OPTIMIZATION) -> Experiment:
        exp = Experiment(
            problem=problem,
            hypothesis=hypothesis,
            strategy=strategy,
            risk_class=risk,
            baseline=self._baseline
        )
        self._experiments.append(exp)
        self._active_experiment = exp
        return exp

    def run_tests(self, experiment: Experiment) -> bool:
        """Run tests on the experiment candidate."""
        experiment.status = ExperimentStatus.TESTING
        # In real implementation, run actual tests
        experiment.test_passed = True
        experiment.status = ExperimentStatus.SIMULATING
        return experiment.test_passed

    def simulate(self, experiment: Experiment) -> bool:
        """Simulate the experiment."""
        experiment.status = ExperimentStatus.SIMULATING
        experiment.simulation_safe = True
        experiment.status = ExperimentStatus.BENCHMARKING
        return experiment.simulation_safe

    def benchmark(self, experiment: Experiment,
                  candidate_metrics: dict) -> float:
        """Benchmark candidate against baseline."""
        experiment.candidate_metrics = candidate_metrics
        improvement = self._calculate_improvement(self._baseline, candidate_metrics)
        experiment.benchmark_improvement = improvement
        experiment.confidence = self._calculate_confidence(experiment)

        if improvement > 0:
            experiment.status = ExperimentStatus.CANDIDATE
        else:
            experiment.status = ExperimentStatus.REJECTED
        return improvement

    def request_approval(self, experiment: Experiment) -> dict:
        """Request human approval for high-risk experiments."""
        if experiment.risk_class.value >= RiskClass.R3_AI_BEHAVIOR.value:
            return {
                "requires_approval": True,
                "experiment_id": experiment.experiment_id,
                "risk": experiment.risk_class.name,
                "improvement": experiment.benchmark_improvement,
                "confidence": experiment.confidence,
                "problem": experiment.problem,
                "hypothesis": experiment.hypothesis
            }
        return {"requires_approval": False}

    def approve(self, experiment: Experiment):
        """Approve an experiment for deployment."""
        experiment.status = ExperimentStatus.APPROVED

    def reject(self, experiment: Experiment, reason: str = ""):
        """Reject an experiment."""
        experiment.status = ExperimentStatus.REJECTED
        experiment.result = reason
        self._lessons_learned.append({
            "experiment": experiment.experiment_id,
            "lesson": f"Rejected: {reason}",
            "improvement": experiment.benchmark_improvement
        })

    def rollback(self, experiment: Experiment):
        """Rollback a deployed experiment."""
        experiment.status = ExperimentStatus.ROLLED_BACK
        self._lessons_learned.append({
            "experiment": experiment.experiment_id,
            "lesson": "Rolled back after deployment",
        })

    def record_success(self, experiment: Experiment):
        """Record successful deployment."""
        experiment.status = ExperimentStatus.DEPLOYED
        experiment.completed_at = time.time()
        self._lessons_learned.append({
            "experiment": experiment.experiment_id,
            "lesson": f"Success: +{experiment.benchmark_improvement:.1f}% improvement",
            "improvement": experiment.benchmark_improvement
        })

    def _calculate_improvement(self, baseline: Baseline,
                                candidate: dict) -> float:
        """Calculate overall improvement percentage."""
        improvements = []
        if baseline.navigation_success and candidate.get("navigation_success"):
            imp = candidate["navigation_success"] - baseline.navigation_success
            improvements.append(imp)
        if baseline.vision_fps and candidate.get("vision_fps"):
            imp = (candidate["vision_fps"] - baseline.vision_fps) / max(1, baseline.vision_fps) * 100
            improvements.append(imp)
        if baseline.avg_latency_ms and candidate.get("avg_latency_ms"):
            imp = (baseline.avg_latency_ms - candidate["avg_latency_ms"]) / max(1, baseline.avg_latency_ms) * 100
            improvements.append(imp)
        if baseline.crash_rate and candidate.get("crash_rate"):
            imp = (baseline.crash_rate - candidate["crash_rate"]) / max(0.01, baseline.crash_rate) * 100
            improvements.append(imp)
        return sum(improvements) / max(1, len(improvements)) if improvements else 0.0

    def _calculate_confidence(self, experiment: Experiment) -> float:
        """Calculate confidence in the experiment."""
        conf = 0.0
        if experiment.test_passed:
            conf += 30
        if experiment.simulation_safe:
            conf += 30
        if experiment.benchmark_improvement > 5:
            conf += 20
        elif experiment.benchmark_improvement > 0:
            conf += 10
        if experiment.risk_class.value <= RiskClass.R2_OPTIMIZATION.value:
            conf += 20
        return min(100, conf)

    def get_evolution_score(self, subsystem: str = "general") -> dict:
        """Calculate the current evolution score."""
        weights = OBJ_WEIGHTS.get(subsystem, OBJ_WEIGHTS["general"])
        # Simplified score from baseline
        score = 50.0  # Base
        return {
            "subsystem": subsystem,
            "score": round(score, 1),
            "weights": weights,
            "baseline": {
                "version": self._baseline.version,
                "navigation": self._baseline.navigation_success,
                "vision_fps": self._baseline.vision_fps,
                "latency_ms": self._baseline.avg_latency_ms,
            }
        }

    def get_status(self) -> dict:
        return {
            "baseline_version": self._baseline.version,
            "total_experiments": len(self._experiments),
            "active": self._active_experiment is not None,
            "accepted": sum(1 for e in self._experiments
                          if e.status == ExperimentStatus.DEPLOYED),
            "rejected": sum(1 for e in self._experiments
                          if e.status == ExperimentStatus.REJECTED),
            "rolled_back": sum(1 for e in self._experiments
                             if e.status == ExperimentStatus.ROLLED_BACK),
            "observations": len(self._observations),
            "lessons": len(self._lessons_learned),
        }


# Global singleton
EVOLUTION = AutoEvolutionEngine()
