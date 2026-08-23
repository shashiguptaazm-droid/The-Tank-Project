"""Evolution Bridge — connects the evolution system to the AIManager.

Registers all configured evolution providers (Groq, Mistral, Cohere,
etc.) and a local GGUF provider as AIProvider adapters so the terminal
and other TankOS components can use real LLMs.

Also registers a **RotationAdapter** that wraps the
``RotationOrchestrator``, giving the terminal automatic circuit-breaker
fallback across all online providers.

Calling ``init_evolution_providers()`` at shell startup wires everything:

    from tank_os.core.evolution_bridge import init_evolution_providers
    init_evolution_providers()  # called once during TankShell.initialize()

Provider priority (cheapest/fastest first):
    1. Local GGUF (offline fallback — fastest)
    2. Groq (fast + free tier)
    3. Cerebras (fast)
    4. Mistral (good quality)
    5. Cohere (good quality)
    6. OpenRouter (broad model access)
    7. Cloudflare (free)
    8. Gemini (if quota available)
    9. Replicate (rate-limited free tier)
    10. DeepSeek (if key valid)
    11. Rotation adapter (umbrella — auto fallback across all)
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from tank_os.core.ai_manager import AIProvider, AIManager
from tank_os.core.local_llm_provider import LocalLlamaProvider

logger = logging.getLogger("tank_os.evolution_bridge")


# ── Adapter: wraps an evolution provider as an AIProvider ─────────────────

class EvolutionProviderAdapter(AIProvider):
    """Wraps a single evolution ``BaseHttpProvider`` as an ``AIProvider``.

    Maps ``chat(text, system_prompt, ...)`` to the evolution
    provider's ``prompt(system=system_prompt, user=text)``.
    """

    def __init__(self, name: str, provider: Any, *,
                 priority: int = 100) -> None:
        super().__init__(name)
        self._provider = provider
        self._priority = priority
        self._last_error: Optional[str] = None
        self._last_call_ms: float = 0.0
        self._success_count = 0
        self._fail_count = 0

    @property
    def is_configured(self) -> bool:
        return self._provider.is_configured if hasattr(
            self._provider, "is_configured") else bool(
                self._provider.api_key)

    def chat(self, text: str, *,
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 512,
             **kwargs: Any) -> str:
        start = time.time()
        try:
            result = self._provider.prompt(
                system=system_prompt or "",
                user=text,
                context=kwargs.get("context"),
            )
            elapsed_ms = (time.time() - start) * 1000
            self._last_call_ms = elapsed_ms
            self._success_count += 1
            text_out = ""
            if isinstance(result, dict):
                text_out = result.get("text", "")
            elif isinstance(result, str):
                text_out = result
            else:
                text_out = str(result)
            return text_out.strip() or self._fallback_text(text)
        except Exception as exc:
            self._last_error = str(exc)[:200]
            self._fail_count += 1
            logger.debug("%s failed: %s", self.name, exc)
            return self._fallback_text(text)

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "available": self.is_configured,
            "type": f"evolution:{type(self._provider).__name__}",
            "model": getattr(self._provider, "model", None),
            "configured": self.is_configured,
            "last_error": self._last_error,
            "last_call_ms": round(self._last_call_ms, 1),
            "successes": self._success_count,
            "failures": self._fail_count,
            "priority": self._priority,
        }

    def _fallback_text(self, original: str) -> str:
        return (
            f"[{self.name}] Provider returned no response. "
            f"Input: {original[:60]}"
        )


# ── Rotation Adapter: wraps the RotationOrchestrator ──────────────────────

class RotationAdapter(AIProvider):
    """Wraps the ``RotationOrchestrator`` as an AIProvider.

    Every ``chat()`` call goes through the orchestrator's circuit-breaker
    rotation logic, automatically falling back across all registered
    evolution providers.
    """

    def __init__(self, orchestrator: Any) -> None:
        super().__init__("rotation")
        self._orch = orchestrator

    def chat(self, text: str, *,
             system_prompt: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 512,
             **kwargs: Any) -> str:
        start = time.time()
        try:
            result = self._orch.run(
                system=system_prompt or "",
                user=text,
            )
            elapsed_ms = (time.time() - start) * 1000
            if result.error is None and result.text:
                return result.text.strip()
            if result.error:
                logger.debug("rotation failed: %s", result.error)
            return result.text.strip() if result.text else (
                "[rotation] All providers exhausted. "
                "Try again later or check API keys."
            )
        except Exception as exc:
            logger.warning("rotation chat failed: %s", exc)
            return f"[rotation] {exc}"

    def get_status(self) -> Dict[str, Any]:
        try:
            available = self._orch.available_provider_names()
            total = self._orch.provider_count()
            return {
                "name": self.name,
                "available": total > 0,
                "type": "rotation-orchestrator",
                "providers_available": available,
                "providers_total": total,
            }
        except Exception as exc:
            return {
                "name": self.name,
                "available": False,
                "type": "rotation-orchestrator",
                "error": str(exc)[:100],
            }


# ── Bridge initializer ───────────────────────────────────────────────────

def init_evolution_providers(*,
                             discover_models: bool = True,
                             register_local: bool = True,
                             preload_local: bool = True,
                             register_rotation: bool = True,
                             set_rotation_default: bool = True) -> int:
    """Discover and register all evolution providers with the AIManager.

    Parameters
    ----------
    discover_models
        If True, run ``ModelDiscoverer`` to discover available models.
    register_local
        If True, register the ``LocalLlamaProvider`` (GGUF fallback).
    preload_local
        If True, eagerly load the local GGUF model during registration.
        Set False for fast bootstrap — model loads lazily on first
        ``chat()`` call. The background preload thread in the terminal
        entry point handles the actual loading.
    register_rotation
        If True, register the ``RotationAdapter`` that wraps the
        ``RotationOrchestrator`` for auto-fallback.
    set_rotation_default
        If True, set the rotation adapter as the default provider.

    Returns
    -------
    int
        Number of providers successfully registered.
    """
    ai = AIManager()
    count = 0

    # ── 1. Register local GGUF provider ────────────────────────────────
    if register_local:
        try:
            local = LocalLlamaProvider()
            if preload_local:
                local.ensure_loaded()
            ai.register_provider("local-llama", local, set_default=False)
            count += 1
            if local.is_loaded:
                logger.info("✅ Local GGUF provider: %s",
                            local.model_info.name if local.model_info else "loaded")
            elif preload_local:
                logger.info("ℹ️ Local GGUF: models found but llama-cpp-python "
                            "not available — will try on first chat()")
            else:
                logger.info("⏳ Local GGUF: registered (lazy-load, "
                            "will warm in background)")
        except Exception as exc:
            logger.warning("Local GGUF provider registration skipped: %s", exc)

    # ── 2. Import and register evolution providers ─────────────────────
    try:
        # Import evolution module (works because tank_ws/src is in sys.path
        # from the shell entry point)
        import sys as _sys
        from pathlib import Path as _Path

        _project_root = _Path(__file__).resolve().parent.parent.parent
        _tank_ws_src = _project_root / "tank_ws" / "src"
        if str(_tank_ws_src) not in _sys.path:
            _sys.path.insert(0, str(_tank_ws_src))

        from tank_assistant.evolution.providers.registry import (
            available_providers,
            names_in_priority_order,
        )
        from tank_assistant.evolution.key_registry import key_registry
        from tank_assistant.evolution.providers.concrete import (
            GroqProvider, CerebrasProvider, MistralProvider,
            CohereProvider, OpenRouterProvider, CloudflareProvider,
            GeminiProvider, ReplicateProvider, DeepSeekProvider,
            HuggingFaceProvider, EndpointAIProvider,
            OpenAIProvider, AnthropicProvider, FreebuffProvider,
            XAIProvider, TogetherProvider, DeepInfraProvider,
            SambaNovaProvider, FireworksProvider, PerplexityProvider,
            HyperbolicProvider, LambdaProvider, VoyageProvider,
            NovitaProvider,
        )

        # ── 3. Optionally discover models ──────────────────────────────
        fallback_catalog: Dict[str, list] = {}
        if discover_models:
            try:
                from tank_assistant.evolution.model_discovery import (
                    model_discoverer,
                )
                catalog = model_discoverer.discover_all(force=False)
                for prov_name, result in catalog.items():
                    if result.models:
                        logger.info(
                            "Model discovery: %s = %d models",
                            prov_name, len(result.models))
                        fallback_catalog[prov_name] = result.models
            except Exception as exc:
                logger.debug("Model discovery skipped: %s", exc)

        # ── 4. Register each enabled evolution provider ────────────────
        priority_map = {
            "groq": 10, "cerebras": 20, "mistral": 30,
            "cohere": 40, "openrouter": 50, "cloudflare": 60,
            "gemini": 70, "replicate": 80, "deepseek": 90,
            "huggingface": 100, "endpointai": 110,
            "openai": 120, "anthropic": 130, "freebuff": 140,
            "xai": 150, "together": 160, "deepinfra": 170,
            "sambanova": 180, "fireworks": 190, "perplexity": 200,
            "hyperbolic": 210, "lambda": 220, "voyage": 230,
            "novita": 240,
        }

        CLASS_MAP = {
            "groq": GroqProvider,
            "cerebras": CerebrasProvider,
            "mistral": MistralProvider,
            "cohere": CohereProvider,
            "openrouter": OpenRouterProvider,
            "cloudflare": CloudflareProvider,
            "gemini": GeminiProvider,
            "replicate": ReplicateProvider,
            "deepseek": DeepSeekProvider,
            "huggingface": HuggingFaceProvider,
            "endpointai": EndpointAIProvider,
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "freebuff": FreebuffProvider,
            "xai": XAIProvider,
            "together": TogetherProvider,
            "deepinfra": DeepInfraProvider,
            "sambanova": SambaNovaProvider,
            "fireworks": FireworksProvider,
            "perplexity": PerplexityProvider,
            "hyperbolic": HyperbolicProvider,
            "lambda": LambdaProvider,
            "voyage": VoyageProvider,
            "novita": NovitaProvider,
        }

        for name in names_in_priority_order():
            if name not in CLASS_MAP:
                continue
            try:
                api_key = key_registry.get(CLASS_MAP[name].KEY_NAME)
                if not api_key:
                    logger.debug("Skipping %s: no API key configured", name)
                    continue

                provider_cls = CLASS_MAP[name]
                instance = provider_cls()
                if not instance.is_configured:
                    continue

                adapter = EvolutionProviderAdapter(
                    name, instance,
                    priority=priority_map.get(name, 100),
                )
                ai.register_provider(name, adapter, set_default=False)
                count += 1
                logger.info("✅ Registered evolution provider: %s (%s)",
                            name, instance.model)
            except Exception as exc:
                logger.debug("Failed to register %s: %s", name, exc)

    except ImportError as exc:
        logger.warning(
            "Evolution module not available — evolution providers "
            "not registered: %s", exc)
    except Exception as exc:
        logger.warning("Evolution provider registration failed: %s", exc)

    # ── 5. Register rotation adapter ───────────────────────────────────
    if register_rotation:
        try:
            from tank_assistant.evolution import (
                build_orchestrator, RotationOrchestrator,
            )
            orch = build_orchestrator("rotation",
                                       fallback_catalog=fallback_catalog)
            rotation_adapter = RotationAdapter(orch)
            ai.register_provider("rotation", rotation_adapter,
                                 set_default=set_rotation_default)
            count += 1
            logger.info("✅ Registered rotation orchestrator provider")
        except Exception as exc:
            logger.warning("Rotation adapter registration skipped: %s", exc)

    # ── 6. Summary ─────────────────────────────────────────────────────
    registered = ai.list_providers()
    provider_names = [p["name"] for p in registered if p.get("available")]
    logger.info(
        "Evolution bridge: %d provider(s) registered with AIManager. "
        "Available: %s. Default: %s",
        count,
        ", ".join(provider_names) or "local-stub (fallback)",
        ai.default_provider,
    )
    return count
