"""TankOS Notification Manager — animated, priority, persistent, grouped, speech-capable."""

from __future__ import annotations
import logging, threading, time, uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.notifications")


class Priority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Notification:
    id: str = ""
    title: str = ""
    message: str = ""
    priority: Priority = Priority.NORMAL
    source: str = ""
    icon: str = ""
    persistent: bool = False
    speech: bool = False
    timestamp: float = 0.0
    group: str = ""
    dismissed: bool = False
    action: Optional[Callable] = None


class NotificationManager:
    _instance: Optional["NotificationManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "NotificationManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._notifications: List[Notification] = []
                cls._instance._max_visible = 5
                cls._instance._bus = EventBus()
            return cls._instance

    def notify(self, title: str, message: str, priority: Priority = Priority.NORMAL,
               source: str = "", icon: str = "", persistent: bool = False,
               speech: bool = False, group: str = "",
               action: Optional[Callable] = None) -> Notification:
        n = Notification(
            id=f"notif_{uuid.uuid4().hex[:8]}",
            title=title, message=message, priority=priority, source=source,
            icon=icon, persistent=persistent, speech=speech, group=group,
            timestamp=time.time(), action=action,
        )
        with self._lock:
            self._notifications.insert(0, n)
            if len(self._notifications) > 50:
                self._notifications = self._notifications[:50]
        self._bus.emit(Event("notification", {
            "id": n.id, "title": title, "message": message,
            "priority": priority.name, "persistent": persistent, "speech": speech,
        }, source=source or "notification_manager"))
        return n

    def dismiss(self, notif_id: str) -> bool:
        with self._lock:
            for n in self._notifications:
                if n.id == notif_id:
                    n.dismissed = True
                    self._notifications.remove(n)
                    return True
        return False

    def dismiss_all(self) -> None:
        with self._lock:
            self._notifications.clear()

    def dismiss_group(self, group: str) -> None:
        with self._lock:
            self._notifications = [n for n in self._notifications if n.group != group]

    def active(self, max_count: Optional[int] = None) -> List[Notification]:
        with self._lock:
            result = sorted(self._notifications, key=lambda n: (n.priority, n.timestamp), reverse=True)
            if max_count: result = result[:max_count]
            return list(result)

    @property
    def count(self) -> int:
        with self._lock: return len(self._notifications)

    def success(self, title: str, message: str, **kw) -> Notification:
        return self.notify(title, message, Priority.NORMAL, **kw)

    def warning(self, title: str, message: str, **kw) -> Notification:
        return self.notify(title, message, Priority.HIGH, **kw)

    def error(self, title: str, message: str, **kw) -> Notification:
        return self.notify(title, message, Priority.CRITICAL, **kw)

    def info(self, title: str, message: str, **kw) -> Notification:
        return self.notify(title, message, Priority.LOW, **kw)
