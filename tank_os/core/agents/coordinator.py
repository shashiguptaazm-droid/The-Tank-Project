"""
TankOS Agent Coordinator — multi-agent collaboration engine.

Handles task delegation, knowledge sharing, collective review,
and orchestration across all specialized agents.
"""

from __future__ import annotations
import logging, threading, time, uuid
from typing import Any, Dict, List, Optional, Tuple
from tank_os.core.agents.base_agent import AgentResult, AgentStatus
from tank_os.core.agents.registry import AgentRegistry
from tank_os.core.event_bus import Event, EventBus


class AgentCoordinator:
    """Orchestrates multiple AI agents for complex tasks.

    The coordinator:
    1. Receives a task
    2. Finds the best agent(s) to handle it
    3. Delegates execution (single or multi-agent)
    4. Merges results from multiple agents
    5. Handles fallback and error recovery
    """

    _instance: Optional["AgentCoordinator"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AgentCoordinator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._registry = AgentRegistry()
                cls._instance._bus = EventBus()
                cls._instance._task_history: List[Dict[str, Any]] = []
            return cls._instance

    def delegate(self, task: str, params: Optional[Dict[str, Any]] = None,
                 preferred_agent: str = "") -> AgentResult:
        """Delegate a task to the best available agent.

        Args:
            task: Task name/type
            params: Optional parameters
            preferred_agent: If set, try this agent first

        Returns:
            AgentResult from the executing agent
        """
        candidates = self._registry.find_for_task(task)

        if preferred_agent:
            candidates.sort(key=lambda x: x[0] != preferred_agent)

        if not candidates:
            err = f"No agent available for task: {task}"
            self._log.error(err)
            return AgentResult(success=False, error=err)

        for agent_name, _ in candidates:
            agent = self._registry.get(agent_name)
            if agent and agent.is_available:
                self._log.info("Delegating %s to %s", task, agent_name)
                result = agent._run_task(task, params)
                self._record_history(agent_name, task, result)
                return result

        return AgentResult(success=False, error="All candidate agents are busy")

    def delegate_multi(self, task: str, params: Optional[Dict[str, Any]] = None,
                       min_votes: int = 1) -> List[AgentResult]:
        """Delegate a task to ALL capable agents and collect results.

        Useful for verification, consensus-building, or parallel processing.
        """
        candidates = self._registry.find_for_task(task)
        results: List[AgentResult] = []

        for agent_name, _ in candidates:
            agent = self._registry.get(agent_name)
            if agent and agent.is_available:
                result = agent._run_task(task, params)
                self._record_history(agent_name, task, result)
                results.append(result)
                if len(results) >= min_votes:
                    break

        return results

    def review_solution(self, task: str, proposed_result: AgentResult) -> List[AgentResult]:
        """Have other agents review a proposed solution.

        Finds agents OTHER than the one that produced the result
        and asks them to review the outcome.
        """
        reviews: List[AgentResult] = []
        for name, agent in self._registry.all().items():
            if name != proposed_result.agent_name and agent.is_available:
                review = agent._run_task(f"review:{task}", {
                    "proposed": proposed_result.to_dict(),
                })
                reviews.append(review)
        return reviews

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast an event to all agents via the event bus."""
        self._bus.emit(Event(event_type, data, source="agent_coordinator"))

    def shutdown_all(self) -> None:
        """Shut down all registered agents."""
        for agent in self._registry.all().values():
            agent.shutdown()

    def _record_history(self, agent_name: str, task: str,
                        result: AgentResult) -> None:
        entry = {
            "ts": time.time(),
            "agent": agent_name,
            "task": task,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
        self._task_history.append(entry)
        if len(self._task_history) > 1000:
            self._task_history = self._task_history[-500:]

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._task_history)

    @property
    def summary(self) -> Dict[str, Any]:
        total = len(self._task_history)
        successes = sum(1 for h in self._task_history if h["success"])
        by_agent: Dict[str, int] = {}
        for h in self._task_history:
            by_agent[h["agent"]] = by_agent.get(h["agent"], 0) + 1
        return {
            "total_tasks": total,
            "success_rate": round(successes / max(total, 1) * 100, 1),
            "agents_used": len(by_agent),
            "per_agent": by_agent,
            "last_task": self._task_history[-1] if self._task_history else None,
        }

    @property
    def _log(self):
        return logging.getLogger("tank_os.agent.coordinator")
