"""Base orchestrator — abstract interface for the 4 evolution modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OrchestratorResult:
    """Standardized return shape from any orchestrator's ``run()``."""
    text: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    providers_used: List[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "tool_calls": self.tool_calls,
            "providers_used": self.providers_used,
            "elapsed_s": self.elapsed_s,
            "error": self.error,
        }


class BaseOrchestrator:
    """Abstract orchestrator.

    Subclasses implement :meth:`run`. The factory
    :func:`evolution.build_orchestrator` instantiates one of the four
    concrete subclasses based on a mode string.
    """

    name: str = "base"

    def __init__(self, *, providers: Optional[List[Any]] = None,
                 **kwargs: Any) -> None:
        self._providers = providers or []

    def run(self, system: str, user: str,
            context: Optional[str] = None,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto") -> OrchestratorResult:
        raise NotImplementedError(
            f"{type(self).__name__}.run() not implemented")

    def _call_provider(self, provider, system, user, context, tools,
                       tool_choice) -> OrchestratorResult:
        """Invoke a single provider with consistent error handling.

        Transient HTTP errors are returned as :class:`OrchestratorResult`
        with ``error`` set — callers (orchestrators) decide whether to
        retry or rotate. Programming errors (anything not
        ``httpx.HTTPError``) are re-raised so the breaker doesn't demote
        a provider because of OUR bug.
        """
        import time
        try:
            import httpx as _httpx
        except ImportError:                                  # pragma: no cover
            class _StubHttpxModule:
                class HTTPError(Exception):
                    pass
            _httpx = _StubHttpxModule
        started = time.monotonic()
        try:
            result = provider.prompt(
                system, user, context=context,
                tools=tools, tool_choice=tool_choice)
            return OrchestratorResult(
                text=(result.get("text") or ""),
                tool_calls=result.get("tool_calls") or [],
                providers_used=[provider.name],
                elapsed_s=time.monotonic() - started,
            )
        except _httpx.HTTPError as exc:
            return OrchestratorResult(
                providers_used=[provider.name],
                elapsed_s=time.monotonic() - started,
                error=f"http: {type(exc).__name__}: {str(exc)[:180]}",
            )
        # Programming errors propagate so the caller (and tests) can see
        # the bug instead of silently demoting a healthy provider.
