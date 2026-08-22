"""Provider registry — names + key vars + concrete classes.

Used by the orchestrators (and :func:`build_orchestrator`) to discover
which providers are available in this environment, instantiate them,
and look up API keys through :class:`KeyRegistry`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from .base import BaseHttpProvider
from ..key_registry import key_registry


# Each entry: name -> (class, KEY_NAME env var).
PROVIDERS: Dict[str, Tuple[Type[BaseHttpProvider], str]] = {}

# Providers that are temporarily disabled (e.g. billing issues, ToS
# concerns, intentional skip for evaluation). Filtered out of every
# auto-discovery path so the orchestrator won't even *attempt* them.
DISABLED_PROVIDERS: set[str] = set()  # Gemini re-enabled; quota resets periodically


def _is_enabled(name: str) -> bool:
    """True if ``name`` is not in :data:`DISABLED_PROVIDERS`."""
    return name not in DISABLED_PROVIDERS


def disable_provider(name: str) -> None:
    """Add ``name`` to :data:`DISABLED_PROVIDERS` at runtime."""
    DISABLED_PROVIDERS.add(name)


def enable_provider(name: str) -> None:
    """Remove ``name`` from :data:`DISABLED_PROVIDERS` at runtime."""
    DISABLED_PROVIDERS.discard(name)


def register_provider(name: str, key_name: str):
    """Class-decorator factory: registers a provider class by name.

    Usage::

        @register_provider("groq", "GROQ_API_KEY")
        class GroqProvider(OpenAIMixin, BaseHttpProvider):
            ...

    Returns a decorator that pops the class into :data:`PROVIDERS`. The
    class is returned unchanged so multiple decorators stack.
    """
    def _decorator(cls: Type[BaseHttpProvider]) -> Type[BaseHttpProvider]:
        PROVIDERS[name] = (cls, key_name)
        return cls
    return _decorator


def all_providers() -> Dict[str, Tuple[Type[BaseHttpProvider], str]]:
    """Snapshot of the provider registry."""
    return dict(PROVIDERS)


def get_provider_class(name: str) -> Optional[Type[BaseHttpProvider]]:
    """Look up a provider class by name. Returns ``None`` if unknown."""
    entry = PROVIDERS.get(name)
    return entry[0] if entry else None


def key_for(name: str) -> Optional[str]:
    """Look up the API key for ``name`` via :data:`key_registry`."""
    entry = PROVIDERS.get(name)
    if not entry:
        return None
    return key_registry.get(entry[1])


def available_providers(
    require_configured: bool = True,
) -> Dict[str, Type[BaseHttpProvider]]:
    """Return ``{name: class}`` for all registered providers that have an
    API key (and are otherwise configured).

    Providers in :data:`DISABLED_PROVIDERS` are always filtered out.
    When ``require_configured`` is ``False``, every *enabled* provider
    is returned regardless of key availability — useful for tests.
    """
    out: Dict[str, Type[BaseHttpProvider]] = {}
    for name, (cls, key_name) in PROVIDERS.items():
        if not _is_enabled(name):
            continue
        if require_configured and not key_registry.get(key_name):
            continue
        out[name] = cls
    return out


def instantiate(name: str, *, api_key: Optional[str] = None,
                model: Optional[str] = None,
                base_url: Optional[str] = None) -> BaseHttpProvider:
    """Build a configured instance. Raises ``KeyError`` if unknown
    or :class:`ValueError` if disabled."""
    if name not in PROVIDERS:
        raise KeyError(f"unknown provider: {name!r}")
    if not _is_enabled(name):
        raise ValueError(f"provider {name!r} is disabled")
    cls, key_name = PROVIDERS[name]
    return cls(
        api_key=api_key or key_registry.get(key_name),
        model=model,
        base_url=base_url,
    )


def names_in_priority_order() -> List[str]:
    """Default priority for :class:`RotationOrchestrator`.

    Cheap/fast providers first (Groq, Cerebras), popular second
    (OpenAI/Anthropic), specialist last (Replicate, HuggingFace).
    Providers in :data:`DISABLED_PROVIDERS` are filtered out.
    """
    preferred = [
        "groq", "cerebras", "openai", "anthropic", "freebuff",
        "openrouter", "deepseek", "mistral", "cohere",
        "cloudflare", "endpointai", "replicate", "huggingface",
    ]
    return [n for n in preferred if n in PROVIDERS and _is_enabled(n)]
