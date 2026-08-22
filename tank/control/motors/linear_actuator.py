"""Tank — Linear Actuator Controller.

For shoulders, biceps, neck tilt, hip, knee joints.
Dual H-bridge control (BTS7960) for direction + PWM speed.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("tank.control.motors.linear")


class LinearActuator:
    def __init__(self, pin_pwm: int, pin_fwd: int, pin_rev: int, name: str = "actuator"):
        self.pin_pwm = pin_pwm
        self.pin_fwd = pin_fwd
        self.pin_rev = pin_rev
        self.name = name
        self._connected = False
        self._position_pct = 50.0  # 0-100%

    def connect(self) -> bool:
        self._connected = True
        logger.info(f"Linear actuator {self.name} connected")
        return True

    def extend(self, speed: float = 0.5) -> None:
        """Extend actuator (0.0-1.0 speed)."""
        self._position_pct = min(100, self._position_pct + 5)
        logger.debug(f"{self.name} EXTEND speed={speed:.1f} pos={self._position_pct:.0f}%")

    def retract(self, speed: float = 0.5) -> None:
        """Retract actuator."""
        self._position_pct = max(0, self._position_pct - 5)
        logger.debug(f"{self.name} RETRACT speed={speed:.1f} pos={self._position_pct:.0f}%")

    def stop(self) -> None:
        logger.debug(f"{self.name} STOP")

    def set_position(self, pct: float) -> None:
        self._position_pct = max(0, min(100, pct))

    def get_position(self) -> Dict[str, Any]:
        return {"name": self.name, "position_pct": self._position_pct, "connected": self._connected}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"name": self.name, "connected": self._connected, "position": self._position_pct}
