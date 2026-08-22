"""``voice.set_max_speed`` / ``voice.set_cruise_mode``.

Configure the chassis motion provider's speed envelope. These are
configuration writes (motors will react next time they're commanded),
so the rate-class is ``write`` with a soft warning when pushed past
the safe envelope.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._chassis_helpers import (
    DEFAULT_MAX_LINEAR_MPS,
    DEFAULT_MAX_ANGULAR_RPS,
    NullChassisMotionProvider,
    clamp,
)


def _safe_float(value: Any, default: float) -> float:
    """Coerce ``value`` to float; garbage / None / empty-string → ``default``.

    Centralised so malicious or malformed plugin params (e.g. a literal
    ``"not-a-float"``) never crash the chassis configuration path.
    Used by :class:`SetMaxSpeedPlugin.run`.
    """
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class SetMaxSpeedPlugin(RobotPlugin):
    NAME = "voice.set_max_speed"
    DESCRIPTION = (
        "Set the chassis linear / angular speed envelope. "
        "Linear in m/s (0.05 – 0.6); angular in rad/s (0.1 – 1.6). "
        "Anything outside the envelope clamps with a TTS warning."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "linear_mps": {"type": "number",
                            "minimum": 0.05, "maximum": 0.6,
                            "default": 0.30},
            "angular_rps": {"type": "number",
                            "minimum": 0.1, "maximum": 1.6,
                            "default": 0.8},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "applied_linear_mps": {"type": "number"},
            "applied_angular_rps": {"type": "number"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "config"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = (ctx.chassis_motion if (ctx is not None
                and hasattr(ctx, "chassis_motion"))
                else NullChassisMotionProvider())
        warnings: list = []

        lin_raw = _safe_float(params.get("linear_mps"), DEFAULT_MAX_LINEAR_MPS)
        ang_raw = _safe_float(params.get("angular_rps"), DEFAULT_MAX_ANGULAR_RPS)
        lin = clamp(lin_raw, 0.05, DEFAULT_MAX_LINEAR_MPS * 2)
        ang = clamp(ang_raw, 0.1, DEFAULT_MAX_ANGULAR_RPS * 2)
        if lin != lin_raw:
            warnings.append(f"linear_mps clamped {lin_raw:.3f} → {lin:.3f} m/s")
        if ang != ang_raw:
            warnings.append(f"angular_rps clamped {ang_raw:.3f} → {ang:.3f} rad/s")
        prov.set_max_linear(lin)
        prov.set_max_angular(ang)
        tts = (f"Max speed set to {lin:.2f} meters per second, "
               f"{ang:.2f} radians per second.")
        if warnings:
            tts += " (with safety clamps.)"
        return {"_ok": True,
                "applied_linear_mps": round(lin, 4),
                "applied_angular_rps": round(ang, 4),
                "warnings": warnings,
                "tts_text": tts}


class SetCruiseModePlugin(RobotPlugin):
    NAME = "voice.set_cruise_mode"
    DESCRIPTION = (
        "Toggle cruise mode — chassis keeps moving straight at the "
        "last commanded linear speed until told to brake or change "
        "direction. Useful for long corridors."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "enabled": {"type": "boolean", "default": True},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "cruise_mode": {"type": "boolean"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "chassis", "config"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        prov = (ctx.chassis_motion if (ctx is not None
                and hasattr(ctx, "chassis_motion"))
                else NullChassisMotionProvider())
        enabled = bool(params.get("enabled", True))
        prov.set_cruise_mode(enabled)
        return {"_ok": True,
                "cruise_mode": enabled,
                "tts_text": ("Cruise mode on." if enabled
                             else "Cruise mode off.")}
