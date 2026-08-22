"""Live sensor state for the dashboard.

A single :class:`SensorState` carries the *current* value of one
sensor topic.  :func:`classify` decides whether the value indicates
the system is OK (green), warning (yellow), or alarm (red).

Lives in its own file so the FastAPI layer doesn't have to know
about the rules. Tests can patch the classifier without spinning
the bridge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    ALARM = "alarm"


@dataclass
class SensorState:
    """One sensor's most recent reading + status classification."""
    topic: str                  # e.g. "/battery/state"
    name: str                   # human label, e.g. "Battery"
    value: Any                  # raw value (number, bool, dict…)
    units: str = ""
    last_update: float = 0.0    # epoch seconds
    status: Status = Status.OK
    hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "last_update": self.last_update,
            "status": self.status.value,
            "hint": self.hint,
        }


# ---------------------------------------------------------------------------
# Classifiers — one per sensor kind.
# Pure functions so they're trivially unit-testable.
# ---------------------------------------------------------------------------
def _classify_battery(value: Any) -> Status:
    pct = float(value.get("percentage", 100.0)) if isinstance(value, dict) else float(value or 100.0)
    if pct < 10.0:
        return Status.ALARM
    if pct < 25.0:
        return Status.WARN
    return Status.OK


def _classify_cpu_temp(value: Any) -> Status:
    c = float(value) if value is not None else -1.0
    if c < 0:
        return Status.WARN                          # sensor missing
    if c >= 80.0:
        return Status.ALARM
    if c >= 65.0:
        return Status.WARN
    return Status.OK


def _classify_lidar(value: Any) -> Status:
    """LiDAR /scan: a dict with min_range_m. Smaller = something close."""
    if not isinstance(value, dict):
        return Status.WARN
    closest = float(value.get("min_range_m", value.get("range_min", 9.99)) or 9.99)
    if closest < 0.35:
        return Status.ALARM
    if closest < 0.80:
        return Status.WARN
    return Status.OK


def _classify_imu(value: Any) -> Status:
    """IMU /imu/data: a dict with ax, ay, az.  Detect free-fall."""
    if not isinstance(value, dict):
        return Status.WARN
    az = float(value.get("az", 9.81) or 9.81)
    if az < 1.0:           # near free-fall
        return Status.ALARM
    if az < 6.0:           # heavy bump
        return Status.WARN
    return Status.OK


def _classify_estop(value: Any) -> Status:
    return Status.ALARM if bool(value) else Status.OK


def _classify_motion(value: Any) -> Status:
    """Motion /status. Battery favourite: ALARM when stuck."""
    if isinstance(value, dict) and value.get("stuck_since"):
        return Status.ALARM
    return Status.OK


_CLASSIFIERS = {
    "/battery/state":      _classify_battery,
    "/health/cpu_c":       _classify_cpu_temp,
    "/scan":               _classify_lidar,
    "/imu/data":           _classify_imu,
    "/estop_external":     _classify_estop,
    "/motion/status":      _classify_motion,
}


def classify(topic: str, value: Any) -> Status:
    fn = _CLASSIFIERS.get(topic)
    if fn is None:
        return Status.OK
    try:
        return fn(value)
    except Exception:
        return Status.WARN


# ---------------------------------------------------------------------------
# Hint generator — short text shown beside the pill so the operator knows why.
# ---------------------------------------------------------------------------
def hint_for(topic: str, value: Any, status: Status) -> str:
    if status == Status.OK:
        return ""
    if topic == "/battery/state":
        pct = (value.get("percentage")
               if isinstance(value, dict) else value) or 0
        return f"{int(float(pct))}%"
    if topic == "/health/cpu_c":
        try:
            return f"{float(value):.1f}°C"
        except Exception:
            return "?"
    if topic == "/scan":
        if isinstance(value, dict):
            return f"{float(value.get('min_range_m', 0)):.2f} m"
        return "?"
    if topic == "/imu/data":
        return "free-fall?" if isinstance(value, dict) and value.get("az", 9.81) < 1 else "bumped"
    if topic == "/estop_external":
        return "LATCHED"
    if topic == "/motion/status" and isinstance(value, dict):
        return f"stuck {value.get('stuck_since','')}"
    return ""
