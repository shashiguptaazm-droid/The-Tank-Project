"""Tank — INA219 Current/Voltage Monitor Driver."""
from __future__ import annotations
import logging, random
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.power")

class PowerMonitor:
    def __init__(self, address: str = "0x40"):
        self.address = address
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def read(self) -> Optional[Dict[str, Any]]:
        if not self._connected:
            return None
        return {
            "voltage_v": round(random.uniform(11.0, 12.6), 2),
            "current_ma": round(random.uniform(500, 5000), 1),
            "power_w": round(random.uniform(6, 60), 1),
            "remaining_pct": round(random.uniform(20, 100), 1),
        }

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "address": self.address}
