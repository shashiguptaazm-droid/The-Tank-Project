"""``voice.aria2_progress`` plugin.

Virtual voice progress poll.

* User: "Hey Tank, how's the torrent?"
* LLM: *calls* ``voice.aria2_progress`` ``{"gid": "abc123"}``.
* Plugin asks aria2 for ``tellStatus(gid)``, formats:
  - ``progress_pct`` (0.0 - 100.0)
  - ``download_speed`` / ``upload_speed`` (bytes/s)
  - ``num_seeders`` / ``connections``
  - ``eta_s`` (computed)
  - ``status`` ("active" | "waiting" | "paused" | "complete" | "error")
* Returns a clean dict so the LLM can say "Inception is at 42 percent,
  1.6 MB/s, ETA 9 minutes."
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from . import RobotPlugin
from ._aria2_common import Aria2Error, tell_status, warn_if_no_token


# aria2 status strings we map to "voice-friendly" labels.
_VOICE_STATUS = {
    "active":    "active",
    "waiting":   "queued",
    "paused":    "paused",
    "complete":  "complete",
    "error":     "error",
    "removed":   "removed",
}


def _format_bytes_per_sec(size: Any) -> int:
    try:
        return int(size or 0)
    except (TypeError, ValueError):
        return 0


def _format_eta(remaining: Any, speed: Any) -> Optional[int]:
    try:
        r = int(remaining or 0)
        s = int(speed or 0)
    except (TypeError, ValueError):
        return None
    if r <= 0 or s <= 0:
        return None
    return r // s


def _format_status(raw: str) -> str:
    return _VOICE_STATUS.get(raw, raw or "unknown")


def _extract_title(raw: Dict[str, Any]) -> str:
    """Best-effort human title from an aria2 ``tellStatus`` payload.

    Three fallbacks, tried in order, each wrapped in try/except so a
    malformed key never reaches the TTS pipeline:

    1. ``bittorrent.info.name``         (preferred when present)
    2. ``files[0].path``                (basename)
    3. ``"the download"``               (constant fallback)

    Never raises.
    """
    try:
        bt = raw.get("bittorrent") or {}
        if isinstance(bt, dict):
            info = bt.get("info")
            if isinstance(info, dict):
                name = info.get("name")
                if isinstance(name, str) and name:
                    return name
    except Exception:
        pass
    try:
        files = raw.get("files")
        if isinstance(files, list) and files:
            first = files[0]
            if isinstance(first, dict):
                path = first.get("path")
                if isinstance(path, str) and path:
                    return path.rsplit("/", 1)[-1] or "the download"
    except Exception:
        pass
    return "the download"


class Aria2ProgressPlugin(RobotPlugin):
    """Poll aria2 for download progress by gid."""

    NAME = "voice.aria2_progress"
    DESCRIPTION = (
        "Poll the local aria2 instance for the current download status "
        "of a single torrent gid, returning percent, speed, ETA, "
        "seeders, and connections. The audio-friendly text the LLM "
        "should speak is given under ``tts_text``. Use this after "
        "``voice.aria2_add`` succeeded."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["gid"],
        "properties": {
            "gid": {"type": "string",
                    "description": "aria2 gid returned by ``voice.aria2_add``"},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "gid":            {"type": "string"},
            "status":         {"type": "string"},
            "progress_pct":   {"type": "number"},
            "size_bytes":     {"type": "integer"},
            "downloaded_bytes": {"type": "integer"},
            "download_speed": {"type": "integer"},
            "upload_speed":   {"type": "integer"},
            "num_seeders":    {"type": "integer"},
            "connections":    {"type": "integer"},
            "eta_s":          {"type": "integer"},
            "tts_text":       {"type": "string",
                               "description":
                                   "Pre-baked natural-language status line "
                                   "ready for the assistant to send to Piper TTS."},
        },
    }
    TAGS = ["read", "voice", "aria2"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        gid = (params.get("gid") or "").strip()
        if not gid:
            return {"gid": "", "status": "rejected",
                    "progress_pct": 0.0,
                    "tts_text": "No download was given to check.",
                    "_ok": False}
        warn_if_no_token()
        try:
            raw = tell_status(gid)
        except Aria2Error as exc:
            return {"gid": gid, "status": "error",
                    "progress_pct": 0.0,
                    "tts_text": f"I couldn't reach aria2: {exc}",
                    "_ok": False}

        total = _format_bytes_per_sec(raw.get("totalLength"))
        done  = _format_bytes_per_sec(raw.get("completedLength"))
        speed_d = _format_bytes_per_sec(raw.get("downloadSpeed"))
        speed_u = _format_bytes_per_sec(raw.get("uploadSpeed"))
        remaining = max(0, total - done)
        pct = (100.0 * done / total) if total > 0 else 0.0
        eta_s = _format_eta(remaining, speed_d)
        status = _format_status(raw.get("status", ""))
        title = _extract_title(raw)
        seeders = raw.get("numSeeders", 0)
        connections = raw.get("connections", 0)

        # TTS-friendly line.  Keep terse so Piper's natural-rhythm stays clean.
        if status == "complete":
            tts = f"{title} finished downloading."
        elif eta_s is None or remaining == 0:
            tts = (f"{title} is at {pct:.0f} percent, "
                   f"downloading at {speed_d / 1e6:.1f} megabytes per second.")
        else:
            minutes = max(1, eta_s // 60)
            tts = (f"{title} is at {pct:.0f} percent, "
                   f"downspeed {speed_d / 1e6:.1f} MB per second, "
                   f"about {minutes} minute{'s' if minutes != 1 else ''} left.")

        return {
            "gid": gid,
            "status": status,
            "progress_pct": round(pct, 2),
            "size_bytes": total,
            "downloaded_bytes": done,
            "download_speed": speed_d,
            "upload_speed":   speed_u,
            "num_seeders":    int(seeders or 0),
            "connections":    int(connections or 0),
            "eta_s":          eta_s if eta_s is not None else 0,
            "tts_text":       tts,
            "_ok": True,
            "_fetched_at":    int(time.time()),
        }
