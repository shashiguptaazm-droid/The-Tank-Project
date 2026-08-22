"""Chassis motion provider — pluggable cmd_vel publisher so all
``voice.<chassis>`` plugins ship hermetic tests.

The :class:`ChassisMotionProvider` interface is what the bridge passes
via ``ctx``. It abstracts whether the platform has a real ROS 2 twist
publisher, a Null replacement (tests / benches), or a backwards-compat
shim over the existing bridge ``cmd_*`` surface.

Geometry helpers convert natural-language distances / angles into
trajectory time + constant Twist vectors that the operator's hardware
can drive, clamped to safe speed envelopes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Safety envelope — matches the chassis defaults in WIRING.md / tank_motion.yaml.
DEFAULT_MAX_LINEAR_MPS = 0.30        # 0.3 m/s = walking pace for a tracked robot
DEFAULT_MAX_ANGULAR_RPS = 0.8        # ~46 °/s
DEFAULT_DISTANCE_TIMEOUT_S = 30.0    # ceiling per "drive N meters"
DEFAULT_ROTATION_TIMEOUT_S = 30.0


@dataclass
class Twist:
    """Linear+angular velocity in the 2D plane. Mirrors ROS ``geometry_msgs/Twist``.

    We don't import ROS here so the module stays pure-Python.
    """
    linear_x: float = 0.0     # m/s forward
    linear_y: float = 0.0     # m/s lateral (unused for skid-steer)
    angular_z: float = 0.0    # rad/s about +z

    def is_zero(self) -> bool:
        return (self.linear_x == 0.0
                and self.linear_y == 0.0
                and self.angular_z == 0.0)

    def to_dict(self) -> Dict[str, float]:
        return {"linear_x": self.linear_x,
                "linear_y": self.linear_y,
                "angular_z": self.angular_z}


class ChassisMotionProvider:
    """Abstract cmd_vel publisher (ROS path uses Twist() messages)."""

    def publish_twist(self, twist: Twist) -> None: ...
    def current_speed(self) -> Tuple[float, float]: ...
    def reset_odometry(self) -> None: ...
    def reset_imu(self) -> None: ...
    def run_calibration(self) -> Dict[str, Any]: ...
    def set_max_linear(self, mps: float) -> None: ...
    def set_max_angular(self, rps: float) -> None: ...
    def set_cruise_mode(self, on: bool) -> None: ...
    def follower_active(self) -> bool: ...
    def follower_start(self) -> None: ...
    def follower_stop(self) -> None: ...
    def patrol_pause(self) -> None: ...
    def patrol_resume(self) -> None: ...


class NullChassisMotionProvider(ChassisMotionProvider):
    """Records every Twist the plugins would have pushed.

    Used by tests + benches + voice plugins outside ROS.
    """

    def __init__(self) -> None:
        self.twists: List[Tuple[float, Twist]] = []   # (ts, twist)
        self.odometry_resets: int = 0
        self.imu_resets: int = 0
        self.calibrations: int = 0
        self.max_linear: float = DEFAULT_MAX_LINEAR_MPS
        self.max_angular: float = DEFAULT_MAX_ANGULAR_RPS
        self.cruise_mode: bool = False
        self.follower: bool = False
        self.patrol_paused: bool = False

    def _stamp(self) -> float:
        return time.monotonic()

    def publish_twist(self, twist: Twist) -> None:
        self.twists.append((self._stamp(), twist))

    def current_speed(self) -> Tuple[float, float]:
        if not self.twists:
            return (0.0, 0.0)
        _, last = self.twists[-1]
        return (last.linear_x, last.angular_z)

    def reset_odometry(self) -> None:
        self.odometry_resets += 1

    def reset_imu(self) -> None:
        self.imu_resets += 1

    def run_calibration(self) -> Dict[str, Any]:
        self.calibrations += 1
        return {"ok": True, "track_width_m": 0.145,
                "wheel_radius_m": 0.035, "samples": 60}

    def set_max_linear(self, mps: float) -> None:
        self.max_linear = clamp(mps, 0.05, DEFAULT_MAX_LINEAR_MPS * 2)

    def set_max_angular(self, rps: float) -> None:
        self.max_angular = clamp(rps, 0.1, DEFAULT_MAX_ANGULAR_RPS * 2)

    def set_cruise_mode(self, on: bool) -> None:
        self.cruise_mode = bool(on)

    def follower_active(self) -> bool:
        return self.follower

    def follower_start(self) -> None:
        self.follower = True

    def follower_stop(self) -> None:
        self.follower = False

    def patrol_pause(self) -> None:
        self.patrol_paused = True

    def patrol_resume(self) -> None:
        self.patrol_paused = False


# ────────────────────────────────────────────────────────────────────────────
# Geometry helpers — same shape as the existing move_to plugin uses.
# ────────────────────────────────────────────────────────────────────────────
def parse_distance_m(text: str) -> float:
    """Parse a free-form distance string. Returns meters.

    Accepts: "1 m", "1.5m", "two meters", "half a meter". Default 1.0.
    """
    text = text.lower().strip()
    if not text:
        return 1.0
    multipliers = {"a": 1.0, "an": 1.0, "one": 1.0, "two": 2.0,
                  "three": 3.0, "four": 4.0, "five": 5.0,
                  "half": 0.5, "quarter": 0.25}
    parts = text.replace(",", " ").split()
    value: Optional[float] = None
    unit_m = 1.0
    for p in parts:
        if p in {"m", "meter", "meters", "metre", "metres"}:
            unit_m = 1.0
        elif p in {"cm", "centimeter", "centimeters"}:
            unit_m = 0.01
        elif p in {"mm", "millimeter"}:
            unit_m = 0.001
        elif p in {"inch", "inches", "in"}:
            unit_m = 0.0254
        elif p in {"ft", "feet", "foot"}:
            unit_m = 0.3048
        elif p in multipliers:
            if p in {"a", "an"}:
                # Indefinite article: only use it if no value yet.
                if value is None:
                    value = multipliers[p]
            else:
                value = multipliers[p]
        else:
            try:
                v = float(p)
                value = v
            except ValueError:
                pass
    if value is None:
        return 1.0
    return abs(value) * unit_m


# Common English angle phrases — "one eighty" colloquially means 180°,
# "two seventy" means 270°, "three sixty" means 360°. Operators often
# say these out loud instead of the numeric form.
_ANGLE_COMPOUNDS = {
    "one twenty": 120.0, "one thirty": 130.0, "one forty": 140.0,
    "one fifty": 150.0, "one sixty": 160.0, "one seventy": 170.0,
    "one eighty": 180.0, "one ninety": 190.0,
    "two twenty": 220.0, "two thirty": 230.0, "two forty": 240.0,
    "two fifty": 250.0, "two sixty": 260.0, "two seventy": 270.0,
    "two eighty": 280.0, "two ninety": 290.0,
    "three twenty": 320.0, "three thirty": 330.0, "three forty": 340.0,
    "three fifty": 350.0, "three sixty": 360.0,
}


def parse_angle_deg(text: str) -> float:
    """Parse a free-form angle. Returns degrees. Default 90.0."""
    text = text.lower().strip()
    if not text:
        return 90.0
    if text in _ANGLE_COMPOUNDS:
        return _ANGLE_COMPOUNDS[text]
    multipliers = {"a": 1.0, "an": 1.0, "half": 0.5,
                  "quarter": 0.25,
                  "one": 1.0, "two": 2.0,
                  "twenty": 20.0, "thirty": 30.0, "forty": 40.0,
                  "fifty": 50.0, "sixty": 60.0, "seventy": 70.0,
                  "eighty": 80.0, "ninety": 90.0, "hundred": 100.0}
    parts = text.replace(",", " ").split()
    value: Optional[float] = None
    for p in parts:
        if p in {"deg", "degree", "degrees"}:
            return float(value or 90.0)
        if p == "rad":
            return float(value or 1.5708) * (180.0 / 3.14159265)
        if p in multipliers:
            value = multipliers[p]
        else:
            try:
                v = float(p)
                value = v
            except ValueError:
                pass
    # No "degrees" → assume degrees anyway (operators say "90" = ninety).
    return (value if value is not None else 90.0)


def clamp(value: float, lo: float, hi: float) -> float:
    """Bounded float. ``None`` / garbage → midpoint of [lo, hi]."""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return (lo + hi) / 2.0


def safe_drive_seconds(distance_m: float, speed_mps: float) -> float:
    """Time to drive ``distance_m`` at ``speed_mps`` with safety ceiling."""
    speed = clamp(abs(speed_mps), 0.05, DEFAULT_MAX_LINEAR_MPS) or 0.05
    t = abs(distance_m) / speed
    return min(t, DEFAULT_DISTANCE_TIMEOUT_S)


def safe_rotate_seconds(angle_deg: float, speed_rps: float) -> float:
    speed = clamp(abs(speed_rps), 0.1, DEFAULT_MAX_ANGULAR_RPS) or 0.1
    t = abs(angle_deg) / max(0.1, speed * (180.0 / 3.14159265))
    return min(t, DEFAULT_ROTATION_TIMEOUT_S)


__all__ = [
    "Twist", "ChassisMotionProvider", "NullChassisMotionProvider",
    "DEFAULT_MAX_LINEAR_MPS", "DEFAULT_MAX_ANGULAR_RPS",
    "DEFAULT_DISTANCE_TIMEOUT_S", "DEFAULT_ROTATION_TIMEOUT_S",
    "parse_distance_m", "parse_angle_deg", "clamp",
    "safe_drive_seconds", "safe_rotate_seconds",
]
