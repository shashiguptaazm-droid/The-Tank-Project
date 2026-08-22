"""TankOS Robot Manager — unified interface for movement, motors, servos, docking, patrol."""

from __future__ import annotations
import logging, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


@dataclass
class RobotStatus:
    vx: float = 0.0; wz: float = 0.0; battery_pct: int = 100
    estop: bool = False; docked: bool = False; patrolling: bool = False
    mode: str = "idle"  # idle, driving, docking, patrolling, charging


class RobotManager:
    _instance: Optional["RobotManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._status = RobotStatus()
                cls._instance._cmd_vel_timer: Optional[threading.Timer] = None
            return cls._instance

    def initialize(self) -> None:
        from tank_os.core.hardware_manager import HardwareManager
        HardwareManager()
        logger.info("RobotManager initialized")

    def drive(self, vx: float = 0.0, wz: float = 0.0, duration_s: float = 1.0) -> None:
        vx = max(-0.5, min(0.5, vx))
        wz = max(-1.5, min(1.5, wz))
        self._status.vx, self._status.wz = vx, wz
        self._status.mode = "driving"
        self._bus.emit(Event("cmd_vel", {"vx": vx, "wz": wz}, source="robot_manager"))
        if self._cmd_vel_timer and self._cmd_vel_timer.is_alive():
            self._cmd_vel_timer.cancel()
        self._cmd_vel_timer = threading.Timer(duration_s, self._stop)
        self._cmd_vel_timer.daemon = True
        self._cmd_vel_timer.start()

    def _stop(self) -> None:
        self._status.vx, self._status.wz = 0.0, 0.0
        self._status.mode = "idle"
        self._bus.emit(Event("cmd_vel", {"vx": 0.0, "wz": 0.0}, source="robot_manager"))

    def estop(self, latch: bool = True) -> None:
        self._status.estop = latch
        self._bus.emit(Event("estop_triggered", {"latched": latch}, source="robot_manager"))

    def dock(self) -> None:
        self._status.mode = "docking"
        self._bus.emit(Event("dock_start", {}, source="robot_manager"))

    def set_docked(self, docked: bool) -> None:
        """Update docked state after docking controller completes."""
        self._status.docked = docked
        self._status.mode = "docked" if docked else "idle"
        self._bus.emit(Event("docked_state_changed", {
            "docked": docked,
        }, source="robot_manager"))

    def patrol(self, mode: str = "random") -> None:
        self._status.patrolling = True
        self._status.mode = "patrolling"
        self._bus.emit(Event("patrol_start", {"mode": mode}, source="robot_manager"))

    def stop_patrol(self) -> None:
        self._status.patrolling = False
        self._status.mode = "idle"
        self._bus.emit(Event("patrol_stop", {}, source="robot_manager"))

    @property
    def status(self) -> RobotStatus: return self._status

    def summary(self) -> Dict[str, Any]:
        return {"vx": self._status.vx, "wz": self._status.wz,
                "estop": self._status.estop, "docked": self._status.docked,
                "mode": self._status.mode, "patrolling": self._status.patrolling}



