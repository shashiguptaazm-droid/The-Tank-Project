"""
Simple Internet — TankOS Voice Plugin.

Bridges the Simple Internet download engine into the TankOS voice command system.
Allows users to say things like:
  - "Hey Tank, download Ubuntu ISO"
  - "Find me the torrent for Inception"
  - "Download the top result"
  - "Search YouTube for piano tutorials"
  - "Show my download queue"
  - "Pause the download"
  - "What's downloading right now?"

This plugin follows the same pattern as the existing voice plugins
(voice.torrent_search, voice.aria2_add, voice.play_youtube) but
uses the unified Simple Internet manager as the backend.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from tank_os.internet.manager import InternetManager
from tank_os.internet.downloader import DownloadStatus
from tank_os.internet.search import SearchQuery, SearchSource

logger = logging.getLogger("tank_os.internet.voice")

_manager_lock = threading.Lock()
_manager: Optional[InternetManager] = None


def _get_manager() -> InternetManager:
    """Get or initialize the InternetManager singleton."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = InternetManager()
            _manager.initialize()
        return _manager


# ═══════════════════════════════════════════════════════════════════════
# Plugin Definitions (compatible with tank_command_bridge RobotPlugin)
# ═══════════════════════════════════════════════════════════════════════

PLUGINS: Dict[str, Dict[str, Any]] = {}


def _register(name: str, description: str,
              params: Dict, response: Dict,
              tags: list, rate_class: str = "write"):
    """Register a voice plugin definition."""
    PLUGINS[name] = {
        "name": name,
        "description": description,
        "parameters": params,
        "response": response,
        "tags": tags,
        "rate_class": rate_class,
    }


