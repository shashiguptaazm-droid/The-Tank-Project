"""Tank — Central Event Bus.

Every important system event flows through here.
Events carry: timestamp, source, type, confidence, data, state.
"""
from __future__ import annotations

import json
import time
import logging
import threading
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger("tank.events")


class EventType(Enum):
    # Sensor events
    SENSOR_CONNECTED = "SENSOR_CONNECTED"
    SENSOR_DISCONNECTED = "SENSOR_DISCONNECTED"
    CAMERA_FRAME = "CAMERA_FRAME"
    LIDAR_SCAN = "LIDAR_SCAN"
    THERMAL_EVENT = "THERMAL_EVENT"
    IMU_UPDATE = "IMU_UPDATE"
    DISTANCE_UPDATED = "DISTANCE_UPDATED"
    PERSON_DETECTED = "PERSON_DETECTED"
    OBJECT_DETECTED = "OBJECT_DETECTED"

    # AI events
    AI_REQUEST_STARTED = "AI_REQUEST_STARTED"
    AI_RESPONSE_RECEIVED = "AI_RESPONSE_RECEIVED"
    AI_REQUEST_FAILED = "AI_REQUEST_FAILED"
    AI_CLASSIFICATION = "AI_CLASSIFICATION"

    # Fusion events
    FUSION_RESULT = "FUSION_RESULT"

    # Decision events
    DECISION_CREATED = "DECISION_CREATED"

    # Action events
    ACTION_STARTED = "ACTION_STARTED"
    ACTION_COMPLETED = "ACTION_COMPLETED"
    ACTION_FAILED = "ACTION_FAILED"

    # Safety events
    SAFETY_STOP = "SAFETY_STOP"
    SAFETY_WARNING = "SAFETY_WARNING"
    WATCHDOG_TIMEOUT = "WATCHDOG_TIMEOUT"

    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    STATE_CHANGED = "STATE_CHANGED"
    NETWORK_ONLINE = "NETWORK_ONLINE"
    NETWORK_OFFLINE = "NETWORK_OFFLINE"
    VPS_CONNECTED = "VPS_CONNECTED"
    VPS_DISCONNECTED = "VPS_DISCONNECTED"


@dataclass
class Event:
    timestamp: float
    source: str
    event_type: EventType
    confidence: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    system_state: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def create(cls, event_type: EventType, source: str, **kwargs) -> "Event":
        return cls(
            timestamp=time.time(),
            source=source,
            event_type=event_type,
            **kwargs,
        )


class EventBus:
    """Thread-safe publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._lock = threading.Lock()
        self._max_history = 10000

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        logger.info(f"[{event.event_type.value}] {event.source} conf={event.confidence:.2f} state={event.system_state}")

        callbacks = list(self._subscribers.get(event.event_type, []))
        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type.value}: {e}")

    def emit(self, event_type: EventType, source: str, **kwargs) -> Event:
        event = Event.create(event_type, source, **kwargs)
        self.publish(event)
        return event

    def history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        with self._lock:
            events = self._history
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return events[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
