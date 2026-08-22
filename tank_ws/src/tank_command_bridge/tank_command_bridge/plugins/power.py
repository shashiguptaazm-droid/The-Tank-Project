"""``voice.power`` plugin.

Set the robot's own power mode.

* ``sleep``        — drive the chassis into a low-power state. Refuses
                    if estop is latched, so the operator can't put the
                    robot to sleep while the e-stop is pressed.
* ``wake``         — wake from sleep.
* ``reboot``       — request a controlled reboot. HARD-HEURISTIC:
                    refuses if the battery is below ~30 % or estop is
                    latched.
* ``soft_restart`` — restart the bridge process only, not the OS. The
                    operator only — used after a code deploy.

No actual OS-level reboot is issued — this plugin writes the
:data:`DEFAULT_POWER_STATE_PATH` JSON file. A small lifecycle script
on the host polls it every second and runs the actual transition.
That keeps the bridge process fully decoupled from system calls.
"""
from __future__ import annotations

import time
from typing import Any, Dict

from . import RobotPlugin
from ._house_helpers import (
    DEFAULT_POWER_STATE_PATH,
    PowerState,
    load_power_state,
    save_power_state,
)



class PowerPlugin(RobotPlugin):
    """Robot power-mode setter."""

    NAME = "voice.power"
    DESCRIPTION = (
        "Request a power-mode change for the robot: ``wake``, ``sleep``, "
        "``soft_restart`` (the bridge), or ``reboot`` (the host). "
        "Refuses ``sleep``/``reboot`` while the e-stop is latched so "
        "the operator can never put a robot to sleep in an unsafe "
        "state. Writes a durable JSON file that the on-host lifecycle "
        "script polls every second and translates into a real "
        "transition."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["mode"],
        "properties": {
            "mode":   {"type": "string",
                        "description":
                            "New state. One of wake | sleep | reboot | "
                            "soft_restart. ``sleep`` requires estop "
                            "released. ``reboot`` requires estop released "
                            "and battery >= 30 %.",
                        "enum": ["wake", "sleep", "reboot", "soft_restart"]},
            "reason": {"type": "string",
                        "description":
                            "Free-text reason used in the audit log.",
                        "default": "voice_command"},
            "estop_latched": {"type": "boolean",
                               "description":
                                   "Caller-supplied estop state. If "
                                   "omitted we read it from "
                                   "tank_security.event_logger or fall "
                                   "back to false.",
                               "default": False},
            "battery_pct":   {"type": "number",
                               "description":
                                   "Latest battery percentage "
                                   "(0..100). Caller-supplied because "
                                   "the bridge lives outside the ros "
                                   "graph in this plugin.",
                               "default": 100.0},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "previous_mode": {"type": "string"},
            "new_mode":      {"type": "string"},
            "accepted":      {"type": "boolean"},
            "rejected_reason": {"type": "string"},
            "tts_text":      {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "power"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        mode = (params.get("mode") or "").strip().lower()
        reason = (params.get("reason") or "voice_command").strip()[:120]
        estop = bool(params.get("estop_latched", False))
        battery_pct = float(params.get("battery_pct", 100.0))

        state = load_power_state()
        previous = state.mode

        # estop-aware refusals.
        if mode in ("sleep", "reboot") and estop:
            return {"_ok": False, "previous_mode": previous,
                    "new_mode": previous, "accepted": False,
                    "rejected_reason": "estop_latched",
                    "tts_text":
                        ("I can't put the robot to sleep while the "
                         "e-stop is pressed.  Release it first.")}

        # battery-aware refusal on reboot.
        if mode == "reboot" and battery_pct < 30.0:
            return {"_ok": False, "previous_mode": previous,
                    "new_mode": previous, "accepted": False,
                    "rejected_reason":
                        f"low_battery:{round(battery_pct, 1)}%",
                    "tts_text":
                        (f"Battery is only {battery_pct:.0f} percent — "
                         "I won't reboot below thirty percent.")}

        if mode not in ("wake", "sleep", "reboot", "soft_restart"):
            return {"_ok": False, "previous_mode": previous,
                    "new_mode": previous, "accepted": False,
                    "rejected_reason": f"unknown_mode:{mode!r}",
                    "tts_text": "I don't recognise that power mode."}

        state.mode = mode
        state.since = time.time()
        state.estop_latched = estop    # mirror what the caller reported
        state.last_transition_reason = reason
        save_power_state(state, DEFAULT_POWER_STATE_PATH)

        # TTS-friendly line.
        line_map = {
            "wake":         "I'm awake now.",
            "sleep":        "Going to sleep. Good night.",
            "reboot":       "Rebooting now — give me a minute.",
            "soft_restart": "Restarting the assistant — back in a sec.",
        }
        return {"_ok": True, "previous_mode": previous,
                "new_mode": mode, "accepted": True,
                "rejected_reason": "",
                "tts_text": line_map.get(mode, f"Power mode is now {mode}.")}
