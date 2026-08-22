"""``voice.turn_left`` / ``voice.turn_right`` / ``voice.spin_around``.

The turn plugins translate "left", "right", "90 degrees", "half turn"
into angular Twist publishes. They use the existing chassis motion
provider so the operator gets the same braking + safety envelope as
the drive plugins.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._chassis_helpers import (
    DEFAULT_MAX_ANGULAR_RPS,
    NullChassisMotionProvider,
    parse_angle_deg,
    safe_rotate_seconds,
)


class TurnPlugin(RobotPlugin):
    """Base — exposes a ``direction`` slot to capture left/right/half/full."""
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "direction": {"type": "string",
                          "enum": ["left", "right", "half", "full"],
                          "default": "left"},
            "angle": {"type": "string",
                       "description": "Optional explicit angle in degrees "
                                      "or in words ('ninety', 'half turn'). "
                                      "If empty, infers from `direction`.",
                       "default": ""},
            "speed_rps": {"type": "number",
                           "description": "Override angular speed in rad/s.",
                           "minimum": 0.1, "maximum": 3.0, "default": 0.0},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "direction": {"type": "string"},
            "angle_deg": {"type": "number"},
            "speed_rps": {"type": "number"},
            "duration_s": {"type": "number"},
            "twists": {"type": "integer"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "motion"]
    RATE_CLASS = "write"

    def _resolve(self, direction: str, angle: str) -> tuple:
        a = (direction or "left").strip().lower()
        angle_text = (angle or "").strip()
        if angle_text:
            deg = parse_angle_deg(angle_text)
        else:
            deg = parse_angle_deg(a)
            if a in {"half", "halfturn"}:
                deg = 180.0
            elif a in {"full", "fullturn", "spin"}:
                deg = 360.0
            elif a == "left":
                deg = 90.0
            elif a == "right":
                deg = 90.0
        sign = -1.0 if a == "left" or a == "half" else 1.0
        if a == "left":
            sign = +1.0
        elif a == "right":
            sign = -1.0
        # 90° → standard quarter turn; half/full are special cases already.
        if a in {"left", "right"} and not angle_text:
            deg = 90.0
        return a, deg, sign

    def _provider(self, ctx: Any) -> Any:
        if ctx is not None and hasattr(ctx, "chassis_motion"):
            return ctx.chassis_motion
        return NullChassisMotionProvider()


class TurnLeftPlugin(TurnPlugin):
    NAME = "voice.turn_left"
    DESCRIPTION = (
        "Rotate the chassis anticlockwise (positive yaw) by a free-form "
        "angle ('90 degrees', 'a quarter turn', 'half spin')."
    )

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        a, deg, sign = self._resolve(params.get("direction", "left"),
                                      params.get("angle", ""))
        prov = self._provider(ctx)
        speed = float(params.get("speed_rps", 0.0) or 0.0) \
            or DEFAULT_MAX_ANGULAR_RPS
        dur_s = safe_rotate_seconds(deg, speed)
        from ._chassis_helpers import Twist
        steps = max(1, int(dur_s * 10))
        for _ in range(steps):
            prov.publish_twist(Twist(linear_x=0.0, angular_z=+abs(speed)))
        prov.publish_twist(Twist())
        return {"_ok": True, "direction": "left",
                "angle_deg": round(deg, 1),
                "speed_rps": round(+abs(speed), 3),
                "duration_s": round(dur_s, 2),
                "twists": len(getattr(prov, "twists", [])),
                "tts_text": f"Turning left {int(deg)} degrees."}


class TurnRightPlugin(TurnPlugin):
    NAME = "voice.turn_right"
    DESCRIPTION = (
        "Rotate the chassis clockwise (negative yaw) by a free-form angle."
    )

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        a, deg, sign = self._resolve(params.get("direction", "right"),
                                      params.get("angle", ""))
        prov = self._provider(ctx)
        speed = float(params.get("speed_rps", 0.0) or 0.0) \
            or DEFAULT_MAX_ANGULAR_RPS
        dur_s = safe_rotate_seconds(deg, speed)
        from ._chassis_helpers import Twist
        steps = max(1, int(dur_s * 10))
        for _ in range(steps):
            prov.publish_twist(Twist(linear_x=0.0, angular_z=-abs(speed)))
        prov.publish_twist(Twist())
        return {"_ok": True, "direction": "right",
                "angle_deg": round(deg, 1),
                "speed_rps": round(-abs(speed), 3),
                "duration_s": round(dur_s, 2),
                "twists": len(getattr(prov, "twists", [])),
                "tts_text": f"Turning right {int(deg)} degrees."}


class SpinPlugin(RobotPlugin):
    NAME = "voice.spin_around"
    DESCRIPTION = (
        "Rotate the chassis 360° in place. Default direction is left "
        "(anticlockwise). 'spin right' → clockwise."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "direction": {"type": "string",
                          "enum": ["left", "right"],
                          "default": "left"},
            "speed_rps": {"type": "number",
                           "minimum": 0.1, "maximum": 3.0, "default": 0.0},
        },
    }
    RESPONSE_SCHEMA = TurnPlugin.RESPONSE_SCHEMA
    TAGS = ["write", "voice", "chassis", "motion"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        d = (params.get("direction") or "left").strip().lower()
        sign = +1.0 if d == "left" else -1.0
        prov = (ctx.chassis_motion if (ctx is not None
                and hasattr(ctx, "chassis_motion"))
                else NullChassisMotionProvider())
        speed = float(params.get("speed_rps", 0.0) or 0.0) \
            or DEFAULT_MAX_ANGULAR_RPS
        dur_s = safe_rotate_seconds(360.0, speed)
        from ._chassis_helpers import Twist
        steps = max(1, int(dur_s * 10))
        for _ in range(steps):
            prov.publish_twist(Twist(linear_x=0.0, angular_z=sign * speed))
        prov.publish_twist(Twist())
        return {"_ok": True, "direction": d,
                "angle_deg": 360.0,
                "speed_rps": round(sign * speed, 3),
                "duration_s": round(dur_s, 2),
                "twists": len(getattr(prov, "twists", [])),
                "tts_text": "Spinning 360 degrees."}
