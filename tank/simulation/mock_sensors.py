"""Tank — Simulation Mock Sensors.

Generates realistic mock data so the entire stack can be tested without hardware.
Same decision engine processes simulated and real events.
"""
from __future__ import annotations

import math
import random
import time
from typing import Dict, Optional

from ..perception.sensor import SensorInterface, SensorType, SensorReading, SensorStatus


class MockCamera(SensorInterface):
    def __init__(self) -> None:
        super().__init__("mock_camera", SensorType.CAMERA)
        self._frame_count = 0

    def connect(self) -> bool:
        self._status = SensorStatus.CONNECTED
        return True

    def read(self) -> Optional[SensorReading]:
        self._frame_count += 1
        # Simulate person detection 30% of the time
        objects = []
        if random.random() < 0.3:
            objects.append({
                "object": "person",
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "distance_m": round(random.uniform(1.0, 5.0), 2),
            })
        elif random.random() < 0.5:
            objects.append({
                "object": "chair",
                "confidence": round(random.uniform(0.6, 0.9), 2),
                "distance_m": round(random.uniform(2.0, 8.0), 2),
            })
        return SensorReading(SensorType.CAMERA, time.time(), {"frame_id": self._frame_count, "detections": objects})

    def disconnect(self) -> None:
        self._status = SensorStatus.DISCONNECTED


class MockLidar(SensorInterface):
    def __init__(self) -> None:
        super().__init__("mock_lidar", SensorType.LIDAR)
        self._base_distance = 3.0

    def connect(self) -> bool:
        self._status = SensorStatus.CONNECTED
        return True

    def read(self) -> Optional[SensorReading]:
        # Simulate slowly changing distance
        self._base_distance += random.uniform(-0.3, 0.3)
        self._base_distance = max(0.1, min(10.0, self._base_distance))
        return SensorReading(SensorType.LIDAR, time.time(), {
            "distance_m": round(self._base_distance, 2),
            "angle_deg": random.randint(0, 359),
        })

    def disconnect(self) -> None:
        self._status = SensorStatus.DISCONNECTED


class MockThermal(SensorInterface):
    def __init__(self) -> None:
        super().__init__("mock_thermal", SensorType.THERMAL)

    def connect(self) -> bool:
        self._status = SensorStatus.CONNECTED
        return True

    def read(self) -> Optional[SensorReading]:
        human = random.random() < 0.25
        return SensorReading(SensorType.THERMAL, time.time(), {
            "human_detected": human,
            "confidence": round(random.uniform(0.6, 0.95), 2) if human else 0.0,
            "avg_temp_c": round(random.uniform(22.0, 38.0), 1),
        })

    def disconnect(self) -> None:
        self._status = SensorStatus.DISCONNECTED


class MockIMU(SensorInterface):
    def __init__(self) -> None:
        super().__init__("mock_imu", SensorType.IMU)
        self._yaw = 0.0

    def connect(self) -> bool:
        self._status = SensorStatus.CONNECTED
        return True

    def read(self) -> Optional[SensorReading]:
        self._yaw += random.uniform(-2.0, 2.0)
        return SensorReading(SensorType.IMU, time.time(), {
            "yaw": round(self._yaw % 360, 1),
            "pitch": round(random.uniform(-5, 5), 1),
            "roll": round(random.uniform(-5, 5), 1),
        })

    def disconnect(self) -> None:
        self._status = SensorStatus.DISCONNECTED


def create_mock_sensors() -> list:
    return [MockCamera(), MockLidar(), MockThermal(), MockIMU()]
