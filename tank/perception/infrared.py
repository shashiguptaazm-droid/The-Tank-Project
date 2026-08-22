"""Tank — Infrared Proximity Sensor Driver."""
from __future__ import annotations
import logging, random
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.infrared")

class InfraredSensor:
    def __init__(self, name: str = "ir"):
        self.name = name
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def read_proximity(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        detected = random.random() < 0.3
        return {"detected": detected, "distance_cm": round(random.uniform(2, 30), 1) if detected else None}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected}
