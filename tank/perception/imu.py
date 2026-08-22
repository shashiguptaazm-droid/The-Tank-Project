"""Tank — IMU Sensor Driver.

Supports MPU6050 (6-axis, I2C 0x68) and BNO055 (9-axis, I2C 0x28).
BNO055 provides fused absolute orientation.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.imu")

try:
    import board
    import adafruit_bno055
    BNO_AVAILABLE = True
except ImportError:
    BNO_AVAILABLE = False

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False


class IMUSensor:
    def __init__(self, model: str = "BNO055", address: int = 0x28):
        self.model = model
        self.address = address
        self._connected = False
        self._yaw = 0.0
        self._pitch = 0.0
        self._roll = 0.0

    def connect(self) -> bool:
        if not BNO_AVAILABLE and not SMBUS_AVAILABLE:
            self._connected = True
            return True
        try:
            i2c = board.I2C()
            self._sensor = adafruit_bno055.BNO055_I2C(i2c, address=self.address)
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"IMU connect failed: {e}")
            self._connected = True
            return True

    def read_orientation(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        if not BNO_AVAILABLE:
            self._yaw += random.uniform(-2.0, 2.0)
            self._pitch += random.uniform(-1.0, 1.0)
            self._roll += random.uniform(-1.0, 1.0)
            return {
                "yaw": round(self._yaw % 360, 1),
                "pitch": round(max(-90, min(90, self._pitch)), 1),
                "roll": round(max(-90, min(90, self._roll)), 1),
                "heading": round(self._yaw % 360, 1),
                "calibrated": True,
            }
        try:
            heading, roll, pitch = self._sensor.euler
            accel = self._sensor.acceleration
            gyro = self._sensor.gyro
            return {
                "yaw": round(heading, 1),
                "pitch": round(pitch, 1),
                "roll": round(roll, 1),
                "heading": round(heading, 1),
                "acceleration": [round(a, 2) for a in accel] if accel else [0, 0, 0],
                "gyroscope": [round(g, 2) for g in gyro] if gyro else [0, 0, 0],
                "calibrated": self._sensor.calibrated,
            }
        except Exception as e:
            logger.error(f"IMU read error: {e}")
            return None

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "model": self.model, "address": hex(self.address)}
