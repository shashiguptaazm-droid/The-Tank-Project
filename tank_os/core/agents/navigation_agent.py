"""TankOS Navigation Agent — SLAM, path planning, waypoints, obstacle avoidance."""

from __future__ import annotations
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult
from tank_os.core.navigation_manager import NavigationManager


class NavigationAgent(BaseAgent):
    name = "navigation"
    description = "SLAM, path planning, waypoints, obstacle avoidance"

    def __init__(self) -> None:
        super().__init__()
        self._nav = NavigationManager()
        self._capabilities = ["navigate", "plan_route", "manage_waypoints",
                              "check_position", "explore", "return_home"]

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        p = params or {}
        if task == "navigate":
            target = p.get("target", "")
            waypoint_names = [w.name for w in self._nav.waypoints]
            if target in waypoint_names:
                self._nav.navigate_waypoint(target)
            else:
                self._nav.navigate_to(p.get("x", 0.0), p.get("y", 0.0))
            return AgentResult(success=True, data={"status": "navigating", "target": target})
        elif task == "plan_route":
            return AgentResult(success=True, data={
                "waypoints": [w.name for w in self._nav.waypoints],
                "current": {"x": self._nav.pose.x, "y": self._nav.pose.y},
            })
        elif task == "manage_waypoints":
            if p.get("action") == "add":
                self._nav.add_waypoint(p["name"], p.get("x", 0.0), p.get("y", 0.0))
            elif p.get("action") == "remove":
                self._nav.remove_waypoint(p.get("name", ""))
            return AgentResult(success=True, data={
                "waypoints": [{"name": w.name, "x": w.x, "y": w.y}
                              for w in self._nav.waypoints],
            })
        return AgentResult(success=False, error=f"Unknown task: {task}")



