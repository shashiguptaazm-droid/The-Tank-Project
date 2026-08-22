"""``voice.drive_forward`` / ``voice.drive_backward`` / ``voice.brake_motion``.

Drive plugins translate free-form distance strings ("a meter",
"two meters", "half a meter") into ``Twist`` vectors and publish them
on the chassis motion provider over ``ctx``. The provider is pluggable
so tests pass a Null stub without spinning ROS.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._chassis_helpers import (
    DEFAULT_MAX_LINEAR_MPS,
    NullChassisMotionProvider,
    parse_distance_m,
    safe_drive_seconds,
)


class _DriveBasePlugin(RobotPlugin):
    """Common parameter schema + ctx resolution."""
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "distance": {"type": "string",
                         "description": "Natural-language distance "
                                        "(e.g. 'two meters', '50 cm'). "
                                        "Defaults to 1.0 meters.",
                         "default": "1 meter"},
            "speed_mps": {"type": "number",
                          "description": "Override linear speed in m/s.",
                          "minimum": 0.05, "maximum": 1.5,
                          "default": 0.0},
        },
    }
    TAGS = ["write", "voice", "chassis", "motion"]

    def _provider(self, ctx: Any) -> Any:
        if ctx is not None and hasattr(ctx, "chassis_motion"):
            return ctx.chassis_motion
        return NullChassisMotionProvider()

    def _params(self, p: Dict[str, Any]) -> tuple:
        dist = parse_distance_m(str(p.get("distance", "") or "1 meter"))
        override = float(p.get("speed_mps", 0.0) or 0.0)
        speed = override if override > 0 else DEFAULT_MAX_LINEAR_MPS
        duration_s = safe_drive_seconds(dist, speed)
        return dist, speed, duration_s


class DriveForwardPlugin(_DriveBasePlugin):
    NAME = "voice.drive_forward"
    DESCRIPTION = (
        "Drive the chassis forward by a free-form distance. Distance "
        "accepts English ('a meter', 'two meters', 'half a meter') "
        "and metric units ('cm', 'mm') and imperial ('in', 'ft')."
    )
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "distance_m": {"type": "number"},
            "speed_mps":  {"type": "number"},
            "duration_s": {"type": "number"},
            "twists":     {"type": "integer",
                           "description": "How many Twist publishes the "
                                          "provider recorded."},
            "tts_text":   {"type": "string"},
        },
    }
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        dist_m, speed, dur_s = self._params(params)
        prov = self._provider(ctx)
        # Publish loop is simulated by the node runtime (sleep + ticks).
        # For plugin-side accounting we record a single twist marker so
        # the provider's history can be inspected.
        from ._chassis_helpers import Twist
        steps = max(1, int(dur_s * 10))
        for _ in range(steps):
            prov.publish_twist(Twist(linear_x=speed,
                                     linear_y=0.0,
                                     angular_z=0.0))
        # Provider does its own braking — publish a brake at end.
        if hasattr(prov, "publish_twist"):
            prov.publish_twist(Twist())
        return {"_ok": True,
                "distance_m": round(dist_m, 3),
                "speed_mps": round(speed, 3),
                "duration_s": round(dur_s, 2),
                "twists": len(getattr(prov, "twists", [])),
                "tts_text": (f"Driving forward {dist_m:.1f} meters "
                             f"at {speed:.2f} m/s.")}


class DriveBackwardPlugin(_DriveBasePlugin):
    NAME = "voice.drive_backward"
    DESCRIPTION = "Drive the chassis backward by a free-form distance."
    RESPONSE_SCHEMA = DriveForwardPlugin.RESPONSE_SCHEMA
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        dist_m, speed, dur_s = self._params(params)
        prov = self._provider(ctx)
        from ._chassis_helpers import Twist
        steps = max(1, int(dur_s * 10))
        for _ in range(steps):
            prov.publish_twist(Twist(linear_x=-speed,
                                     linear_y=0.0,
                                     angular_z=0.0))
        if hasattr(prov, "publish_twist"):
            prov.publish_twist(Twist())
        return {"_ok": True,
                "distance_m": round(dist_m, 3),
                "speed_mps": -round(speed, 3),
                "duration_s": round(dur_s, 2),
                "twists": len(getattr(prov, "twists", [])),
                "tts_text": (f"Reversing {dist_m:.1f} meters "
                             f"at {speed:.2f} m/s.")}


class BrakeMotionPlugin(RobotPlugin):
    NAME = "voice.brake_motion"
    DESCRIPTION = (
        "Immediately halt any chassis motion. Publishes a zero Twist "
        "and resets the cmd_vel stream. "
    )
    PARAMETERS_SCHEMA = {"type": "object", "properties": {}}
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "halted": {"type": "boolean"},
            "last_speed": {"type": "object"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "safety"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = (ctx.chassis_motion if (ctx is not None
                and hasattr(ctx, "chassis_motion"))
                else NullChassisMotionProvider())
        from ._chassis_helpers import Twist
        prov.publish_twist(Twist())
        # Best-effort: stop follower too so it doesn't keep commanding motion.
        try:
            prov.follower_stop()
        except Exception:
            pass
        v, w = prov.current_speed()
        return {"_ok": True, "halted": True,
                "last_speed": {"linear_mps": float(v),
                               "angular_rps": float(w)},
                "tts_text": "Stopping."}
