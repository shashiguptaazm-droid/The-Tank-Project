"""BaseTask + TaskRegistry.

The registry is a process-wide singleton (so external callers like
``tank_command_bridge`` can pick up tasks without an explicit import).
Adding tasks should ONLY happen at module import time so the
registry is stable before any robot traffic arrives.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .intent import Context, Intent, Result


@dataclass
class BaseTask:
    """Subclass and decorate with :func:`register`."""

    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters_schema: Dict = field(default_factory=lambda: {"type": "object"})

    # Subclass internals
    patterns: List[Tuple[re.Pattern, float]] = field(default_factory=list)
    confidence_threshold: float = 0.4

    # ---------------- subclass API ----------------
    def can_handle(self, intent: Intent) -> Tuple[bool, float]:
        """Return ``(matched, confidence)`` for ``intent``.

        Default impl: regex-match each of ``self.patterns`` against the
        lowercase text and take the maximum confidence. Override for
        tasks that need richer slot-filling.
        """
        if not intent.text:
            return False, 0.0
        best = 0.0
        for pat, conf in self.patterns:
            if pat.search(intent.text):
                best = max(best, float(conf))
        return best > 0.0, best

    def extract_params(self, intent: Intent) -> Dict:
        """Hook for slot-filling. Default: return empty dict so empty
        tasks pass through."""
        return {}

    def run(self, intent: Intent, ctx: Context) -> Result:           # pragma: no cover
        raise NotImplementedError(
            f"{self.__class__.__name__}.run() must be overridden"
        )


# --------------------------------------------------------------------------- #
# Registry singleton
# --------------------------------------------------------------------------- #

class TaskRegistry:
    """Process-global map of task name -> BaseTask instance.

    Thread-safe ``register`` + ``get`` so speculative imports from
    ``tank_command_bridge`` don't race with the task modules during
    package import."""

    _instance: Optional["TaskRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "TaskRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tasks = {}  # type: ignore[attr-defined]
                cls._instance._registry_lock = threading.Lock()  # type: ignore[attr-defined]
            return cls._instance

    def register(self, task: BaseTask) -> None:
        if not task.name:
            raise ValueError("BaseTask.name must be set before register()")
        with self._registry_lock:
            existing = self._tasks.get(task.name)
            if existing is not None and existing.__class__ == task.__class__:
                # Idempotent registration (Pytest collection + first import).
                return
            self._tasks[task.name] = task

    def unregister(self, name: str) -> None:
        with self._registry_lock:
            self._tasks.pop(name, None)

    def get(self, name: str) -> Optional[BaseTask]:
        return self._tasks.get(name)

    def all(self) -> List[BaseTask]:
        with self._registry_lock:
            return list(self._tasks.values())

    def manifest(self) -> Dict:
        """Return a tool-shaped manifest suitable for merging into
        ``tank_command_bridge.manifest_json()``."""
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "tags": ["task"] + t.tags,
                    "request_body": {
                        "type": "object",
                        "required": ["audit_id", "params"],
                        "properties": {
                            "audit_id": {
                                "type": "string",
                                "format": "uuid",
                                "description":
                                    "client-generated UUIDv4 for "
                                    "audit log",
                            },
                            "params": t.parameters_schema,
                        },
                    },
                    "parameters": t.parameters_schema,
                    "rate_class": "write",
                }
                for t in self.all()
            ],
        }


def register(cls) -> BaseTask:
    """Class decorator that registers a Task subclass into the global
    registry. Use at module top of each task module::

        @register
        class ComeToOwnerTask(BaseTask):
            name = "come_to_owner"
            ...
    """
    instance = cls()
    TaskRegistry().register(instance)
    return instance
