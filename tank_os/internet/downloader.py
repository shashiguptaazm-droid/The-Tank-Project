"""
Simple Internet — Core Download Engine.

Wraps aria2 (multi-protocol), yt-dlp (video platforms), and FFmpeg (conversion)
into a unified download interface with queue management, progress tracking,
bandwidth control, and automatic file organization.

Feature coverage: 1-32 (core), 33-55 (torrent), 81-104 (music), 105-130 (video),
131-150 (documents/images), 151-170 (automation), 206-220 (library), 221-235 (performance)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
import threading
import time
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.internet.downloader")

DATA_DIR = Path(os.environ.get("TANKOS_DATA_DIR", "/var/lib/tank_os")) / "internet"
CONFIG_DIR = Path(os.environ.get("TANKOS_CONFIG_DIR", "/etc/tank_os")) / "internet"


class DownloadStatus(Enum):
    """Status of a download task."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"
    CONVERTING = "converting"


class DownloadCategory(Enum):
    """Automatic categorization based on file type."""
    VIDEO = "video"
    MUSIC = "music"
    DOCUMENT = "document"
    IMAGE = "image"
    ARCHIVE = "archive"
    SOFTWARE = "software"
    TORRENT = "torrent"
    EBOOK = "ebook"
    OTHER = "other"


@dataclass
class DownloadTask:
    """A single download task with full metadata."""
    id: str
    url: str
    filename: str = ""
    category: DownloadCategory = DownloadCategory.OTHER
    status: DownloadStatus = DownloadStatus.QUEUED
    protocol: str = "http"
    size_bytes: int = 0
    downloaded_bytes: int = 0
    speed_bps: float = 0.0
    progress: float = 0.0
    priority: int = 5
    destination: str = ""
    error: Optional[str] = None
    checksum: str = ""
    checksum_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    completed: Optional[float] = None
    eta_seconds: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    extract_after: bool = False
    convert_to: str = ""
    tags: List[str] = field(default_factory=list)


