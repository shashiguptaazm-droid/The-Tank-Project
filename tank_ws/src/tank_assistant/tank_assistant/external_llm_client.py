"""External LLM client — Pi → AI (the outbound half of the bridge).

A small ROS node that subscribes ``/assistant/uncertain`` and, when a
local llama.cpp reply is below confidence, calls out to one or more
external LLM providers (Freebuff API, OpenAI, Anthropic) and publishes
the merged answer on ``/assistant/from_external``.

Native tool-calling
-------------------
OpenAI's ``tools=[...]`` field and Anthropic's ``tools=[...]`` field let
the provider parse tool calls natively — far more reliable than asking
a model to emit markdown-fenced JSON. The bridge manifest is mapped to
each provider's native tool schema; the resulting ``tool_calls`` are
forwarded to ``/assistant/tool_call`` so the assistant loop can execute
them via the bridge.

The :class:`BaseProvider` keeps the on-the-wire format normalisation
small::

    BaseProvider.prompt(system, user, *, context=None, tools=None,
                        tool_choice='auto') -> dict

The returned dict has ``text`` (str, may be empty if tool_calls fired)
and ``tool_calls`` (list[dict], each with ``name``/``params``).

Per-provider subclasses are:

* :class:`OpenAIProvider`     — POST /v1/chat/completions (native tools)
* :class:`AnthropicProvider`  — POST /v1/messages       (native tools)
* :class:`FreebuffProvider`   — Generic OpenAI-shaped HTTP passthrough

Providers share a module-level :data:`_httpx_client_pool` (keyed by
timeout) so we don't pay TLS / TCP setup on every burst.

Usage (CLI first-pass)::

    TANK_API_PROVIDER=openai OPENAI_API_KEY=sk-... \\
        python3 -m tank_assistant.external_llm_client
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import time
from typing import Any, Dict, List, Optional

try:
    import rclpy                                   # noqa: F401
    from rclpy.node import Node
    from std_msgs.msg import String
    _RCLPY_AVAILABLE = True
except ImportError:
    _RCLPY_AVAILABLE = False

    class _StubNode:                               # type: ignore[no-redef]
        def __init__(self, *_a, **_k): pass
        def create_subscription(self, *_a, **_k): return None
        def create_publisher(self, *_a, **_k): return type(
            "P", (), {"publish": lambda s, m: None})()
        def get_logger(self): return type("L", (), {
            "info": lambda *a, **k: None,
            "warn": lambda *a, **k: None,
            "error": lambda *a, **k: None,
        })()

    Node = _StubNode                               # type: ignore[assignment]
    class _StubString:
        def __init__(self, data: str = "") -> None:
            self.data = data
    String = _StubString                           # type: ignore[assignment]


HTTP_TIMEOUT_S = float(os.environ.get("TANK_EXTERNAL_LLM_TIMEOUT", "8.0"))
PROVIDER_ENV = {
    "openai":    "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "freebuff":  "FREEBUFF_API_KEY",
    "groq":      "GROQ_API_KEY",
    "together":  "TOGETHER_API_KEY",
}

# Module-level pool — lets providers keep a single httpx.Client so we
# don't pay TLS / TCP setup on every /assistant/uncertain burst.
_httpx_client_pool: "dict[str, object]" = {}


def _httpx_client(timeout: float) -> "object":
    try:
        import httpx  # type: ignore
    except ImportError as exc:                                  # pragma: no cover
        raise RuntimeError("httpx not installed") from exc
    key = f"{float(timeout):.3f}"
    cli = _httpx_client_pool.get(key)
    if cli is None:
        cli = httpx.Client(timeout=float(timeout))
        _httpx_client_pool[key] = cli
    return cli


def _load_manifest() -> Dict[str, Any]:
    """Best-effort fetch of the bridge tool manifest."""
    try:
        from tank_command_bridge.manifest import manifest_json  # type: ignore
        return manifest_json()
    except Exception:
        return {}


def _manifest_to_openai_tools(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map bridge manifest → OpenAI ``tools=[...]`` format.

    Each OpenAI tool is::

        {"type": "function",
         "function": {"name": ..., "description": ...,
                      "parameters": <JSON Schema>}}
    """
    out: List[Dict[str, Any]] = []
    for tool in manifest.get("tools", []):
        out.append({
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object"}),
            },
        })
    return out


