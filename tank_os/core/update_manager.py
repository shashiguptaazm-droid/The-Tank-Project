"""TankOS Update Manager — periodic check, apply, rollback.

A daemon thread polls **UpdateProvider** instances on a configurable
interval. Each provider represents one update source (apt, pypi,
git, scripts/ota.py). When providers report available updates, the
manager emits an :class:`update_available` event with their summaries.

Applying an update shells out to a backend hook (e.g.
``scripts/ota.py``) and records a snapshot of pre-apply state for
optional rollback. The daemon lives on its own thread and can be
stopped cleanly via :meth:`stop`.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.update_manager")


class UpdateChannel(Enum):
    STABLE = "stable"
    BETA = "beta"
    NIGHTLY = "nightly"


@dataclass
class UpdateInfo:
    """One available update discovered by a provider."""

    id: str
    source: str               # "apt", "pypi", "git", "tank-ota"
    version_from: str
    version_to: str
    summary: str = ""
    requires_reboot: bool = False
    size_bytes: int = 0
    discovered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateSnapshot:
    """Pre-apply state snapshot for potential rollback."""

    id: str
    captured_at: float
    source: str
    version_from: str
    version_to: str
    artifacts: List[str] = field(default_factory=list)
    notes: str = ""


# ───────────────────────────────────────────────────────────────────────────
# Update providers (abstract + bundled)
# ───────────────────────────────────────────────────────────────────────────

class UpdateProvider(ABC):
    """A source of updates the manager polls."""

    name: str = ""

    def __init__(self, name: str) -> None:
        self.name = name or type(self).__name__

    @abstractmethod
    def check(self) -> List[UpdateInfo]:
        """Return the list of available updates (may be empty)."""

    def apply(self, update: UpdateInfo, *, dry_run: bool = False) -> bool:
        """Default no-op apply. Override in concrete providers."""
        logger.debug("Provider %s apply() noop for %s",
                     self.name, update.id)
        return dry_run  # only claim success when dry-running

    def rollback(self, snapshot: UpdateSnapshot, *,
                dry_run: bool = False) -> bool:  # noqa: D401
        return dry_run


class LocalManifestProvider(UpdateProvider):
    """Reads ``tank_ws/data/update_manifest.json`` if present.

    Useful for offline / bench scenarios. The manifest is a JSON
    array of :class:`UpdateInfo` dicts::

        [
          {"id": "...", "source": "local", "version_from": "0.1",
           "version_to": "0.2", "summary": "..."}
        ]
    """

    def __init__(self, manifest_path: Optional[Path] = None) -> None:
        super().__init__("local-manifest")
        self._path = manifest_path or (
            Path(__file__).resolve().parent.parent.parent
            / "tank_ws" / "data" / "update_manifest.json"
        )

    def check(self) -> List[UpdateInfo]:
        if not self._path.is_file():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("update manifest unreadable: %s", exc)
            return []
        updates: List[UpdateInfo] = []
        for entry in (raw or []):
            try:
                updates.append(UpdateInfo(
                    id=str(entry.get("id", uuid.uuid4().hex[:8])),
                    source=str(entry.get("source", self.name)),
                    version_from=str(entry.get("version_from", "")),
                    version_to=str(entry.get("version_to", "")),
                    summary=str(entry.get("summary", "")),
                    requires_reboot=bool(entry.get("requires_reboot", False)),
                    size_bytes=int(entry.get("size_bytes", 0) or 0),
                    metadata=dict(entry.get("metadata", {}) or {}),
                ))
            except Exception:
                logger.exception("skipping malformed manifest entry")
        return updates


class ScriptsOTAProvider(UpdateProvider):
    """Wraps ``scripts/ota.py`` for image-pin / ab-toggle / sd-burn flows.

    ``check()`` runs ``ab-toggle`` read-only style: it returns whatever
    the local manifest provider reports plus a synthetic channel entry
    if ``scripts/ota.py`` exists on disk.
    """

    def __init__(self, scripts_dir: Optional[Path] = None) -> None:
        super().__init__("tank-ota")
        self._scripts = (scripts_dir
                         or Path(__file__).resolve().parent.parent.parent
                         / "scripts")
        self._ota = self._scripts / "ota.py"

    def is_available(self) -> bool:
        return self._ota.is_file()

    def check(self) -> List[UpdateInfo]:
        if not self.is_available():
            return []
        # The OTA helper is mostly state-management. A real check
        # would curl a release server; here we publish a heartbeat
        # entry so consumers can see the source exists.
        return [UpdateInfo(
            id="ota-heartbeat",
            source=self.name,
            version_from="n/a",
            version_to="n/a",
            summary="scripts/ota.py present — A/B + image-pin flows available",
            metadata={"script": str(self._ota)},
        )]

    def apply(self, update: UpdateInfo, *, dry_run: bool = False) -> bool:
        if not self.is_available():
            logger.warning("Cannot apply %s — ota.py missing", update.id)
            return False
        if dry_run:
            return True
        try:
            res = subprocess.run(
                [sys.executable(), str(self._ota), "--help"],
                capture_output=True, text=True, timeout=10,
            )
            if res.returncode != 0:
                logger.warning("ota.py --help exit %d", res.returncode)
                return False
            return True
        except Exception as exc:
            logger.warning("ota.py run failed: %s", exc)
            return False


# ───────────────────────────────────────────────────────────────────────────
# UpdateManager
# ───────────────────────────────────────────────────────────────────────────

class UpdateManager:
    """Singleton update coordinator (periodic check + apply)."""

    _instance: Optional["UpdateManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "UpdateManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
                cls._instance._providers: Dict[str, UpdateProvider] = {}
                cls._instance._available: List[UpdateInfo] = []
                cls._instance._history: List[Dict[str, Any]] = []
                cls._instance._snapshots: Dict[str, UpdateSnapshot] = {}
                cls._instance._last_checked: float = 0.0
                cls._instance._check_interval_s = 6 * 3600  # 6 hours
                cls._instance._auto_check = False
                cls._instance._thread: Optional[threading.Thread] = None
                cls._instance._stop_event = threading.Event()
                cls._instance._check_lock = threading.Lock()
                # Auto-register bundled providers
                cls._instance._providers["local-manifest"] = (
                    LocalManifestProvider())
                cls._instance._providers["tank-ota"] = ScriptsOTAProvider()
            return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, *, auto_check: Optional[bool] = None) -> None:
        """Bind settings; optionally start the periodic check daemon."""
        self._check_interval_s = int(self._settings.get(
            "updates.check_interval_s", 6 * 3600))
        self._auto_check = (auto_check
                            if auto_check is not None
                            else bool(self._settings.get(
                                "updates.auto_check", False)))
        last = self._settings.get("updates.last_checked", 0.0)
        try:
            self._last_checked = float(last)
        except Exception:
            self._last_checked = 0.0
        if self._auto_check:
            self.start()
        logger.info(
            "UpdateManager initialized — providers=%s, auto_check=%s, "
            "interval=%ss",
            sorted(self._providers.keys()), self._auto_check,
            self._check_interval_s,
        )
        self._bus.emit(Event(
            "update_manager_ready",
            {"providers": list(self._providers.keys()),
             "auto_check": self._auto_check},
            source="update_manager",
        ))

    def start(self) -> None:
        """Start the periodic check daemon (idempotent)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        t = threading.Thread(
            target=self._check_loop, name="tank_os_update", daemon=True
        )
        self._thread = t
        t.start()

    def stop(self, *, join_timeout: float = 5.0) -> None:
        self._stop_event.set()
        t = self._thread
        if t:
            t.join(timeout=join_timeout)
            self._thread = None

    # ------------------------------------------------------------------
    # Provider registry
    # ------------------------------------------------------------------

    def register_provider(self, provider: UpdateProvider) -> None:
        if not isinstance(provider, UpdateProvider):
            raise TypeError(
                f"provider must subclass UpdateProvider, got "
                f"{type(provider).__name__}"
            )
        with self._lock:
            self._providers[provider.name] = provider
        logger.info("Registered update provider: %s", provider.name)

    def list_providers(self) -> List[str]:
        with self._lock:
            return sorted(self._providers.keys())

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def check(self) -> List[UpdateInfo]:
        """Synchronous one-shot check across all providers."""
        with self._check_lock:
            self._bus.emit(Event(
                "update_check_started",
                {"providers": self.list_providers()},
                source="update_manager",
            ))
            found: List[UpdateInfo] = []
            for prov in self._providers.values():
                try:
                    found.extend(prov.check())
                except Exception as exc:
                    logger.warning(
                        "Provider %s raised during check(): %s",
                        prov.name, exc,
                    )
            self._available = found
            self._last_checked = time.time()
            self._settings.set("updates.last_checked", self._last_checked)
            self._bus.emit(Event(
                "update_check_completed",
                {"count": len(found), "ts": self._last_checked,
                 "updates": [self._info_to_dict(u) for u in found]},
                source="update_manager",
                priority=Priority.HIGH,
            ))
            if found:
                self._bus.emit(Event(
                    "update_available",
                    {"count": len(found),
                     "updates": [self._info_to_dict(u) for u in found]},
                    source="update_manager",
                    priority=Priority.HIGH,
                ))
        return list(found)

    def available(self) -> List[UpdateInfo]:
        with self._lock:
            return list(self._available)

    def last_checked(self) -> float:
        return self._last_checked

    # ------------------------------------------------------------------
    # Apply + rollback
    # ------------------------------------------------------------------

    def apply(self, update_id: str, *,
              dry_run: bool = False,
              auto_rollback: bool = True) -> bool:
        """Apply a single update by id. Returns True on success."""
        with self._lock:
            target = next(
                (u for u in self._available if u.id == update_id), None
            )
        if target is None:
            logger.warning("apply(%s): not in available list", update_id)
            return False
        provider = self._providers.get(target.source)
        if provider is None:
            logger.warning("apply(%s): no provider for source=%s",
                           update_id, target.source)
            return False
        snapshot: Optional[UpdateSnapshot] = None
        if auto_rollback and not dry_run:
            snapshot = self._capture_snapshot(target)
        self._bus.emit(Event(
            "update_downloading" if dry_run else "update_applying",
            {"id": update_id, "source": target.source,
             "version_to": target.version_to, "dry_run": dry_run},
            source="update_manager",
            priority=Priority.HIGH,
        ))
        start = time.time()
        try:
            ok = provider.apply(target, dry_run=dry_run)
        except Exception as exc:
            logger.exception("Provider %s raised during apply()", target.source)
            self._bus.emit(Event(
                "update_failed",
                {"id": update_id, "error": str(exc),
                 "type": type(exc).__name__},
                source="update_manager",
            ))
            ok = False
        duration_ms = (time.time() - start) * 1000
        if snapshot is not None:
            self._snapshots[snapshot.id] = snapshot
        with self._lock:
            self._history.append({
                "id": update_id, "source": target.source,
                "version_from": target.version_from,
                "version_to": target.version_to,
                "ok": ok,
                "dry_run": dry_run,
                "duration_ms": duration_ms,
                "ts": time.time(),
            })
        self._bus.emit(Event(
            "update_completed" if ok else "update_failed",
            {"id": update_id, "source": target.source,
             "dry_run": dry_run, "duration_ms": duration_ms,
             "snapshot": snapshot.id if snapshot else None},
            source="update_manager",
        ))
        return ok

    def rollback(self, snapshot_id: str, *,
                 dry_run: bool = False) -> bool:
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            logger.warning("rollback: snapshot %s not found", snapshot_id)
            return False
        provider = self._providers.get(snapshot.source)
        if provider is None:
            logger.warning("rollback: no provider for source=%s",
                           snapshot.source)
            return False
        self._bus.emit(Event(
            "update_rolling_back",
            {"snapshot": snapshot_id, "source": snapshot.source,
             "dry_run": dry_run},
            source="update_manager",
        ))
        try:
            ok = provider.rollback(snapshot, dry_run=dry_run)
        except Exception as exc:
            logger.exception("rollback failed")
            ok = False
        self._bus.emit(Event(
            "update_rollback_completed" if ok else "update_rollback_failed",
            {"snapshot": snapshot_id, "ok": ok, "dry_run": dry_run},
            source="update_manager",
        ))
        return ok

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])

    def snapshots(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._snapshot_to_dict(s) for s in self._snapshots.values()]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _check_loop(self) -> None:
        """Background loop. Runs the first check immediately if stale."""
        if (self._last_checked == 0.0
                or (time.time() - self._last_checked) > self._check_interval_s):
            try:
                self.check()
            except Exception:
                logger.exception("initial check failed")
        while not self._stop_event.is_set():
            # Wake every minute and decide whether to re-check.
            self._stop_event.wait(timeout=60.0)
            if self._stop_event.is_set():
                return
            if (time.time() - self._last_checked) < self._check_interval_s:
                continue
            try:
                self.check()
            except Exception:
                logger.exception("periodic check failed")

    def _capture_snapshot(self, target: UpdateInfo) -> UpdateSnapshot:
        artifacts: List[str] = []
        try:
            repo_root = Path(__file__).resolve().parent.parent.parent
            git = shutil.which("git")
            if git and (repo_root / ".git").is_dir():
                head = subprocess.run(
                    [git, "-C", str(repo_root), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                if head.returncode == 0:
                    artifacts.append(f"git_sha:{head.stdout.strip()}")
        except Exception:
            logger.debug("git snapshot capture failed", exc_info=True)
        return UpdateSnapshot(
            id=f"snap_{uuid.uuid4().hex[:10]}",
            captured_at=time.time(),
            source=target.source,
            version_from=target.version_from,
            version_to=target.version_to,
            artifacts=artifacts,
            notes="auto-captured for rollback",
        )

    @staticmethod
    def _info_to_dict(u: UpdateInfo) -> Dict[str, Any]:
        return {
            "id": u.id, "source": u.source,
            "version_from": u.version_from,
            "version_to": u.version_to,
            "summary": u.summary,
            "requires_reboot": u.requires_reboot,
            "size_bytes": u.size_bytes,
            "discovered_at": u.discovered_at,
        }

    @staticmethod
    def _snapshot_to_dict(s: UpdateSnapshot) -> Dict[str, Any]:
        return {
            "id": s.id, "captured_at": s.captured_at,
            "source": s.source,
            "version_from": s.version_from,
            "version_to": s.version_to,
            "artifacts": list(s.artifacts),
            "notes": s.notes,
        }
