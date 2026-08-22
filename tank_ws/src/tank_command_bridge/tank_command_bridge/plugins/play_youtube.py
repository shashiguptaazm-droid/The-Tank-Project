"""``voice.play_youtube`` plugin.

Voice flow::

  user:  "Hey Tank, play The Dark Side of the Moon on the living room TV"
  llm:   "Want me to extract YouTube audio?"
  user:  "Yes"
  llm:   → ``voice.play_youtube {"query":"Pink Floyd Dark Side of the Moon video",
                                 "cast_target": "living room tv",
                                 "format": "audio"}``

Two-step flow:

1. Resolves ``query`` into a direct playable URL via ``yt-dlp -g``.
2. Hands the URL to ``voice.play_tv`` (internal bridge) — we call our
   own ``shell_cast`` helper so this plugin is independently working
   when ``play_tv`` is intentionally disabled.

``yt-dlp`` is a lazy import (subprocess call) — missing binary
returns a friendly ``_hint`` instead of traceback.
"""
from __future__ import annotations

from typing import Any, Dict

from . import RobotPlugin
from ._house_helpers import shell_cast, shell_ytdlp


class PlayYouTubePlugin(RobotPlugin):
    """YouTube search → extract URL → cast to a named device."""

    NAME = "voice.play_youtube"
    DESCRIPTION = (
        "Search YouTube via ``yt-dlp -g`` for the given query, extract "
        "a direct playable URL (audio or video), then cast it to a "
        "named Chromecast / AirPlay speaker or TV. Without a cast "
        "target, returns the URL + a friendly hint so the LLM can "
        "ask the user to pick one."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query":    {"type": "string",
                          "description": "Search query for YouTube."},
            "format":   {"type": "string",
                          "description": "Stream flavour.",
                          "enum": ["audio", "video"], "default": "audio"},
            "cast_target": {"type": "string",
                            "description":
                                "Friendly name of the cast device to "
                                "play on. If empty, the URL is returned "
                                "but not cast.",
                            "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "query":     {"type": "string"},
            "url":       {"type": "string",
                           "description":
                               "Direct media URL produced by yt-dlp "
                               "(empty if extraction failed)."},
            "format":    {"type": "string"},
            "cast": {
                "type": "object",
                "description":
                    "Result of the cast attempt if ``cast_target`` "
                    "was supplied.",
                "properties": {
                    "pid": {"type": "integer"},
                    "binary": {"type": "string"},
                    "device": {"type": "string"},
                },
            },
            "tts_text":  {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "media", "youtube"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        query = (params.get("query") or "").strip()
        if not query:
            return {"_ok": False, "_error": "missing query",
                    "tts_text": "What do you want me to play from YouTube?",
                    "url": "", "cast": {}, "format": "",
                    "query": ""}
        fmt = str(params.get("format", "audio")).lower()
        target = (params.get("cast_target") or "").strip()

        extracted = shell_ytdlp(query, audio_only=(fmt == "audio"))
        if not extracted.get("_ok"):
            return {"_ok": False, "query": query, "format": fmt,
                    "url": "", "cast": {},
                    "_hint": extracted.get("_hint", "yt-dlp failed"),
                    "tts_text":
                        ("I couldn't pull that YouTube video. "
                         f"{extracted.get('_hint', '')}")}

        url = extracted["url"]
        out: Dict[str, Any] = {"_ok": True, "query": query, "format": fmt,
                              "url": url, "cast": {},
                              "tts_text": ""}
        if target:
            cast_out = shell_cast(target, url)
            out["cast"] = cast_out if cast_out.get("_ok") else {}
            if cast_out.get("_ok"):
                out["tts_text"] = f"Casting to {target}."
            else:
                out["tts_text"] = (
                    f"I have the stream but couldn't cast — "
                    f"{cast_out.get('_hint', 'cast failed')}"
                )
        else:
            out["tts_text"] = (
                "I extracted the YouTube stream. "
                "Which device would you like me to play it on?"
            )
        return out
