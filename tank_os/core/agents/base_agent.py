"""
TankOS Base Agent — foundation for all specialized AI agents.

Every agent extends BaseAgent, registers with AgentRegistry, and
communicates through the Event Bus. Agents can delegate tasks to
each other via the AgentCoordinator.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus


class AgentStatus(Enum):
    IDLE = auto()
    BUSY = auto()
    WAITING = auto()
    ERROR = auto()
    SHUTDOWN = auto()


@dataclass
class AgentResult:
    """Result from an agent's execution."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0
    agent_name: str = ""
    task_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "agent_name": self.agent_name,
            "task_id": self.task_id,
        }


class BaseAgent:
    """Abstract base for all specialized AI agents.

    Subclasses MUST define:
    - name: str — unique agent identifier
    - description: str — what this agent does

    Subclasses SHOULD override:
    - initialize() — setup resources, register event handlers
    - execute(task: str, params: dict) -> AgentResult — main work method
    - shutdown() — cleanup
    """

    name: str = "base_agent"
    description: str = "Base AI agent"

    def __init__(self) -> None:
        self.log = logging.getLogger(f"tank_os.agent.{self.name}")
        self.bus = EventBus()
        self._status = AgentStatus.IDLE
        self._lock = threading.Lock()
        self._current_task: str = ""
        self._start_time: float = 0.0
        self._capabilities: List[str] = []
        self._confidence: float = 1.0

    def initialize(self) -> None:
        """Set up the agent. Register event handlers, connect to services."""
        self.log.info("Agent %s initialized", self.name)

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute a task and return a result.

        Args:
            task: The task name/type to execute
            params: Optional parameters dict

        Returns:
            AgentResult with success/failure and data
        """
        raise NotImplementedError(
            f"{type(self).__name__}.execute() must be overridden"
        )

    def shutdown(self) -> None:
        """Clean up resources when agent is unloaded."""
        self._status = AgentStatus.SHUTDOWN
        self.log.info("Agent %s shut down", self.name)

    # ------------------------------------------------------------------
    # Status & capabilities
    # ------------------------------------------------------------------

    @property
    def status(self) -> AgentStatus:
        with self._lock:
            return self._status

    @property
    def current_task(self) -> str:
        with self._lock:
            return self._current_task

    @property
    def capabilities(self) -> List[str]:
        return list(self._capabilities)

    @property
    def is_available(self) -> bool:
        with self._lock:
            return self._status == AgentStatus.IDLE

    def can_handle(self, task: str) -> Tuple[bool, float]:
        """Check if this agent can handle a task.

        Returns (can_handle: bool, confidence: 0.0-1.0).
        """
        return task in self._capabilities, self._confidence

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def _run_task(self, task: str,
                  params: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Run a task with status tracking."""
        start = time.time()
        task_id = str(uuid.uuid4())[:8]

        with self._lock:
            self._status = AgentStatus.BUSY
            self._current_task = task
            self._start_time = start

        self.bus.emit(Event("agent_task_started", {
            "agent": self.name, "task": task, "id": task_id,
        }))

        try:
            result = self.execute(task, params or {})
            result.agent_name = self.name
            result.task_id = task_id
            result.duration_ms = (time.time() - start) * 1000
        except Exception as exc:
            self.log.exception("Agent %s failed task %s", self.name, task)
            result = AgentResult(
                success=False, error=str(exc),
                agent_name=self.name, task_id=task_id,
                duration_ms=(time.time() - start) * 1000,
            )

        with self._lock:
            self._status = AgentStatus.IDLE
            self._current_task = ""

        self.bus.emit(Event("agent_task_completed", {
            "agent": self.name, "task": task, "id": task_id,
            "success": result.success, "duration_ms": result.duration_ms,
        }))

        return result

    def report_error(self, error: str) -> None:
        """Report an error state."""
        with self._lock:
            self._status = AgentStatus.ERROR
        self.bus.emit(Event("agent_error", {
            "agent": self.name, "error": error,
        }))
        self.log.error("Agent %s error: %s", self.name, error)
