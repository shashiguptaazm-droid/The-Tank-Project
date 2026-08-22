"""``voice.play_tv`` plugin.

Cast a media URL to a specific TV or cast receiver by friendly name.

The plugin relies on :func:`shell_cast` which prefers ``cast-now`` and
falls back to ``catt`` — both are spawned as background processes
so the bridge returns immediately.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._house_helpers import shell_cast


class PlayTvPlugin(RobotPlugin):
    """Cast a media URL to a TV / receiver by name."""

    NAME = "voice.play_tv"
    DESCRIPTION = (
        "Cast an http(s) video or audio URL to a named TV or cast "
        "receiver (``living room tv``, ``kitchen echo``, etc.). The "
        "device must be on the LAN and reachable; this plugin does "
        "NOT issue a network probe — pair it with ``voice.find_devices`` "
        "if the LLM needs a device catalogue first."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["tv_name", "url"],
        "properties": {
            "tv_name": {"type": "string",
                        "description":
                            "Friendly name of the cast receiver / TV."},
            "url":     {"type": "string",
                        "description": "http(s) URL to play."},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "tv_name":  {"type": "string"},
            "url":      {"type": "string"},
            "cast": {
                "type": "object",
                "properties": {
                    "pid": {"type": "integer"},
                    "binary": {"type": "string"},
                },
            },
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "media", "cast"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        tv = (params.get("tv_name") or "").strip()
        url = (params.get("url") or "").strip()
        if not tv or not url:
            return {"_ok": False, "_error": "missing tv_name or url",
                    "tts_text":
                        ("I need both a TV name and a URL to play on it."),
                    "cast": {}, "tv_name": tv, "url": url}
        cast_out = shell_cast(tv, url)
        if cast_out.get("_ok"):
            return {"_ok": True, "tv_name": tv, "url": url, "cast": cast_out,
                    "tts_text":
                        f"Casting to {tv}."}
        return {"_ok": False, "tv_name": tv, "url": url, "cast": {},
                "_hint": cast_out.get("_hint", "cast failed"),
                "tts_text":
                    (f"I couldn't cast to {tv} — "
                     f"{cast_out.get('_hint', 'cast failed')}")}
