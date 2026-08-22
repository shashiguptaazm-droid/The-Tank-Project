"""``voice.play_music`` plugin.

Alexa-style music playback against a local library.

Voice flow::

  user:  "Hey Tank, play Time by Pink Floyd"
  llm:   "I found two files — Time by Pink Floyd on Dark Side of the
          Moon, 9.6 MB; and another Time by Pink Floyd in a live set.
          Play the studio album one?"
  user:  "Yes"
  llm:   → ``voice.play_music {"track": "Time", "artist": "Pink Floyd"}``

Defaults to /music (or ~/Music if /music doesn't exist) and spawns
``mpv --no-video`` non-blocking as a background subprocess so the
voice loop returns immediately and the LLM can keep composing.

Future Spotify
~~~~~~~~~~~~~~
A future plugin can wrap Spotify Web API tokens alongside this one
without breaking the schema here; we'd add a ``provider: spotify``
parameter that splits the param tree cleanly.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import RobotPlugin
from ._house_helpers import (
    DEFAULT_MUSIC_ROOTS,
    TrackHit,
    scan_music,
    shell_mpv,
)


class PlayMusicPlugin(RobotPlugin):
    """Play a track from the configured local music library."""

    NAME = "voice.play_music"
    DESCRIPTION = (
        "Search the local music library (defaults /music, /srv/music, "
        "~/Music) for tracks whose filename matches the query (with "
        "artist hint if supplied), then spawn ``mpv --no-video`` to "
        "play the chosen file in the background. Returns the actual path "
        "and a process pid so the LLM can confirm what is now playing."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query":  {"type": "string",
                       "description":
                           "Movie / album / playlist name to search for. "
                           "Substring match against filename."},
            "artist": {"type": "string",
                       "description":
                           "Optional artist hint; weights scoring if the "
                           "filename parses as \"Artist - Title\".",
                       "default": ""},
            "root":   {"type": "string",
                       "description":
                           "Music-root override; default searches "
                           "``/music``, ``/srv/music`` and ``~/Music``.",
                       "default": ""},
            "limit":  {"type": "integer",
                       "description":
                           "Max tracks to consider (default 5, max 20).",
                       "minimum": 1, "maximum": 20, "default": 5},
            "blocking": {"type": "boolean",
                          "description":
                              "If true, R waits for mpv to finish. "
                              "Default false — mpv plays in background.",
                          "default": False},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "tracks": {
                "type": "array",
                "description": "Scored candidate tracks ranked by score.",
                "items": {
                    "type": "object",
                    "properties": {
                        "path":   {"type": "string"},
                        "title":  {"type": "string"},
                        "artist": {"type": "string"},
                        "score":  {"type": "number"},
                    },
                },
            },
            "now_playing": {
                "type": "object",
                "nullable": True,
                "properties": {
                    "path":  {"type": "string"},
                    "pid":   {"type": "integer"},
                    "title": {"type": "string"},
                },
                "description":
                    "Result of spawning mpv for the top hit, if any.",
            },
            "tts_text": {"type": "string",
                          "description":
                              "Pre-baked line the assistant speaks back "
                              "to the user — e.g. \"Playing Time by "
                              "Pink Floyd.\""},
        },
    }
    TAGS = ["write", "voice", "media"]
    RATE_CLASS = "write"     # spawns a process

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        query = (params.get("query") or "").strip()
        artist_hint = (params.get("artist") or "").strip().lower()
        limit = int(params.get("limit", 5))
        blocking = bool(params.get("blocking", False))
        explicit_root = (params.get("root") or "").strip()
        roots: List = []
        if explicit_root:
            from pathlib import Path
            roots.append(Path(explicit_root))
        else:
            from pathlib import Path
            roots.extend(Path(r) for r in DEFAULT_MUSIC_ROOTS)

        # Boost score for artist hint by re-querying with combined query.
        effective_query = (query + " " + artist_hint).strip() if artist_hint else query
        hits = scan_music(effective_query, roots=roots, limit=limit)
        if not hits:
            return {"tracks": [],
                    "now_playing": None,
                    "tts_text": f"I couldn't find any track matching {query!r}.",
                    "_ok": False}

        track_dicts = [self._track_dict(h) for h in hits]
        top: TrackHit = hits[0]
        spawned = shell_mpv(top.path, video=False, blocking=blocking)
        if not spawned.get("_ok"):
            return {"tracks": track_dicts,
                    "now_playing": None,
                    "tts_text":
                        (f"I found {top.title} by {top.artist or 'unknown'} "
                         f"but couldn't start playback: "
                         f"{spawned.get('_hint', 'mpv unavailable')}"),
                    "_ok": False}
        title = top.title or top.path.rsplit("/", 1)[-1]
        return {"tracks": track_dicts,
                "now_playing": {"path": top.path,
                                "pid": spawned.get("pid", 0),
                                "title": title},
                "tts_text": (f"Playing {title}"
                             + (f" by {top.artist}" if top.artist else "")),
                "_ok": True}

    @staticmethod
    def _track_dict(h: TrackHit) -> Dict[str, Any]:
        return {"path": h.path, "title": h.title,
                "artist": h.artist, "score": round(h.score(), 2)}
