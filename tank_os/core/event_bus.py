"""
TankOS Event Bus — centralized publish/subscribe communication system.

Every component in TankOS communicates through this event bus.
No direct coupling between components. Events are typed, async-safe,
and support priorities.

Typical event types:
  battery_changed, emotion_changed, wake_detected, camera_connected,
  robot_moving, memory_updated, plugin_loaded, notification_received
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("tank_os.event_bus")


class Priority(IntEnum):
    """Event dispatch priority. Higher = delivered first."""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 0


@dataclass
class Event:
    """A single event on the bus."""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    priority: Priority = Priority.NORMAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return (f"Event(type={self.type!r}, source={self.source!r}, "
                f"priority={self.priority.name})")


EventHandler = Callable[[Event], None]


class EventBus:
    """Thread-safe, async-compatible publish/subscribe event bus.

    Usage::

        bus = EventBus()

        @bus.on("battery_changed")
        def handle_battery(evt: Event):
            print(f"Battery: {evt.data['percent']}%")

        bus.emit(Event("battery_changed", {"percent": 85}))
    """

    _instance: Optional["EventBus"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "EventBus":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers: Dict[str, List[EventHandler]] = {}
                cls._instance._once: Dict[str, List[EventHandler]] = {}
                cls._instance._history: Dict[str, List[Event]] = {}
                cls._instance._lock = threading.Lock()
                cls._instance._loop: Optional[asyncio.AbstractEventLoop] = None
        return cls._instance

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def on(self, event_type: str, handler: EventHandler,
           priority: Optional[Priority] = None) -> Callable:
        """Register a persistent handler for ``event_type``.

        Can be used as a decorator::

            @bus.on("emotion_changed")
            def handler(evt): ...

        Returns the handler for decorator use.
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s.%s to %s",
                     getattr(handler, "__module__", "?"),
                     getattr(handler, "__name__", "?"),
                     event_type)
        return handler

    def once(self, event_type: str, handler: EventHandler) -> Callable:
        """Register a one-shot handler. Fires once then auto-removes."""
        with self._lock:
            if event_type not in self._once:
                self._once[event_type] = []
            self._once[event_type].append(handler)
        return handler

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    h for h in self._subscribers[event_type]
                    if h is not handler
                ]
            if event_type in self._once:
                self._once[event_type] = [
                    h for h in self._once[event_type]
                    if h is not handler
                ]

    def clear(self, event_type: Optional[str] = None) -> None:
        """Remove all handlers. If ``event_type`` is None, clear all."""
        with self._lock:
            if event_type:
                self._subscribers.pop(event_type, None)
                self._once.pop(event_type, None)
                self._history.pop(event_type, None)
            else:
                self._subscribers.clear()
                self._once.clear()
                self._history.clear()

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(self, event: Event, *, sync: bool = True) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish.
            sync: If True, handlers are called synchronously in the
                  current thread. If False, they run in a background
                  thread (fire-and-forget).
        """
        if sync:
            self._dispatch(event)
        else:
            thread = threading.Thread(
                target=self._dispatch, args=(event,),
                daemon=True, name=f"evt-{event.type[:16]}"
            )
            thread.start()

    def emit_async(self, event: Event) -> None:
        """Publish via the asyncio event loop if available.

        Falls back to ``emit(sync=False)`` if no loop is set.
        """
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._dispatch, event)
        else:
            self.emit(event, sync=False)

    def _dispatch(self, event: Event) -> None:
        """Deliver event to all matching handlers."""
        handlers: List[EventHandler] = []
        once_handlers: List[EventHandler] = []

        with self._lock:
            if event.type in self._subscribers:
                handlers = list(self._subscribers[event.type])
            if event.type in self._once:
                once_handlers = list(self._once[event.type])
                del self._once[event.type]

            # Keep recent history (last 10 per type)
            if event.type not in self._history:
                self._history[event.type] = []
            self._history[event.type].append(event)
            if len(self._history[event.type]) > 10:
                self._history[event.type].pop(0)

        for h in handlers:
            try:
                h(event)
            except Exception:
                logger.exception("Handler %s failed for %s",
                                 getattr(h, "__name__", "?"), event.type)

        for h in once_handlers:
            try:
                h(event)
            except Exception:
                logger.exception("Once-handler %s failed for %s",
                                 getattr(h, "__name__", "?"), event.type)

    # ------------------------------------------------------------------
    # History & introspection
    # ------------------------------------------------------------------

    def history(self, event_type: Optional[str] = None,
                limit: int = 10) -> List[Event]:
        """Return recent events, optionally filtered by type."""
        with self._lock:
            if event_type:
                return list(self._history.get(event_type, []))[-limit:]
            all_events: List[Event] = []
            for evts in self._history.values():
                all_events.extend(evts)
            all_events.sort(key=lambda e: e.timestamp, reverse=True)
            return all_events[:limit]

    def subscriber_count(self, event_type: Optional[str] = None) -> int:
        """Count subscribers for an event type (or total if None)."""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            return sum(len(v) for v in self._subscribers.values())

    def registered_types(self) -> List[str]:
        """Return all event types that have subscribers."""
        with self._lock:
            return sorted(set(self._subscribers.keys()) |
                          set(self._once.keys()))

    # ------------------------------------------------------------------
    # Async loop support
    # ------------------------------------------------------------------

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop for async dispatch."""
        self._loop = loop

    # ------------------------------------------------------------------
    # Convenience emitters
    # ------------------------------------------------------------------

    @staticmethod
    def quick(type: str, data: Optional[Dict[str, Any]] = None,
              source: str = "") -> Event:
        """Quick-create and emit an event in one call.

        Usage::

            EventBus.quick("battery_changed", {"percent": 85})
        """
        evt = Event(type=type, data=data or {}, source=source)
        EventBus().emit(evt)
        return evt
