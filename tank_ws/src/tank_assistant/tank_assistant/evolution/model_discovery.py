"""Model discovery — auto-find available models from each provider's API.

Provides a :class:`ModelDiscoverer` that queries each provider's models
endpoint (e.g. ``/v1/models``), parses the response, and returns a dict
of ``{provider_name: [model_id, ...]}``.

Integration
-----------
- Called by :class:`RotationOrchestrator` during init to warm the cache.
- Called periodically by a background refresh (or on demand via CLI).
- Results can be persisted to a JSON file and used to update
  ``concrete.py`` defaults and ``worker.js`` fallback catalog.

Thread safety
-------------
Internally uses a read/write lock; the public API is safe to call from
multiple threads (e.g. orchestrator + CLI refresh).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Make httpx optional — if not installed, discovery degrades gracefully.
try:
    import httpx  # type: ignore
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None  # type: ignore[assignment]

from .key_registry import key_registry, get_key
from .providers.registry import DISABLED_PROVIDERS

_LOG = logging.getLogger("tank_assistant.evolution.model_discovery")

# ── Data types ───────────────────────────────────────────────────────────────

@dataclass
class DiscoveryResult:
    """Result of a single provider's model discovery."""
    provider: str
    models: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_s: float = 0.0
    stale: bool = False


@dataclass
class ProviderEndpoint:
    """How to discover models for a provider."""
    name: str
    url: str
    auth_header: str            # "Bearer" or "Token" or "Key"
    env_key: str                # which env var holds the API key
    json_path: List[str]        # path through JSON to the model list
    json_model_field: List[str] = field(default_factory=lambda: ["id"])
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    transform_fn: Optional[Callable[[str], str]] = None


# ── Endpoint registry — one entry per discoverable provider ──────────────────

DISCOVERY_ENDPOINTS: Dict[str, ProviderEndpoint] = {
    "groq": ProviderEndpoint(
        name="groq",
        url="https://api.groq.com/openai/v1/models",
        auth_header="Bearer",
        env_key="GROQ_API_KEY",
        json_path=["data"],
    ),
    "openrouter": ProviderEndpoint(
        name="openrouter",
        url="https://openrouter.ai/api/v1/models",
        auth_header="Bearer",
        env_key="OPENROUTER_API_KEY",
        json_path=["data"],
        filter_fn=lambda m: _is_free_openrouter_model(m),
    ),
    "deepseek": ProviderEndpoint(
        name="deepseek",
        url="https://api.deepseek.com/models",
        auth_header="Bearer",
        env_key="DEEPSEEK_API_KEY",
        json_path=["data"],
    ),
    "mistral": ProviderEndpoint(
        name="mistral",
        url="https://api.mistral.ai/v1/models",
        auth_header="Bearer",
        env_key="MISTRAL_API_KEY",
        json_path=["data"],
    ),
    "cohere": ProviderEndpoint(
        name="cohere",
        url="https://api.cohere.ai/v1/models",
        auth_header="Bearer",
        env_key="COHERE_API_KEY",
        json_path=["models"],
        json_model_field=["name", "id"],
    ),
    "cerebras": ProviderEndpoint(
        name="cerebras",
        url="https://api.cerebras.ai/v1/models",
        auth_header="Bearer",
        env_key="CEREBRAS_API_KEY",
        json_path=["data"],
    ),
    "gemini": ProviderEndpoint(
        name="gemini",
        url="",
        auth_header="Key",
        env_key="GEMINI_API_KEY",
        json_path=["models"],
        json_model_field=["name"],
        transform_fn=lambda n: n.replace("models/", ""),
        filter_fn=lambda m: _gemini_supports_chat(m),
    ),
    "cloudflare": ProviderEndpoint(
        name="cloudflare",
        url="",
        auth_header="Bearer",
        env_key="CLOUDFLARE_WORKER_API_KEY",
        json_path=["result"],
        json_model_field=["id"],
    ),
    "huggingface": ProviderEndpoint(
        name="huggingface",
        url="https://router.huggingface.co/v1/models",
        auth_header="Bearer",
        env_key="HUGGINGFACE_API_KEY",
        json_path=["data"],
        filter_fn=lambda m: "Instruct" in str(m.get("id", "")),
    ),
}
"""
Note: Only providers with model-discovery APIs are listed here.
Replicate, EndpointAI, Anthropic, and OpenAI are intentionally omitted
because they either lack a public models endpoint (Replicate uses static
version hashes) or require additional configuration for discovery
(Anthropic has no free-tier models endpoint; OpenAI requires an active
paid account).
"""



def _is_free_openrouter_model(model: Dict[str, Any]) -> bool:
    """Return True if the OpenRouter model is free (pricing all zero)."""
    pricing = model.get("pricing") or {}
    prompt = float(pricing.get("prompt", pricing.get("input", "NaN")))
    completion = float(pricing.get("completion", pricing.get("output", "NaN")))
    return prompt == 0.0 and completion == 0.0


def _gemini_supports_chat(model: Dict[str, Any]) -> bool:
    """Return True if the Gemini model supports generateContent."""
    methods = model.get("supportedGenerationMethods") or []
    return "generateContent" in methods


