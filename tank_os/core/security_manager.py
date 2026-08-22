"""TankOS Security Manager — authentication, fingerprint, surveillance, e-stop."""
from __future__ import annotations
import logging, threading, time, hashlib, os
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.security_manager")

class SecurityEvent(Enum):
    AUTH_SUCCESS = auto(); AUTH_FAIL = auto(); FINGERPRINT_SCANNED = auto()
    MOTION_DETECTED = auto(); INTRUSION = auto(); E_STOP_ACTIVATED = auto()
    SURVEILLANCE_STARTED = auto(); SURVEILLANCE_STOPPED = auto()

class SecurityManager:
    _instance: Optional["SecurityManager"] = None; _lock = threading.Lock()
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._authenticated = False
                cls._instance._estop_latched = False
                cls._instance._surveillance = False
                cls._instance._auth_tokens: Dict[str, str] = {}
            return cls._instance
    def initialize(self) -> None:
        self._load_keys()
        self._bus.on("estop_triggered", lambda e: self._handle_estop(e))
        logger.info("SecurityManager initialized")
    def _load_keys(self) -> None:
        api_key = os.environ.get("TANK_API_KEY", "")
        if api_key: self._auth_tokens["api"] = hashlib.sha256(api_key.encode()).hexdigest()
    def authenticate(self, token: str) -> bool:
        hashed = hashlib.sha256(token.encode()).hexdigest()
        if hashed in self._auth_tokens.values():
            self._authenticated = True
            self._bus.emit(Event("security_auth", {"success": True}, source="security"))
            return True
        self._bus.emit(Event("security_auth", {"success": False}, source="security"))
        return False
    def estop(self, latch: bool = True) -> None:
        self._estop_latched = latch
        self._bus.emit(Event("estop_triggered", {"latched": latch}, source="security"))
        logger.warning("E-STOP %s", "LATCHED" if latch else "RELEASED")
    @property
    def is_estop(self) -> bool: return self._estop_latched
    def toggle_surveillance(self) -> bool:
        self._surveillance = not self._surveillance
        evt = SecurityEvent.SURVEILLANCE_STARTED if self._surveillance else SecurityEvent.SURVEILLANCE_STOPPED
        self._bus.emit(Event("surveillance", {"active": self._surveillance}, source="security"))
        return self._surveillance
    def lock(self) -> None:
        self._bus.emit(Event("system_locked", {}, source="security"))
        logger.info("System locked")

    def unlock(self, token: str) -> bool:
        if self.authenticate(token):
            self._bus.emit(Event("system_unlocked", {}, source="security"))
            logger.info("System unlocked")
            return True
        return False

    @property
    def is_authenticated(self) -> bool: return self._authenticated
    @property
    def is_surveillance_active(self) -> bool: return self._surveillance
    def _handle_estop(self, event: Event) -> None:
        self._estop_latched = event.data.get("latched", True)
