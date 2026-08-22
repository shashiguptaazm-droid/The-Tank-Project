"""Concrete providers — 11 new + 3 backwards-compat (OpenAI/Anthropic/Freebuff).

Each class is tiny: it just declares ``name``, ``DEFAULT_MODEL``,
``DEFAULT_BASE``, ``KEY_NAME`` and (if custom-shaped) overrides the
``_format_payload`` / ``_parse_response`` hooks on
:class:`CustomJsonMixin`.

All OpenAI-shaped providers share :class:`OpenAIMixin` (Groq, Cerebras,
OpenRouter, DeepSeek, EndpointAI, Freebuff, OpenAI).
Custom-shaped providers share :class:`CustomJsonMixin` (Anthropic,
Gemini, Mistral, Cohere, Replicate, HuggingFace, Cloudflare).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .base import BaseHttpProvider, OpenAIMixin, CustomJsonMixin
from .registry import register_provider, PROVIDERS

# Clear any stale entries left over from a previous import cycle where
# the @register_provider decorator was buggy and registered
# ``BaseHttpProvider`` itself as the class. Safe to do — every import of
# this module re-registers all 14 providers below.
PROVIDERS.clear()


# ════════════════════════════════════════════════════════════════════════
# OpenAI-shaped providers (use OpenAIMixin as-is)
# ════════════════════════════════════════════════════════════════════════

@register_provider("openai", "OPENAI_API_KEY")
class OpenAIProvider(OpenAIMixin, BaseHttpProvider):
    name = "openai"
    DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    DEFAULT_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    KEY_NAME = "OPENAI_API_KEY"


@register_provider("groq", "GROQ_API_KEY")
class GroqProvider(OpenAIMixin, BaseHttpProvider):
    name = "groq"
    DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    DEFAULT_BASE = os.environ.get(
        "GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    KEY_NAME = "GROQ_API_KEY"


@register_provider("cerebras", "CEREBRAS_API_KEY")
class CerebrasProvider(OpenAIMixin, BaseHttpProvider):
    name = "cerebras"
    DEFAULT_MODEL = os.environ.get(
        "CEREBRAS_MODEL", "gpt-oss-120b")
    DEFAULT_BASE = os.environ.get(
        "CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
    KEY_NAME = "CEREBRAS_API_KEY"


@register_provider("openrouter", "OPENROUTER_API_KEY")
class OpenRouterProvider(OpenAIMixin, BaseHttpProvider):
    name = "openrouter"
    DEFAULT_MODEL = os.environ.get(
        "OPENROUTER_MODEL", "openai/gpt-4o-mini")
    DEFAULT_BASE = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    KEY_NAME = "OPENROUTER_API_KEY"


@register_provider("deepseek", "DEEPSEEK_API_KEY")
class DeepSeekProvider(OpenAIMixin, BaseHttpProvider):
    name = "deepseek"
    DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    DEFAULT_BASE = os.environ.get(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    KEY_NAME = "DEEPSEEK_API_KEY"


@register_provider("endpointai", "ENDPOINT_AI_API_KEY")
class EndpointAIProvider(OpenAIMixin, BaseHttpProvider):
    """Catch-all for any user-configured OpenAI-shaped endpoint.

    Base URL must be provided via ``ENDPOINT_AI_BASE_URL`` env var or the
    ``base_url=`` kwarg; the model via ``ENDPOINT_AI_MODEL``.
    """
    name = "endpointai"
    DEFAULT_MODEL = os.environ.get("ENDPOINT_AI_MODEL", "endpoint-ai-default")
    DEFAULT_BASE = os.environ.get(
        "ENDPOINT_AI_BASE_URL", "https://api.endpoint.ai/v1")
    KEY_NAME = "ENDPOINT_AI_API_KEY"


@register_provider("freebuff", "FREEBUFF_API_KEY")
class FreebuffProvider(OpenAIMixin, BaseHttpProvider):
    """Freebuff agent gateway — OpenAI-shaped by default."""
    name = "freebuff"
    DEFAULT_MODEL = os.environ.get("FREEBUFF_MODEL", "freebuff-default")
    DEFAULT_BASE = os.environ.get(
        "FREEBUFF_BASE_URL", "https://api.freebuff.com/v1")
    KEY_NAME = "FREEBUFF_API_KEY"


# ════════════════════════════════════════════════════════════════════════
# Anthropic — custom-shaped, system prompt in dedicated field
# ════════════════════════════════════════════════════════════════════════

@register_provider("anthropic", "ANTHROPIC_API_KEY")
class AnthropicProvider(CustomJsonMixin, BaseHttpProvider):
    name = "anthropic"
    DEFAULT_MODEL = os.environ.get(
        "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    DEFAULT_BASE = os.environ.get(
        "ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    KEY_NAME = "ANTHROPIC_API_KEY"

    def _endpoint_path(self) -> str:
        return "/messages"

    def _extra_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }

    def _format_payload(self, system, user, context, tools, tool_choice):
        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 512,
            "system": system,
            "messages": [
                {"role": "user",
                 "content": user + ("\n\nContext:\n" + context if context else "")},
            ],
        }
        if tools:
            body["tools"] = tools
        return body

    def _parse_response(self, data):
        text = ""
        tool_calls: List[Dict[str, Any]] = []
        for chunk in data.get("content", []):
            ctype = chunk.get("type")
            if ctype == "text":
                text += chunk.get("text", "")
            elif ctype == "tool_use":
                tool_calls.append({
                    "name": chunk.get("name", ""),
                    "params": chunk.get("input") or {},
                })
        return {"text": text.strip(), "tool_calls": tool_calls}


# ════════════════════════════════════════════════════════════════════════
# Gemini — generateContent API
# ════════════════════════════════════════════════════════════════════════

@register_provider("gemini", "GEMINI_API_KEY")
class GeminiProvider(CustomJsonMixin, BaseHttpProvider):
    name = "gemini"
    DEFAULT_MODEL = os.environ.get(
        "GEMINI_MODEL", "gemini-2.5-flash")
    DEFAULT_BASE = os.environ.get(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta")
    KEY_NAME = "GEMINI_API_KEY"

    def _endpoint_path(self) -> str:
        return (
            f"/models/{self.model}:generateContent"
            f"?key={self.api_key}")

    def _extra_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _format_payload(self, system, user, context, tools, tool_choice):
        return {
            "contents": [
                {"role": "user",
                 "parts": [{"text": user + (
                     "\n\nContext:\n" + context if context else "")}]},
            ],
            "systemInstruction": {
                "parts": [{"text": system}],
            } if system else None,
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.4},
        }

    def _parse_response(self, data):
        text = ""
        tool_calls: List[Dict[str, Any]] = []
        for cand in data.get("candidates", []) or []:
            content = cand.get("content", {})
            for part in content.get("parts", []) or []:
                if "text" in part:
                    text += part["text"]
                # Gemini function-calling maps to "functionCall" parts; for
                # now we keep this minimal — orchestrator can fall back
                # to the local parser.
                if "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append({
                        "name": fc.get("name", ""),
                        "params": fc.get("args") or {},
                    })
        return {"text": text.strip(), "tool_calls": tool_calls}


# ════════════════════════════════════════════════════════════════════════
# Mistral — chat completions, similar to OpenAI but with /v1 path
# ════════════════════════════════════════════════════════════════════════

@register_provider("mistral", "MISTRAL_API_KEY")
class MistralProvider(CustomJsonMixin, BaseHttpProvider):
    name = "mistral"
    DEFAULT_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
    DEFAULT_BASE = os.environ.get(
        "MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    KEY_NAME = "MISTRAL_API_KEY"

    def _endpoint_path(self) -> str:
        return "/chat/completions"

    def _extra_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _format_payload(self, system, user, context, tools, tool_choice):
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system",
                 "content": system + (
                     "\n\n" + context if context else "")},
                {"role": "user", "content": user},
            ],
            "max_tokens": 512,
            "temperature": 0.4,
        }
        if tools:
            # Mistral uses "type": "function" wrapper.
            body["tools"] = tools
            if tool_choice:
                body["tool_choice"] = tool_choice
        return body

    def _parse_response(self, data):
        try:
            msg = data["choices"][0]["message"]
        except Exception as exc:
            raise RuntimeError(
                f"mistral: bad payload: {exc}") from exc
        text = (msg.get("content") or "").strip()
        tool_calls: List[Dict[str, Any]] = []
        for tc in msg.get("tool_calls") or []:
            try:
                fn = tc.get("function") or {}
                args_raw = fn.get("arguments", "{}")
                args = (json.loads(args_raw)
                        if isinstance(args_raw, str) else args_raw)
            except Exception:
                args = {}
            tool_calls.append({"name": fn.get("name", ""), "params": args})
        return {"text": text, "tool_calls": tool_calls}


# (MistralProvider._parse_response uses json.loads; ``import json`` is at
# the top of this module.)

# ════════════════════════════════════════════════════════════════════════
# Cloudflare Workers AI — REST /ai/run/@cf/<model>
# ════════════════════════════════════════════════════════════════════════

@register_provider("cloudflare", "CLOUDFLARE_WORKER_API_KEY")
class CloudflareProvider(CustomJsonMixin, BaseHttpProvider):
    """Cloudflare Workers AI. Requires CF_ACCOUNT_ID env var.

    Base URL is ``https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run``.
    """
    name = "cloudflare"
    DEFAULT_MODEL = os.environ.get(
        "CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    KEY_NAME = "CLOUDFLARE_WORKER_API_KEY"
    DEFAULT_BASE = ""  # computed in __init__

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        if not self.base_url:
            account_id = os.environ.get(
                "CLOUDFLARE_ACCOUNT_ID", "")
            self.base_url = (
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{account_id}/ai/run")

    def _endpoint_path(self) -> str:
        return f"/{self.model}"

    def _extra_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _format_payload(self, system, user, context, tools, tool_choice):
        return {
            "messages": [
                {"role": "system", "content": system + (
                    "\n\n" + context if context else "")},
                {"role": "user", "content": user},
            ],
            "max_tokens": 512,
        }

    def _parse_response(self, data):
        result = data.get("result") or {}
        resp = result.get("response") or ""
        return {"text": str(resp).strip(), "tool_calls": []}


# ════════════════════════════════════════════════════════════════════════
# Cohere — chat API
# ════════════════════════════════════════════════════════════════════════

@register_provider("cohere", "COHERE_API_KEY")
class CohereProvider(CustomJsonMixin, BaseHttpProvider):
    name = "cohere"
    DEFAULT_MODEL = os.environ.get("COHERE_MODEL", "command-r-plus-08-2024")
    DEFAULT_BASE = os.environ.get(
        "COHERE_BASE_URL", "https://api.cohere.ai/v1")
    KEY_NAME = "COHERE_API_KEY"

    def _endpoint_path(self) -> str:
        return "/chat"

    def _extra_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def _format_payload(self, system, user, context, tools, tool_choice):
        body: Dict[str, Any] = {
            "model": self.model,
            "message": user + (
                "\n\nContext:\n" + context if context else ""),
            "max_tokens": 512,
            "temperature": 0.4,
        }
        if system:
            body["preamble"] = system
        return body

    def _parse_response(self, data):
        return {"text": (data.get("text") or "").strip(), "tool_calls": []}


# ════════════════════════════════════════════════════════════════════════
# Replicate — Predictions API (version-hash mode)
# ════════════════════════════════════════════════════════════════════════

@register_provider("replicate", "REPLICATE_API_KEY")
class ReplicateProvider(CustomJsonMixin, BaseHttpProvider):
    """Replicate predictions API. Requires a model version hash (not a
    model name string). Free tier is rate-limited to ~6 req/min.
    Slow; treat as last-resort."""
    name = "replicate"
    DEFAULT_MODEL = os.environ.get(
        "REPLICATE_VERSION",
        "meta/meta-llama-3.3-70b-instruct")
    DEFAULT_BASE = os.environ.get(
        "REPLICATE_BASE_URL", "https://api.replicate.com/v1")
    KEY_NAME = "REPLICATE_API_KEY"
    DEFAULT_TIMEOUT_S = 60.0

    def _endpoint_path(self) -> str:
        return "/predictions"

    def _extra_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"}

    def _format_payload(self, system, user, context, tools, tool_choice):
        return {
            "version": self.model,
            "input": {
                "system_prompt": system,
                "prompt": user + (
                    "\n\nContext:\n" + context if context else ""),
                "max_new_tokens": 512,
            },
        }

    def _parse_response(self, data):
        out = data.get("output")
        if isinstance(out, list):
            text = "".join(str(x) for x in out)
        else:
            text = str(out) if out is not None else ""
        return {"text": text.strip(), "tool_calls": []}


# ════════════════════════════════════════════════════════════════════════
# HuggingFace Inference — serverless API
# ════════════════════════════════════════════════════════════════════════

@register_provider("huggingface", "HUGGINGFACE_API_KEY")
class HuggingFaceProvider(CustomJsonMixin, BaseHttpProvider):
    name = "huggingface"
    DEFAULT_MODEL = os.environ.get(
        "HUGGINGFACE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
    DEFAULT_BASE = os.environ.get(
        "HUGGINGFACE_BASE_URL",
        "https://api-inference.huggingface.co/models")
    KEY_NAME = "HUGGINGFACE_API_KEY"
    DEFAULT_TIMEOUT_S = 60.0

    def _endpoint_path(self) -> str:
        return f"/{self.model}"

    def _extra_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _format_payload(self, system, user, context, tools, tool_choice):
        return {
            "inputs": (
                f"<|system|>\n{system}\n<|user|>\n{user}"
                f"{('\\n\\nContext:\\n' + context) if context else ''}"),
            "parameters": {"max_new_tokens": 512, "temperature": 0.4,
                           "return_full_text": False},
        }

    def _parse_response(self, data):
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            text = data.get("generated_text", "") or data.get("text", "")
        else:
            text = ""
        return {"text": str(text).strip(), "tool_calls": []}
