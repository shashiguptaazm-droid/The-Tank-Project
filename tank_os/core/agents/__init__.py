"""
TankOS AI Agent Framework — specialized agents that collaborate under the AI Manager.

Hosts Navigation, Vision, Security, Coding, Health, and Companion agents
with a multi-agent collaboration engine for task delegation, knowledge
sharing, and collective review.
"""

from tank_os.core.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from tank_os.core.agents.registry import AgentRegistry
from tank_os.core.agents.coordinator import AgentCoordinator
from tank_os.core.agents.navigation_agent import NavigationAgent
from tank_os.core.agents.vision_agent import VisionAgent
from tank_os.core.agents.security_agent import SecurityAgent
from tank_os.core.agents.coding_agent import CodingAgent
from tank_os.core.agents.health_agent import HealthAgent
from tank_os.core.agents.companion_agent import CompanionAgent

__all__ = [
    "BaseAgent", "AgentResult", "AgentStatus",
    "AgentRegistry",
    "AgentCoordinator",
    "NavigationAgent",
    "VisionAgent",
    "SecurityAgent",
    "CodingAgent",
    "HealthAgent",
    "CompanionAgent",
]
