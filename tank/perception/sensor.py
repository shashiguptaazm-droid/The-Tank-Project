"""Tank — Sensor Abstraction Layer.

Every sensor implements SensorInterface.
Application code depends on interfaces, not hardware.
Allows REAL HARDWARE and SIMULATION to use the same pipeline.
"""
from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception")


class SensorType(Enum):
    CAMERA = "CAMERA"
    LIDAR = "LIDAR"
    THERMAL = "THERMAL"
    IMU = "IMU"
    ULTRASONIC = "ULTRASONIC"
    FINGERPRINT = "FINGERPRINT"


class SensorStatus(Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    READING = "READING"


@dataclass
class SensorReading:
    sensor_type: SensorType
    timestamp: float
    data: Dict[str, Any]
    confidence: float = 1.0
    status: SensorStatus = SensorStatus.CONNECTED


class SensorInterface(ABC):
    def __init__(self, name: str, sensor_type: SensorType) -> None:
        self.name = name
        self.sensor_type = sensor_type
        self._status = SensorStatus.DISCONNECTED

    @property
    def status(self) -> SensorStatus:
        return self._status

    @abstractmethod
    def connect(self) -> bool:
        """Initialize hardware connection. Returns True if successful."""

    @abstractmethod
    def read(self) -> Optional[SensorReading]:
        """Read current sensor data."""

    @abstractmethod
    def disconnect(self) -> None:
        """Clean shutdown."""

    def health_check(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.sensor_type.value, "status": self._status.value}
