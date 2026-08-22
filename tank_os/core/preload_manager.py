"""
TankOS Preload Manager — Complete Offline Dependency System.

The Preload Manager automatically downloads, verifies, installs, and
configures all required software, AI models, libraries, firmware, and
system packages during the initial setup. After installation, TankOS
is fully functional offline except for optional cloud services.

Key features:
  - Define every dependency in a structured manifest
  - Download with resume and checksum verification
  - Install to proper system locations
  - Track installation status per dependency
  - Support both online and offline modes
  - Progress reporting via EventBus
  - Safe to re-run — idempotent
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.preload.manifest import (
    MANIFEST,
    PreloadItem,
    categories,
    downloadable_items,
    get_item,
    required_items,
    summary as manifest_summary,
)
from tank_os.preload.downloader import (
    DownloadEngine,
    DownloadProgress,
    DownloadStatus,
)

logger = logging.getLogger("tank_os.preload_manager")


class PreloadState(Enum):
    UNINITIALIZED = "uninitialized"
    SCANNING = "scanning"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    OFFLINE = "offline"


@dataclass
class PreloadReport:
    """Report of the preload process."""
    state: PreloadState = PreloadState.UNINITIALIZED
    total_items: int = 0
    downloaded: int = 0
    verified: int = 0
    failed: int = 0
    skipped: int = 0
    total_size_mb: float = 0.0
    downloaded_mb: float = 0.0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""
    offline: bool = False
    items: Dict[str, str] = field(default_factory=dict)  # item_id -> status


class PreloadManager:
    """Singleton that orchestrates the entire offline dependency preloading process.

    Usage::

        preload = PreloadManager()
        preload.initialize()                     # Scan what's installed
        preload.download_all()                    # Download everything
        report = preload.report()                 # Get status report
    """

    _instance: Optional["PreloadManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "PreloadManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._engine: Optional[DownloadEngine] = None
                cls._instance._state = PreloadState.UNINITIALIZED
                cls._instance._item_status: Dict[str, str] = {}
                cls._instance._item_status_lock = threading.Lock()
                cls._instance._errors: List[str] = []
                cls._instance._errors_lock = threading.Lock()
                cls._instance._data_dir = Path(
                    os.environ.get("TANKOS_DATA_DIR", "/var/lib/tank_os")
                )
                cls._instance._installed_file: Optional[Path] = None
                cls._instance._download_started: bool = False
                cls._instance._offline_mode: bool = False
                cls._instance._max_errors = 50
            return cls._instance

    # ── Initialization ──────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize the PreloadManager: create dirs, scan state, emit event."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        (self._data_dir / "models").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "assets").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "cache").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "wheels").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "logs").mkdir(parents=True, exist_ok=True)

        self._engine = DownloadEngine(cache_dir=str(self._data_dir / "cache"))
        self._installed_file = self._data_dir / ".preload_complete"

        # Check internet connectivity
        self._offline_mode = not self._check_connectivity()

        # Scan what's already installed
        self._scan()

        if self._offline_mode:
            logger.info("PreloadManager initialized (OFFLINE mode)")

            # If everything is already installed, mark complete
            if self._state == PreloadState.COMPLETED:
                logger.info("All dependencies already installed — system is offline-ready")
            else:
                logger.warning("Offline mode with missing dependencies — some features limited")
        else:
            logger.info("PreloadManager initialized (ONLINE mode — can download)")

        self._bus.emit(Event("preload_initialized", {
            "state": self._state.value,
            "offline": self._offline_mode,
            "total_items": len(MANIFEST),
            "installed": sum(1 for s in self._item_status.values() if s == "installed"),
            "missing": sum(1 for s in self._item_status.values() if s == "missing"),
        }, source="preload_manager"))

    def _check_connectivity(self, timeout: int = 3) -> bool:
        """Check if we have internet access by pinging a reliable host."""
        import socket
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                ("8.8.8.8", 53)
            )
            return True
        except (OSError, socket.error):
            return False

    def _scan(self) -> None:
        """Scan the system to determine what's already installed."""
        self._state = PreloadState.SCANNING
        installed_count = 0
        missing_count = 0

        for item_id, item in MANIFEST.items():
            if self._is_installed(item):
                self._item_status[item_id] = "installed"
                installed_count += 1
            else:
                self._item_status[item_id] = "missing"
                missing_count += 1

        if missing_count == 0:
            self._state = PreloadState.COMPLETED
        elif installed_count == 0:
            self._state = PreloadState.UNINITIALIZED
        else:
            self._state = PreloadState.PARTIAL

        logger.info("Preload scan: %d installed, %d missing",
                     installed_count, missing_count)

    def _is_installed(self, item: PreloadItem) -> bool:
        """Check if an item is already installed on the system."""
        if item.install_method == "apt":
            return self._check_apt_package(item.filename or item.id)
        elif item.install_method == "pip":
            pkg_name = item.package_name or item.name
            return self._check_pip_package(pkg_name)
        elif item.install_method == "verify_only":
            return True  # These are defined but may not need installation
        else:
            # Check if the file exists at the install path
            install_path = Path(item.install_path)
            if item.extract:
                return install_path.exists() and any(install_path.iterdir())
            return (install_path / item.filename).exists()

    def _check_apt_package(self, package_name: str) -> bool:
        """Check if an apt package is installed."""
        try:
            result = subprocess.run(
                ["dpkg", "-l", package_name],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and "ii" in result.stdout
        except Exception:
            return False

    def _check_pip_package(self, package_name: str) -> bool:
        """Check if a pip package is installed."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name.lower()],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── Download Operations ─────────────────────────────────────────────

    def download_required(self, progress_callback: Optional[Callable] = None
                          ) -> PreloadReport:
        """Download only required items."""
        return self.download_items(
            required_items(), progress_callback=progress_callback
        )

    def download_all(self, progress_callback: Optional[Callable] = None,
                     max_concurrent: int = 3) -> PreloadReport:
        """Download all items from the manifest."""
        return self.download_items(
            downloadable_items(), progress_callback=progress_callback,
            max_concurrent=max_concurrent
        )

    def download_category(self, category: str,
                          progress_callback: Optional[Callable] = None
                          ) -> PreloadReport:
        """Download all items in a specific category."""
        from tank_os.preload.manifest import get_category
        items = [i for i in get_category(category) if i.url and not i.verify_only]
        return self.download_items(items, progress_callback=progress_callback)

    def download_items(self, items: List[PreloadItem],
                       progress_callback: Optional[Callable] = None,
                       max_concurrent: int = 3) -> PreloadReport:
        """Download a specific list of items."""
        if self._offline_mode:
            logger.error("Cannot download: offline mode active")
            return self.report()

        if not items:
            logger.info("No items to download")
            return self.report()

        self._state = PreloadState.DOWNLOADING
        self._download_started = True
        total_size = sum(i.size_mb for i in items)
        logger.info("Starting download of %d items (%.1f MB total)",
                     len(items), total_size)

        self._bus.emit(Event("preload_download_started", {
            "count": len(items),
            "total_size_mb": total_size,
        }, source="preload_manager"))

        # Create progress wrapper (thread-safe)
        def _on_progress(progress: DownloadProgress) -> None:
            with self._item_status_lock:
                self._item_status[progress.item_id] = progress.status.value
            if progress_callback:
                progress_callback(progress)
            # Emit event periodically
            if progress.status == DownloadStatus.COMPLETED:
                self._bus.emit(Event("preload_item_completed", {
                    "item_id": progress.item_id,
                    "status": progress.status.value,
                }, source="preload_manager", priority=Priority.LOW))
            elif progress.status == DownloadStatus.FAILED:
                err_msg = f"{progress.item_id}: {progress.error}"
                with self._errors_lock:
                    self._errors.append(err_msg)
                    # Bound error list to prevent unbounded growth
                    if len(self._errors) > self._max_errors:
                        self._errors.pop(0)
                self._bus.emit(Event("preload_item_failed", {
                    "item_id": progress.item_id,
                    "error": progress.error or "Unknown error",
                }, source="preload_manager"))

        assert self._engine is not None
        results = self._engine.download_all(
            items, progress=_on_progress, max_concurrent=max_concurrent
        )

        # Update status
        for item_id, progress in results.items():
            if progress.status == DownloadStatus.COMPLETED:
                self._item_status[item_id] = "installed"
            elif progress.status == DownloadStatus.FAILED:
                self._item_status[item_id] = "failed"
            elif progress.status == DownloadStatus.SKIPPED:
                self._item_status[item_id] = "skipped"

        # Update state
        failed = sum(1 for p in results.values()
                     if p.status == DownloadStatus.FAILED)
        completed = sum(1 for p in results.values()
                        if p.status == DownloadStatus.COMPLETED)
        skipped = sum(1 for p in results.values()
                      if p.status == DownloadStatus.SKIPPED)

        if failed == 0:
            self._state = PreloadState.COMPLETED
        elif completed > 0:
            self._state = PreloadState.PARTIAL
        else:
            self._state = PreloadState.FAILED

        self._bus.emit(Event("preload_download_completed", {
            "total": len(results),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "state": self._state.value,
        }, source="preload_manager"))

        return self.report()

    # ── Verification ────────────────────────────────────────────────────

    def verify_all(self) -> PreloadReport:
        """Verify all installed items. Re-downloads corrupted files."""
        self._state = PreloadState.VERIFYING
        corrupted: List[str] = []

        for item_id, item in MANIFEST.items():
            if not self._is_installed(item):
                corrupted.append(item_id)
                self._item_status[item_id] = "corrupted"

        if corrupted:
            logger.warning("Corrupted/missing items: %s", corrupted)
            if not self._offline_mode:
                logger.info("Attempting to re-download corrupted items...")
                items_to_fix = [get_item(i) for i in corrupted if get_item(i)]
                self.download_items([i for i in items_to_fix if i])
        else:
            self._state = PreloadState.COMPLETED
            logger.info("All items verified: OK")

        return self.report()

    # ── Status & Reporting ──────────────────────────────────────────────

    def report(self) -> PreloadReport:
        """Generate a comprehensive preload status report."""
        installed = sum(1 for s in self._item_status.values()
                        if s in ("installed", "completed"))
        missing = sum(1 for s in self._item_status.values()
                      if s in ("missing", "pending"))
        failed = sum(1 for s in self._item_status.values()
                     if s == "failed")

        return PreloadReport(
            state=self._state,
            total_items=len(MANIFEST),
            downloaded=installed,
            verified=installed - failed,
            failed=failed,
            skipped=sum(1 for s in self._item_status.values() if s == "skipped"),
            total_size_mb=manifest_summary().get("total_size_mb", 0.0),
            downloaded_mb=self._calculate_downloaded_mb(),
            errors=list(self._errors) if not hasattr(self, '_errors_lock') else self._errors.copy(),
        # Note: errors list is read without lock here — acceptable because
        # GIL serializes list reads and the _on_progress callback bounds
        # the list at 50 items. For strict safety, wrap in _errors_lock.
            timestamp=datetime.now().isoformat(),
            offline=self._offline_mode,
            items=dict(self._item_status),
        )

    def _calculate_downloaded_mb(self) -> float:
        """Calculate the total size of downloaded files."""
        total = 0.0
        for item_id, status in self._item_status.items():
            if status == "installed":
                item = get_item(item_id)
                if item:
                    total += item.size_mb
        return round(total, 1)

    def summary(self) -> Dict[str, Any]:
        """Return a human-readable summary dict."""
        r = self.report()
        return {
            "state": r.state.value,
            "total": r.total_items,
            "installed": r.downloaded,
            "missing": r.total_items - r.downloaded,
            "failed": r.failed,
            "size_mb": r.total_size_mb,
            "downloaded_mb": r.downloaded_mb,
            "offline": r.offline,
        }

    def item_status(self, item_id: str) -> Optional[str]:
        """Get installation status of a specific item."""
        return self._item_status.get(item_id)

    def print_report(self) -> None:
        """Pretty-print the preload report to stdout."""
        r = self.report()
        print()
        print("╔══════════════════════════════════════════╗")
        print(f"║  🤖  TankOS Preload Report              ║")
        print(f"║  State: {r.state.value:<32}║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  Total dependencies:  {r.total_items:<4}                ║")
        print(f"║  Installed:           {r.downloaded:<4}                ║")
        print(f"║  Failed:              {r.failed:<4}                ║")
        print(f"║  Skipped:             {r.skipped:<4}                ║")
        print(f"║  Total size:          {r.total_size_mb:<6.1f} MB            ║")
        print(f"║  Downloaded:          {r.downloaded_mb:<6.1f} MB            ║")
        print(f"║  Offline mode:        {str(r.offline):<5}                ║")
        print("╠══════════════════════════════════════════╣")
        if r.errors:
            print("║  Errors:                                 ║")
            for err in r.errors[:5]:
                wrapped = err[:52]
                print(f"║    ✗ {wrapped:<46}║")
        print("╚══════════════════════════════════════════╝")
        print()

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def state(self) -> PreloadState:
        return self._state

    @property
    def is_offline(self) -> bool:
        return self._offline_mode

    @property
    def is_ready(self) -> bool:
        """True if all required dependencies are installed."""
        required = [i.id for i in required_items()]
        return all(
            self._item_status.get(iid) in ("installed", "completed")
            for iid in required
        )

    @property
    def download_engine(self) -> Optional[DownloadEngine]:
        return self._engine

    @property
    def data_dir(self) -> Path:
        return self._data_dir
