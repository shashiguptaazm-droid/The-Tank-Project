"""TankOS Coding Agent — code analysis, meta store queries, diagnostics, refactoring."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult


class CodingAgent(BaseAgent):
    name = "coding"
    description = "Code analysis, meta store queries, diagnostics, refactoring"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities = ["analyze_code", "query_meta", "diagnose",
                              "search_code", "check_health", "refactor"]
        self._meta_available = False
        self._check_meta()

    def _check_meta(self) -> None:
        try:
            from tank_os.core.settings_manager import SettingsManager
            SettingsManager()
            self._meta_available = True
        except ImportError:
            self._meta_available = False

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        p = params or {}
        if task == "analyze_code":
            path = p.get("path", "")
            try:
                content = Path(path).read_text() if path else ""
                return AgentResult(success=True, data={
                    "path": path,
                    "length": len(content) if content else 0,
                    "lines": content.count("\n") if content else 0,
                })
            except Exception as exc:
                return AgentResult(success=False, error=str(exc))
        elif task == "query_meta":
            query = p.get("query", "")
            kind = p.get("kind", "code")
            return AgentResult(success=True, data={
                "kind": kind, "query": query,
                "meta_available": self._meta_available,
                "note": "Full meta store integration: TODO",
            })
        elif task == "diagnose":
            from tank_os.core.diagnostics_manager import DiagnosticsManager
            summary = DiagnosticsManager().summary()
            return AgentResult(success=True, data=summary)
        elif task == "search_code":
            return AgentResult(success=True, data={
                "query": p.get("query", ""),
                "meta_available": self._meta_available,
            })
        return AgentResult(success=False, error=f"Unknown task: {task}")