def _manifest_to_anthropic_tools(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map bridge manifest → Anthropic ``tools=[...]`` format.

    Anthropic wants ``input_schema`` instead of ``parameters``.
    """
    out: List[Dict[str, Any]] = []
    for tool in manifest.get("tools", []):
        out.append({
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "input_schema": tool.get("parameters", {"type": "object"}),
        })
    return out


class BaseProvider:
    """Abstract base. Subclasses override ``_call(system, user, ctx, tools)``.

    Returned dict shape::

        {"text": "...",            # may be empty if only tool_calls
         "tool_calls": [           # list of {"name": str, "params": dict}
             {"name": "move", "params": {...}}, ...
         ]}
    """
    name = "base"

    def __init__(self, *, timeout: float = HTTP_TIMEOUT_S,
                 base_url: Optional[str] = None) -> None:
        self.timeout = float(timeout)
        self.base_url = base_url

    def prompt(self, system: str, user: str,
               context: Optional[str] = None,
               tools: Optional[List[Dict[str, Any]]] = None,
               tool_choice: Optional[str] = "auto") -> Dict[str, Any]:
        """Returns ``{"text": str, "tool_calls": list}``.

        Backwards compat: providers that don't implement native tools
        fall back to the plain-string prompt and ``tool_calls`` will be
        empty. Callers should always check both keys.
        """
        try:
            return self._call(system, user, context or "", tools, tool_choice)
        except Exception as exc:
            raise RuntimeError(f"{self.name} call failed: {exc}") from exc

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    """OpenAI chat completions + any OpenAI-shaped gateway (Together,
    Groq, Freebuff's default base, etc.)."""
    name = "openai"
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_BASE = "https://api.openai.com/v1"

    def __init__(self, api_key: str, model: Optional[str] = None,
                 base_url: Optional[str] = None) -> None:
        super().__init__(
            base_url=base_url or os.environ.get("OPENAI_BASE_URL",
                                                self.DEFAULT_BASE),
        )
        self.api_key = api_key
        self.model = model or os.environ.get("OPENAI_MODEL",
                                             self.DEFAULT_MODEL)

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system",
                 "content": system + ("\n\n" + context if context else "")},
                {"role": "user", "content": user},
            ],
            "max_tokens": 512,
            "temperature": 0.4,
        }
        if tools:
            body["tools"] = tools
            if tool_choice:
                body["tool_choice"] = tool_choice
        client = _httpx_client(self.timeout)
        r = client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        try:
            msg = data["choices"][0]["message"]
        except Exception as exc:
            raise RuntimeError(f"bad openai payload: {exc}") from exc

        text = (msg.get("content") or "").strip()
        tool_calls: List[Dict[str, Any]] = []
        for tc in msg.get("tool_calls") or []:
            try:
                fn = tc.get("function") or {}
                args_raw = fn.get("arguments", "{}")
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}
            tool_calls.append({"name": fn.get("name", ""), "params": args})
        return {"text": text, "tool_calls": tool_calls}


class AnthropicProvider(BaseProvider):
    """Anthropic Messages API. System prompt goes in the dedicated
    ``system`` field (NOT prepended to user)."""
    name = "anthropic"
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"
    DEFAULT_BASE = "https://api.anthropic.com/v1"

    def __init__(self, api_key: str, model: Optional[str] = None,
                 base_url: Optional[str] = None) -> None:
        super().__init__(
            base_url=base_url or os.environ.get(
                "ANTHROPIC_BASE_URL", self.DEFAULT_BASE),
        )
        self.api_key = api_key
        self.model = model or os.environ.get(
            "ANTHROPIC_MODEL", self.DEFAULT_MODEL)

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 512,
            "system": system,
            "messages": [
                {"role": "user",
                 "content": user + ("\n\nContext:\n" + context
                                     if context else "")},
            ],
        }
        if tools:
            body["tools"] = tools
        client = _httpx_client(self.timeout)
        r = client.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        text = ""
        tool_calls: List[Dict[str, Any]] = []
        try:
            for chunk in data.get("content", []):
                ctype = chunk.get("type")
                if ctype == "text":
                    text += chunk.get("text", "")
                elif ctype == "tool_use":
                    tool_calls.append({
                        "name": chunk.get("name", ""),
                        "params": chunk.get("input") or {},
                    })
        except Exception as exc:
            raise RuntimeError(f"bad anthropic payload: {exc}") from exc
        return {"text": text.strip(), "tool_calls": tool_calls}


class FreebuffProvider(OpenAIProvider):
    """Freebuff agent gateway — OpenAI-shaped by default. Override with
    ``FREEBUFF_BASE_URL``."""
    name = "freebuff"
    DEFAULT_MODEL = "freebuff-default"
    DEFAULT_BASE = "https://api.freebuff.com/v1"

    def __init__(self, api_key: str, model: Optional[str] = None,
                 base_url: Optional[str] = None) -> None:
        super().__init__(
            api_key=api_key,
            model=model or os.environ.get("FREEBUFF_MODEL",
                                           self.DEFAULT_MODEL),
            base_url=base_url or os.environ.get(
                "FREEBUFF_BASE_URL", self.DEFAULT_BASE),
        )


