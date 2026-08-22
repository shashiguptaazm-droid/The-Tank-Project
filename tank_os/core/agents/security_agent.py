"""TankOS Security Agent — intrusion detection, surveillance, auth, e-stop."""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult
from tank_os.core.security_manager import SecurityManager


class SecurityAgent(BaseAgent):
    name = "security"
    description = "Intrusion detection, surveillance, auth, e-stop"

    def __init__(self) -> None:
        super().__init__()
        self._security = SecurityManager()
        self._capabilities = ["authenticate", "estop", "surveillance",
                              "check_security", "lock", "unlock"]

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        p = params or {}
        if task == "authenticate":
            token = p.get("token", "")
            ok = self._security.authenticate(token)
            return AgentResult(success=ok, data={"authenticated": ok})
        elif task == "estop":
            latch = p.get("latch", True)
            self._security.estop(latch)
            return AgentResult(success=True, data={"estop": self._security.is_estop})
        elif task == "surveillance":
            active = self._security.toggle_surveillance()
            return AgentResult(success=True, data={"surveillance": active})
        elif task == "check_security":
            return AgentResult(success=True, data={
                "estop": self._security.is_estop,
                "surveillance": self._security.is_surveillance_active,
                "authenticated": self._security.is_authenticated,
            })
        return AgentResult(success=False, error=f"Unknown task: {task}")


