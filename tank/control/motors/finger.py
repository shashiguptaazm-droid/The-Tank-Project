"""Tank — Finger Servo Controller.

SG90 microservo control for 5-finger hand (10 DOF total).
Each finger has 2 servos: base flex + tip curl.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("tank.control.motors.finger")


class FingerController:
    def __init__(self, finger_name: str, pwm_channel: int = 0):
        self.finger_name = finger_name
        self.pwm_channel = pwm_channel
        self._flex_angle = 0  # 0=straight, 180=full curl
        self._curl_angle = 0
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def flex(self, angle: int = 90) -> None:
        self._flex_angle = max(0, min(180, angle))
        logger.debug(f"finger {self.finger_name} flex={angle}°")

    def curl(self, angle: int = 90) -> None:
        self._curl_angle = max(0, min(180, angle))
        logger.debug(f"finger {self.finger_name} curl={angle}°")

    def grab(self) -> None:
        """Full grab: flex + curl."""
        self.flex(150)
        self.curl(150)

    def release(self) -> None:
        """Full release: straighten."""
        self.flex(0)
        self.curl(0)

    def get_state(self) -> Dict[str, Any]:
        return {"finger": self.finger_name, "flex": self._flex_angle, "curl": self._curl_angle, "connected": self._connected}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"finger": self.finger_name, "connected": self._connected}
