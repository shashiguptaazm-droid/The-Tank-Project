"""TankOS Power Manager — battery monitoring, auto-dock, sleep, performance modes."""

from __future__ import annotations
import logging, threading, time
from typing import Any, Dict, Optional
from tank_os.core.event_bus import Event, EventBus
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.power_manager")


class PowerManager:
    _instance: Optional["PowerManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "PowerManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._battery_pct = 100
                cls._instance._charging = False
                cls._instance._voltage = 5.0
                cls._instance._current_ma = 0.0
                cls._instance._performance = "balanced"
                cls._instance._low_threshold = 20
                cls._instance._emergency_threshold = 10
                cls._instance._sleep_timeout = 30
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
                cls._instance._running = False
                cls._instance._charge_cycles = 0
                cls._instance._battery_temp_c = 25.0
            return cls._instance

    def initialize(self) -> None:
        self._low_threshold = self._settings.get("power.low_battery_threshold", 20)
        self._emergency_threshold = self._settings.get("power.emergency_threshold", 10)
        self._sleep_timeout = self._settings.get("power.sleep_timeout_minutes", 30)
        self._performance = self._settings.get("power.performance_mode", "balanced")
        self._charge_cycles = self._settings.get("power.charge_cycles", 0)
        self._battery_temp_c = self._settings.get("power.battery_temp", 25.0)
        self._start_monitoring()

    def _start_monitoring(self) -> None:
        self._running = True
        t = threading.Thread(target=self._monitor, daemon=True, name="tank_os_power")
        t.start()

    def _monitor(self) -> None:
        while self._running:
            self._read_battery()
            time.sleep(10)

    def _read_battery(self) -> None:
        try:
            import subprocess
            result = subprocess.run(
                ["cat", "/sys/class/power_supply/*/capacity"],
                capture_output=True, text=True, timeout=2, shell=True
            )
            if result.stdout.strip():
                new_pct = int(result.stdout.strip().split("\n")[-1])
                changed = new_pct != self._battery_pct
                self._battery_pct = new_pct
                if changed:
                    self._bus.emit(Event("battery_changed", {
                        "percent": self._battery_pct,
                        "charging": self._charging,
                    }, source="power_manager"))

            result2 = subprocess.run(
                ["cat", "/sys/class/power_supply/*/status"],
                capture_output=True, text=True, timeout=2, shell=True
            )
            if "Charging" in result2.stdout:
                if not self._charging:
                    self._bus.emit(Event("charging_state_changed", {
                        "charging": True, "percent": self._battery_pct,
                    }, source="power_manager"))
                self._charging = True
            elif "Discharging" in result2.stdout:
                if self._charging:
                    self._bus.emit(Event("charging_state_changed", {
                        "charging": False, "percent": self._battery_pct,
                    }, source="power_manager"))
                self._charging = False

            self._check_alerts()
        except Exception:
            pass

    def _check_alerts(self) -> None:
        if self._battery_pct <= self._low_threshold and not self._charging:
            self._bus.emit(Event("battery_critical", {
                "percent": self._battery_pct,
                "charging": self._charging,
            }, source="power_manager"))
        if self._battery_pct <= self._emergency_threshold and not self._charging:
            self._bus.emit(Event("battery_emergency", {
                "percent": self._battery_pct,
                "charging": self._charging,
            }, source="power_manager"))

    @property
    def battery_percent(self) -> int: return self._battery_pct
    @property
    def is_charging(self) -> bool: return self._charging
    @property
    def voltage(self) -> float: return self._voltage
    @property
    def current_ma(self) -> float: return self._current_ma
    @property
    def performance_mode(self) -> str: return self._performance
    @property
    def battery_temp_c(self) -> float: return self._battery_temp_c
    @property
    def charge_cycles(self) -> int: return self._charge_cycles

    def set_performance(self, mode: str) -> None:
        if mode in ("powersave", "balanced", "performance"):
            self._performance = mode
            self._settings.set("power.performance_mode", mode)
            self._bus.emit(Event("performance_changed", {"mode": mode}))

    def sleep(self) -> None:
        self._bus.emit(Event("system_sleep", {}))
        try:
            import subprocess
            subprocess.run(["systemctl", "suspend"], timeout=5)
        except Exception: pass

    def shutdown(self) -> None:
        self._bus.emit(Event("system_shutdown", {}))
        try:
            import subprocess
            subprocess.run(["shutdown", "-h", "now"], timeout=5)
        except Exception: pass

    def reboot(self) -> None:
        self._bus.emit(Event("system_reboot", {}))
        try:
            import subprocess
            subprocess.run(["reboot"], timeout=5)
        except Exception: pass
