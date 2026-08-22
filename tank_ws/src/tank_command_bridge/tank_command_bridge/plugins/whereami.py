"""``voice.whereami`` plugin.

"Where am I?" — looks up the zone name for the current pose.

Pose comes from the operator-curated zone map's ``current_pose`` field
(:data:`DEFAULT_ZONE_MAP_PATH`). We do NOT subscribe to live SLAM
output today — the lightweight design is "the router process writes
its current pose into the map file every few seconds; ``whereami``
reads it". This stays useful when SLAM drifts and the user wants a
quick verbal answer.

The schema lets the caller pass ``x_m``/``y_m`` overrides so the LLM
can answer about a hypothetical position without changing the
operator's recorded pose.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._house_helpers import (
    DEFAULT_ZONE_MAP_PATH,
    ZoneMap,
    load_zone_map,
)


class WhereAmIPlugin(RobotPlugin):
    """Resolve a 2D pose → zone name."""

    NAME = "voice.whereami"
    DESCRIPTION = (
        "Report the zone name for the current pose. Reads the "
        "``current_pose`` field of :file:`/etc/tank/zone_map.json` "
        "(the bridge writes it every few seconds) and matches against "
        "the zone radii. Returns ``\"unknown zone\"`` if no zone "
        "contains the pose."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "x_m":   {"type": "number",
                       "description":
                           "Optional pose-X override. If both x_m and "
                           "y_m are supplied, those are used. "
                           "Otherwise the operator's current_pose is.",
                       "default": 0.0},
            "y_m":   {"type": "number",
                       "description": "Optional pose-Y override.",
                       "default": 0.0},
            "use_override_only": {"type": "boolean",
                                    "description":
                                        "If true, do NOT fall back to "
                                        "current_pose.",
                                    "default": False},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "zone":     {"type": "string",
                          "description":
                              "Resolved zone name, or \"unknown zone\"."},
            "pose":     {"type": "object",
                          "properties": {
                              "x_m": {"type": "number"},
                              "y_m": {"type": "number"},
                          }},
            "all_zones": {
                "type": "array",
                "description":
                    "All zones in the map, useful so the LLM can "
                    "explain \"I see a kitchen and a living room\".",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":     {"type": "string"},
                        "x_m":      {"type": "number"},
                        "y_m":      {"type": "number"},
                        "radius_m": {"type": "number"},
                    },
                },
            },
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "navigation"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        zm: ZoneMap = load_zone_map(DEFAULT_ZONE_MAP_PATH)
        use_override_only = bool(params.get("use_override_only", False))

        x_in = params.get("x_m")
        y_in = params.get("y_m")
        if (not use_override_only
            and (x_in is None or float(x_in) == 0.0)
            and (y_in is None or float(y_in) == 0.0)
            and isinstance(zm.current_pose.get("x"), (int, float))):
            x = float(zm.current_pose.get("x", 0.0))
            y = float(zm.current_pose.get("y", 0.0))
        else:
            try:
                x = float(x_in)
                y = float(y_in)
            except (TypeError, ValueError):
                x = float(zm.current_pose.get("x", 0.0))
                y = float(zm.current_pose.get("y", 0.0))

        zone = zm.zone_at(x, y)
        zone_name = zone.name if zone else "unknown zone"
        if zone_name == "unknown zone":
            tts = "I'm not sure which room I'm in right now."
        else:
            tts = f"I'm in the {zone_name}."

        return {
            "_ok": True,
            "zone": zone_name,
            "pose": {"x_m": float(x), "y_m": float(y)},
            "all_zones": [
                {"name": z.name, "x_m": z.x_m, "y_m": z.y_m,
                 "radius_m": z.radius_m}
                for z in zm.zones
            ],
            "tts_text": tts,
        }
