"""Rotation orchestrator — weighted round-robin across healthy providers.

The default evolution mode. Picks providers in priority order (cheap
fast ones first), invokes the first that the circuit breaker permits,
and falls through to the next on transient failure.

Model discovery integration
---------------------------
When a ``fallback_catalog`` is provided (from :class:`ModelDiscoverer`),
the orchestrator tries discovered alternative models for a provider
*before* moving to the next provider.  On success the cached provider
is permanently healed with the working model name.

Failure handling
----------------
- HTTP 429 / 401 / 5xx → record failure on the breaker, retry next.
- Validation / unknown error → also retry (treat as transient).
- All providers exhausted → return an :class:`OrchestratorResult` with
  ``error`` set; the caller can decide to escalate.
"""
from __future__ import annotations

import logging
import random
import threading
from typing import Any, Dict, List, Optional, Tuple

from ..health import health_monitor
from ..providers.registry import (
    DISABLED_PROVIDERS,
    available_providers,
    instantiate,
    names_in_priority_order,
)
from .base import BaseOrchestrator, OrchestratorResult


_LOG = logging.getLogger("tank_assistant.evolution.rotation")


class RotationOrchestrator(BaseOrchestrator):
    """Walk the provider priority list; first healthy one wins."""

    name = "rotation"

    def __init__(self, *, providers: Optional[List[Any]] = None,
                 max_attempts: int = 4,  # limits *providers* tried, not model retries
                 jitter: bool = True,
                 fallback_catalog: Optional[Dict[str, List[str]]] = None,
                 **kwargs: Any) -> None:
        super().__init__(providers=providers, **kwargs)
        self._max_attempts = max(1, int(max_attempts))
        self._jitter = bool(jitter)
        self._lock = threading.Lock()
        # Cache: name -> instance, created lazily on first use.
        self._cache: Dict[str, Any] = {}
        # Discovered fallback models: provider_name -> [model_id, ...]
        self._fallback_catalog: Dict[str, List[str]] = fallback_catalog or {}

    # ── Public API ──────────────────────────────────────────────────────

    def available_provider_names(self, *, configured_only: bool = False) -> List[str]:
        """Names of providers the orchestrator can dispatch to.

        Parameters
        ----------
        configured_only
            When ``True``, returns only providers whose API key has
            actually been loaded (regardless of whether the registry
            entry exists). When ``False`` (default), returns the full
            enabled list — useful for introspection.

        When ``self._providers`` is injected (test path), the injected
        list is always returned as-is — the caller explicitly provided
        those providers, so we trust they're usable.

        Public API — used by ``external_llm_client._EvolutionProvider``
        to decide whether to actually wire the provider.
        """
        if self._providers:
            return [p.name for p in self._providers
                    if p.name not in DISABLED_PROVIDERS]
        return [name for name, _ in self._ordered_providers(
            require_configured=configured_only)]

    def provider_count(self, *, configured_only: bool = False) -> int:
        """Cheap count — equivalent to ``len(available_provider_names(...))``."""
        return len(self.available_provider_names(configured_only=configured_only))

    def run(self, system: str, user: str,
            context: Optional[str] = None,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto") -> OrchestratorResult:
        order = self._ordered_providers()
        if not order:
            return OrchestratorResult(error="no providers available")

        # Snapshot of healthy subset, with jitter fallback to the full list.
        healthy = health_monitor.available_providers([n for n, _ in order])
        if not healthy:
            healthy = [n for n, _ in order]

        if self._jitter:
            # Small randomization at the front to spread load when several
            # providers are HEALTHY.
            front = healthy[: max(0, min(3, len(healthy) - 1))]
            random.shuffle(front)
            tail = healthy[len(front):]
            healthy = front + tail

        attempts = 0
        last_err: Optional[str] = None
        for name in healthy:
            if attempts >= self._max_attempts:
                break
            attempts += 1
            provider = self._get_provider(name)
            if provider is None or not provider.is_configured:
                continue
            if not health_monitor.can_attempt(name):
                continue

            # ── Model fallback: try default + discovered alternatives ──
            models_to_try = [getattr(provider, 'model', None)]
            fallbacks = self._fallback_catalog.get(name, [])
            # Add up to 3 discovered fallbacks, skipping the default
            for m in fallbacks[:3]:
                if m and m != models_to_try[0]:
                    models_to_try.append(m)
            models_to_try = [m for m in models_to_try if m]

            provider_success = False
            for mod in models_to_try:
                if hasattr(provider, 'model'):
                    provider.model = mod
                result = self._call_provider(
                    provider, system, user, context, tools, tool_choice)
                if result.error is None:
                    health_monitor.record_success(name)
                    _LOG.info("provider %s succeeded with model %s", name, mod)
                    return result
                last_err = result.error
                _LOG.debug("provider %s model %s failed: %s",
                           name, mod, result.error)

            # All models for this provider exhausted — record and try next
            health_monitor.record_failure(name)
            _LOG.debug("provider %s: all %d model(s) exhausted",
                       name, len(models_to_try))

        return OrchestratorResult(
            error=(last_err or "all providers failed"),
            providers_used=[],
        )

    # ── Internals ───────────────────────────────────────────────────────

    def _ordered_providers(self, *, require_configured: bool = False) -> List[Tuple[str, type]]:
        """Return ``[(name, class)]`` in priority order.

        Honours injected ``providers=`` (test path), registry priority,
        disabled filtering, and (when ``require_configured=True``) only
        those whose API key has been loaded.
        """
        if self._providers:
            return [(p.name, type(p)) for p in self._providers
                    if p.name not in DISABLED_PROVIDERS]
        configured = available_providers(require_configured=require_configured)
        priority = names_in_priority_order()
        seen: set[str] = set()
        out: List[Tuple[str, type]] = []
        for n in priority:
            if n in configured and n not in seen:
                out.append((n, configured[n]))
                seen.add(n)
        for n, cls in configured.items():
            if n not in seen:
                out.append((n, cls))
                seen.add(n)
        return out

    def _get_provider(self, name: str):
        with self._lock:
            inst = self._cache.get(name)
            if inst is not None:
                return inst
            # Check injected providers first (test / programmatic path)
            for p in self._providers:
                if p.name == name:
                    self._cache[name] = p
                    return p
            try:
                inst = instantiate(name)
            except Exception as exc:
                _LOG.debug("instantiate %s failed: %s", name, exc)
                return None
            self._cache[name] = inst
            return inst

    # Test hooks — let tests inject providers without touching the registry.
    def _set_test_provider(self, name: str, instance) -> None:
        with self._lock:
            self._cache[name] = instance

    def _clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # ── Model fallback API ─────────────────────────────────────────

    def set_fallback_catalog(self, catalog: Dict[str, List[str]]) -> None:
        """Update the fallback model catalog from discovery results.

        Called after :meth:`ModelDiscoverer.discover_all` to feed
        fresh model lists into the orchestrator.  Subsequent calls to
        :meth:`run` will try discovered alternatives when the default
        model fails.
        """
        with self._lock:
            self._fallback_catalog = dict(catalog)
            _LOG.info("fallback catalog updated: %d provider(s)",
                      len(self._fallback_catalog))

    @property
    def fallback_catalog(self) -> Dict[str, List[str]]:
        """Snapshot of the current fallback model catalog (read-only)."""
        with self._lock:
            return dict(self._fallback_catalog)
