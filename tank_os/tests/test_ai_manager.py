"""pytest suite for :mod:`tank_os.core.ai_manager`."""
from __future__ import annotations

import pytest

from tank_os.core.ai_manager import (
    AIProvider,
    AIProviderError,
    AIResponse,
    AIManager,
    EchoProvider,
    LocalStubProvider,
)


# ───────────────────────────────────────────────────────────────────────────
# Provider registry
# ───────────────────────────────────────────────────────────────────────────

def test_initialize_registers_local_stub_by_default():
    ai = AIManager()
    ai.initialize()
    assert ai.default_provider == "local-stub"
    names = {p["name"] for p in ai.list_providers()}
    assert "local-stub" in names


def test_register_provider_must_subclass_interface():
    ai = AIManager()
    ai.initialize()
    with pytest.raises(TypeError):
        ai.register_provider("bogus", object())  # not AIProvider
    with pytest.raises(ValueError):
        ai.register_provider("", EchoProvider())  # empty name


def test_register_then_unregister_provider():
    ai = AIManager()
    ai.initialize()
    ai.register_provider("echo", EchoProvider())
    assert "echo" in {p["name"] for p in ai.list_providers()}
    assert ai.unregister_provider("echo") is True
    assert "echo" not in {p["name"] for p in ai.list_providers()}


def test_local_stub_cannot_be_unregistered():
    ai = AIManager()
    ai.initialize()
    assert ai.unregister_provider("local-stub") is False
    assert "local-stub" in {p["name"] for p in ai.list_providers()}


def test_set_default_unknown_provider_is_rejected():
    ai = AIManager()
    ai.initialize()
    assert ai.set_default("does-not-exist") is False
    assert ai.default_provider == "local-stub"


def test_register_with_set_default_promotes_to_default():
    ai = AIManager()
    ai.initialize()
    ai.register_provider("echo", EchoProvider(), set_default=True)
    assert ai.default_provider == "echo"


# ───────────────────────────────────────────────────────────────────────────
# Dispatch (chat)
# ───────────────────────────────────────────────────────────────────────────

def test_chat_dispatch_with_echo_event_payload(event_catcher):
    catcher = event_catcher("ai_request_started",
                            "ai_response_complete",
                            "ai_error")
    ai = AIManager()
    ai.initialize()
    ai.register_provider("echo", EchoProvider(), set_default=True)
    resp = ai.chat("ping")
    assert isinstance(resp, AIResponse)
    assert resp.text == "ping"
    assert resp.provider == "echo"
    assert resp.duration_ms >= 0
    assert len(catcher.of("ai_request_started")) == 1
    assert len(catcher.of("ai_response_complete")) == 1
    assert catcher.count("ai_error") == 0


def test_chat_falls_back_to_local_stub_for_missing_provider(event_catcher):
    catcher = event_catcher("ai_response_complete")
    ai = AIManager()
    ai.initialize()
    resp = ai.chat("hi", provider="no-such-provider")
    assert resp.provider == "local-stub"
    assert "[stub]" in resp.text
    assert len(catcher.of("ai_response_complete")) == 1


def test_chat_propagates_provider_exception(event_catcher):
    catcher = event_catcher("ai_error")
    ai = AIManager()
    ai.initialize()

    class BoomProvider(AIProvider):
        def __init__(self):
            super().__init__("boom")
        def chat(self, text, **kwargs):
            raise RuntimeError("kaboom")

    ai.register_provider("boom", BoomProvider(), set_default=True)
    with pytest.raises(AIProviderError) as exc_info:
        ai.chat("x")
    assert "kaboom" in str(exc_info.value)
    assert len(catcher.of("ai_error")) == 1


def test_chat_with_local_stub_returns_marker(event_catcher):
    ai = AIManager()
    ai.initialize()
    resp = ai.chat("tell me a joke")
    assert resp.provider == "local-stub"
    # LocalStubProvider echoes the input bound to its max_tokens budget.
    assert resp.text.startswith("[stub]")


# ───────────────────────────────────────────────────────────────────────────
# Streaming
# ───────────────────────────────────────────────────────────────────────────

def test_stream_yields_chunks_and_emits_token_events(event_catcher):
    catcher = event_catcher("ai_token_received",
                            "ai_response_complete")
    ai = AIManager()
    ai.initialize()

    class WordsProvider(AIProvider):
        def __init__(self):
            super().__init__("words")
        def chat(self, text, **kwargs):
            return " ".join(text.split())
        def stream(self, text, **kwargs):
            for tok in text.split():
                yield tok

    ai.register_provider("words", WordsProvider(), set_default=True)
    gen = ai.stream("alpha beta gamma")
    chunks = list(gen)
    assert chunks == ["alpha", "beta", "gamma"]
    assert len(catcher.of("ai_token_received")) == 3
    [event] = catcher.of("ai_response_complete")
    assert event.data["stream"] is True
    # Production streams join chunks without a separator.
    assert event.data["text"] == "alphabetagamma"


# ───────────────────────────────────────────────────────────────────────────
# History + introspection
# ───────────────────────────────────────────────────────────────────────────

def test_recent_requests_and_responses_bounded():
    ai = AIManager()
    ai.initialize()
    for i in range(60):
        ai.chat(f"msg-{i}")
    requests = ai.recent_requests(limit=100)
    responses = ai.recent_responses(limit=100)
    assert len(requests) == 50  # bounded by _max_history
    assert len(responses) == 50
    assert requests[-1]["text"] == "msg-59"


def test_summary_reports_provider_count():
    ai = AIManager()
    ai.initialize()
    ai.chat("a")
    ai.chat("b")
    s = ai.summary()
    assert s["default"] == "local-stub"
    assert "local-stub" in s["providers"]
    assert s["requests"] >= 2
    assert s["responses"] >= 2


def test_provider_status_for_unknown_returns_unavailable():
    ai = AIManager()
    ai.initialize()
    info = ai.provider_status("does-not-exist")
    assert info["available"] is False


def test_local_stub_provider_status_offline():
    p = LocalStubProvider()
    info = p.get_status()
    assert info["offline"] is True
    assert info["available"] is True
    assert info["name"] == "local-stub"


# ───────────────────────────────────────────────────────────────────────────
# Sanity
# ───────────────────────────────────────────────────────────────────────────

def test_echo_provider_returns_input_unchanged():
    p = EchoProvider()
    assert p.chat("same text") == "same text"
