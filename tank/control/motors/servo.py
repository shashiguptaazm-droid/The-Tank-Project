"""Tank — Servo Motor Controller.

PWM-based servo control for neck, arms, ankles, fingers.
Supports direct GPIO (RPi) and Arduino serial bridge.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.control.motors.servo")

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False


class ServoController:
    def __init__(self, pin: int, name: str = "servo", min_duty: int = 2, max_duty: int = 12):
        self.pin = pin
        self.name = name
        self.min_duty = min_duty
        self.max_duty = max_duty
        self._connected = False
        self._position = 90  # center

    def connect(self) -> bool:
        if RPI_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, 50)
            self._pwm.start(0)
        self._connected = True
        logger.info(f"Servo {self.name} connected (pin={self.pin})")
        return True

    def set_angle(self, angle: int) -> bool:
        """Set servo angle 0-180 degrees."""
        if not self._connected:
            return False
        angle = max(0, min(180, angle))
        duty = self.min_duty + (angle / 180.0) * (self.max_duty - self.min_duty)
        if RPI_AVAILABLE and hasattr(self, '_pwm'):
            self._pwm.ChangeDutyCycle(duty)
        self._position = angle
        logger.debug(f"Servo {self.name} → {angle}°")
        return True

    def set_position_pct(self, pct: float) -> bool:
        """Set position as percentage 0-100."""
        angle = int(pct * 1.8)
        return self.set_angle(angle)

    def get_position(self) -> Dict[str, Any]:
        return {"name": self.name, "angle": self._position, "connected": self._connected}

    def stop(self) -> None:
        if hasattr(self, '_pwm'):
            self._pwm.stop()

    def disconnect(self) -> None:
        self.stop()
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"name": self.name, "pin": self.pin, "connected": self._connected, "position": self._position}
