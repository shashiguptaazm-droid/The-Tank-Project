"""
TankOS Agent Registry — singleton registry of all AI agents.

Agents register themselves at import time. The registry tracks their
status, handles lookups by name or capability, and provides discovery
for the AgentCoordinator.
"""

from __future__ import annotations
import logging, threading
from typing import Any, Dict, List, Optional, Tuple
from tank_os.core.agents.base_agent import BaseAgent
from tank_os.core.event_bus import Event, EventBus


class AgentRegistry:
    _instance: Optional["AgentRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AgentRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._agents: Dict[str, BaseAgent] = {}
                cls._instance._bus = EventBus()
            return cls._instance

    def register(self, agent: BaseAgent) -> None:
        with AgentRegistry._lock:
            self._agents[agent.name] = agent
        agent.initialize()
        self._bus.emit(Event("agent_registered", {
            "name": agent.name,
            "capabilities": agent.capabilities,
        }))
        self.log.debug("Registered agent: %s", agent.name)

    def unregister(self, name: str) -> bool:
        agent = self._agents.pop(name, None)
        if agent:
            agent.shutdown()
            self._bus.emit(Event("agent_unregistered", {"name": name}))
            return True
        return False

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def find_for_task(self, task: str) -> List[Tuple[str, float]]:
        """Find all agents that can handle a task.

        Returns sorted list of (agent_name, confidence).
        """
        candidates = []
        for name, agent in self._agents.items():
            if agent.is_available:
                can, conf = agent.can_handle(task)
                if can:
                    candidates.append((name, conf))
        candidates.sort(key=lambda x: -x[1])
        return candidates

    def all(self) -> Dict[str, BaseAgent]:
        return dict(self._agents)

    def names(self) -> List[str]:
        return sorted(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)

    @property
    def log(self):
        return logging.getLogger("tank_os.agent.registry")
