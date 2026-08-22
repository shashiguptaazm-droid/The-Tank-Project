"""Command implementations — one function per manifest entry.

Each takes a pre-validated ``params`` dict and a publisher set (the
:class:`~tank_command_bridge.app.BridgeNode`). Pure functions, easy to
unit-test. Move is clamped to the same limits declared in the manifest.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple


# Limits — mirrored from manifest.py so unit tests and production both
# agree on the clamping math.
MAX_VX = 0.5
MAX_WZ = 1.5
MAX_DURATION_S = 5.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def cmd_estop(params: Dict, publishers: Any,
              _now=time.time) -> Dict:
    state = bool(params.get("state", True))
    publishers.publish_estop(state)
    publishers.software_estop_latch(state)
    return {"latched": state, "ts": _now()}


def cmd_move(params: Dict, publishers: Any,
             _now=time.time) -> Dict:
    """Publish a bounded Twist for ``duration_s`` seconds and then a
    zero Twist (so the watchdog stops the motors). Honours the
    software estop latch."""
    if publishers.is_software_estop_latched():
        return {"vx_eff": 0.0, "wz_eff": 0.0,
                "duration_s_eff": 0.0,
                "rejected": "estop_latched"}
    vx = clamp(params.get("vx", 0.0), -MAX_VX, MAX_VX)
    wz = clamp(params.get("wz", 0.0), -MAX_WZ, MAX_WZ)
    dur = clamp(params.get("duration_s", 1.0), 0.0, MAX_DURATION_S)
    publishers.publish_move(vx=vx, wz=wz)
    # Schedule the zero-publish after ``dur`` seconds via the bridge
    # thread's timer facilities — this keeps the threading model clean.
    publishers.schedule_zero_move(dur)
    return {"vx_eff": vx, "wz_eff": wz, "duration_s_eff": dur}


def cmd_patrol(params: Dict, publishers: Any, _now=time.time) -> Dict:
    if publishers.is_software_estop_latched():
        return {"accepted": False, "mode": params.get("mode", "stop"),
                "rejected": "estop_latched"}
    mode = str(params.get("mode", "stop")).strip().lower()
    accepted = publishers.publish_patrol(mode)
    return {"accepted": accepted, "mode": mode}


def cmd_dock(params: Dict, publishers: Any, _now=time.time) -> Dict:
    if publishers.is_software_estop_latched():
        return {"armed": False, "rejected": "estop_latched"}
    arm = bool(params.get("enable", False))
    publishers.publish_dock_enable(arm)
    return {"armed": arm}


def cmd_capture(params: Dict, publishers: Any, _now=time.time) -> Dict:
    """Return base64 of the latest camera frame, downsampled to
    ``max_px``. ``publishers`` exposes ``snapshot_camera_jpeg``."""
    max_px = int(params.get("max_px", 640))
    return publishers.snapshot_camera_jpeg(max_px=max_px) or \
        {"ts": _now(), "width": 0, "height": 0,
         "data_url": ""}


def cmd_telemetry(params: Dict, publishers: Any, _now=time.time) -> Dict:
    return publishers.snapshot_telemetry()


def cmd_query(params: Dict, publishers: Any, _now=time.time) -> Dict:
    kind = str(params.get("kind", "knowledge")).strip().lower()
    text = str(params.get("text", "")).strip()
    k = int(params.get("k", 3))
    return publishers.publish_meta_query(kind=kind, text=text, k=k)


def cmd_chat(params: Dict, publishers: Any, _now=time.time) -> Dict:
    text = str(params.get("text", "")).strip()
    use_external = bool(params.get("use_external_llm", False))
    return publishers.publish_chat(text=text, use_external=use_external)


# Dispatch table — the FastAPI layer consults by command name.
DISPATCH: Dict[str, Callable[[Dict, Any], Dict]] = {
    "estop":    cmd_estop,
    "move":     cmd_move,
    "patrol":   cmd_patrol,
    "dock":     cmd_dock,
    "capture":  cmd_capture,
    "telemetry": cmd_telemetry,
    "query":    cmd_query,
    "chat":     cmd_chat,
}


RATE_CLASS: Dict[str, str] = {
    "estop":    "write",
    "move":     "write",
    "patrol":   "write",
    "dock":     "write",
    "capture":  "read",
    "telemetry": "read",
    "query":    "read",
    "chat":     "read",
}


# =============================================================================
# Voice-command plugin auto-discovery.
#
# Drop new plugins in ``plugins/`` and add their entry-point to
# ``plugins.PLUGIN_PATHS``.  They register themselves into DISPATCH /
# RATE_CLASS above.  See :mod:`tank_command_bridge.plugins` for the base
# class and contract.
# =============================================================================
from .plugins import _register_voice_plugins  # noqa: E402
_REGISTERED = _register_voice_plugins(DISPATCH, RATE_CLASS)
