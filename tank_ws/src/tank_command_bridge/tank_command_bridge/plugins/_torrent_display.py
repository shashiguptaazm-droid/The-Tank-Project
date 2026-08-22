"""Shared store for the torrent search / display / ask-confirm flow.

Three sub-stores:

* ``RecentResultsStore``  — last N search results keyed by magnet hash.
* ``ActiveDownloadsStore``— GIDs of currently-downloading torrents.
* ``PickStore``           — pending user pick (LLM proposes a row, user says yes/no).

The same objects are reused across ``torrent_search``, the new
``torrent_display`` plugin, and the dashboard route at
``/api/torrent/{results,pick,cancel}``.

This file is pure-Python; no ROS dependency. It can be replaced in tests
with stubs that record the calls.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


DEFAULT_RESULTS_KEEP = 20


@dataclass
class TorrentResult:
    """Same shape as the dict ``voice.torrent_search`` returns, but as a
    real dataclass so the display plugin can re-serialise it."""
    title: str
    source: str
    size_bytes: int
    seeders: int
    magnet: str
    infohash: str = ""
    info_uri: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TorrentResult":
        return cls(
            title=str(d.get("title", ""))[:200],
            source=str(d.get("source", ""))[:32],
            size_bytes=int(d.get("size_bytes", 0)),
            seeders=int(d.get("seeders", 0)),
            magnet=str(d.get("magnet") or d.get("access_uri", "")),
            infohash=str(d.get("infohash", ""))[:64],
            info_uri=str(d.get("info_uri", ""))[:300],
        )


class RecentResultsStore:
    """Last N torrent results. Most recent first. Thread-safe."""

    def __init__(self, keep: int = DEFAULT_RESULTS_KEEP) -> None:
        self._keep = max(1, int(keep))
        self._lock = threading.Lock()
        self._items: List[TorrentResult] = []
        self._last_query: str = ""
        self._ts: float = 0.0

    def push(self, results: List[Dict[str, Any]],
             query: str = "") -> None:
        with self._lock:
            if query:
                self._last_query = query
            self._ts = time.time()
            self._items.clear()
            for r in results:
                try:
                    self._items.append(TorrentResult.from_dict(r))
                except Exception:
                    pass
            # dedupe by infohash (or magnet fallback)
            seen = set()
            deduped: List[TorrentResult] = []
            for it in self._items:
                k = it.infohash or it.magnet
                if k in seen:
                    continue
                seen.add(k)
                deduped.append(it)
                if len(deduped) >= self._keep:
                    break
            self._items = deduped

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [it.to_dict() for it in self._items]

    def at(self, index: int) -> Optional[TorrentResult]:
        with self._lock:
            if 0 <= index < len(self._items):
                return self._items[index]
            return None

    def last_query(self) -> str:
        with self._lock:
            return self._last_query

    def age_s(self) -> float:
        with self._lock:
            return time.time() - self._ts if self._ts else 0.0

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._last_query = ""
            self._ts = 0.0


class ActiveDownloadsStore:
    """Tracks GIDs of currently running aria2 downloads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._gids: Dict[str, Dict[str, Any]] = {}

    def mark_active(self, gid: str, meta: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._gids[gid] = {
                "gid": gid,
                "started_at": time.time(),
                **(meta or {}),
            }

    def mark_done(self, gid: str) -> None:
        with self._lock:
            self._gids.pop(gid, None)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._gids.values())

    def contains(self, gid: str) -> bool:
        with self._lock:
            return gid in self._gids


# Module-level singletons — voice plugins and the dashboard route share them.
RECENT_RESULTS = RecentResultsStore()
ACTIVE_DOWNLOADS = ActiveDownloadsStore()


__all__ = [
    "TorrentResult", "RecentResultsStore", "ActiveDownloadsStore",
    "RECENT_RESULTS", "ACTIVE_DOWNLOADS",
    "DEFAULT_RESULTS_KEEP",
]
