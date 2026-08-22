"""TankOS AI Manager — provider registry + dispatch.

Concrete LLM providers are plugged in at runtime via
:meth:`AIManager.register_provider`. A :class:`LocalStubProvider` is
always registered so the bot can degrade gracefully when no model is
loaded — useful for benches, CI, and offline reload scenarios.

Architecture
------------
``AIProvider`` (abstract) → registry → dispatch (``chat``/``stream``).

Lower-level concrete providers live elsewhere:
    * ``tank_assistant.llm_node`` — local llama.cpp wrapper (ROS).
    * ``tank_assistant.external_llm_client`` — OpenAI / Anthropic /
      Freebuff providers (ROS).

Either of those may import this module and call
``AIManager.register_provider(name, adapter)`` once their model is
ready, so the rest of TankOS can hit it via ``ai_manager.chat(...)``
without depending on ROS.

Events emitted on the EventBus:
    ai_request_started     — text + provider queued.
    ai_token_received      — streaming chunk.
    ai_response_complete   — full reply + provider + duration.
    ai_error               — exception info from a provider call.
    ai_provider_changed    — default provider swapped.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.settings_manager import SettingsManager

logger = logging.getLogger("tank_os.ai_manager")


# ───────────────────────────────────────────────────────────────────────────
# Exceptions + dataclasses
# ───────────────────────────────────────────────────────────────────────────

class AIProviderError(RuntimeError):
    """Raised by providers that fail to satisfy a request."""


@dataclass
class AIRequest:
    """An incoming request to the AI layer."""

    id: str
    text: str
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 512
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class AIResponse:
    """Provider-agnostic response shape."""

    text: str
    provider: str
    duration_ms: float
    request_id: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ───────────────────────────────────────────────────────────────────────────
# Provider abstract base
# ───────────────────────────────────────────────────────────────────────────

class AIProvider(ABC):
    """Abstract interface every AI provider must satisfy."""

    name: str = ""

    def __init__(self, name: str) -> None:
        self.name = name or type(self).__name__

    @abstractmethod
    def chat(self, text: str, *,
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 512,
             **kwargs: Any) -> str:
        """Send a single-shot prompt and return the response text."""

    def stream(self, text: str, *,
               system_prompt: Optional[str] = None,
               temperature: float = 0.7,
               max_tokens: int = 512,
               **kwargs: Any) -> Generator[str, None, None]:
        """Default non-streaming generator fallback."""
        yield self.chat(text, system_prompt=system_prompt,
                        temperature=temperature, max_tokens=max_tokens,
                        **kwargs)

    def get_status(self) -> Dict[str, Any]:
        """Lightweight status snapshot — overridable."""
        return {"name": self.name, "available": True,
                "type": type(self).__name__}


# ───────────────────────────────────────────────────────────────────────────
# Bundled provider — LocalStubProvider (always available)
# ───────────────────────────────────────────────────────────────────────────

class LocalStubProvider(AIProvider):
    """Deterministic offline provider — echoes structured JSON.

    Used by default so the rest of TankOS can call ``chat`` without
    blowing up during benches / CI / first boot.
    """

    def __init__(self) -> None:
        super().__init__("local-stub")

    def chat(self, text: str, *,
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 512,
             **kwargs: Any) -> str:
        # Truncate to the requested token budget *very* loosely (4 ch/tok)
        budget = max(8, max_tokens) * 4
        reply = f"[stub] I heard: {text.strip()[: max(0, budget - 32)]}"
        return reply

    def get_status(self) -> Dict[str, Any]:
        return {"name": self.name, "available": True,
                "type": "stub", "offline": True}


class EchoProvider(AIProvider):
    """Tiniest possible provider — useful in tests."""

    def __init__(self) -> None:
        super().__init__("echo")

    def chat(self, text: str, **kwargs: Any) -> str:  # noqa: D401
        return text


# ───────────────────────────────────────────────────────────────────────────
# AIManager
# ───────────────────────────────────────────────────────────────────────────

class AIManager:
    """Singleton AI provider registry and dispatcher."""

    _instance: Optional["AIManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AIManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._settings = SettingsManager()
                cls._instance._providers: Dict[str, AIProvider] = {}
                cls._instance._default: Optional[str] = None
                cls._instance._history: List[AIRequest] = []
                cls._instance._responses: List[AIResponse] = []
                cls._instance._max_history = 50
                cls._instance._lock = threading.Lock()
                # Pre-register the always-available stub provider
                cls._instance._providers["local-stub"] = LocalStubProvider()
                cls._instance._default = "local-stub"
            return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Bind to settings; ensure default provider is selected."""
        self._default = self._settings.get("ai.provider", "local-stub")
        if self._default not in self._providers:
            logger.info("AI provider %s not registered; using local-stub",
                        self._default)
            self._default = "local-stub"
        logger.info(
            "AIManager initialized — default=%s, providers=%s",
            self._default, sorted(self._providers.keys()),
        )
        self._bus.emit(Event(
            "ai_initialized",
            {"default": self._default,
             "providers": sorted(self._providers.keys())},
            source="ai_manager",
        ))

    # ------------------------------------------------------------------
    # Provider registry
    # ------------------------------------------------------------------

    def register_provider(self, name: str,
                          provider: AIProvider,
                          *, set_default: bool = False) -> bool:
        """Add (or replace) a provider by name.

        If ``set_default`` is True (or this is the first provider
        besides ``local-stub``) and no default is set, this provider
        becomes the new default.
        """
        if not isinstance(provider, AIProvider):
            raise TypeError(
                f"provider must subclass AIProvider, got {type(provider).__name__}"
            )
        if not name:
            raise ValueError("provider name must be a non-empty string")
        # Mirror the provider's own name attribute if it differs
        if not provider.name:
            provider.name = name
        else:
            # Don't allow surprising name mismatches
            name = provider.name
        with self._lock:
            replaced = name in self._providers
            self._providers[name] = provider
            if set_default or self._default in (None, "local-stub"):
                self._default = name
        self._bus.emit(Event(
            "ai_provider_changed",
            {"name": name, "replaced": replaced, "default": self._default},
            source="ai_manager",
        ))
        logger.info("Registered AI provider: %s%s",
                    name, " (now default)" if self._default == name else "")
        return True

    def unregister_provider(self, name: str) -> bool:
        """Remove a provider. ``local-stub`` is never removed."""
        if name == "local-stub":
            logger.debug("Refusing to unregister local-stub provider")
            return False
        with self._lock:
            if name not in self._providers:
                return False
            del self._providers[name]
            if self._default == name:
                self._default = "local-stub"
        self._bus.emit(Event(
            "ai_provider_changed",
            {"name": name, "removed": True, "default": self._default},
            source="ai_manager",
        ))
        return True

    def list_providers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.get_status() for p in self._providers.values()]

    def provider_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            prov = self._providers.get(name or self._default or "")
            if prov is None:
                return {"available": False, "name": name or ""}
            return prov.get_status()

    def get_provider(self, name: str):
        """Return the raw ``AIProvider`` instance for ``name``, or ``None``.

        Useful for warmup / preload routines that need access to the
        actual provider object (e.g. calling ``ensure_loaded()`` on a
        ``LocalLlamaProvider``).
        """
        with self._lock:
            return self._providers.get(name)

    def set_default(self, name: str) -> bool:
        """Switch default provider. Must already be registered."""
        with self._lock:
            if name not in self._providers:
                return False
            self._default = name
        self._bus.emit(Event(
            "ai_provider_changed",
            {"name": name, "default": name},
            source="ai_manager",
        ))
        return True

    @property
    def default_provider(self) -> str:
        return self._default or "local-stub"

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def chat(self, text: str, *, provider: Optional[str] = None,
             system_prompt: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             **kwargs: Any) -> AIResponse:
        """Dispatch a single-shot chat request and return :class:`AIResponse`."""
        req = AIRequest(
            id=f"ai_{uuid.uuid4().hex[:10]}",
            text=text,
            provider=provider,
            system_prompt=system_prompt,
            temperature=(temperature
                         if temperature is not None
                         else float(self._settings.get("ai.temperature", 0.7))),
            max_tokens=(max_tokens
                        if max_tokens is not None
                        else int(self._settings.get("ai.max_tokens", 512))),
        )
        return self._dispatch(req)

    def _dispatch(self, req: AIRequest) -> AIResponse:
        chosen_name = req.provider or self._default or "local-stub"
        with self._lock:
            prov = self._providers.get(chosen_name)
            if prov is None:
                # fall back to local-stub
                prov = self._providers["local-stub"]
                chosen_name = "local-stub"
        self._record_request(req)
        self._bus.emit(Event(
            "ai_request_started",
            {"id": req.id, "provider": chosen_name, "text": req.text},
            source="ai_manager", priority=Priority.HIGH,
        ))
        start = time.time()
        try:
            text = prov.chat(
                req.text,
                system_prompt=req.system_prompt,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
        except Exception as exc:
            self._bus.emit(Event(
                "ai_error",
                {"id": req.id, "provider": chosen_name,
                 "error": str(exc), "type": type(exc).__name__},
                source="ai_manager",
            ))
            logger.warning("Provider %s raised %s during chat(): %s",
                           chosen_name, type(exc).__name__, exc)
            raise AIProviderError(
                f"{chosen_name}: {exc}"
            ) from exc
        elapsed_ms = (time.time() - start) * 1000
        resp = AIResponse(
            text=text, provider=chosen_name, duration_ms=elapsed_ms,
            request_id=req.id,
        )
        self._record_response(resp)
        self._bus.emit(Event(
            "ai_response_complete",
            {"id": req.id, "provider": chosen_name,
             "text": text, "duration_ms": elapsed_ms},
            source="ai_manager",
        ))
        return resp

    def stream(self, text: str, *, provider: Optional[str] = None,
               **kwargs: Any) -> Generator[str, None, AIResponse]:
        """Stream tokens, then yield a final response summary.

        Each ``yield`` is a token chunk from the provider's
        :meth:`stream` method. The terminal ``return`` is the
        aggregated :class:`AIResponse`.
        """
        req = AIRequest(
            id=f"ai_{uuid.uuid4().hex[:10]}",
            text=text, provider=provider,
        )
        chosen_name = req.provider or self._default or "local-stub"
        with self._lock:
            prov = self._providers.get(chosen_name) or self._providers[
                "local-stub"
            ]
            if prov is self._providers["local-stub"]:
                chosen_name = "local-stub"
        self._record_request(req)
        self._bus.emit(Event(
            "ai_request_started",
            {"id": req.id, "provider": chosen_name, "text": req.text,
             "stream": True},
            source="ai_manager", priority=Priority.HIGH,
        ))
        start = time.time()
        chunks: List[str] = []
        try:
            for chunk in prov.stream(text, **kwargs):
                chunks.append(chunk)
                self._bus.emit(Event(
                    "ai_token_received",
                    {"id": req.id, "chunk": chunk},
                    source="ai_manager",
                ))
                yield chunk
        except Exception as exc:
            self._bus.emit(Event(
                "ai_error",
                {"id": req.id, "provider": chosen_name,
                 "error": str(exc), "type": type(exc).__name__},
                source="ai_manager",
            ))
            raise AIProviderError(f"{chosen_name}: {exc}") from exc
        elapsed_ms = (time.time() - start) * 1000
        full = "".join(chunks)
        resp = AIResponse(
            text=full, provider=chosen_name, duration_ms=elapsed_ms,
            request_id=req.id,
        )
        self._record_response(resp)
        self._bus.emit(Event(
            "ai_response_complete",
            {"id": req.id, "provider": chosen_name,
             "text": full, "duration_ms": elapsed_ms, "stream": True},
            source="ai_manager",
        ))

    # ------------------------------------------------------------------
    # History + introspection
    # ------------------------------------------------------------------

    def recent_requests(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            out = list(self._history[-limit:])
        return [{"id": r.id, "provider": r.provider, "text": r.text,
                 "created_at": r.created_at} for r in out]

    def recent_responses(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            out = list(self._responses[-limit:])
        return [{"id": r.request_id, "provider": r.provider,
                 "text": r.text, "duration_ms": r.duration_ms}
                for r in out]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            provider_names = sorted(self._providers.keys())
        return {
            "default": self._default,
            "providers": provider_names,
            "requests": len(self._history),
            "responses": len(self._responses),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _record_request(self, req: AIRequest) -> None:
        with self._lock:
            self._history.append(req)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def _record_response(self, resp: AIResponse) -> None:
        with self._lock:
            self._responses.append(resp)
            if len(self._responses) > self._max_history:
                self._responses = self._responses[-self._max_history:]
