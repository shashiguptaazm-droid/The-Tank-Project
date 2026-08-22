"""
TankOS Settings Manager — persistent, JSON-backed configuration.

Every manager and plugin reads and writes settings through this
centralised store.  Settings are persisted to ``~/.config/tank_os/settings.json``
and cached in memory for fast access.

Sections: network, audio, voice, ai, personality, emotions, privacy,
power, display, developer, hardware, ros.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.settings")

CONFIG_DIR = Path.home() / ".config" / "tank_os"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

# Default settings tree — every key should have a default.
DEFAULTS: Dict[str, Any] = {
    "network": {
        "wifi_ssid": "",
        "wifi_password": "",
        "lte_apn": "",
        "vpn_enabled": False,
        "vpn_provider": "wireguard",
        "hostname": "tank",
    },
    "audio": {
        "input_device": "",
        "output_device": "",
        "volume": 80,
        "muted": False,
        "tts_enabled": True,
        "tts_rate": 1.0,
        "tts_pitch": 1.0,
    },
    "voice": {
        "wake_word_enabled": True,
        "wake_word": "hey tank",
        "sensitivity": 0.5,
        "always_listening": True,
        "language": "en-US",
    },
    "ai": {
        "provider": "local",
        "local_model": "",
        "external_endpoint": "",
        "external_api_key": "",
        "temperature": 0.7,
        "max_tokens": 512,
        "context_length": 4096,
    },
    "personality": {
        "name": "Tank",
        "tone": "warm",
        "response_style": "balanced",
        "backstory": "",
        "emoji_use": True,
    },
    "emotions": {
        "enabled": True,
        "decay_rate": 1.0,
        "expressiveness": 0.8,
        "hysteresis": 0.3,
    },
    "privacy": {
        "camera_enabled": True,
        "microphone_enabled": True,
        "recording_enabled": False,
        "data_collection": False,
        "cloud_sync": False,
    },
    "power": {
        "low_battery_threshold": 20,
        "emergency_threshold": 10,
        "auto_dock_enabled": True,
        "sleep_timeout_minutes": 30,
        "performance_mode": "balanced",
        "charge_cycles": 0,
        "battery_temp": 25.0,
    },
    "charging": {
        "auto_enabled": True,
        "target_pct": 95,
        "schedule_threshold": 50,
        "max_duration_minutes": 120,
        "dock_check_interval_s": 30,
        "approach_distance_m": 0.5,
        "alignment_tolerance_cm": 2.0,
        "enable_scheduler": True,
        "enable_emergency": True,
    },
    "display": {
        "brightness": 80,
        "theme": "dark",
        "accent_color": "#00BFFF",
        "font_size": 14,
        "animations_enabled": True,
        "fps_limit": 60,
        "wallpaper": "",
    },
    "developer": {
        "debug_mode": False,
        "log_level": "INFO",
        "ros_topic_monitor": False,
        "simulation_mode": False,
        "api_test_endpoint": "",
    },
    "hardware": {
        "camera_device": "/dev/video0",
        "lidar_port": "/dev/ttyUSB0",
        "imu_address": 0x28,
        "oled_address": 0x70,
        "pca9685_address": 0x40,
    },
    "ros": {
        "domain_id": 0,
        "namespace": "/tank",
        "auto_start": True,
        "node_timeout_seconds": 10,
    },
}


class SettingsManager:
    """Thread-safe JSON-persisted settings with merge-defaults."""

    _instance: Optional["SettingsManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SettingsManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._data: Dict[str, Any] = {}
                cls._instance._dirty = False
                cls._instance._bus = EventBus()
                cls._instance._file_lock = threading.Lock()
            return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load settings from disk, merging with defaults."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
        self._bus.emit(Event("settings_loaded", {}, source="settings_manager"))

    def _load(self) -> Dict[str, Any]:
        """Load from JSON or return defaults."""
        if SETTINGS_PATH.exists():
            try:
                raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                return self._deep_merge(DEFAULTS, raw)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load settings: %s", exc)
        return dict(DEFAULTS)

    def save(self) -> None:
        """Persist current settings to disk."""
        with self._file_lock:
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                SETTINGS_PATH.write_text(
                    json.dumps(self._data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                self._dirty = False
            except OSError as exc:
                logger.error("Failed to save settings: %s", exc)

    def reset(self) -> None:
        """Reset all settings to factory defaults."""
        self._data = dict(DEFAULTS)
        self.save()
        self._bus.emit(Event("settings_reset", {}, source="settings_manager"))

    # ------------------------------------------------------------------
    # Read / Write
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting by dotted path.

        Examples::

            settings.get("audio.volume")        # 80
            settings.get("display.theme")       # "dark"
            settings.get("nonexistent", 42)     # 42
        """
        parts = key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire settings section (e.g. ``"audio"``)."""
        return dict(self._data.get(section, {}))

    def set(self, key: str, value: Any) -> None:
        """Set a setting by dotted path.

        Emits ``settings_changed`` on the event bus.
        """
        parts = key.split(".")
        target = self._data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        self._dirty = True
        self._bus.emit(Event("settings_changed", {
            "key": key,
            "value": value,
        }, source="settings_manager"))

    def set_section(self, section: str, values: Dict[str, Any]) -> None:
        """Set all values in a section (merge)."""
        if section not in self._data:
            self._data[section] = {}
        self._data[section].update(values)
        self._dirty = True
        self._bus.emit(Event("settings_changed", {
            "section": section,
            "values": values,
        }, source="settings_manager"))

    def all(self) -> Dict[str, Any]:
        """Return the full settings dict (read-only snapshot)."""
        return dict(self._data)

    def defaults(self) -> Dict[str, Any]:
        """Return the factory defaults."""
        return dict(DEFAULTS)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def sections(self) -> List[str]:
        return sorted(self._data.keys())

    def is_dirty(self) -> bool:
        return self._dirty

    def path(self) -> str:
        return str(SETTINGS_PATH)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_merge(base: Dict[str, Any],
                    override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge ``override`` into ``base``.

        Missing keys in ``override`` are filled from ``base``.
        """
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = SettingsManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
