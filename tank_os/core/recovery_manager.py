"""TankOS Recovery Manager — crash recovery, safe mode, watchdog, backups, restoration."""
from __future__ import annotations
import logging, threading, time, os, json, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.recovery_manager")

class RecoveryManager:
    _instance: Optional["RecoveryManager"] = None; _lock = threading.Lock()
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._safe_mode = False
                cls._instance._crash_count = 0
                cls._instance._max_crashes = 3
                cls._instance._backup_dir = Path.home() / ".config" / "tank_os" / "backups"
            return cls._instance
    def initialize(self) -> None:
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._check_crash_state()
        logger.info("RecoveryManager initialized")
    def _check_crash_state(self) -> None:
        state_file = Path.home() / ".config" / "tank_os" / ".crash_state"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self._crash_count = data.get("count", 0) + 1
            except Exception: self._crash_count += 1
        else:
            self._crash_count = 0
        if self._crash_count >= self._max_crashes:
            self._safe_mode = True
            logger.warning("Too many crashes (%d) — entering SAFE MODE", self._crash_count)
            self._bus.emit(Event("safe_mode_entered", {"crash_count": self._crash_count}))
        self._save_crash_state()
    def _save_crash_state(self) -> None:
        state_file = Path.home() / ".config" / "tank_os" / ".crash_state"
        state_file.write_text(json.dumps({"count": self._crash_count, "ts": time.time()}))
    def clear_crash_count(self) -> None:
        self._crash_count = 0
        state_file = Path.home() / ".config" / "tank_os" / ".crash_state"
        if state_file.exists(): state_file.unlink()
        logger.info("Crash count cleared")
    def backup(self, label: str = "") -> Optional[Path]:
        ts = time.strftime("%Y%m%d_%H%M%S")
        name = f"backup_{ts}_{label}" if label else f"backup_{ts}"
        backup_path = self._backup_dir / name
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            settings_src = Path.home() / ".config" / "tank_os" / "settings.json"
            if settings_src.exists():
                import shutil
                shutil.copy2(settings_src, backup_path / "settings.json")
            self._bus.emit(Event("backup_created", {"path": str(backup_path), "label": label}))
            logger.info("Backup created: %s", backup_path)
            return backup_path
        except Exception as exc:
            logger.error("Backup failed: %s", exc)
            return None
    def restore(self, backup_path: Path) -> bool:
        try:
            settings_file = backup_path / "settings.json"
            if settings_file.exists():
                import shutil
                shutil.copy2(settings_file, Path.home() / ".config" / "tank_os" / "settings.json")
            self._bus.emit(Event("backup_restored", {"path": str(backup_path)}))
            self.clear_crash_count()
            logger.info("Restored from: %s", backup_path)
            return True
        except Exception as exc:
            logger.error("Restore failed: %s", exc)
            return False
    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for d in sorted(self._backup_dir.iterdir()):
            if d.is_dir():
                backups.append({"name": d.name, "path": str(d), "ts": d.stat().st_mtime})
        return backups
    @property
    def in_safe_mode(self) -> bool: return self._safe_mode
    @property
    def crash_count(self) -> int: return self._crash_count
