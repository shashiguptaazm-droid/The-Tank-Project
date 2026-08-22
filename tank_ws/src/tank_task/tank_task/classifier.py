"""Intent classifier — picks the best task + fills params.

Layered:
1. Regex ``can_handle`` (confidence 0..1).
2. Best-confidence wins across all registered tasks. Ties broken by
   ``first registered``.
3. If confidence < 0.4 AND an "uncertain" sink is provided, emit
   ``/assistant/uncertain`` so the existing
   ``tank_assistant.external_llm_client`` pipeline can fill slots via
   Freebuff/OpenAI/Anthropic instead of staying silent.

Returns ``(task, intent)`` so the caller can ``run()`` directly.
``intent.confidence`` is set from the chosen task's match score.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .base import BaseTask, TaskRegistry
from .intent import Intent


# Threshold under which the classifier escalates to external LLM.
DEFAULT_THRESHOLD = 0.4


@dataclass
class ClassificationResult:
    task: Optional[BaseTask]
    intent: Intent
    escalated: bool = False                     # published /assistant/uncertain


def classify(intent: Intent,
             registry: Optional[TaskRegistry] = None,
             threshold: float = DEFAULT_THRESHOLD,
             publish_uncertain: Optional[Callable[[Intent], None]] = None
             ) -> ClassificationResult:
    """Pick a task for ``intent``.

    ``publish_uncertain`` is invoked when the best match confidence is
    below ``threshold`` so the existing
    ``tank_assistant.external_llm_client`` can decide whether to
    call out to Freebuff/OpenAI/Anthropic. If ``None`` the escalation
    is logged-only.
    """
    registry = registry or TaskRegistry()
    if not intent.text:
        return ClassificationResult(task=None, intent=intent)

    ranked: List[Tuple[BaseTask, float]] = []
    for task in registry.all():
        try:
            matched, confidence = task.can_handle(intent)
        except Exception:
            matched, confidence = False, 0.0
        if matched:
            ranked.append((task, float(confidence)))
    ranked.sort(key=lambda tc: tc[1], reverse=True)

    if not ranked:
        return ClassificationResult(task=None, intent=intent)

    chosen, confidence = ranked[0]
    filled = Intent(
        raw_text=intent.raw_text,
        source=intent.source,
        confidence=confidence,
        params={**chosen.extract_params(intent), **(intent.params or {})},
        ts=intent.ts,
    )

    if confidence < threshold:
        if publish_uncertain is not None:
            try:
                publish_uncertain(filled)
            except Exception:
                pass
        return ClassificationResult(
            task=None, intent=filled, escalated=True)

    return ClassificationResult(task=chosen, intent=filled)


# --------------------------------------------------------------------------- #
# Module-level keep-alive lock (used by TaskRouter so two bridge/voice
# callers can't run tasks concurrently)
# --------------------------------------------------------------------------- #

class TaskLock:
    """Single-flight task lock shared across voice + bridge invocations.

    Acquirers should respect the timed try-acquire so a wedged task
    can't permanently block the robot."""

    def __init__(self, timeout_sec: float = 30.0) -> None:
        self._lock = threading.RLock()
        self._holder: Optional[str] = None
        self._acquired_at: Optional[float] = None
        self.timeout_sec = float(timeout_sec)

    def try_acquire(self, name: str) -> bool:
        import time
        now = time.monotonic()
        if self._lock.acquire(blocking=False):
            # Auto-release stale holds longer than the timeout so a
            # crashed task doesn't permanently lock the robot out.
            if self._acquired_at and (now - self._acquired_at) > self.timeout_sec:
                try:
                    if self._lock.locked():
                        self._lock.release()
                except Exception:
                    pass
            self._holder = name
            self._acquired_at = now
            return True
        return False

    def release(self) -> None:
        with self._lock:
            self._holder = None
            self._acquired_at = None

    def holder(self) -> Optional[str]:
        return self._holder
