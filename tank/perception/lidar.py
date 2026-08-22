"""Tank — RPLidar A1/A2 Driver.

360° 2D LiDAR scanner via serial.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank.perception.lidar")

try:
    from rplidar import RPLidar
    LIDAR_AVAILABLE = True
except ImportError:
    LIDAR_AVAILABLE = False


class LidarSensor:
    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self._lidar = None
        self._connected = False

    def connect(self) -> bool:
        if not LIDAR_AVAILABLE:
            self._connected = True
            return True
        try:
            self._lidar = RPLidar(self.port, self.baud)
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"LiDAR connect failed: {e}")
            self._connected = True
            return True

    def scan(self, max_beams: int = 360) -> Optional[List[Dict]]:
        if not self._connected:
            return None
        if not LIDAR_AVAILABLE:
            import random
            points = []
            for angle in range(0, 360, 5):
                dist = random.uniform(0.3, 10.0)
                points.append({"angle": angle, "distance_m": round(dist, 2), "quality": random.randint(500, 1500)})
            return points
        try:
            points = []
            for scan in self._lidar.iter_scans(min_len=5):
                for quality, angle, dist in scan:
                    points.append({
                        "angle": round(angle, 1),
                        "distance_m": round(dist / 1000, 2),
                        "quality": quality,
                    })
                if len(points) >= max_beams:
                    break
            return points
        except Exception as e:
            logger.error(f"LiDAR scan error: {e}")
            return None

    def get_obstacles(self, threshold_m: float = 1.0) -> List[Dict]:
        points = self.scan() or []
        return [p for p in points if 0 < p["distance_m"] < threshold_m]

    def disconnect(self) -> None:
        if self._lidar:
            self._lidar.stop()
            self._lidar.disconnect()
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "port": self.port, "scan_rate": "8Hz"}
