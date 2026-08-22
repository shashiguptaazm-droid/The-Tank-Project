"""Tests for tank_assistant.external_llm_client.

Mocks httpx at the module level so we never hit the network even when
httpx is installed.  Asserts the request payload structure AND the
parsed-response mapping for each provider.
"""
from __future__ import annotations

import os
import sys

# Path injection — let this test find the sibling tank_assistant
# package when pytest is invoked from inside tank_command_bridge/.
HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_PARENT = os.path.normpath(os.path.join(HERE, "..", ".."))
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)

import pytest  # noqa: E402

# pytest.importorskip is the idiomatic, side-effect-free way to skip
# the whole module when a peer package is missing (avoids noisy
# ModuleNotFoundError at collection). Use it BEFORE the heavy import.
pytest.importorskip("tank_assistant.external_llm_client",
                     reason="tank_assistant sibling package not importable in this env")

from tank_assistant.external_llm_client import (  # noqa: E402
    AnthropicProvider,
    BaseProvider,
    FreebuffProvider,
    OpenAIProvider,
    build_provider,
)


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("simulated http failure")


def test_openai_provider_payload_and_returns_first_choice(monkeypatch):
    p = OpenAIProvider("sk-test", model="gpt-test")
    captured = {}

    def fake_post(self, url, **kw):
        captured["url"] = url
        captured["headers"] = kw.get("headers")
        captured["body"] = kw.get("json")
        return _FakeResponse({
            "choices": [{"message": {"content": "hello"}}],
        })

    monkeypatch.setattr("httpx.Client.post", fake_post)
    out = p.prompt(system="sys", user="hi")
    assert out == "hello"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    msgs = captured["body"]["messages"]
    assert msgs[0]["role"] == "system"
    assert "sys" in msgs[0]["content"]
    assert msgs[1]["content"] == "hi"


def test_anthropic_provider_payload_uses_messages_and_extracts_text(monkeypatch):
    p = AnthropicProvider("sk-ant-test", model="claude-test")
    captured = {}

    def fake_post(self, url, **kw):
        captured["body"] = kw.get("json")
        captured["headers"] = kw.get("headers")
        return _FakeResponse({
            "content": [
                {"type": "text", "text": "hi from claude"},
                {"type": "tool_use", "name": "irrelevant"},
            ]
        })

    monkeypatch.setattr("httpx.Client.post", fake_post)
    out = p.prompt(system="sys", user="hi")
    assert out == "hi from claude"
    assert captured["headers"]["x-api-key"] == "sk-ant-test"
    assert captured["body"]["system"] == "sys"
    assert captured["body"]["messages"][0]["role"] == "user"


def test_freebuff_provider_is_openai_shaped(monkeypatch):
    p = FreebuffProvider("fb-test", model="fb-default")
    captured = {}

    def fake_post(self, url, **kw):
        captured["url"] = url
        return _FakeResponse({
            "choices": [{"message": {"content": "fb hi"}}]
        })

    monkeypatch.setattr("httpx.Client.post", fake_post)
    out = p.prompt(system="sys", user="hi")
    assert out == "fb hi"
    # Defaults to Freebuff's gateway
    assert "freebuff.com" in captured["url"] or \
           captured["url"].startswith(p.base_url)


def test_provider_timeout_surfaces_as_runtime_error(monkeypatch):
    p = OpenAIProvider("sk-test")

    def fake_post(self, url, **kw):
        raise RuntimeError("simulated network timeout")

    monkeypatch.setattr("httpx.Client.post", fake_post)
    with pytest.raises(RuntimeError):
        p.prompt(system="sys", user="hi")


def test_build_provider_auto_selects_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("FREEBUFF_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = build_provider()
    assert isinstance(p, OpenAIProvider)
    assert p.api_key == "sk-test"


def test_build_provider_returns_none_when_no_keys(monkeypatch):
    monkeypatch.delenv("FREEBUFF_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TANK_API_PROVIDER", raising=False)
    assert build_provider() is None


def test_base_provider_prompt_returns_subclass_string():
    """Abstract base — `_call` raises NotImplementedError; subclasses
    normally wire up providers."""

    class _Stub(BaseProvider):
        def _call(self, system, user, context):
            return f"{system}|{user}|{context}"

    p = _Stub()
    assert p.prompt("a", "b", "c") == "a|b|c"
