"""TankOS Health Agent — system monitoring, battery, diagnostics, predictive maintenance."""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult


class HealthAgent(BaseAgent):
    name = "health"
    description = "System monitoring, battery, diagnostics, predictive maintenance"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = ["check_health", "check_battery", "check_disk",
                              "check_uptime", "check_temperature", "check_all"]

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        from tank_os.core.diagnostics_manager import DiagnosticsManager
        from tank_os.core.power_manager import PowerManager
        from tank_os.core.storage_manager import StorageManager

        p = params or {}
        diag = DiagnosticsManager()
        power = PowerManager()
        storage = StorageManager()

        if task == "check_health":
            s = diag.summary()
            return AgentResult(success=True, data=s)
        elif task == "check_battery":
            return AgentResult(success=True, data={
                "percent": power.battery_percent,
                "charging": power.is_charging,
                "mode": power.performance_mode,
            })
        elif task == "check_disk":
            return AgentResult(success=True, data=storage.usage_summary())
        elif task == "check_uptime":
            d = diag.collect()
            uptime = d.get("uptime", 0)
            hours = uptime / 3600
            return AgentResult(success=True, data={
                "uptime_seconds": uptime,
                "uptime_hours": round(hours, 1),
            })
        elif task == "check_temperature":
            d = diag.collect()
            return AgentResult(success=True, data={
                "cpu_c": d.get("temperature", {}).get("cpu_c", "?"),
            })
        elif task == "check_all":
            s = diag.summary()
            s["battery"] = power.battery_percent
            s["charging"] = power.is_charging
            return AgentResult(success=True, data=s)
        return AgentResult(success=False, error=f"Unknown task: {task}")


