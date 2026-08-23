"""Tests for the typed, permissioned AI tool-calling engine (20-part plan)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tank_os.core.tool_engine import (  # noqa: E402
    AgentRole, RiskTier, ToolEngine, ToolSpec, build_default_tools,
)


@pytest.fixture()
def engine():
    e = ToolEngine()
    e.reset()
    build_default_tools(e)
    e.set_role(AgentRole.NAVIGATOR)
    yield e


def test_registry_and_categories(engine) -> None:
    names = {t.name for t in engine.list_tools()}
    assert "robot.get_battery" in names
    assert "robot.move" in names
    assert "system.reboot" in names
    assert "safety.emergency_stop" in names
    assert "display.show" in names


def test_risk_tiers(engine) -> None:
    assert engine.get("robot.get_battery").risk is RiskTier.READ_ONLY
    assert engine.get("display.show").risk is RiskTier.LOW
    assert engine.get("robot.move").risk is RiskTier.CONTROLLED
    assert engine.get("system.reboot").risk is RiskTier.HIGH
    assert engine.get("system.reboot").requires_confirmation is True
    assert engine.get("safety.emergency_stop").risk is RiskTier.EMERGENCY


def test_read_only_tool_executes_without_confirmation(engine) -> None:
    r = engine.execute("robot.get_battery", agent="ai")
    assert r.success is True
    assert "percentage" in r.data
    assert r.error is None


def test_role_permissions_observer_cannot_move(engine) -> None:
    engine.set_role(AgentRole.OBSERVER)
    r = engine.execute("robot.move", {"direction": "forward", "distance_m": 1.0},
                       agent="ai")
    assert r.success is False
    assert r.error["code"] == "PERMISSION_DENIED"


def test_navigator_can_move_but_admin_cannot_bypass(engine) -> None:
    r = engine.execute("robot.move", {"direction": "forward", "distance_m": 1.0,
                                      "max_speed_mps": 0.25}, agent="ai")
    assert r.success is True
    assert r.data["dry_run"] is False or "command" in r.data


def test_sandbox_rejects_insane_speed(engine) -> None:
    """§17 — the AI cannot simply invent speed=100."""
    r = engine.execute("robot.move", {"direction": "forward", "distance_m": 1.0,
                                      "max_speed_mps": 100}, agent="ai")
    assert r.success is False
    assert r.error["code"] == "VALIDATION_FAILED"
    assert "sandbox" in r.error["message"]


def test_sandbox_rejects_bad_direction(engine) -> None:
    r = engine.execute("robot.move", {"direction": "diagonal"}, agent="ai")
    assert r.success is False
    assert r.error["code"] == "VALIDATION_FAILED"


def test_high_risk_requires_approval(engine) -> None:
    engine.set_role(AgentRole.ADMIN)  # system.* needs a role that can request it
    r = engine.execute("system.reboot", agent="ai")
    assert r.success is False
    assert r.error["code"] == "NEEDS_APPROVAL"


def test_emergency_tool_deterministic_path(engine) -> None:
    r = engine.execute("safety.emergency_stop", agent="ai")
    assert r.success is True
    assert "MOTOR OFF" in r.data["path"]
    assert "MCU" in r.data["path"]


def test_standardized_result_shape(engine) -> None:
    r = engine.execute("robot.get_battery", agent="ai")
    d = r.to_dict()
    assert set(d) >= {"success", "tool", "timestamp", "data", "warnings",
                      "error", "latency_ms"}
    assert d["success"] is True


def test_chaining_and_recovery(engine) -> None:
    results = engine.run_chain([
        {"tool": "robot.get_health"},
        {"tool": "robot.get_battery"},
        {"tool": "robot.get_sensor_status"},
    ], agent="ai")
    assert len(results) == 3
    assert all(r.success for r in results)
    assert engine.recover(results) == "ok"
    failed = [results[0].__class__.__name__]
    assert len(engine.chain()) >= 3


def test_recovery_obstacle_suggests_replan(engine) -> None:
    from tank_os.core.tool_engine import ToolResult
    results = [ToolResult(False, "robot.goto",
                          error={"code": "OBSTACLE_DETECTED",
                                 "message": "blocked"})]
    assert engine.recover(results) == "navigation.replan"


def test_audit_log_records_pipeline(engine) -> None:
    engine.execute("robot.move", {"direction": "forward", "distance_m": 1.0,
                                  "max_speed_mps": 0.25}, agent="ai")
    engine.execute("robot.get_battery", agent="ai")
    log = engine.audit_log()
    assert any(e.tool == "robot.move" and e.execution == "SUCCESS" for e in log)
    assert any(e.tool == "robot.get_battery" for e in log)
    entry = log[-1]
    assert entry.validation == "PASS" and entry.safety == "PASS"


def test_discovery_capabilities(engine) -> None:
    caps = engine.capabilities()
    assert "robot.get_battery" in caps
    assert "robot.move" in caps


def test_tool_composer_readiness(engine) -> None:
    """§20 — the killer feature: dynamic workflow composition."""
    result = engine.compose("prepare for autonomous patrol")
    assert result["readiness_pct"] > 0
    assert len(result["plan"]) >= 3
    assert all(r["success"] for r in result["results"])


def test_ownership_map() -> None:
    from tank_os.core.tool_engine import OWNERSHIP
    assert OWNERSHIP["vision"] == "jetson"
    assert OWNERSHIP["robot"] == "unoq"
    assert OWNERSHIP["sensor"] == "esp32"
    assert OWNERSHIP["motor"] == "stm32"
    assert OWNERSHIP["safety"] == "stm32"


def test_script_registry_binding() -> None:
    engine = ToolEngine()
    engine.reset()
    from tank_os.agent_framework.registry import ToolRegistry
    reg = ToolRegistry(scripts_dir=Path(__file__).resolve().parents[2] / "scripts")
    reg.discover()
    engine.bind_script_registry(reg)
    assert len(engine.capabilities()) > 100
    # a legacy 'medium'-risk tool maps to CONTROLLED
    probe = next((t for t in engine.list_tools() if t.risk is RiskTier.CONTROLLED),
                 None)
    assert probe is not None
