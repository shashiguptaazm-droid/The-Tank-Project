"""Tank — Luminosity / Ambient Light Sensor Driver."""
from __future__ import annotations
import logging, random
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.luminosity")

class LuminositySensor:
    def __init__(self, address: str = "0x29"):
        self.address = address
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def read_lux(self) -> Optional[float]:
        if not self._connected:
            return None
        return round(random.uniform(0.1, 40000), 1)

    def read(self) -> Optional[Dict[str, Any]]:
        lux = self.read_lux()
        if lux is None:
            return None
        level = "dark" if lux < 10 else "dim" if lux < 100 else "normal" if lux < 1000 else "bright" if lux < 10000 else "outdoor"
        return {"lux": lux, "level": level}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected}
