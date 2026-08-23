"""Tests for the RobotDoctor — including the plan's fault-injection
acceptance test: inject a known fault and verify the diagnosis identifies
the *correct* subsystem (not merely plausible text)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tank_os.core.robot_doctor import RobotDoctor, SEV_FAULT, SEV_WARN

#: One fault per subsystem, mapping to (subsystem, telemetry). The plan's
#: acceptance test injects ~20 known faults; here we cover the full range
#: of scored subsystems plus edge cases.
FAULTS = {
    "motor-stall": ("motors", {"fault": "stall", "enabled": True}),
    "motor-temp": ("motors", {"fault": None, "enabled": True, "temperature_c": 92}),
    "servo-fault": ("servos", {"fault": "stuck", "enabled": True}),
    "imu-offline": ("imu", {"rate_hz": 0, "dropouts": 9, "calibrated": True}),
    "imu-drift": ("imu", {"rate_hz": 60, "dropouts": 12, "calibrated": False}),
    "battery-low": ("battery", {"percent": 12, "voltage": 11.1, "temp_c": 32}),
    "battery-critical": ("battery", {"percent": 3, "voltage": 10.2, "temp_c": 40}),
    "cpu-peak": ("cpu_ram", {"cpu_percent": 99, "ram_percent": 40, "temp_c": 60}),
    "ram-pressure": ("cpu_ram", {"cpu_percent": 50, "ram_percent": 95, "temp_c": 55}),
    "mcu-disconnect": ("mcu", {"connected": False}),
    "mcu-stale": ("mcu", {"connected": True, "heartbeat_age_s": 12}),
    "jetson-latency": ("jetson", {"reachable": True, "latency_ms": 450, "cmd_timeout": False}),
    "jetson-timeout": ("jetson", {"reachable": True, "latency_ms": 30, "cmd_timeout": True}),
    "jetson-unreachable": ("jetson", {"reachable": False}),
    "esp32-offline": ("esp32", {"total": 3, "online": 2, "offline": 1,
                                "boards": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}),
    "esp32-all-offline": ("esp32", {"total": 3, "online": 0, "offline": 3,
                                    "boards": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}),
    "network-down": ("network", {"connected": False, "signal_percent": 0}),
    "wifi-weak": ("network", {"connected": True, "signal_percent": 18}),
    "service-down": ("services", {"failed": ["tank-ai.service"]}),
    "telemetry-unavailable": ("motors", {"unavailable": True}),
}

#: Expected minimum severity per injected fault.
EXPECTED_STATUS = {
    "motor-stall": SEV_FAULT,
    "motor-temp": SEV_WARN,
    "servo-fault": SEV_FAULT,
    "imu-offline": SEV_FAULT,
    "imu-drift": SEV_WARN,
    "battery-low": SEV_WARN,
    "battery-critical": SEV_FAULT,
    "cpu-peak": SEV_FAULT,
    "ram-pressure": SEV_WARN,
    "mcu-disconnect": SEV_FAULT,
    "mcu-stale": SEV_WARN,
    "jetson-latency": SEV_WARN,
    "jetson-timeout": SEV_FAULT,
    "jetson-unreachable": SEV_FAULT,
    "esp32-offline": SEV_WARN,
    "esp32-all-offline": SEV_FAULT,
    "network-down": SEV_FAULT,
    "wifi-weak": SEV_WARN,
    "service-down": SEV_FAULT,
    "telemetry-unavailable": SEV_FAULT,
}


HEALTHY = {
    "motors": {"fault": None, "enabled": True, "temperature_c": 40},
    "servos": {"fault": None, "enabled": True},
    "imu": {"rate_hz": 60, "dropouts": 0, "calibrated": True},
    "battery": {"percent": 85, "voltage": 12.2, "temp_c": 30},
    "cpu_ram": {"cpu_percent": 40, "ram_percent": 50, "temp_c": 55},
    "mcu": {"connected": True, "heartbeat_age_s": 1},
    "jetson": {"reachable": True, "latency_ms": 12, "cmd_timeout": False},
    "esp32": {"total": 3, "online": 3, "offline": 0,
               "boards": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
    "network": {"connected": True, "signal_percent": 90},
    "services": {"failed": []},
}


def _fresh_doctor() -> RobotDoctor:
    """Return a hermetic doctor: pristine singleton + a healthy board,
    so only the injected fault can move the diagnosis."""
    doctor = RobotDoctor()
    doctor.reset()
    for name, telemetry in HEALTHY.items():
        _inject(doctor, name, telemetry)
    return doctor


def _inject(doctor: RobotDoctor, name: str, telemetry: dict) -> None:
    def collector():
        return dict(telemetry)
    collector.__name__ = f"fault_{name}"
    doctor.register(name, collector)


@pytest.mark.parametrize("fault", sorted(FAULTS))
def test_fault_identified_in_correct_subsystem(fault: str) -> None:
    """The plan's acceptance test: each known fault must blame the right
    subsystem — not produce plausible text about the wrong one."""
    subsystem, telemetry = FAULTS[fault]
    doctor = _fresh_doctor()
    _inject(doctor, subsystem, telemetry)

    diag = doctor.diagnose()

    # The injected subsystem must be the TOP likely cause.
    assert diag.causes, f"{fault}: expected at least one likely cause"
    assert diag.causes[0].subsystem == subsystem, (
        f"{fault}: diagnosis blamed {diag.causes[0].subsystem}, "
        f"expected {subsystem}")

    # And its status must meet the expected severity.
    report = next(r for r in diag.subsystems if r.name == subsystem)
    statuses = {SEV_FAULT: 0, SEV_WARN: 1}[EXPECTED_STATUS[fault]]
    rank = {SEV_FAULT: 0, SEV_WARN: 1, "ok": 2}[report.status]
    assert rank <= statuses, (
        f"{fault}: expected >= {EXPECTED_STATUS[fault]}, got {report.status}")


def test_healthy_robot_scores_high() -> None:
    diag = _fresh_doctor().diagnose()
    assert diag.health_score >= 90


def test_health_score_drops_when_fault_injected() -> None:
    healthy = _fresh_doctor().diagnose().health_score
    doctor = _fresh_doctor()
    _inject(doctor, "battery", {"percent": 2, "voltage": 9.8, "temp_c": 42})
    faulty = doctor.diagnose().health_score
    assert faulty < healthy


def test_recommendation_includes_reconnect_for_esp32() -> None:
    doctor = _fresh_doctor()
    _inject(doctor, "esp32", {"total": 3, "online": 2, "offline": 1, "boards": []})
    diag = doctor.diagnose()
    assert any("esp32" in r.lower() for r in diag.recommendations)


def test_render_contains_health_and_cause() -> None:
    doctor = _fresh_doctor()
    _inject(doctor, "network", {"connected": False, "signal_percent": 0})
    text = doctor.diagnose().render()
    assert "ROBOT HEALTH:" in text
    assert "LIKELY CAUSE:" in text
    assert "RECOMMENDATION:" in text


def test_jetson_host_subsystems_warn_not_fault_on_unoq() -> None:
    """On the UNO Q, Jetson-only subsystems must warn, not fault."""
    doctor = _fresh_doctor()
    _inject(doctor, "motors", {"unavailable": True, "host": "jetson"})
    diag = doctor.diagnose()
    report = next(r for r in diag.subsystems if r.name == "motors")
    assert report.status == SEV_WARN


def test_unknown_fault_subclass_is_scored() -> None:
    doctor = _fresh_doctor()
    _inject(doctor, "custom", {"something": 1})
    diag = doctor.diagnose()
    report = next(r for r in diag.subsystems if r.name == "custom")
    assert report.status == "ok"
