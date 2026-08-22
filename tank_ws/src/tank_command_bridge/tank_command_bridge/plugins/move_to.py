"""``voice.move_to`` plugin.

Conversational motion. Two modes in one plugin:

* ``zone``     — "go to the kitchen" — loads the operator-curated
                  zone map from disk, looks up the named zone / waypoint,
                  and persists a motion intent. The host lifecycle
                  script polls :data:`DEFAULT_MOTION_INTENT_PATH` and
                  actually drives the chassis.

* ``relative`` — "back up half a meter" / "spin left ninety degrees" —
                  clamps the distance, scales the vector, persists
                  the same intent.

Why a file (instead of in-memory dispatch)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Today's bridge process does not have a live motion publisher
(``tank_navigation`` may not be loaded in the same process).  A
received-intent file is observable state that:
  * any consumer can poll without needing an IPC contract,
  * survives the bridge dying between intent and dispatch, and
  * produces an audit trail in the directory alongside the power
    state file.

Safety rules
~~~~~~~~~~~~
* ``relative.distance_m`` is clamped between
  :data:`RELATIVE_MIN_M` (``0.05``) and :data:`RELATIVE_MAX_M`
  (``4.0``).
* Every motion refuses if the estop is latched. Caller must pass
  ``estop_latched=False`` (or omit) to let the robot move.
* Zone mode disables when the named zone is missing from the map and
  the LLM hasn't supplied an explicit (x, y) override.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import RobotPlugin
from ._house_helpers import (
    DEFAULT_MOTION_INTENT_PATH,
    DEFAULT_ZONE_MAP_PATH,
    MAX_FREE_VX_M_S,
    MAX_FREE_WZ_RAD_S,
    RELATIVE_MAX_M,
    RELATIVE_MIN_M,
    ZoneMap,
    clamp_relative_distance,
    load_zone_map,
    save_motion_intent,
)

_RELATIVE_DIRS = {
    "forward":  (0.5,  0.0),
    "back":     (-0.5, 0.0),
    "backward": (-0.5, 0.0),
    "left":     (0.0,  0.6),
    "right":    (0.0, -0.6),
    "stop":     (0.0,  0.0),
}


class MoveToPlugin(RobotPlugin):
    """Conversational motion (zone OR relative)."""

    NAME = "voice.move_to"
    DESCRIPTION = (
        "Drive the chassis in two ways: ``zone`` mode looks up the "
        "named zone in :file:`/etc/tank/zone_map.json` and persists a "
        "motion-intent record pointing at its (x, y) anchor; "
        "``relative`` mode parses a direction + distance and persists "
        "a clamped Twist. The on-host lifecycle script polls the "
        "intent file every ~200 ms and hands it to the navigation "
        "stack; this plugin does NOT depend on a live in-process "
        "publisher. Refuses motion while the e-stop is latched or "
        "if the target zone is not in the map."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["mode"],
        "properties": {
            "mode":  {"type": "string",
                       "enum": ["zone", "relative"], "default": "relative"},
            "zone":  {"type": "string",
                       "description": "Zone name (zone mode)."},
            "direction": {"type": "string",
                           "enum": sorted(_RELATIVE_DIRS.keys()),
                           "description": "Direction (relative mode)."},
            "distance_m": {"type": "number",
                            "description":
                                "Distance to traverse in metres "
                                "(relative mode); clamped 0.05-4.0.",
                            "minimum": 0.0, "maximum": 4.5, "default": 0.5},
            "x_m":   {"type": "number",
                       "description": "Optional direct X override."},
            "y_m":   {"type": "number",
                       "description": "Optional direct Y override."},
            "duration_s": {
                "type": "number",
                "description":
                    "Duration cap (s). Default 2.0.",
                "minimum": 0.1, "maximum": 5.0, "default": 2.0,
            },
            "estop_latched": {"type": "boolean",
                               "description":
                                   "True means the e-stop is engaged. "
                                   "Any motion will be rejected.",
                               "default": False},
            "zone_map_path": {"type": "string",
                               "description":
                                   "Override for the zone-map path.",
                               "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "object",
                "description":
                    "Resolved motion intent that was persisted to the "
                    "intent file."
                ,
                "properties": {
                    "vx":     {"type": "number"},
                    "wz":     {"type": "number"},
                    "duration_s": {"type": "number"},
                    "target_zone": {"type": "string"},
                    "target_x_m": {"type": "number"},
                    "target_y_m": {"type": "number"},
                },
            },
            "intent_path": {"type": "string",
                             "description":
                                 "Absolute path of the intent file "
                                 "written (for audit / debug)."},
            "tts_text":   {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "motion"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        estop = bool(params.get("estop_latched", False))
        if estop:
            return {"_ok": False, "intent": {},
                    "intent_path": "",
                    "tts_text":
                        "I can't move while the e-stop is pressed.",
                    "rejected_reason": "estop_latched"}

        mode = (params.get("mode") or "relative").strip().lower()
        duration = float(params.get("duration_s", 2.0))
        if mode == "zone":
            return self._zone_mode(params, duration)
        if mode == "relative":
            return self._relative_mode(params, duration)
        return {"_ok": False, "intent": {}, "intent_path": "",
                "tts_text": f"I don't know motion mode {mode!r}."}

    # ----- helpers -----
    def _zone_mode(self, params: Dict[str, Any],
                   duration: float) -> Dict[str, Any]:
        name = (params.get("zone") or "").strip()
        zone_path = params.get("zone_map_path") or DEFAULT_ZONE_MAP_PATH
        zm: ZoneMap = load_zone_map(zone_path)
        explicit_x = params.get("x_m")
        explicit_y = params.get("y_m")

        if explicit_x is not None and explicit_y is not None:
            intent = {"vx": MAX_FREE_VX_M_S * 0.6,
                      "wz": 0.0,
                      "duration_s": duration,
                      "target_zone": name or "(freeform)",
                      "target_x_m": float(explicit_x),
                      "target_y_m": float(explicit_y)}
            self._persist_intent(intent)
            return {"_ok": True, "intent": intent,
                    "intent_path": str(DEFAULT_MOTION_INTENT_PATH),
                    "tts_text":
                        f"Heading to {(float(explicit_x), float(explicit_y))}."}

        if not name:
            return {"_ok": False, "intent": {}, "intent_path": "",
                    "tts_text":
                        "Which zone should I drive to? You can also "
                        "give me a metre offset like 'forward 1.0'."}
        zone = zm.get_zone(name) or zm.get_waypoint(name)
        if zone is None:
            return {"_ok": False, "intent": {}, "intent_path": "",
                    "tts_text":
                        f"I don't know where {name!r} is — add it to "
                         f"{DEFAULT_ZONE_MAP_PATH}."}
        vx = MAX_FREE_VX_M_S * 0.6
        wz = 0.0
        intent = {"vx": vx, "wz": wz,
                  "duration_s": duration,
                  "target_zone": zone.name,
                  "target_x_m": zone.x_m,
                  "target_y_m": zone.y_m}
        self._persist_intent(intent)
        return {"_ok": True, "intent": intent,
                "intent_path": str(DEFAULT_MOTION_INTENT_PATH),
                "tts_text": f"Heading to {zone.name}."}

    def _relative_mode(self, params: Dict[str, Any],
                       duration: float) -> Dict[str, Any]:
        raw_dir = (params.get("direction") or "").strip().lower()
        scaled = _RELATIVE_DIRS.get(raw_dir)
        if scaled is None:
            return {"_ok": False, "intent": {}, "intent_path": "",
                    "tts_text":
                        (f"I don't know direction {raw_dir!r}; try "
                         "forward / back / left / right / stop.")}
        distance_m = clamp_relative_distance(
            float(params.get("distance_m", 0.5))
        )
        v_target, w_target = scaled
        vx = max(-MAX_FREE_VX_M_S, min(MAX_FREE_VX_M_S,
                                       round(v_target * distance_m, 3)))
        wz = max(-MAX_FREE_WZ_RAD_S, min(MAX_FREE_WZ_RAD_S, w_target))

        intent = {"vx": vx, "wz": wz,
                  "duration_s": duration,
                  "target_zone": "",
                  "target_x_m": 0.0,
                  "target_y_m": 0.0}
        self._persist_intent(intent)
        readable = "stopping" if raw_dir == "stop" else \
            f"moving {raw_dir} {distance_m:.2f} metres"
        return {"_ok": True, "intent": intent,
                "intent_path": str(DEFAULT_MOTION_INTENT_PATH),
                "tts_text": f"OK, {readable}."}

    @staticmethod
    def _persist_intent(intent: Dict[str, Any]) -> None:
        """Persist via :func:`save_motion_intent`.

        The path is the module-level constant exposed by
        :mod:`_house_helpers`. Tests that need to verify the file
        land at a specific path can patch
        ``tank_command_bridge.plugins.move_to.DEFAULT_MOTION_INTENT_PATH``.
        """
        save_motion_intent(intent, DEFAULT_MOTION_INTENT_PATH)
