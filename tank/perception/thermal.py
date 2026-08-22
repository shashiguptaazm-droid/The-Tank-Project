"""Tank — MLX90640 Thermal Sensor Driver.

I2C thermal array camera (32x24 pixels, 110° FOV).
Used for human detection and heat mapping.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.thermal")

try:
    import board
    import adafruit_mlx90640
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False


class ThermalSensor:
    def __init__(self, address: str = "0x33"):
        self.address = address
        self._connected = False
        self._frame = [0.0] * 768  # 32x24

    def connect(self) -> bool:
        if not MLX_AVAILABLE:
            logger.info("MLX90640 not available — simulating thermal")
            self._connected = True
            return True
        try:
            i2c = board.I2C()
            self._mlx = adafruit_mlx90640.MLX90640(i2c)
            self._mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Thermal sensor connect failed: {e}")
            self._connected = True
            return True

    def read(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        if not MLX_AVAILABLE:
            import random
            human_present = random.random() < 0.25
            temps = [random.uniform(20.0, 38.0) for _ in range(768)]
            return {
                "temperatures": temps[:32*24],
                "min_temp_c": round(min(temps), 1),
                "max_temp_c": round(max(temps), 1),
                "avg_temp_c": round(sum(temps)/len(temps), 1),
                "human_detected": human_present,
                "confidence": round(random.uniform(0.6, 0.95), 2) if human_present else 0.0,
            }
        try:
            self._mlx.getFrame(self._frame)
            temps = list(self._frame)
            hot_pixels = sum(1 for t in temps if t > 35.0)
            human_present = hot_pixels > 20
            return {
                "temperatures": temps,
                "min_temp_c": round(min(temps), 1),
                "max_temp_c": round(max(temps), 1),
                "avg_temp_c": round(sum(temps)/len(temps), 1),
                "human_detected": human_present,
                "confidence": round(min(1.0, hot_pixels / 50), 2),
            }
        except Exception as e:
            logger.error(f"Thermal read error: {e}")
            return None

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "resolution": "32x24", "fov": "110°"}
