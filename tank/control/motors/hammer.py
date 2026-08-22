"""Tank — HAMMER Electromagnetic Actuator Module."""
from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger("tank.control.motors.hammer")


class HAMMERActuator:
    def __init__(self, name: str = "hammer"):
        self.name = name
        self._connected = False
        self._active = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def activate(self) -> None:
        self._active = True
        logger.debug(f"HAMMER {self.name} ACTIVATED")

    def deactivate(self) -> None:
        self._active = False
        logger.debug(f"HAMMER {self.name} deactivated")

    def is_active(self) -> bool:
        return self._active

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"name": self.name, "connected": self._connected, "active": self._active}
