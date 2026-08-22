"""Evolution System — provider registry, orchestrators, health, key management,
model discovery.

Public API
----------
- :data:`key_registry` — singleton :class:`KeyRegistry` for by-name key access.
- :func:`get_key` — convenience wrapper around ``key_registry.get``.
- :data:`model_discoverer` — singleton :class:`ModelDiscoverer` for querying
  each provider's models API to discover available models.
- :class:`RotationOrchestrator`, :class:`EnsembleOrchestrator`,
  :class:`RefinementOrchestrator`, :class:`AutoTrainOrchestrator` —
  the 4 evolution modes.
- :func:`register_provider` — registers a provider class + key name in the
  internal provider registry so :class:`RotationOrchestrator` can discover it.
- :func:`build_orchestrator` — factory: takes a mode name, returns the
  matching orchestrator instance (or ``RotationOrchestrator`` as default).
"""
from .key_registry import KeyRegistry, key_registry, get_key, parse_dotenv_text
from .model_discovery import (
    ModelDiscoverer,
    DiscoveryResult,
    model_discoverer,
    DISCOVERY_ENDPOINTS,
)
from .health import (
    CircuitBreaker,
    TokenBucket,
    HealthMonitor,
    health_monitor,
    CircuitState,
)
from .providers.base import (
    BaseHttpProvider,
    OpenAIMixin,
    CustomJsonMixin,
    BaseProvider,            # backwards-compat re-export
)
from .providers.concrete import (
    OpenAIProvider,
    AnthropicProvider,
    FreebuffProvider,
    OpenRouterProvider,
    GroqProvider,
    GeminiProvider,
    MistralProvider,
    CloudflareProvider,
    CerebrasProvider,
    CohereProvider,
    ReplicateProvider,
    HuggingFaceProvider,
    EndpointAIProvider,
    DeepSeekProvider,
)
from .providers.registry import (
    register_provider,
    all_providers,
    get_provider_class,
    PROVIDERS,
    DISABLED_PROVIDERS,
    disable_provider,
    enable_provider,
)
from .orchestrators.base import BaseOrchestrator, OrchestratorResult
from .orchestrators.rotation import RotationOrchestrator
# Optional orchestrators — import lazily so the package loads even when
# these modules haven't shipped yet. ``factory.build_orchestrator`` does
# its own defensive import and returns a fallback when they're absent.
from .factory import (
    build_orchestrator,
    OrchestratorMode,
    EnsembleOrchestrator,
    RefinementOrchestrator,
    AutoTrainOrchestrator,
    ENSEMBLE_OK,
    REFINEMENT_OK,
    AUTO_TRAIN_OK,
)


__all__ = [
    "KeyRegistry", "key_registry", "get_key", "parse_dotenv_text",
    "ModelDiscoverer", "DiscoveryResult", "model_discoverer",
    "DISCOVERY_ENDPOINTS",
    "CircuitBreaker", "TokenBucket", "HealthMonitor",
    "health_monitor", "CircuitState",
    "BaseHttpProvider", "OpenAIMixin", "CustomJsonMixin", "BaseProvider",
    # Provider classes (re-exported for backwards compat)
    "OpenAIProvider", "AnthropicProvider", "FreebuffProvider",
    "OpenRouterProvider", "GroqProvider", "GeminiProvider",
    "MistralProvider", "CloudflareProvider", "CerebrasProvider",
    "CohereProvider", "ReplicateProvider", "HuggingFaceProvider",
    "EndpointAIProvider", "DeepSeekProvider",
    # Provider registry
    "register_provider", "all_providers", "get_provider_class", "PROVIDERS",
    "DISABLED_PROVIDERS", "disable_provider", "enable_provider",
    # Orchestrators (only present when shipped)
    "BaseOrchestrator", "OrchestratorResult",
    "RotationOrchestrator",
    "EnsembleOrchestrator", "RefinementOrchestrator", "AutoTrainOrchestrator",
    # Factory
    "build_orchestrator", "OrchestratorMode",
    "ENSEMBLE_OK", "REFINEMENT_OK", "AUTO_TRAIN_OK",
]
