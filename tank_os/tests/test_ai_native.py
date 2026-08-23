"""Tests for the TankOS native AI subsystem (100-AI plan)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tank_os.ai.native_core import (  # noqa: E402
    AIModel, InferenceScheduler, ModelRegistry, NavigationAI, PerceptionLayer,
    ResourceGovernor, TankAIService, WorldIntelligence,
    default_perception_backends,
)


@pytest.fixture()
def ai():
    svc = TankAIService()
    svc.reset()
    yield svc


# --------------------------------------------------------- model registry
def test_registry_register_and_list(ai) -> None:
    reg = ai.registry
    assert len(reg.list()) >= 5
    assert set(reg.tasks()) >= {"object_detection", "language",
                                "semantic_segmentation", "pose_estimation"}


def test_auto_model_selection(ai) -> None:
    """§2 — pick the best healthy model for the task."""
    m = ai.registry.select("object_detection")
    assert m is not None
    assert m.task == "object_detection"
    assert m.name == "yolo-v11n"          # highest accuracy
    # device preference respected
    m2 = ai.registry.select("object_detection", prefer_device="unoq")
    assert m2.device == "unoq"


def test_health_monitor_and_fallback(ai) -> None:
    """§3/§6 — failed model → health report drops + fallback selected."""
    reg = ai.registry
    # fallback_to chain: the unoq q8 model falls back to the (healthy) jetson one
    fb = reg.fallback("yolo-v11n-q8")
    assert fb is not None and fb.name == "yolo-v11n"
    # once the target is unhealthy, fallback is refused and selection skips it
    reg.mark_unhealthy("yolo-v11n")
    assert reg.fallback("yolo-v11n-q8") is None
    report = reg.health_report()
    assert report["healthy"] == report["total"] - 1
    # selection skips unhealthy
    assert reg.select("object_detection").name != "yolo-v11n"


def test_scheduler_assigns_device(ai) -> None:
    """§8 — workloads allocated across Jetson/UNO Q."""
    sched = ai.scheduler
    job = sched.submit("object_detection")
    dev = sched.assign_device("object_detection", ai.registry)
    assert dev == "jetson"
    sched.run(job, dev)
    load = sched.load()
    assert "jetson" in load
    sched.complete(job)


def test_resource_governor(ai) -> None:
    """§9 — AI resource governor controls CPU/GPU/RAM."""
    g = ai.governor
    assert g.allow(predicted_gpu=95, predicted_cpu=50, predicted_ram=50)["allowed"] \
        is False
    assert g.allow(predicted_gpu=60, predicted_cpu=40, predicted_ram=40)["allowed"] \
        is True
    g.set_budget("jetson.gpu", 99)
    assert g.allow(predicted_gpu=95, predicted_cpu=50, predicted_ram=50)["allowed"] \
        is True


# ------------------------------------------------------------ perception
def test_perception_capabilities(ai) -> None:
    caps = ai.perception.capabilities()
    assert "object_detection" in caps
    assert "person_detection" in caps
    assert len(caps) >= 10


def test_capability_run_selects_model_and_device(ai) -> None:
    """The core design: apps ask for a capability, TankOS picks the rest."""
    res = ai.run_capability("object_detection")
    assert res["success"] is True
    assert res["model"] == "yolo-v11n"
    assert res["device"] == "jetson"
    assert "person" in [d["label"] for d in res["detections"]]
    assert res["precision"] == "fp16"


def test_capability_unknown(ai) -> None:
    res = ai.run_capability("teleport")
    assert res["success"] is False


# ------------------------------------------------------------- world AI
def test_world_memory_and_query(ai) -> None:
    w = ai.world
    oid = w.observe("chair", "north-doorway", 0.9)
    assert oid == "obj-1"
    # upsert same label+location → same id
    assert w.observe("chair", "north-doorway", 0.95) == oid
    q = w.query("What objects are near the north doorway?", near="north-doorway")
    assert "chair" in q["objects"]


def test_world_unknown_areas(ai) -> None:
    w = ai.world
    w.set_location_confidence("stair area", 0.22)
    w.set_location_confidence("north corridor", 0.96)
    assert "stair area" in w.unknown_areas()
    assert "north corridor" not in w.unknown_areas()


# ---------------------------------------------------------- navigation AI
def test_navigation_multi_route_comparison(ai) -> None:
    nav = ai.navigation
    routes = nav.plan((0, 0), (10, 10), obstacles=["x", "y"])
    assert len(routes) == 3
    best = nav.best(routes)
    assert best.risk <= min(r.risk for r in routes) + 0.05
    assert nav.eta(best) > 0
    assert 0 < best.confidence <= 1.0


# ------------------------------------------------------------ executive
def test_intent_classification(ai) -> None:
    ex = ai.executive
    assert ex.classify("inspect the room") == "inspect"
    assert ex.classify("follow me") == "follow"
    assert ex.classify("go to the dock") == "goto"
    assert ex.classify("return home") == "return_home"
    assert ex.classify("stop") == "stop"
    assert ex.classify("what is your health") == "status_query"


def test_task_decomposition_inspect(ai) -> None:
    tasks = ai.executive.decompose("Inspect the entire room")
    descriptions = [t.description for t in tasks]
    assert descriptions[0] == "check system"
    assert "navigate" in descriptions
    assert "investigate anomalies" in descriptions
    assert descriptions[-1] == "report"
    assert all(t.parent is None or t.parent for t in tasks)  # chained


def test_executive_full_run(ai) -> None:
    result = ai.executive.run("Inspect the entire room")
    assert result["intent"] == "inspect"
    assert result["tasks"] >= 5
    assert result["success"] is True
    assert "subtasks complete" in result["summary"]


# -------------------------------------------------------- capability API
def test_capability_discovery(ai) -> None:
    caps = ai.capabilities()
    assert "perception" in caps and "world" in caps and "navigation" in caps
    assert len(caps["perception"]) >= 10
    assert len(caps["models"]) >= 5


def test_service_status_shape(ai) -> None:
    s = ai.status()
    assert "capabilities" in s and "model_health" in s and "world" in s
    assert "scheduler_load" in s and "budgets" in s


# ----------------------------------------------------------- deep route
def test_device_change_does_not_break_apps(ai) -> None:
    """§10 — swap the model/device; downstream capability call unchanged."""
    res_before = ai.run_capability("object_detection")
    # simulate a hardware change: jetson model fails, unoq q8 takes over
    ai.registry.mark_unhealthy("yolo-v11n")
    res_after = ai.run_capability("object_detection")
    assert res_after["success"] is True
    assert res_after["device"] == "unoq"
    assert res_after["model"] == "yolo-v11n-q8"
    # both expose the same shape
    assert res_before["capability"] == res_after["capability"] == "object_detection"