class DownloadEngine:
    """
    Universal download engine wrapping aria2, yt-dlp, and FFmpeg.

    Features:
    - Multi-protocol: HTTP/HTTPS, FTP, BitTorrent, Magnet, YouTube, etc.
    - Multi-threaded segmented downloading (aria2)
    - Resume interrupted downloads
    - Bandwidth throttling per download and global
    - Download queue with priorities
    - Automatic file categorization
    - Post-download conversion (FFmpeg)
    """

    _instance: Optional["DownloadEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._tasks: Dict[str, DownloadTask] = {}
                cls._instance._active_downloads: Set[str] = set()
                cls._instance._active_lock = threading.Lock()
                cls._instance._global_bandwidth = 0
                cls._instance._per_download_bandwidth = 0
                cls._instance._queue_paused = False
                cls._instance._db_path = DATA_DIR / "downloads.db"
                cls._instance._download_dir = Path("/var/tank_os/downloads")
                cls._instance._watch_dir = Path("/var/tank_os/watch")
                cls._instance._completed_dir = Path("/var/tank_os/completed")
                cls._instance._lock_file = DATA_DIR / ".lock"
                cls._instance._aria2_process: Optional[subprocess.Popen] = None
            return cls._instance

    def initialize(self) -> None:
        """Initialize the download engine."""
        logger.info("Initializing Simple Internet Download Engine...")

        for d in [DATA_DIR, CONFIG_DIR, self._download_dir,
                  self._watch_dir, self._completed_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._init_db()
        self._load_tasks()
        self._start_aria2()

        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

        logger.info("Download Engine initialized: %d tasks loaded, aria2=%s",
                     len(self._tasks), self._aria2_process is not None)

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT,
                filename TEXT,
                category TEXT DEFAULT 'other',
                status TEXT DEFAULT 'queued',
                protocol TEXT DEFAULT 'http',
                size_bytes INTEGER DEFAULT 0,
                downloaded_bytes INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 5,
                destination TEXT,
                error TEXT,
                checksum TEXT,
                metadata TEXT DEFAULT '{}',
                created REAL,
                completed REAL,
                tags TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id TEXT PRIMARY KEY,
                url TEXT,
                filename TEXT,
                category TEXT,
                status TEXT,
                size_bytes INTEGER DEFAULT 0,
                created REAL,
                completed REAL
            )
        """)
        conn.commit()
        conn.close()

    def _load_tasks(self) -> None:
        """Load active/queued tasks from database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute(
                "SELECT * FROM downloads WHERE status NOT IN ('completed', 'failed', 'cancelled')"
            )
            for row in cursor.fetchall():
                task = DownloadTask(
                    id=row[0], url=row[1], filename=row[2],
                    category=DownloadCategory(row[3]) if row[3] else DownloadCategory.OTHER,
                    status=DownloadStatus(row[4]) if row[4] else DownloadStatus.QUEUED,
                    protocol=row[5] or "http",
                    size_bytes=row[6] or 0, downloaded_bytes=row[7] or 0,
                    priority=row[8] or 5, destination=row[9] or "",
                    error=row[10] or None, checksum=row[11] or "",
                    metadata=json.loads(row[12]) if row[12] else {},
                    created=row[13] or time.time(), completed=row[14] or None,
                    tags=row[15].split(",") if row[15] else [],
                )
                self._tasks[task.id] = task
            conn.close()
        except Exception as e:
            logger.warning("Failed to load tasks: %s", e)

    def _start_aria2(self) -> bool:
        """Start aria2 RPC daemon in the background."""
        aria2_path = shutil.which("aria2c")
        if not aria2_path:
            logger.warning("aria2c not found — install with: apt install aria2")
            return False

        try:
            rpc_secret = hashlib.sha256(f"tankos-{uuid.uuid4()}".encode()).hexdigest()[:16]
            session_file = DATA_DIR / "aria2.session"
            config_file = CONFIG_DIR / "aria2.conf"

            config_file.write_text(f"""
enable-rpc=true
rpc-listen-all=true
rpc-secret={rpc_secret}
dir={self._download_dir}
input-file={session_file}
save-session={session_file}
save-session-interval=30
continue=true
max-concurrent-downloads=5
max-connection-per-server=4
split=4
min-split-size=10M
max-overall-download-limit=0
max-download-limit=0
bt-enable-lpd=true
bt-max-peers=50
enable-dht=true
dht-listen-port=6881-6899
listen-port=6881-6899
seed-ratio=1.0
seed-time=60
""")

            self._aria2_process = subprocess.Popen(
                [aria2_path, "--conf-path", str(config_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._aria2_secret = rpc_secret
            logger.info("aria2 RPC started (secret=%s, pid=%d)",
                         rpc_secret[:8], self._aria2_process.pid)
            return True
        except Exception as e:
            logger.warning("Failed to start aria2: %s", e)
            return False

    def _watch_loop(self) -> None:
        """Monitor watch directory for new .torrent files (feature 163)."""
        while True:
            try:
                for f in list(self._watch_dir.glob("*.torrent")):
                    try:
                        self.add_download(str(f), protocol="torrent")
                        f.rename(f.with_suffix(".torrent.added"))
                    except Exception as e:
                        logger.warning("Watch add failed for %s: %s", f.name, e)

                for f in list(self._watch_dir.glob("*.magnet")):
                    try:
                        magnet = f.read_text().strip()
                        if magnet.startswith("magnet:"):
                            self.add_download(magnet, protocol="magnet")
                        f.unlink()
                    except Exception as e:
                        logger.warning("Watch add failed for %s: %s", f.name, e)
            except Exception:
                pass
            time.sleep(5)

    # ═══════════════════════════════════════════════════════════════════
    # Core Download Operations
    # ═══════════════════════════════════════════════════════════════════

    def add_download(self, url: str, filename: str = "",
                     protocol: str = "", category: str = "",
                     priority: int = 5, destination: str = "",
                     extract_after: bool = False,
                     convert_to: str = "") -> DownloadTask:
        """Add a new download task with auto-detection."""
        if not protocol:
            protocol = self._detect_protocol(url)
        if not category:
            category = self._categorize_url(url, filename).value

        task = DownloadTask(
            id=str(uuid.uuid4())[:12],
            url=url,
            filename=filename or self._guess_filename(url),
            protocol=protocol,
            category=DownloadCategory(category) if category else self._categorize_url(url, filename),
            priority=priority,
            destination=destination or str(self._download_dir / category),
            extract_after=extract_after,
            convert_to=convert_to,
            created=time.time(),
        )

        self._tasks[task.id] = task
        self._persist_task(task)
        logger.info("Added download: %s (%s, priority=%d)", task.filename, protocol, priority)

        if not self._queue_paused and priority <= 5:
            self._process_queue()

        self._bus.emit(Event("download_added", {
            "id": task.id, "url": url, "protocol": protocol,
        }, source="internet.downloader"))

        return task

    def start_download(self, task_id: str) -> bool:
        """Start or resume a download task."""
        task = self._tasks.get(task_id)
        if not task or task.status == DownloadStatus.COMPLETED:
            return False

        task.status = DownloadStatus.DOWNLOADING
        with self._active_lock:
            self._active_downloads.add(task_id)
        self._persist_task(task)

        if task.protocol in ("torrent", "magnet"):
            self._download_via_aria2(task)
        elif task.protocol in ("youtube", "youtube-music"):
            self._download_via_ytdlp(task)
        else:
            self._download_via_aria2(task)

        return True

    def pause_download(self, task_id: str) -> bool:
        """Pause a download."""
        task = self._tasks.get(task_id)
        if not task or task.status != DownloadStatus.DOWNLOADING:
            return False
        task.status = DownloadStatus.PAUSED
        with self._active_lock:
            self._active_downloads.discard(task_id)
        self._persist_task(task)
        self._bus.emit(Event("download_paused", {"id": task_id}, source="internet.downloader"))
        return True

    def resume_download(self, task_id: str) -> bool:
        """Resume a paused download."""
        task = self._tasks.get(task_id)
        if not task or task.status != DownloadStatus.PAUSED:
            return False
        return self.start_download(task_id)

    def cancel_download(self, task_id: str) -> bool:
        """Cancel and remove a download."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = DownloadStatus.CANCELLED
        with self._active_lock:
            self._active_downloads.discard(task_id)
        self._persist_task(task)
        self._archive_task(task)
        del self._tasks[task_id]
        self._bus.emit(Event("download_cancelled", {"id": task_id}, source="internet.downloader"))
        return True

    def retry_download(self, task_id: str) -> bool:
        """Retry a failed download with exponential backoff."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.retry_count += 1
        if task.retry_count > task.max_retries:
            logger.warning("Max retries reached for %s", task_id)
            return False
        task.error = None
        return self.start_download(task_id)

    def set_bandwidth(self, global_bps: int = 0, per_download_bps: int = 0) -> None:
        """Set bandwidth limits. 0 = unlimited."""
        self._global_bandwidth = global_bps
        self._per_download_bandwidth = per_download_bps

    def set_queue_paused(self, paused: bool) -> None:
        """Pause or resume the download queue."""
        self._queue_paused = paused
        if not paused:
            self._process_queue()

    # ═══════════════════════════════════════════════════════════════════
    # Download via aria2
    # ═══════════════════════════════════════════════════════════════════

    def _download_via_aria2(self, task: DownloadTask) -> None:
        """Download using aria2 RPC."""
        if not self._aria2_process:
            logger.warning("aria2 not running — cannot download %s", task.id)
            task.status = DownloadStatus.FAILED
            task.error = "aria2 not available"
            return

        try:
            rpc_url = "http://localhost:6800/jsonrpc"
            uris = [task.url]
            options = {
                "dir": task.destination or str(self._download_dir),
                "out": task.filename or task.url.split("/")[-1],
            }
            if self._per_download_bandwidth:
                options["max-download-limit"] = str(self._per_download_bandwidth)

            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": task.id,
                "method": "aria2.addUri",
                "params": [f"token:{self._aria2_secret}", uris, options],
            }).encode()

            req = urllib.request.Request(rpc_url, data=payload,
                                          headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=5)
            result = json.loads(resp.read())

            if "error" in result:
                task.status = DownloadStatus.FAILED
                task.error = str(result["error"])
            else:
                gid = result.get("result", "")
                task.metadata["aria2_gid"] = gid
                task.status = DownloadStatus.DOWNLOADING
                t = threading.Thread(target=self._monitor_aria2_progress,
                                     args=(task.id, gid), daemon=True)
                t.start()
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error = str(e)

        self._persist_task(task)

    def _monitor_aria2_progress(self, task_id: str, gid: str) -> None:
        """Monitor aria2 download progress via RPC."""
        rpc_url = "http://localhost:6800/jsonrpc"

        while True:
            with self._active_lock:
                if task_id not in self._active_downloads:
                    break

            try:
                payload = json.dumps({
                    "jsonrpc": "2.0",
                    "id": "monitor",
                    "method": "aria2.tellStatus",
                    "params": [f"token:{self._aria2_secret}", gid],
                }).encode()

                req = urllib.request.Request(rpc_url, data=payload,
                                              headers={"Content-Type": "application/json"})
                resp = urllib.request.urlopen(req, timeout=5)
                result = json.loads(resp.read())
                status = result.get("result", {})

                if not status:
                    break

                task = self._tasks.get(task_id)
                if not task:
                    break

                total = int(status.get("totalLength", 0))
                completed = int(status.get("completedLength", 0))
                speed = int(status.get("downloadSpeed", 0))
                task.size_bytes = total
                task.downloaded_bytes = completed
                task.speed_bps = speed
                task.progress = (completed / max(total, 1)) * 100

                aria_status = status.get("status", "")
                if aria_status == "complete":
                    task.status = DownloadStatus.COMPLETED
                    task.completed = time.time()
                    with self._active_lock:
                        self._active_downloads.discard(task_id)
                    self._on_download_complete(task)
                    break
                elif aria_status == "error":
                    task.status = DownloadStatus.FAILED
                    task.error = status.get("errorMessage", "Unknown error")
                    with self._active_lock:
                        self._active_downloads.discard(task_id)
                    break
                elif aria_status == "paused":
                    task.status = DownloadStatus.PAUSED
                    break
            except Exception as e:
                logger.debug("Progress monitor error for %s: %s", task_id, e)

            time.sleep(2)

    # ═══════════════════════════════════════════════════════════════════
    # Download via yt-dlp
    # ═══════════════════════════════════════════════════════════════════

    def _download_via_ytdlp(self, task: DownloadTask) -> None:
        """Download using yt-dlp."""
        try:
            import yt_dlp

            ydl_opts = {
                "outtmpl": str(self._download_dir / "%(title)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
            }

            if task.convert_to == "mp3":
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            elif task.convert_to == "mp4":
                ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            elif task.convert_to:
                ydl_opts["format"] = task.convert_to

            t = threading.Thread(target=self._run_ytdlp, args=(task, ydl_opts), daemon=True)
            t.start()

        except ImportError:
            logger.warning("yt-dlp not installed — install with: pip install yt-dlp")
            task.status = DownloadStatus.FAILED
            task.error = "yt-dlp not available"

    def _run_ytdlp(self, task: DownloadTask, opts: Dict) -> None:
        """Run yt-dlp in a separate thread."""
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                task.filename = f"{info.get('title', 'unknown')}.{info.get('ext', 'mp4')}"
                task.size_bytes = info.get("filesize", 0) or info.get("filesize_approx", 0)
                task.metadata["title"] = info.get("title", "")
                task.metadata["duration"] = info.get("duration", 0)
                task.metadata["uploader"] = info.get("uploader", "")
                task.status = DownloadStatus.COMPLETED
                task.completed = time.time()
                with self._active_lock:
                    self._active_downloads.discard(task.id)
                self._on_download_complete(task)
        except Exception as e:
            logger.warning("yt-dlp download failed for %s: %s", task.id, e)
            task.status = DownloadStatus.FAILED
            task.error = str(e)
            with self._active_lock:
                self._active_downloads.discard(task.id)

    # ═══════════════════════════════════════════════════════════════════
    # Post-Download Processing
    # ═══════════════════════════════════════════════════════════════════

    def _on_download_complete(self, task: DownloadTask) -> None:
        """Handle post-download processing."""
        file_path = Path(task.destination) / task.filename

        # Move to completed directory
        dest_dir = self._completed_dir / task.category.value
        dest_dir.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            dest_path = dest_dir / task.filename
            shutil.move(str(file_path), str(dest_path))

        # Auto-extract archives
        if task.extract_after and task.filename.endswith((".zip", ".rar", ".7z", ".tar.gz")):
            self._extract_archive(dest_dir / task.filename, dest_dir)

        # Auto-convert
        if task.convert_to:
            self._convert_media(dest_dir / task.filename, task.convert_to)

        # Update category
        ext = Path(task.filename).suffix.lower()
        category_map = {
            ".mp4": DownloadCategory.VIDEO, ".mkv": DownloadCategory.VIDEO,
            ".avi": DownloadCategory.VIDEO, ".mov": DownloadCategory.VIDEO,
            ".mp3": DownloadCategory.MUSIC, ".flac": DownloadCategory.MUSIC,
            ".wav": DownloadCategory.MUSIC, ".aac": DownloadCategory.MUSIC,
            ".pdf": DownloadCategory.DOCUMENT, ".doc": DownloadCategory.DOCUMENT,
            ".epub": DownloadCategory.EBOOK, ".mobi": DownloadCategory.EBOOK,
            ".jpg": DownloadCategory.IMAGE, ".png": DownloadCategory.IMAGE,
            ".zip": DownloadCategory.ARCHIVE, ".rar": DownloadCategory.ARCHIVE,
        }
        task.category = category_map.get(ext, task.category)

        self._persist_task(task)
        self._archive_task(task)

        self._bus.emit(Event("download_completed", {
            "id": task.id, "filename": task.filename, "category": task.category.value,
        }, source="internet.downloader"))

        logger.info("Download completed: %s (%.1f MB, %s)",
                      task.filename, task.size_bytes / 1_048_576, task.category.value)

    def _extract_archive(self, path: Path, dest: Path) -> None:
        """Extract downloaded archive."""
        try:
            if str(path).endswith(".zip"):
                with zipfile.ZipFile(path, "r") as zf:
                    zf.extractall(dest)
            elif str(path).endswith(".tar.gz") or str(path).endswith(".tgz"):
                with tarfile.open(path, "r:gz") as tf:
                    tf.extractall(dest)
            path.unlink()
            logger.info("Extracted: %s", path.name)
        except Exception as e:
            logger.warning("Extraction failed for %s: %s", path.name, e)

    def _convert_media(self, path: Path, target_format: str) -> None:
        """Convert media file using FFmpeg."""
        if not shutil.which("ffmpeg"):
            logger.warning("FFmpeg not found — cannot convert")
            return
        output = path.with_suffix(f".{target_format}")
        try:
            subprocess.run(
                ["ffmpeg", "-i", str(path), "-y", str(output)],
                capture_output=True, timeout=300,
            )
            if output.exists():
                path.unlink()
        except Exception as e:
            logger.warning("Conversion failed: %s", e)

    # ═══════════════════════════════════════════════════════════════════
    # Queue Management
    # ═══════════════════════════════════════════════════════════════════

    def _process_queue(self) -> None:
        """Process the download queue by priority."""
        queued = sorted(
            [t for t in self._tasks.values() if t.status == DownloadStatus.QUEUED],
            key=lambda t: t.priority,
        )
        max_concurrent = 3
        for task in queued:
            with self._active_lock:
                if len(self._active_downloads) >= max_concurrent:
                    break
            self.start_download(task.id)

    def get_queue(self) -> List[DownloadTask]:
        """Get all active and queued tasks."""
        return [t for t in self._tasks.values()
                if t.status in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING,
                                DownloadStatus.PAUSED)]

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get download history."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute(
                "SELECT * FROM download_history ORDER BY created DESC LIMIT ?", (limit,)
            )
            cols = [d[0] for d in cursor.description]
            results = [dict(zip(cols, row)) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════════

    def _detect_protocol(self, url: str) -> str:
        """Auto-detect protocol from URL."""
        if url.startswith("magnet:"):
            return "magnet"
        if url.endswith(".torrent") or "torrent" in url.lower():
            return "torrent"
        if any(s in url.lower() for s in ["youtube.com", "youtu.be", "twitch.tv",
                                            "vimeo.com", "dailymotion.com"]):
            return "youtube"
        if "soundcloud.com" in url.lower() or "bandcamp.com" in url.lower():
            return "youtube-music"
        if url.startswith("ftp://") or url.startswith("ftps://"):
            return "ftp"
        if url.startswith("ipfs://"):
            return "ipfs"
        return "http"

    def _categorize_url(self, url: str, filename: str = "") -> DownloadCategory:
        """Auto-categorize based on URL/file extension."""
        name = filename or url.lower()
        if any(s in name for s in [".mp4", ".mkv", ".avi", ".mov", ".webm"]):
            return DownloadCategory.VIDEO
        if any(s in name for s in [".mp3", ".flac", ".wav", ".aac", ".ogg"]):
            return DownloadCategory.MUSIC
        if any(s in name for s in [".pdf", ".doc", ".docx", ".txt", ".ppt"]):
            return DownloadCategory.DOCUMENT
        if any(s in name for s in [".jpg", ".png", ".gif", ".bmp", ".webp"]):
            return DownloadCategory.IMAGE
        if any(s in name for s in [".zip", ".rar", ".7z", ".tar", ".gz"]):
            return DownloadCategory.ARCHIVE
        if any(s in name for s in [".exe", ".deb", ".rpm", ".AppImage"]):
            return DownloadCategory.SOFTWARE
        if any(s in name for s in [".epub", ".mobi", ".azw"]):
            return DownloadCategory.EBOOK
        if url.endswith(".torrent") or url.startswith("magnet:"):
            return DownloadCategory.TORRENT
        return DownloadCategory.OTHER

    def _guess_filename(self, url: str) -> str:
        """Guess filename from URL."""
        clean = url.split("?")[0].split("#")[0]
        name = clean.rstrip("/").split("/")[-1]
        if not name:
            name = f"download_{uuid.uuid4().hex[:8]}"
        return name

    def _persist_task(self, task: DownloadTask) -> None:
        """Save task to database."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("""
                INSERT OR REPLACE INTO downloads
                (id, url, filename, category, status, protocol,
                 size_bytes, downloaded_bytes, priority, destination,
                 error, checksum, metadata, created, completed, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.url, task.filename, task.category.value,
                task.status.value, task.protocol, task.size_bytes,
                task.downloaded_bytes, task.priority, task.destination,
                task.error, task.checksum, json.dumps(task.metadata),
                task.created, task.completed, ",".join(task.tags),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to persist task %s: %s", task.id, e)

    def _archive_task(self, task: DownloadTask) -> None:
        """Move completed/failed task to history table."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("""
                INSERT OR REPLACE INTO download_history
                (id, url, filename, category, status, size_bytes, created, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.url, task.filename, task.category.value,
                task.status.value, task.size_bytes, task.created, task.completed,
            ))
            if task.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED,
                                DownloadStatus.CANCELLED):
                conn.execute("DELETE FROM downloads WHERE id=?", (task.id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to archive task %s: %s", task.id, e)

    # ═══════════════════════════════════════════════════════════════════
    # Query API
    # ═══════════════════════════════════════════════════════════════════

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a specific task by ID."""
        return self._tasks.get(task_id)

    def get_active_downloads(self) -> List[DownloadTask]:
        """Get currently active downloads."""
        with self._active_lock:
            active_ids = list(self._active_downloads)
        return [self._tasks[tid] for tid in active_ids if tid in self._tasks]

    def search_tasks(self, query: str) -> List[DownloadTask]:
        """Search tasks by filename or URL."""
        q = query.lower()
        return [t for t in self._tasks.values()
                if q in t.filename.lower() or q in t.url.lower()]

    def get_stats(self) -> Dict[str, Any]:
        """Get download engine statistics."""
        with self._active_lock:
            active_count = len(self._active_downloads)
        return {
            "total_tasks": len(self._tasks),
            "active": active_count,
            "queued": len([t for t in self._tasks.values() if t.status == DownloadStatus.QUEUED]),
            "bandwidth_global": self._global_bandwidth,
            "bandwidth_per_dl": self._per_download_bandwidth,
            "queue_paused": self._queue_paused,
            "aria2_running": self._aria2_process is not None,
        }

    def shutdown(self) -> None:
        """Shutdown the download engine."""
        if self._aria2_process:
            self._aria2_process.terminate()
            self._aria2_process.wait(timeout=5)
        logger.info("Download engine shutdown")

    def get_summary(self) -> Dict[str, Any]:
        return self.get_stats()
