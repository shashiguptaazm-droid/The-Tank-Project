"""Intent / Context / Result dataclasses for the tank_task framework.

Pure-Python (no rclpy imports) so pipelines and tests can build,
match, and route intents on benches without ROS.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


# Pattern used by TaskRouter to identify decision-append audit IDs.
# Project convention from STATUS.md §9 rule 3.
_DEC_ID_PATTERN = re.compile(r"^[A-Z0-9_-]{2,32}$")


@dataclass
class Intent:
    """A single user/shell intent routed to a Task."""

    raw_text: str
    source: str = "voice"                          # 'voice' or 'api'
    confidence: float = 1.0                       # set by classifier
    params: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=lambda: time.time())

    @property
    def text(self) -> str:
        return (self.raw_text or "").strip().lower()


@dataclass
class Context:
    """Per-task execution context. Holds publishers + result sink.

    Each task is started with a Context built by the TaskRouter so
    tasks never need to construct their own rclpy publishers. Tests
    hand-build Contexts with NullHal-style objects.
    """

    publish_cmd_vel: Optional[Callable[[float, float], None]] = None
    publish_estop:   Optional[Callable[[bool], None]]      = None
    publish_patrol:  Optional[Callable[[str], bool]]      = None
    publish_dock_enable: Optional[Callable[[bool], None]] = None
    publish_pan_tilt: Optional[Callable[[float, float], None]] = None
    publish_assistant_text: Optional[Callable[[str], None]]    = None
    publish_meta_decision: Optional[Callable[[dict], None]]    = None
    publish_task_status:   Optional[Callable[[dict], None]]    = None
    ros_node: Any = None                              # optional Node ref


@dataclass
class Result:
    """Success/failure of one task run."""

    success: bool = True
    message: str = ""                              # capped to 200 chars
    data: Optional[Dict[str, Any]] = None        # task-specific

    def clipped(self, max_chars: int = 200) -> "Result":
        if len(self.message) > max_chars:
            object.__setattr__(self, "message",
                                self.message[: max_chars - 1] + "\u2026")
        return self


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_decision_id() -> str:
    """``DEC-T-<hex>`` audit id (project convention)."""
    candidate = "DEC-T-" + uuid.uuid4().hex[:8]
    if not _DEC_ID_PATTERN.match(candidate):
        # Fallback to a slightly longer id just in case of collision.
        candidate = "DEC-T-" + uuid.uuid4().hex[:12]
    return candidate


def persist_event(ctx: Context, intent: Intent, result: Result) -> None:
    """Mirror a task execution into tank_meta via /meta/decision_append.

    DB-first → JSON-second pattern lives in meta_node; we just publish
    the JSON envelope here. ``problem`` field is clipped to 1 KB and
    ``solution`` to 2 KB by meta_node before writing, so we keep
    on-the-wire payloads under the per-field caps to keep the file sane.
    """
    if not ctx.publish_meta_decision:
        return
    payload = {
        "id": make_decision_id(),
        "problem":  f"task '{intent.raw_text[:1000]}'",
        "reason":   f"source={intent.source} confidence={intent.confidence:.2f}",
        "solution": (result.message or "")[:2000],
        "result":   "success" if result.success else "failure",
        "ts":       intent.ts,
    }
    try:
        ctx.publish_meta_decision(json.dumps(payload))
    except Exception:
        # never crash the task on a persist hiccup
        pass


def is_valid_decision_id(value: str) -> bool:
    return bool(_DEC_ID_PATTERN.match(value or ""))
