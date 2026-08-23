"""Tests for the TankOS Evolution Engine (TEE) — 25-part evolution plan."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tank_os.core.evolution_engine import (  # noqa: E402
    EvolutionEngine, EvolutionStage, ProposalStatus, multi_objective_score,
)


@pytest.fixture()
def evo():
    e = EvolutionEngine()
    e.reset()
    yield e


# ------------------------------------------------------------- baseline
def test_baseline_exists(evo) -> None:
    b = evo.baseline
    assert b.navigation_success == 0.91
    assert 0 < b.mission_completion < 1
    assert len(b.to_dict()) == 6


# ----------------------------------------------------- weakness discovery
def test_weakness_discovery_finds_pattern(evo) -> None:
    for i in range(40):
        outcome = "success" if i % 4 else "failure"
        cause = "dynamic-obstacle" if i % 4 == 0 else None
        location = "corridor-b" if i % 8 == 0 else None
        evo.record_mission(f"m-{i}", outcome, cause, location)
    weaks = evo.weaknesses(window=40)
    assert any(w["type"] == "cause" and w["value"] == "dynamic-obstacle"
               for w in weaks)
    assert any(w["type"] == "location" and w["value"] == "corridor-b"
               for w in weaks)


def test_no_weaknesses_when_all_success(evo) -> None:
    for i in range(20):
        evo.record_mission(f"m-{i}", "success")
    assert evo.weaknesses() == []


# ------------------------------------------------------------- proposals
def test_proposal_respects_bounds(evo) -> None:
    p = evo.propose("replan issues", "navigation.prediction_horizon", 99.0,
                    "better")
    # clamped to the genome bound (0.5, 3.0)
    assert p.new_value <= 3.0
    assert p.old_value == 1.5  # default genome
    assert p.status is ProposalStatus.DRAFT


def test_proposal_id_sequence(evo) -> None:
    p1 = evo.propose("a", "navigation.prediction_horizon", 2.0, "x")
    p2 = evo.propose("b", "vision.inference_rate", 20, "x")
    assert p1.id == "001" and p2.id == "002"


# ----------------------------------------------------- replay benchmark
def test_replay_benchmark_better_candidate_scores_higher(evo) -> None:
    p = evo.propose("blockage", "navigation.prediction_horizon", 2.0, "better")
    evo.replay_benchmark(p, replay_success=0.951, baseline_success=0.912,
                         safety_ok=True)
    assert p.candidate_score > p.baseline_score
    assert "PASS" in p.explanation


def test_replay_benchmark_safety_hard_gate(evo) -> None:
    """§9 — safety is a hard constraint: unsafe candidate scores 0."""
    p = evo.propose("blockage", "navigation.prediction_horizon", 2.0, "better")
    cand = multi_objective_score(reliability=0.99, accuracy=0.99, latency_ms=10,
                                 energy=1.0, compute=1.0, safety_ok=False)
    assert cand == 0.0
    evo.replay_benchmark(p, replay_success=0.99, baseline_success=0.9,
                         safety_ok=False)
    assert p.candidate_score == 0.0


def test_multi_objective_weights() -> None:
    s = multi_objective_score(reliability=1.0, accuracy=1.0, latency_ms=0,
                              energy=1.0, compute=1.0, safety_ok=True)
    assert s == pytest.approx(1.0)
    s2 = multi_objective_score(reliability=0.5, accuracy=0.5, latency_ms=250,
                               energy=0.5, compute=0.5, safety_ok=True)
    assert 0.0 < s2 < s


# ------------------------------------------------- approve/deploy/rollback
def test_deploy_requires_approval(evo) -> None:
    p = evo.propose("blockage", "navigation.prediction_horizon", 2.0, "better")
    assert evo.deploy(p) is None            # not approved → no deploy
    evo.replay_benchmark(p, 0.95, 0.91, safety_ok=True)
    evo.approve(p)
    gen = evo.deploy(p)
    assert gen is not None
    assert gen.number == 1
    assert p.status is ProposalStatus.DEPLOYED
    assert evo.current_generation().number == 1
    # genome actually changed
    assert evo.current_genome()["navigation"]["prediction_horizon"] == 2.0


def test_rollback_returns_to_previous(evo) -> None:
    p = evo.propose("blockage", "navigation.prediction_horizon", 2.0, "better")
    evo.replay_benchmark(p, 0.95, 0.91)
    evo.approve(p)
    evo.deploy(p)
    assert evo.current_generation().number == 1
    rolled = evo.rollback()
    assert rolled.number == 0
    assert evo.current_generation().number == 0
    # genome restored
    assert evo.current_genome()["navigation"]["prediction_horizon"] == 1.5


def test_reject(evo) -> None:
    p = evo.propose("blockage", "navigation.prediction_horizon", 2.0, "x")
    evo.reject(p)
    assert p.status is ProposalStatus.REJECTED
    assert p.stage is EvolutionStage.REJECTED


# ------------------------------------------------------------ experiments
def test_experiment_benchmarks_variants(evo) -> None:
    exp = evo.run_experiment("Vision FPS vs battery", "battery",
                             {"A: 20 FPS": {"fps": 20}, "B: 10 FPS": {"fps": 10}})
    assert exp.status == "complete"
    assert len(exp.results) == 2
    assert all(0 < v < 1 for v in exp.results.values())


# -------------------------------------------------------- resource-aware
def test_resource_check_rejects_overload(evo) -> None:
    ok = evo.resource_check(gpu_pct=83, cpu_pct=47, ram_pct=62, battery_pct=41,
                            model_size_multiplier=1.2)
    assert ok["allowed"] is False
    assert "Rejected" in ok["reason"]
    ok2 = evo.resource_check(gpu_pct=30, cpu_pct=20, ram_pct=30, battery_pct=80)
    assert ok2["allowed"] is True


# ------------------------------------------------------------- shadow
def test_shadow_compare_and_summary(evo) -> None:
    evo.shadow_compare("LEFT", "LEFT", True, True)
    evo.shadow_compare("LEFT", "RIGHT", True, True)
    s = evo.shadow_summary()
    assert s["decisions"] == 2
    assert s["different"] == 1
    assert s["candidate_better_pct"] == 50.0


# ------------------------------------------------------------- policy
def test_policy_no_uncontrolled_self_modification(evo) -> None:
    pol = evo.policy()
    assert "modify E-stop logic" in pol["forbidden"]
    assert "increase motor limits" in pol["forbidden"]
    assert "disable safety" in pol["forbidden"]
    assert "propose" in pol["allowed"]
    assert "optimize bounded parameters" in pol["allowed"]


# ------------------------------------------------------------- summary
def test_summary_shape(evo) -> None:
    s = evo.summary()
    assert "generation" in s and "generations" in s and "baseline" in s
    assert "proposals" in s and "history" in s and "policy" not in s
    assert s["generations"][0]["number"] == 0


# ------------------------------------------------------------- evolution story
def test_evolution_story_progression(evo) -> None:
    """§23 — the judge demo: show how the robot evolved."""
    stages = [("navigation.prediction_horizon", 1.0, 0.71, 0.82),
              ("navigation.prediction_horizon", 1.5, 0.82, 0.89),
              ("navigation.prediction_horizon", 2.0, 0.89, 0.94)]
    for i, (param, val, base, cand) in enumerate(stages):
        p = evo.propose(f"stage {i}", param, val, "better")
        evo.replay_benchmark(p, cand, base, safety_ok=True)
        evo.approve(p)
        evo.deploy(p)
    gens = [g.score for g in evo.generations]
    assert gens == sorted(gens)  # monotonic improvement story
    assert gens[-1] > gens[0]