# ── The discoverer ───────────────────────────────────────────────────────────

class ModelDiscoverer:
    """Discovers available models from each provider's API.

    Usage::

        discoverer = ModelDiscoverer()
        catalog = discoverer.discover_all()  # {provider: [model, ...]}

    Public API
    ----------
    - :meth:`discover_all` — run discovery for all enabled, configured
      providers in parallel (thread pool).
    - :meth:`discover_single` — run discovery for one provider.
    - :meth:`load_catalog` / :meth:`save_catalog` — persist to JSON.
    - :meth:`build_fallback_catalog` — build the dict that can be used
      to update ``worker.js`` fallbackCatalog or ``concrete.py`` defaults.
    """

    def __init__(self, *,
                 cache_ttl_s: float = 3600.0,
                 timeout_s: float = 15.0,
                 catalog_path: Optional[Path] = None) -> None:
        self._cache_ttl_s = cache_ttl_s
        self._timeout_s = timeout_s
        self._catalog_path = catalog_path or Path(
            os.environ.get(
                "TANK_MODEL_CATALOG_PATH",
                "/var/lib/tank_os/models/registry/models_catalog.json",
            ))
        self._lock = threading.RLock()
        self._catalog: Dict[str, DiscoveryResult] = {}
        self._last_discovery_ts: float = 0.0
        self._http_client: Optional[httpx.Client] = None

    # ── Public API ──────────────────────────────────────────────────────

    def discover_all(self, *,
                     force: bool = False,
                     providers: Optional[List[str]] = None,
                     timeout_s: Optional[float] = None) -> Dict[str, DiscoveryResult]:
        """Discover models for all enabled + configured providers.

        Parameters
        ----------
        force
            Bypass TTL cache and re-fetch from every provider.
        providers
            Optional subset of provider names to check. When ``None``,
            discovers all providers from :data:`DISCOVERY_ENDPOINTS` that
            have keys configured and are not disabled.
        timeout_s
            Per-request timeout. Defaults to ``self._timeout_s``.

        Returns
        -------
        Dict[str, DiscoveryResult]
            Provider name -> result with models (or error).
        """
        if not HAS_HTTPX:
            _LOG.error("httpx not installed — cannot discover models")
            return {}

        now = time.monotonic()
        with self._lock:
            if not force and self._catalog and (
                    now - self._last_discovery_ts < self._cache_ttl_s):
                return dict(self._catalog)

        targets = self._resolve_targets(providers)
        if not targets:
            _LOG.warning("No providers to discover (none configured/enabled)")
            return {}

        results: Dict[str, DiscoveryResult] = {}
        threads: List[threading.Thread] = []

        for endpoint in targets:
            t = threading.Thread(
                target=self._discover_one,
                args=(endpoint, results, timeout_s or self._timeout_s),
                daemon=True,
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=(timeout_s or self._timeout_s) + 5.0)

        with self._lock:
            self._catalog.update(results)
            self._last_discovery_ts = time.monotonic()

        return dict(self._catalog)

    def discover_single(self, provider: str, *,
                        timeout_s: Optional[float] = None) -> DiscoveryResult:
        """Discover models for a single provider.

        Parameters
        ----------
        provider
            Provider name (e.g. ``"groq"``).
        timeout_s
            Per-request timeout. Defaults to ``self._timeout_s``.

        Returns
        -------
        DiscoveryResult
            Result with models (or error).
        """
        endpoint = DISCOVERY_ENDPOINTS.get(provider)
        if endpoint is None:
            return DiscoveryResult(provider=provider,
                                   error=f"unknown provider: {provider!r}")
        result = DiscoveryResult(provider=provider)
        try:
            models = self._fetch_models(endpoint, timeout_s or self._timeout_s)
            result.models = models
        except Exception as exc:
            result.error = str(exc)[:200]
        with self._lock:
            self._catalog[provider] = result
        return result

    def get_catalog_snapshot(self) -> Dict[str, DiscoveryResult]:
        """Return the current in-memory catalog (may be stale or empty)."""
        with self._lock:
            return dict(self._catalog)

    # ── Persistence ────────────────────────────────────────────────────

    def load_catalog(self, path: Optional[Path] = None) -> Dict[str, DiscoveryResult]:
        """Load a previously saved catalog from a JSON file.

        Returns the loaded catalog dict.
        """
        path = path or self._catalog_path
        if not path.exists():
            _LOG.debug("catalog not found at %s", path)
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            catalog: Dict[str, DiscoveryResult] = {}
            for provider, data in raw.items():
                catalog[provider] = DiscoveryResult(
                    provider=provider,
                    models=data.get("models", []),
                    error=data.get("error"),
                    duration_s=data.get("duration_s", 0.0),
                    stale=data.get("stale", False),
                )
            with self._lock:
                self._catalog = catalog
            return dict(catalog)
        except Exception as exc:
            _LOG.warning("failed to load catalog: %s", exc)
            return {}

    def save_catalog(self, path: Optional[Path] = None) -> Path:
        """Save the current catalog to a JSON file.

        Returns the path written to.
        """
        path = path or self._catalog_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            raw = {
                prov: {
                    "models": res.models,
                    "error": res.error,
                    "duration_s": round(res.duration_s, 2),
                    "stale": res.stale,
                }
                for prov, res in self._catalog.items()
            }
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        _LOG.info("catalog saved (%d providers) to %s", len(raw), path)
        return path

    def build_fallback_catalog(self) -> Dict[str, List[str]]:
        """Build a simple ``{provider: [model, ...]}`` dict from results.

        Only includes providers that have models (no errors).
        Useful for updating ``worker.js`` fallback catalog or
        ``concrete.py`` defaults.
        """
        with self._lock:
            return {
                prov: res.models[:10]
                for prov, res in self._catalog.items()
                if res.models and not res.error
            }

    # ── Internals ──────────────────────────────────────────────────────

    def _resolve_targets(self,
                         providers: Optional[List[str]] = None
                         ) -> List[ProviderEndpoint]:
        """Return the list of ProviderEndpoint to query.

        Filters by enabled + configured.  Cloudflare is special — also
        requires ``CLOUDFLARE_ACCOUNT_ID``.
        """
        if providers is not None:
            return [ep for ep in DISCOVERY_ENDPOINTS.values()
                    if ep.name in providers]
        out: List[ProviderEndpoint] = []
        for name, ep in DISCOVERY_ENDPOINTS.items():
            if name in DISABLED_PROVIDERS:
                continue
            key = get_key(ep.env_key)
            if not key:
                continue
            if name == "cloudflare":
                cf_id = get_key("CLOUDFLARE_ACCOUNT_ID")
                if not cf_id:
                    continue
            out.append(ep)
        return out

    def _discover_one(self, endpoint: ProviderEndpoint,
                      results: Dict[str, DiscoveryResult],
                      timeout_s: float) -> None:
        """Thread target — fetches one provider's models."""
        start = time.monotonic()
        result = DiscoveryResult(provider=endpoint.name)
        try:
            models = self._fetch_models(endpoint, timeout_s)
            result.models = models
        except Exception as exc:
            result.error = str(exc)[:200]
        result.duration_s = time.monotonic() - start
        results[endpoint.name] = result
        _LOG.debug("%s: %d models in %.1fs",
                    endpoint.name, len(result.models), result.duration_s)

    def _fetch_models(self, endpoint: ProviderEndpoint,
                      timeout_s: float) -> List[str]:
        """Hit the provider's models API and return a clean list of model IDs."""
        url = self._build_url(endpoint)
        headers = self._build_headers(endpoint)
        client = self._get_http_client(timeout_s)
        r = client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        return self._extract_models(data, endpoint)

    def _build_url(self, endpoint: ProviderEndpoint) -> str:
        """Build the URL, handling special cases like Gemini / Cloudflare."""
        if endpoint.name == "gemini":
            key = get_key("GEMINI_API_KEY")
            return (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={key}")
        if endpoint.name == "cloudflare":
            cf_id = get_key("CLOUDFLARE_ACCOUNT_ID")
            if not cf_id:
                raise RuntimeError(
                    "Cloudflare discovery requires CLOUDFLARE_ACCOUNT_ID")
            return (
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{cf_id}/ai/models/search")
        return endpoint.url

    def _build_headers(self, endpoint: ProviderEndpoint) -> Dict[str, str]:
        """Build auth headers."""
        key = get_key(endpoint.env_key)
        if endpoint.auth_header == "Token":
            return {"Authorization": f"Token {key}"}
        if endpoint.auth_header == "Key":
            return {}  # key is in URL query param for Gemini
        return {"Authorization": f"Bearer {key}"}

    def _extract_models(self, data: Dict[str, Any],
                        endpoint: ProviderEndpoint) -> List[str]:
        """Navigate JSON to extract model IDs with optional filtering."""
        # Navigate json_path
        current: Any = data
        for key in endpoint.json_path:
            if isinstance(current, dict):
                current = current.get(key, [])
            elif isinstance(current, list):
                # If the path wants to go into a list, take first element
                current = current[0].get(key, []) if current else []
            else:
                return []

        if not isinstance(current, list):
            return []

        model_ids: Set[str] = set()
        for item in current:
            if not isinstance(item, dict):
                continue
            if endpoint.filter_fn and not endpoint.filter_fn(item):
                continue
            model_id = None
            for field in endpoint.json_model_field:
                val = item.get(field)
                if val and isinstance(val, str):
                    model_id = val
                    break
            if not model_id:
                continue
            if endpoint.transform_fn:
                model_id = endpoint.transform_fn(model_id)
            if model_id and " " not in model_id:
                model_ids.add(model_id)

        return sorted(model_ids)

    def _get_http_client(self, timeout_s: float) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=timeout_s,
                                              follow_redirects=True)
        return self._http_client

    def close(self) -> None:
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None


# ── Module-level singleton ───────────────────────────────────────────────────

model_discoverer = ModelDiscoverer()

__all__ = [
    "ModelDiscoverer",
    "DiscoveryResult",
    "ProviderEndpoint",
    "model_discoverer",
    "DISCOVERY_ENDPOINTS",
]
