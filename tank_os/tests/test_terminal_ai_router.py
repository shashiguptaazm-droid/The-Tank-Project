"""pytest suite for :mod:`tank_os.shell.terminal.ai_router`."""
from __future__ import annotations

import json

import pytest

from tank_os.core.ai_manager import (
    AIProvider, AIResponse, AIManager,
)
from tank_os.shell.terminal.ai_router import AIReply, AIRouter, _decode_reply


# ───────────────────────────────────────────────────────────────────────────
# Reply decoder
# ───────────────────────────────────────────────────────────────────────────

def test_decode_strict_json_returns_command():
    reply = _decode_reply(json.dumps({"command": "ls -la", "explanation": "list"}))
    assert isinstance(reply, AIReply)
    assert reply.command == "ls -la"
    assert reply.explanation == "list"


def test_decode_stripped_json_fences():
    reply = _decode_reply(
        "```json\n" + json.dumps({"command": "echo hi"}) + "\n```"
    )
    assert reply is not None
    assert reply.command == "echo hi"


def test_decode_extracts_first_json_block_from_chatter():
    body = (
        "Sure! Here you go:\n"
        + json.dumps({"command": "ls -la", "explanation": "list files"})
        + "\nHope that helps!"
    )
    reply = _decode_reply(body)
    assert reply is not None
    assert reply.command == "ls -la"
    assert reply.explanation == "list files"


def test_decode_empty_command_field_returns_none():
    body = json.dumps({"command": "", "explanation": "ambiguous"})
    assert _decode_reply(body) is None


def test_decode_falls_back_to_first_known_verb():
    body = "I think you want: `ls -la /etc`"
    reply = _decode_reply(body)
    assert reply is not None
    assert reply.command == "ls -la /etc"


def test_decode_returns_none_for_unparseable_text():
    assert _decode_reply("just a chatty response, no commands") is None


def test_decode_handles_dict_with_extra_keys():
    body = json.dumps({"command": "pwd", "explanation": "x",
                       "extra": "ignored"})
    reply = _decode_reply(body)
    assert reply is not None
    assert reply.command == "pwd"


# ───────────────────────────────────────────────────────────────────────────
# AIRouter integration (with a deterministic fake provider)
# ───────────────────────────────────────────────────────────────────────────

class _ScriptedProvider(AIProvider):
    """Test provider: returns the next canned reply per call."""

    def __init__(self, script):
        super().__init__("scripted")
        self._script = list(script)
        self.calls = []

    def chat(self, text, *, system_prompt=None, **kwargs):
        self.calls.append({"text": text, "system_prompt": system_prompt})
        if not self._script:
            raise RuntimeError("no more canned replies")
        return self._script.pop(0)


def _attach_provider(manager: AIManager, provider, *, default: bool = True):
    manager.register_provider(provider.name, provider, set_default=default)


def test_airouter_natural_to_shell_happy_path():
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, _ScriptedProvider([
        json.dumps({"command": "ls -la /tmp", "explanation": "list /tmp"}),
    ]), default=True)
    router = AIRouter(ai=ai)
    reply = router.natural_to_shell("show me /tmp contents")
    assert reply is not None
    assert reply.command == "ls -la /tmp"


def test_airouter_returns_none_when_ai_offers_no_command():
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, _ScriptedProvider([
        json.dumps({"command": "", "explanation": "ambiguous"}),
    ]), default=True)
    router = AIRouter(ai=ai)
    assert router.natural_to_shell("what is love") is None


def test_airouter_falls_through_when_ai_raises():
    class _Boom(AIProvider):
        def __init__(self):
            super().__init__("boom")
        def chat(self, text, **kwargs):
            raise RuntimeError("kaboom")
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, _Boom(), default=True)
    router = AIRouter(ai=ai)
    assert router.natural_to_shell("anything") is None


def test_airouter_explain_error_returns_ai_text():
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, _ScriptedProvider([
        "You forgot the closing quote; try `ls \"/tmp\"`.",
    ]), default=True)
    router = AIRouter(ai=ai)
    explanation = router.explain_error("ls /tmp", "Unterminated quoted string")
    assert "closing quote" in explanation
    assert "ls" in explanation


def test_airouter_explain_error_returns_empty_on_failure():
    class _Boom(AIProvider):
        def __init__(self):
            super().__init__("boom")
        def chat(self, text, **kwargs):
            raise RuntimeError("kaboom")
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, _Boom(), default=True)
    router = AIRouter(ai=ai)
    assert router.explain_error("foo", "bar") == ""


def test_airouter_system_prompt_includes_goal():
    """The router should put the goal in the body so the AI sees it."""
    provider = _ScriptedProvider([
        json.dumps({"command": "ls"}),
    ])
    ai = AIManager()
    ai.initialize()
    _attach_provider(ai, provider, default=True)
    router = AIRouter(ai=ai)
    router.natural_to_shell("list files")
    assert provider.calls, "provider was not called"
    prompt = provider.calls[0]["text"]
    assert "list files" in prompt
    assert "Goal:" in prompt
