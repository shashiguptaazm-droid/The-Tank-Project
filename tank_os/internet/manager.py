"""
Simple Internet — Unified Download Manager.

Ties together the download engine, search engine, library management,
and voice plugin integration into one cohesive TankOS module.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus
from tank_os.internet.downloader import DownloadEngine, DownloadTask, DownloadStatus, DownloadCategory
from tank_os.internet.search import SearchEngine, SearchQuery, SearchResult, SearchSource

logger = logging.getLogger("tank_os.internet.manager")
DATA_DIR = Path(os.environ.get("TANKOS_DATA_DIR", "/var/lib/tank_os")) / "internet"


class InternetManager:
    """Unified manager for Simple Internet — the TankOS universal downloader."""

    _instance: Optional["InternetManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._downloader: Optional[DownloadEngine] = None
                cls._instance._searcher: Optional[SearchEngine] = None
                cls._instance._library_db = DATA_DIR / "library.db"
                cls._instance._rss_sources: List[Dict[str, Any]] = []
                cls._instance._automation_rules: List[Dict[str, Any]] = []
                cls._instance._watch_folders: List[Path] = []
                cls._instance._initialized = False
            return cls._instance

    def initialize(self) -> None:
        """Initialize the Simple Internet manager."""
        logger.info("Initializing Simple Internet Manager...")
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self._downloader = DownloadEngine()
        self._downloader.initialize()
        self._searcher = SearchEngine()
        self._init_library_db()

        # Scan existing files into library on startup
        self.scan_library()

        self._bus.on("internet_download_request", self._on_download_request)
        self._bus.on("internet_search_request", self._on_search_request)
        self._bus.on("internet_rss_refresh", self._on_rss_refresh)

        self._initialized = True
        logger.info("Simple Internet Manager initialized")

    def _init_library_db(self) -> None:
        """Initialize the media/library database."""
        conn = sqlite3.connect(str(self._library_db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS library (
                id TEXT PRIMARY KEY, filename TEXT, path TEXT,
                category TEXT DEFAULT 'other', size_bytes INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0, artist TEXT DEFAULT '',
                album TEXT DEFAULT '', title TEXT DEFAULT '', year INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 0, tags TEXT DEFAULT '',
                play_count INTEGER DEFAULT 0, last_played REAL DEFAULT 0,
                created REAL, checksum TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rss_sources (
                url TEXT PRIMARY KEY, name TEXT, category TEXT DEFAULT '',
                filters TEXT DEFAULT '{}', last_checked REAL DEFAULT 0,
                enabled INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id TEXT PRIMARY KEY, name TEXT,
                condition_type TEXT, condition_value TEXT,
                action_type TEXT, action_value TEXT,
                enabled INTEGER DEFAULT 1, created REAL
            )
        """)
        conn.commit()
        conn.close()

    def download(self, url: str, **kwargs) -> Optional[DownloadTask]:
        """Add a download task."""
        if not self._downloader:
            return None
        return self._downloader.add_download(url, **kwargs)

    def search_and_download(self, query: str, source: str = "torrent") -> Optional[DownloadTask]:
        """Search and directly download the best result."""
        sq = SearchQuery(query=query, source=SearchSource(source), limit=5)
        results = self._searcher.search(sq) if self._searcher else []
        if not results:
            return None
        best = results[0]
        dl_url = best.magnet or best.url
        if dl_url:
            return self.download(dl_url, filename=best.title[:50])
        if "youtube.com" in best.url or "youtu.be" in best.url:
            return self.download(best.url, protocol="youtube")
        return None

    def get_active(self) -> List[DownloadTask]:
        """Get active downloads."""
        return self._downloader.get_active_downloads() if self._downloader else []

    def get_queue(self) -> List[DownloadTask]:
        """Get download queue."""
        return self._downloader.get_queue() if self._downloader else []

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get download history."""
        return self._downloader.get_history(limit) if self._downloader else []

    def search(self, query: str, source: str = "torrent", limit: int = 20) -> List[SearchResult]:
        """Execute a search."""
        if not self._searcher:
            return []
        return self._searcher.search(SearchQuery(query=query, source=SearchSource(source), limit=limit))

    def search_all(self, query: str, limit: int = 5) -> Dict[str, List[SearchResult]]:
        """Search all sources simultaneously."""
        if not self._searcher:
            return {}
        return self._searcher.search_all(query, limit_per_source=limit)

    def get_search_history(self) -> List[Dict[str, Any]]:
        """Get search history."""
        return self._searcher.get_history() if self._searcher else []

    def get_bookmarks(self) -> List[SearchResult]:
        """Get bookmarked results."""
        return self._searcher.get_bookmarks() if self._searcher else []

    def scan_library(self) -> int:
        """Scan download directory and add files to library."""
        scan_dir = Path("/var/tank_os/completed")
        if not scan_dir.exists():
            return 0

        conn = sqlite3.connect(str(self._library_db))
        count = 0
        for f in scan_dir.rglob("*"):
            if not f.is_file() or f.suffix in (".part", ".added"):
                continue
            existing = conn.execute("SELECT id FROM library WHERE path=?", (str(f),)).fetchone()
            if existing:
                continue
            ext = f.suffix.lower()
            cat_map = {".mp4": "video", ".mkv": "video", ".avi": "video",
                        ".mp3": "music", ".flac": "music", ".wav": "music",
                        ".pdf": "document", ".epub": "ebook", ".jpg": "image"}
            category = cat_map.get(ext, "other")
            conn.execute(
                "INSERT INTO library (id, filename, path, category, size_bytes, created) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4())[:12], f.name, str(f), category, f.stat().st_size, time.time()),
            )
            count += 1
        conn.commit()
        conn.close()
        logger.info("Library scan: %d new files", count)
        return count

    def get_library(self, category: str = "", query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Query the media library."""
        conn = sqlite3.connect(str(self._library_db))
        sql = "SELECT * FROM library WHERE 1=1"
        params: List[Any] = []
        if category:
            sql += " AND category=?"
            params.append(category)
        if query:
            sql += " AND (filename LIKE ? OR artist LIKE ? OR title LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        sql += " ORDER BY created DESC LIMIT ?"
        params.append(limit)
        cursor = conn.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        results = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def update_library_item(self, item_id: str, **kwargs) -> bool:
        """Update metadata for a library item."""
        conn = sqlite3.connect(str(self._library_db))
        allowed = {"rating", "tags", "artist", "album", "title", "year"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            conn.close()
            return False
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [item_id]
        conn.execute(f"UPDATE library SET {set_clause} WHERE id=?", values)
        conn.commit()
        conn.close()
        return True

    def add_rss_source(self, url: str, name: str = "", filters: Optional[Dict] = None) -> bool:
        """Add an RSS feed for automated downloads."""
        conn = sqlite3.connect(str(self._library_db))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO rss_sources (url, name, filters) VALUES (?, ?, ?)",
                (url, name or url, json.dumps(filters or {})),
            )
            conn.commit()
            self._rss_sources.append({"url": url, "name": name, "filters": filters or {}})
            return True
        except Exception as e:
            logger.warning("Failed to add RSS source: %s", e)
            return False
        finally:
            conn.close()

    def refresh_rss(self) -> int:
        """Check all RSS feeds for new items."""
        conn = sqlite3.connect(str(self._library_db))
        sources = conn.execute("SELECT url, name, filters FROM rss_sources WHERE enabled=1").fetchall()
        conn.close()

        new_items = 0
        for url, name, _ in sources:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "TankOS/1.0 RSS Reader"})
                resp = urllib.request.urlopen(req, timeout=15)
                root = ET.fromstring(resp.read().decode("utf-8", errors="replace"))
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    if title and link:
                        self.download(link, filename=title[:100])
                        new_items += 1

                conn2 = sqlite3.connect(str(self._library_db))
                conn2.execute("UPDATE rss_sources SET last_checked=? WHERE url=?", (time.time(), url))
                conn2.commit()
                conn2.close()
            except Exception as e:
                logger.warning("RSS refresh failed for %s: %s", name or url, e)

        logger.info("RSS refresh: %d new items", new_items)
        return new_items

    def _on_download_request(self, event: Event) -> None:
        url = event.data.get("url", "")
        if url:
            self.download(url, **event.data.get("options", {}))

    def _on_search_request(self, event: Event) -> None:
        query = event.data.get("query", "")
        source = event.data.get("source", "torrent")
        if query:
            self.search(query, source)

    def _on_rss_refresh(self, event: Event) -> None:
        self.refresh_rss()

    def get_stats(self) -> Dict[str, Any]:
        dl_stats = self._downloader.get_stats() if self._downloader else {}
        lib_count = 0
        try:
            conn = sqlite3.connect(str(self._library_db))
            lib_count = conn.execute("SELECT COUNT(*) FROM library").fetchone()[0]
            conn.close()
        except Exception:
            pass
        return {
            "active_downloads": dl_stats.get("active", 0),
            "queued": dl_stats.get("queued", 0),
            "library_files": lib_count,
            "rss_sources": len(self._rss_sources),
            "automation_rules": len(self._automation_rules),
            "initialized": self._initialized,
        }

    def get_summary(self) -> Dict[str, Any]:
        return self.get_stats()
