"""Tests for the TankOS canonical core (30-part architecture plan)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tank_os.core.tankos_core import (  # noqa: E402
    Command, CommandPriority, CommandSource, Device, DeviceManager, DeviceState,
    HealthManager, MissionState, RobotState, StateManager, TankOS,
)


@pytest.fixture()
def tank():
    t = TankOS()
    t.boot()
    yield t


# ------------------------------------------------------------- devices
def test_device_discovery_and_lifecycle(tank) -> None:
    devs = tank.devices.list()
    assert len(devs) >= 15
    assert tank.devices.get("motor.left") is not None
    assert tank.devices.get("motor.left").controller == "stm32"
    # lifecycle: degrade → fault → recover → ready
    d = tank.devices.get("lidar")
    d.status = DeviceState.DEGRADED
    assert d.status is DeviceState.DEGRADED
    tank.devices.set_state("lidar", DeviceState.FAULT, health=0.2)
    assert tank.devices.get("lidar").status is DeviceState.FAULT
    tank.devices.reset("lidar")
    assert tank.devices.get("lidar").status is DeviceState.READY
    assert tank.devices.get("lidar").health == 1.0


def test_device_canonical_identity(tank) -> None:
    d = tank.devices.get("camera")
    assert d.to_dict()["type"] == "camera"
    assert d.to_dict()["firmware"] == "3.0.1"


# ------------------------------------------------------------- state
def test_boot_sequence_reaches_ready(tank) -> None:
    assert tank.state.state() is RobotState.READY


def test_state_transitions_legal() -> None:
    sm = StateManager()
    assert sm.transition(RobotState.SELF_TEST) is True   # BOOT → SELF_TEST
    assert sm.transition(RobotState.READY) is True
    assert sm.transition(RobotState.AUTONOMOUS) is True
    assert sm.transition(RobotState.MISSION) is True
    # illegal: READY→MISSION is legal but MISSION→BOOT is not
    assert sm.transition(RobotState.BOOT) is False


def test_any_state_can_estop() -> None:
    sm = StateManager()
    sm.transition(RobotState.SELF_TEST)
    assert sm.transition(RobotState.EMERGENCY_STOP) is True
    assert sm.transition(RobotState.SAFE_MODE) is True
    assert sm.transition(RobotState.RECOVERY) is True
    assert sm.transition(RobotState.SELF_TEST) is True
    assert sm.transition(RobotState.READY) is True


# ------------------------------------------------------------- command bus
def test_command_bus_validate_and_execute(tank) -> None:
    entry = tank.commands.send(Command("robot.move", CommandSource.HUMAN,
                                       {"direction": "forward"}))
    assert entry["execution"] == "EXECUTED"
    assert entry["validation"] == "PASS"
    assert entry["safety"] == "PASS"
    assert entry["latency_ms"] >= 0


def test_command_bus_rejects_unknown(tank) -> None:
    entry = tank.commands.send(Command("robot.explode", CommandSource.AI))
    assert entry["validation"] == "FAIL"
    assert entry["execution"] == "REJECTED_UNKNOWN"


def test_estop_priority_blocks_commands(tank) -> None:
    tank.commands.estop()
    assert tank.state.state() is RobotState.EMERGENCY_STOP
    entry = tank.commands.send(Command("robot.move", CommandSource.HUMAN))
    assert entry["safety"] == "ESTOP_LATCH"
    assert entry["execution"] == "BLOCKED"
    tank.commands.estop_clear()
    assert tank.state.state() is RobotState.READY


def test_command_priority_order() -> None:
    order = [CommandPriority.ESTOP, CommandPriority.HUMAN, CommandPriority.SAFETY,
             CommandPriority.MISSION, CommandPriority.AI, CommandPriority.BACKGROUND]
    assert order == sorted(order, reverse=True)


def test_command_trace_observability(tank) -> None:
    tank.commands.send(Command("robot.move", CommandSource.HUMAN))
    tank.commands.send(Command("display.show", CommandSource.AI,
                               {"screen": "dashboard"}))
    trace = tank.commands.trace()
    assert len(trace) >= 2
    assert all("ts" in e and "latency_ms" in e for e in trace)


# ------------------------------------------------------------- health
def test_health_from_measurable_signals(tank) -> None:
    report = tank.health.report()
    assert 0 <= report.overall <= 100
    assert "motor" in report.components
    # degrade a motor → overall drops
    tank.devices.set_state("motor.left", DeviceState.FAULT, health=0.1)
    report2 = tank.health.report()
    assert report2.components["motor"] < report.components["motor"]


# ------------------------------------------------------------- missions
def test_mission_lifecycle(tank) -> None:
    m = tank.missions.create("patrol", ["goto:A", "scan", "return_home"])
    assert m.status is MissionState.VALIDATING
    tank.missions.start(m.id)
    assert m.status is MissionState.RUNNING
    assert tank.state.state() is RobotState.MISSION
    tank.missions.pause(m.id)
    assert m.status is MissionState.PAUSED
    tank.missions.resume(m.id)
    assert m.status is MissionState.RUNNING
    tank.missions.advance(m.id)
    assert m.progress == 10
    tank.missions.complete(m.id)
    assert m.status is MissionState.COMPLETED
    assert m.progress == 100


def test_mission_block_and_abort(tank) -> None:
    m = tank.missions.create("patrol")
    tank.missions.start(m.id)
    tank.missions.block(m.id, "obstacle")
    assert m.status is MissionState.BLOCKED
    tank.missions.cancel(m.id)
    assert m.status is MissionState.ABORTED


# ------------------------------------------------------------- API
def test_canonical_api_surface(tank) -> None:
    api = tank.api()
    assert "tank.device" in api and "discover" in api["tank.device"]
    assert "tank.state" in api and "transition" in api["tank.state"]
    assert "tank.command" in api and "estop" in api["tank.command"]
    assert "tank.mission" in api and "start" in api["tank.mission"]
    assert "tank.health" in api and "report" in api["tank.health"]
    assert "tank.event" in api


def test_status_report(tank) -> None:
    s = tank.status()
    assert s["state"] == "ready"
    assert s["devices"] >= 15
    assert "health" in s and "missions" in s and "command_trace" in s


# ------------------------------------------------------------- CLI
def test_cli_status_and_mission():
    import argparse
    from tank_os.cli import tankos_cli
    tankos_cli.TANK = TankOS()
    tankos_cli.TANK.boot()
    assert tankos_cli.cmd_status(None) == 0
    assert tankos_cli.cmd_devices(argparse.Namespace(type=None)) == 0
    assert tankos_cli.cmd_battery(None) == 0
    assert tankos_cli.main(["health"]) == 0
    assert tankos_cli.main(["mission", "start", "--type", "patrol"]) == 0
    assert tankos_cli.main(["safety", "estop"]) == 0
    assert tankos_cli.main(["safety", "clear"]) == 0
    assert tankos_cli.main(["api"]) == 0
