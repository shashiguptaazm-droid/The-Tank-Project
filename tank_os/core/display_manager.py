"""TankOS Display Manager — brightness, multi-display, screen blanking, DSI/HDMI."""

from __future__ import annotations
import logging, glob, os, subprocess, threading, time
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.display_manager")


class DisplayManager:
    _instance: Optional["DisplayManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DisplayManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._brightness = 80
                cls._instance._blanked = False
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
            return cls._instance

    def initialize(self) -> None:
        self._brightness = self._settings.get("display.brightness", 80)
        self._apply_brightness()
        self._bus.emit(Event("display_initialized", {"brightness": self._brightness}))

    @property
    def brightness(self) -> int: return self._brightness

    def set_brightness(self, value: int) -> None:
        self._brightness = max(1, min(100, value))
        self._apply_brightness()
        self._settings.set("display.brightness", self._brightness)
        self._bus.emit(Event("display_brightness_changed", {"value": self._brightness}))

    def _apply_brightness(self) -> None:
        try:
            for p in glob.glob("/sys/class/backlight/*/brightness"):
                with open(p, "w") as f:
                    f.write(f"{self._brightness}\n")
        except Exception:
            pass

    def blank(self) -> None:
        self._blanked = True
        try:
            subprocess.run(["vcgencmd", "display_power", "0"], timeout=2, capture_output=True)
        except Exception:
            pass
        self._bus.emit(Event("display_blanked", {}))

    def unblank(self) -> None:
        self._blanked = False
        try:
            subprocess.run(["vcgencmd", "display_power", "1"], timeout=2, capture_output=True)
        except Exception:
            pass
        self._bus.emit(Event("display_unblanked", {}))