_register(
    name="voice.internet_download",
    description=(
        "Download any URL (HTTP/HTTPS, magnet, torrent file, YouTube video) "
        "using Simple Internet. Automatically detects the protocol and adds "
        "it to the download queue."
    ),
    params={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string",
                    "description": "URL to download. Supports HTTP, HTTPS, magnet:, .torrent, YouTube, etc."},
            "filename": {"type": "string",
                         "description": "Optional custom filename override",
                         "default": ""},
            "priority": {"type": "integer",
                         "description": "Priority (1-10, lower is higher priority)",
                         "minimum": 1, "maximum": 10, "default": 5},
            "convert_to": {"type": "string",
                           "description": "Convert after download (e.g. 'mp3', 'mp4')",
                           "default": ""},
        },
    },
    response={
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "filename": {"type": "string"},
            "protocol": {"type": "string"},
            "status": {"type": "string"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["write", "voice", "download", "internet"],
)

_register(
    name="voice.internet_search",
    description=(
        "Search the internet for torrents, web pages, YouTube videos, "
        "images, or news. Returns ranked results. Can be followed up "
        "with voice.internet_download to download the chosen result."
    ),
    params={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string",
                      "description": "Search query"},
            "source": {"type": "string",
                       "enum": ["web", "torrent", "youtube", "soundcloud", "images", "news"],
                       "description": "Search source",
                       "default": "web"},
            "limit": {"type": "integer",
                      "description": "Max results (default 5, max 20)",
                      "minimum": 1, "maximum": 20, "default": 5},
        },
    },
    response={
        "type": "object",
        "properties": {
            "results": {"type": "array"},
            "total": {"type": "integer"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["read", "voice", "search", "internet"],
)

_register(
    name="voice.internet_queue",
    description=(
        "Show the current download queue — active, queued, and paused downloads. "
        "Returns the status of each download including progress percentage."
    ),
    params={
        "type": "object",
        "properties": {},
    },
    response={
        "type": "object",
        "properties": {
            "active": {"type": "integer"},
            "queued": {"type": "integer"},
            "items": {"type": "array"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["read", "voice", "download"],
)

_register(
    name="voice.internet_cancel",
    description=(
        "Cancel a download by its ID. Use voice.internet_queue first "
        "to see the list of active downloads and their IDs."
    ),
    params={
        "type": "object",
        "required": ["task_id"],
        "properties": {
            "task_id": {"type": "string",
                        "description": "Task ID to cancel"},
        },
    },
    response={
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["write", "voice", "download"],
)

_register(
    name="voice.internet_status",
    description=(
        "Report the overall status of the download system — how many "
        "downloads are active, queued, and total files in the library."
    ),
    params={
        "type": "object",
        "properties": {},
    },
    response={
        "type": "object",
        "properties": {
            "active": {"type": "integer"},
            "queued": {"type": "integer"},
            "library": {"type": "integer"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["read", "voice", "download"],
)

_register(
    name="voice.internet_library",
    description=(
        "Browse the downloaded media library — search by filename, "
        "category (video, music, document), or see all files."
    ),
    params={
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "Optional search within library",
                      "default": ""},
            "category": {"type": "string",
                         "enum": ["", "video", "music", "document", "image", "ebook"],
                         "description": "Filter by category",
                         "default": ""},
        },
    },
    response={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "items": {"type": "array"},
            "tts_text": {"type": "string"},
        },
    },
    tags=["read", "voice", "library"],
)


# ═══════════════════════════════════════════════════════════════════════
# Plugin Run Functions
# ═══════════════════════════════════════════════════════════════════════

def _safe_name(s: str, max_len: int = 80) -> str:
    """Truncate and clean a string for TTS."""
    return s.strip()[:max_len].replace("_", " ")


def run_plugin(name: str, params: Dict[str, Any],
               ctx: Any = None) -> Dict[str, Any]:
    """Dispatch a Simple Internet voice command."""
    m = _get_manager()

    if name == "voice.internet_download":
        url = params.get("url", "").strip()
        if not url:
            return {
                "_ok": False,
                "tts_text": "I need a URL to download. What should I download?",
            }
        task = m.download(
            url,
            filename=params.get("filename", ""),
            priority=params.get("priority", 5),
            convert_to=params.get("convert_to", ""),
        )
        if task:
            return {
                "task_id": task.id,
                "filename": task.filename,
                "protocol": task.protocol,
                "status": task.status.value,
                "tts_text": f"Added {_safe_name(task.filename)} to the download queue.",
                "_ok": True,
            }
        return {
            "_ok": False,
            "tts_text": "Sorry, I couldn't add that download. Please check the URL.",
        }

    elif name == "voice.internet_search":
        query = params.get("query", "").strip()
        source = params.get("source", "web")
        limit = min(int(params.get("limit", 5)), 20)

        if not query:
            return {"_ok": False, "tts_text": "What should I search for?"}

        results = m.search(query, source=source, limit=limit)
        if not results:
            return {
                "results": [],
                "total": 0,
                "tts_text": f"I couldn't find any results for {_safe_name(query)} on {source}.",
            }

        # Format for TTS
        top = results[:3]
        lines = [f"Found {len(results)} results. Top hits: "]
        for i, r in enumerate(top, 1):
            title = _safe_name(r.title, 60)
            size = ""
            if r.size_bytes:
                mb = r.size_bytes / 1_048_576
                size = f", {mb:.0f} MB"
            seeds = f", {r.seeders} seeders" if r.seeders else ""
            lines.append(f"{i}. {title}{size}{seeds}")

        return {
            "results": [r.__dict__ for r in results],
            "total": len(results),
            "tts_text": ". ".join(lines),
            "_ok": True,
        }

    elif name == "voice.internet_queue":
        queue = m.get_queue()
        active = [t for t in queue if t.status == DownloadStatus.DOWNLOADING]
        queued = [t for t in queue if t.status == DownloadStatus.QUEUED]

        lines = []
        if active:
            for t in active[:3]:
                lines.append(f"{_safe_name(t.filename)}: {t.progress:.0f}%")
        else:
            lines.append("No active downloads")

        return {
            "active": len(active),
            "queued": len(queued),
            "items": [{"id": t.id, "filename": t.filename,
                       "status": t.status.value, "progress": t.progress}
                      for t in queue[:10]],
            "tts_text": f"{len(active)} active, {len(queued)} queued. " + ". ".join(lines),
            "_ok": True,
        }

    elif name == "voice.internet_cancel":
        task_id = params.get("task_id", "").strip()
        if not task_id:
            return {"_ok": False, "tts_text": "Which download should I cancel?"}

        from tank_os.internet.downloader import DownloadEngine
        eng = DownloadEngine()
        ok = eng.cancel_download(task_id)
        return {
            "ok": ok,
            "tts_text": "Cancelled the download." if ok else "Couldn't find that download.",
            "_ok": ok,
        }

    elif name == "voice.internet_status":
        stats = m.get_stats()
        active = stats.get("active_downloads", 0)
        queued = stats.get("queued", 0)
        lib_files = stats.get("library_files", 0)
        return {
            "active": active,
            "queued": queued,
            "library": lib_files,
            "tts_text": (
                f"Download system: {active} active, {queued} queued, "
                f"and {lib_files} files in the library."
            ),
            "_ok": True,
        }

    elif name == "voice.internet_library":
        query = params.get("query", "")
        category = params.get("category", "")
        items = m.get_library(category=category, query=query, limit=10)

        if not items:
            return {"count": 0, "items": [],
                    "tts_text": "Your library is empty. Start downloading to fill it up.",
                    "_ok": True}

        names = [_safe_name(i.get("filename", "?"), 40) for i in items[:5]]
        return {
            "count": len(items),
            "items": items[:10],
            "tts_text": f"Library has {len(items)} files. Recently: " + ", ".join(names),
            "_ok": True,
        }

    return {"_ok": False, "tts_text": f"Unknown voice command: {name}"}
