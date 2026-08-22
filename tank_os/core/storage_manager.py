"""TankOS Storage Manager — local files, NVMe, SD card, backups, cloud sync."""

from __future__ import annotations
import logging, os, shutil, subprocess, threading, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


@dataclass
class StorageVolume:
    mount: str = ""; device: str = ""
    total_gb: float = 0.0; used_gb: float = 0.0; free_gb: float = 0.0
    fs_type: str = ""; label: str = ""


class StorageManager:
    _instance: Optional["StorageManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._volumes: Dict[str, StorageVolume] = {}
                cls._instance._data_dir = Path("/var/lib/tank")
            return cls._instance

    def initialize(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self.scan()
        logger.info("StorageManager initialized")

    def scan(self) -> Dict[str, StorageVolume]:
        try:
            r = subprocess.run(["df", "-B1"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6 and parts[0].startswith("/dev/"):
                    vol = StorageVolume(
                        device=parts[0], mount=parts[5],
                        total_gb=round(int(parts[1]) / 1e9, 2),
                        used_gb=round(int(parts[2]) / 1e9, 2),
                        free_gb=round(int(parts[3]) / 1e9, 2),
                    )
                    self._volumes[parts[5]] = vol
        except Exception: pass
        return dict(self._volumes)

    def get_volume(self, mount: str) -> Optional[StorageVolume]:
        return self._volumes.get(mount)

    @property
    def volumes(self) -> Dict[str, StorageVolume]:
        return dict(self._volumes)

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def usage_summary(self) -> Dict[str, Any]:
        root = self._volumes.get("/")
        if root:
            return {"total_gb": root.total_gb, "used_gb": root.used_gb,
                    "free_gb": root.free_gb, "percent": round(root.used_gb / max(0.1, root.total_gb) * 100, 1)}
        return {"error": "unavailable"}