def build_provider() -> Optional[BaseProvider]:
    """Pick the first provider that has its env key set.

    Backwards-compat wrapper. Internally routes through the evolution
    system's :class:`RotationOrchestrator` (or whichever mode is
    configured via ``TANK_EVOLUTION_MODE``), so all 14 providers are
    available — not just the 3 this module historically knew about.

    If ``TANK_API_PROVIDER`` is set to a single provider name (legacy
    behaviour), only that provider is used. Otherwise the orchestrator
    auto-discovers every configured provider (skipping those in
    :data:`evolution.providers.registry.DISABLED_PROVIDERS`).
    """
    explicit = os.environ.get("TANK_API_PROVIDER", "").strip().lower()
    if explicit in {"rotation", "ensemble", "refinement", "auto_train"}:
        # Explicit evolution mode.
        return _EvolutionProvider(mode=explicit)

    if explicit:
        # Legacy: pin to one provider. Map legacy PROVIDER_ENV entries
        # onto the new evolution registry.
        legacy_env = PROVIDER_ENV.get(explicit)
        if legacy_env and not os.environ.get(legacy_env):
            return None
        return _EvolutionProvider(mode="rotation", only=explicit)

    # Default — full RotationOrchestrator with auto-discovery.
    orch = _EvolutionProvider()
    return orch if orch.is_configured() else None


class _EvolutionProvider(BaseProvider):
    """Backwards-compat adapter: :class:`BaseProvider` interface over
    the evolution system's orchestrator.

    The legacy :class:`BaseProvider.prompt` returns
    ``{"text": str, "tool_calls": list}``. The new orchestrator returns
    an :class:`OrchestratorResult` with the same fields (plus metadata).
    This adapter converts one to the other so callers like
    :class:`ExternalLlmClientNode` don't need to change.
    """

    def __init__(self, *, mode: str = "rotation", only: Optional[str] = None,
                 **kwargs: Any) -> None:
        super().__init__()
        self.name = mode
        try:
            from .evolution.factory import build_orchestrator
            from .evolution.providers.registry import (
                PROVIDERS, DISABLED_PROVIDERS,
                key_for, instantiate,
            )
        except ImportError as exc:                            # pragma: no cover
            raise RuntimeError(
                "evolution package not importable; "
                "ensure tank_assistant/evolution/ is on PYTHONPATH"
            ) from exc
        self._mode = mode
        self._only = only
        # Build a single-provider list if --only was passed.
        if only is not None:
            if only in DISABLED_PROVIDERS:
                raise RuntimeError(
                    f"provider {only!r} is in DISABLED_PROVIDERS")
            if only not in PROVIDERS:
                raise RuntimeError(f"unknown provider {only!r}")
            api_key = key_for(only)
            if not api_key:
                self._orch = None
                return
            self._orch = build_orchestrator(
                mode="rotation",
                providers=[instantiate(only, api_key=api_key)],
                **kwargs,
            )
            return
        # Auto-discover mode — pass `providers=None` so the orchestrator
        # reads from the registry.
        self._orch = build_orchestrator(mode=mode, providers=None, **kwargs)

    def is_configured(self) -> bool:
        """True if at least one provider is wired with a key."""
        if self._orch is None:
            return False
        try:
            avail = self._orch.available_provider_names(configured_only=True)
            return bool(avail)
        except Exception:
            return False

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        if self._orch is None:
            raise RuntimeError("orchestrator not initialised")
        result = self._orch.run(
            system, user, context=context,
            tools=tools, tool_choice=tool_choice,
        )
        return {
            "text": result.text or "",
            "tool_calls": result.tool_calls or [],
            # Surface metadata under well-known keys (callers ignore extras).
            "providers_used": list(result.providers_used),
            "elapsed_s": float(result.elapsed_s),
            "error": result.error,
        }


# --------------------------------------------------------------------------- #
# ROS node — outbound call when local LLM is uncertain
# --------------------------------------------------------------------------- #

