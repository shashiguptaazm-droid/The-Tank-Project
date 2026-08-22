"""Base provider classes + OpenAI-shaped + custom-JSON mixins.

Class hierarchy
---------------
- :class:`BaseHttpProvider` — owns the shared httpx pool, base URL,
  api_key, model, timeout. ``prompt()`` delegates to ``_call()``.
- :class:`OpenAIMixin` — implements ``_call()`` for any provider whose
  chat-completions endpoint follows OpenAI's wire format. Subclasses
  just declare ``name``, ``DEFAULT_MODEL``, ``DEFAULT_BASE``.
- :class:`CustomJsonMixin` — provides generic ``_post()`` and the body
  envelope (``{system, messages, max_tokens}``); subclasses override
  ``_format_payload()`` / ``_parse_response()`` to convert.

Backward compat
---------------
The legacy ``BaseProvider`` / ``OpenAIProvider`` / ``AnthropicProvider``
/ ``FreebuffProvider`` from :mod:`tank_assistant.external_llm_client`
are preserved by being subclassed from :class:`BaseHttpProvider` here.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

# Make httpx optional so the test suite can import BaseHttpProvider
# without the dependency actually being installed. If you actually call
# ``provider.prompt()`` against a live HTTP endpoint, httpx must be
# importable at runtime.
try:
    import httpx  # type: ignore
except ImportError:                                          # pragma: no cover
    class _StubHttpx:                                        # type: ignore[no-redef]
        class Client:                                         # type: ignore[no-redef]
            def __init__(self, *_a, **_k): pass
            def post(self, *_a, **_k):
                raise RuntimeError("httpx not installed")
        class HTTPError(Exception):                          # type: ignore[no-redef]
            pass
    httpx = _StubHttpx()                                      # type: ignore[assignment]

from ..key_registry import get_key


# ── Module-level httpx client pool (keyed by timeout) ────────────────────

_HTTPX_POOL: Dict[float, Any] = {}


def _httpx_client(timeout: float) -> httpx.Client:
    """Get-or-create a shared httpx.Client for the given timeout."""
    cli = _HTTPX_POOL.get(timeout)
    if cli is None:
        cli = httpx.Client(timeout=float(timeout))
        _HTTPX_POOL[timeout] = cli
    return cli


# ── Base ─────────────────────────────────────────────────────────────────

class BaseHttpProvider:
    """Base class for all providers. Owns the connection pool + identity."""

    name: str = "base"
    DEFAULT_MODEL: str = ""
    DEFAULT_BASE: str = ""
    KEY_NAME: str = ""             # env-var name to look up in KeyRegistry
    DEFAULT_TIMEOUT_S: float = 30.0

    def __init__(self, *, api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: Optional[float] = None) -> None:
        # Resolve API key through the registry; if not provided, look it up.
        self.api_key = api_key or (
            get_key(self.KEY_NAME) if self.KEY_NAME else None)
        self.model = model or self.DEFAULT_MODEL
        self.base_url = (base_url or self.DEFAULT_BASE).rstrip("/")
        self.timeout = float(timeout if timeout is not None else self.DEFAULT_TIMEOUT_S)
        self.last_error: Optional[str] = None
        self.last_used_ts: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def prompt(self, system: str, user: str,
               context: Optional[str] = None,
               tools: Optional[List[Dict[str, Any]]] = None,
               tool_choice: Optional[str] = "auto") -> Dict[str, Any]:
        """Run one call. Returns ``{"text": str, "tool_calls": list}``.

        Subclasses override :meth:`_call`.
        """
        try:
            result = self._call(system, user, context or "",
                                tools, tool_choice)
        except Exception as exc:
            self.last_error = str(exc)[:200]
            raise
        self.last_used_ts = time.monotonic()
        self.last_error = None
        return result

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{type(self).__name__}._call not implemented")


# ── OpenAI-shaped mixin ──────────────────────────────────────────────────

class OpenAIMixin:
    """Implements the standard OpenAI ``POST /v1/chat/completions`` flow.

    Subclasses set ``name``, ``DEFAULT_MODEL``, ``DEFAULT_BASE``, ``KEY_NAME``.
    Supports tool-calling via the native ``tools=[...]`` field.
    """

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
        cli = _httpx_client(self.timeout)
        r = cli.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        try:
            msg = data["choices"][0]["message"]
        except Exception as exc:
            raise RuntimeError(
                f"{self.name}: bad openai-shaped payload: {exc}") from exc
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


# ── Custom-JSON mixin ─────────────────────────────────────────────────────

class CustomJsonMixin:
    """Generic mixin for providers with custom request/response formats.

    Subclasses override :meth:`_format_payload` and :meth:`_parse_response`.
    Provides :meth:`_post` for the actual HTTP call.
    """

    def _post(self, path: str, payload: Dict[str, Any],
              extra_headers: Optional[Dict[str, str]] = None
              ) -> Dict[str, Any]:
        cli = _httpx_client(self.timeout)
        url = (
            f"{self.base_url}{path}"
            if path.startswith("/") else f"{self.base_url}/{path}")
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        r = cli.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()

    def _call(self, system: str, user: str, context: str,
              tools: Optional[List[Dict[str, Any]]],
              tool_choice: Optional[str]) -> Dict[str, Any]:
        payload = self._format_payload(system, user, context, tools, tool_choice)
        data = self._post(self._endpoint_path(), payload, self._extra_headers())
        return self._parse_response(data)

    # ── Default no-op hooks; subclasses override ─────────────────────────
    def _endpoint_path(self) -> str:        # noqa: D401
        return "/chat/completions"

    def _extra_headers(self) -> Optional[Dict[str, str]]:
        return None

    def _format_payload(self, system: str, user: str, context: str,
                        tools: Optional[List[Dict[str, Any]]],
                        tool_choice: Optional[str]) -> Dict[str, Any]:
        return {
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": 512,
            "context": context or None,
            "tools": tools or None,
        }

    def _parse_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": str(data), "tool_calls": []}


# ── Backwards-compat: re-export the legacy interface ─────────────────────

# The legacy ``external_llm_client.py`` defined ``BaseProvider`` with a
# ``prompt() -> str`` interface. We keep that symbol so old imports still
# work; new code should use ``BaseHttpProvider.prompt() -> dict``.

class BaseProvider:                                            # type: ignore[no-redef]
    """Backwards-compat shim. Wraps a :class:`BaseHttpProvider`.

    Used by the existing :class:`ExternalLlmClientNode` until the
    orchestrator migration lands. Prefer ``BaseHttpProvider`` for new
    code.
    """

    def __init__(self, inner: BaseHttpProvider) -> None:
        self._inner = inner

    def prompt(self, system: str, user: str,
               context: Optional[str] = None,
               tools: Optional[List[Dict[str, Any]]] = None,
               tool_choice: Optional[str] = "auto") -> Dict[str, Any]:
        return self._inner.prompt(system, user, context, tools, tool_choice)

    @property
    def name(self) -> str:
        return self._inner.name

    def __getattr__(self, item: str) -> Any:
        return getattr(self._inner, item)
