"""Tank — Foot Pressure Sensor (FSR) Driver."""
from __future__ import annotations
import logging, random
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.pressure")

class PressureSensor:
    def __init__(self, name: str = "fsr"):
        self.name = name
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def read_force(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        force_kg = round(random.uniform(0, 10), 2)
        return {"force_kg": force_kg, "ground_contact": force_kg > 0.5, "weight_distribution": "left" if "left" in self.name else "right"}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "type": "FSR"}