class ExternalLlmClientNode(Node):  # type: ignore[no-redef]
    """Subscribes ``/assistant/uncertain`` and publishes its external
    call back on ``/assistant/from_external``. Built so the existing
    ``llm_node.py`` can stay focused on local inference; if the local
    model is unsure, it fires the trigger here.

    Native tool-calling: when the provider returns ``tool_calls``, the
    node publishes them on ``/assistant/tool_call`` so the LLM loop
    can execute via the bridge.
    """

    _EXECUTOR = None  # class-level — single bounded pool per process

    def __init__(self, provider: Optional[BaseProvider] = None) -> None:
        super().__init__("external_llm_client")
        self._provider = provider or build_provider()
        self._from_ext = self.create_publisher(
            String, "/assistant/from_external", 10,
        )
        self._tool_call_pub = self.create_publisher(
            String, "/assistant/tool_call", 10,
        )
        self._uncertain_sub = self.create_subscription(
            String, "/assistant/uncertain", self._on_uncertain, 10,
        )
        # Cache mapped tools so we don't re-map on every /assistant/uncertain.
        # Evolution orchestrator handles per-provider tool formatting inside
        # each provider's _call(), so we just pass the manifest verbatim
        # for the legacy BaseProvider path (OpenAI-shaped) and Anthropic
        # format for Anthropic.
        self._mapped_tools: List[Dict[str, Any]] = []
        if self._provider:
            manifest = _load_manifest()
            if manifest.get("tools"):
                if isinstance(self._provider, AnthropicProvider):
                    self._mapped_tools = _manifest_to_anthropic_tools(manifest)
                elif isinstance(self._provider, _EvolutionProvider):
                    # Pass manifest in OpenAI shape — every OpenAI-shaped
                    # provider (Groq/Cerebras/OpenRouter/...) shares that.
                    # Non-OpenAI-shaped providers (Gemini/Mistral/...) do
                    # their own tool transformation inside their _call().
                    self._mapped_tools = _manifest_to_openai_tools(manifest)
                else:
                    self._mapped_tools = _manifest_to_openai_tools(manifest)
        # Bounded pool so a /assistant/uncertain burst can't spawn
        # unbounded daemon threads.
        if ExternalLlmClientNode._EXECUTOR is None:
            ExternalLlmClientNode._EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="ext-llm",
            )
        if self._provider:
            mode_info = ""
            if isinstance(self._provider, _EvolutionProvider):
                try:
                    avail = self._provider._orch.available_provider_names(
                        configured_only=True)
                except Exception:
                    avail = []
                mode_info = f" mode={self._provider.name} providers={avail}"
            self.get_logger().info(
                f"external_llm_client online — provider={self._provider.name}"
                f" tools={len(self._mapped_tools)}"
                f"{mode_info}"
            )
        else:
            self.get_logger().warn(
                "external_llm_client: no provider configured "
                "(set any of the 14 provider keys via "
                "/etc/edulabs-thesis-worker/worker.env or "
                "TANK_API_PROVIDER); outbound calls will no-op"
            )

    def _on_uncertain(self, msg: String) -> None:
        if not self._provider:
            return
        try:
            payload = json.loads(msg.data or "{}")
        except Exception:
            payload = {"text": msg.data or ""}
        text = str(payload.get("text", ""))
        context = str(payload.get("context", ""))
        if not text:
            return
        # Submit through the bounded pool so /assistant/uncertain
        # bursts can't spawn unbounded threads on the Pi 5.
        ExternalLlmClientNode._EXECUTOR.submit(
            self._call_external, text, context,
        )

    def _call_external(self, text: str, context: str) -> None:
        try:
            system = (
                "You are a concise assistant for The Tank (a ROS 2 "
                "Pi 5 robot). Keep replies under 80 words. Don't "
                "speculate about hardware you don't know."
            )
            result = self._provider.prompt(
                system, text, context=context,
                tools=self._mapped_tools or None,
            )
            payload = {
                "ts": time.time(),
                "provider": self._provider.name,
                "text": (result.get("text") or "")[:2000],
                "tool_calls": result.get("tool_calls") or [],
                # Forward orchestrator metadata when present.
                "providers_used": result.get("providers_used") or [],
                "elapsed_s": result.get("elapsed_s"),
                "error": result.get("error"),
            }
            # Strip None values to keep the wire payload tidy.
            payload = {k: v for k, v in payload.items() if v is not None}
            self._from_ext.publish(String(data=json.dumps(payload)))
            # Forward native tool_calls for the LLM loop to execute.
            for tc in payload["tool_calls"]:
                self._tool_call_pub.publish(String(data=json.dumps({
                    "ts": time.time(),
                    "provider": self._provider.name,
                    "tool": tc.get("name", ""),
                    "params": tc.get("params") or {},
                })))
        except Exception as exc:
            self.get_logger().warn(
                f"external LLM call failed: {exc}",
                throttle_duration_sec=20.0,
            )


def main(args=None) -> None:
    if not _RCLPY_AVAILABLE:
        print("external_llm_client CLI: rclpy not installed; "
              "set env keys and rerun on the Pi 5", flush=True)
        return
    rclpy.init(args=args)
    node = ExternalLlmClientNode()
    # Allow pytest to construct us without spinning; main() blocks.
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
