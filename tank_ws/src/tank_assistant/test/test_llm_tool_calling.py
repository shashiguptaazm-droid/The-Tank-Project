"""Tool-calling tests for the assistant LLM node.

These tests cover the tool-calling layer WITHOUT spinning up ROS:
- The scan-based parser (markdown-fence + bare-JSON fallback).
- The system-prompt builder.
- The state machine (via LlmNode with stubbed engine + stubbed
  ``requests.post``).
- The 2nd LLM synthesis pass for read-class tools.

ROS is imported lazily so the suite runs on a plain Python dev box.
"""
from __future__ import annotations

import json
import os
import sys
from unittest import mock

import pytest


# ── Path setup so the parent package can be imported ──────────────────────
# ROS 2 ament_python layout:
#   tank_ws/src/tank_assistant/         <- top-level ROS package
#     tank_assistant/                    <- inner Python module
#       llm_node.py
#       external_llm_client.py
#     test/test_llm_tool_calling.py      <- us
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC_PARENT = os.path.abspath(os.path.join(_HERE, "..", ".."))  # tank_ws/src/
if _SRC_PARENT not in sys.path:
    sys.path.insert(0, _SRC_PARENT)

from tank_assistant import llm_node  # noqa: E402

# Reuse the in-module String stub when rclpy is unavailable — avoids
# duplicating the constructor logic in the test file.
String = llm_node.String


class _RecordingEngine:
    """Captures every prompt the LLM node makes and replays scripted replies."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def prompt(self, system: str, user: str, max_tokens: int) -> str:
        self.prompts.append((system, user))
        if self.replies:
            return self.replies.pop(0)
        return ""


_MOVE_TOOL = {
    "name": "move",
    "rate_class": "write",
    "description": "drive the base",
    "parameters": {"type": "object"},
}
_TELEMETRY_TOOL = {
    "name": "telemetry",
    "rate_class": "read",
    "description": "aggregate health read",
    "parameters": {"type": "object"},
}
_FAKE_MANIFEST = {"tools": [_MOVE_TOOL, _TELEMETRY_TOOL]}


# ── pytest fixtures — patches persist for the whole test ─────────────────

@pytest.fixture
def manifest_mock():
    """Patch _load_manifest() so __init__ doesn't try to reach the bridge."""
    with mock.patch.object(llm_node, "_load_manifest",
                           return_value=_FAKE_MANIFEST):
        yield _FAKE_MANIFEST


@pytest.fixture
def exec_mock():
    """Patch LlmNode._execute_tool so tests don't hit the network."""
    with mock.patch.object(llm_node.LlmNode, "_execute_tool",
                           return_value={"ok": True}) as m:
        yield m


@pytest.fixture
def llm_node_factory(manifest_mock, exec_mock):
    """Returns a callable that builds a fully-configured LlmNode.

    Using a factory (rather than a fixture returning a single node) lets
    each test build its own node with a custom engine, while the patches
    stay active for the duration of the test.
    """
    def _make(engine, *, bridge_url="http://bridge:8082",
              api_key="test-key", confirm_timeout_s=15.0,
              tools_enabled=True):
        node = llm_node.LlmNode(engine=engine)
        node._bridge_url = bridge_url
        node._api_key = api_key
        node._confirm_timeout_s = confirm_timeout_s
        node._tools_enabled = tools_enabled
        node._state = llm_node.ST_IDLE
        node._pending_cmd = None
        node._pending_intent = ""
        node._pending_ts = 0.0
        return node

    return _make


def _capture_publisher(node) -> list:
    """Replace ``node._reply_pub`` with one that records published strings."""
    published = []

    def _cap(msg):
        # msg is a _StubString with .data attribute
        published.append(msg.data if hasattr(msg, "data") else str(msg))

    node._reply_pub = mock.Mock(publish=_cap)
    return published


# ══════════════════════════════════════════════════════════════════════════
# Parser tests — pure functions, no node needed
# ══════════════════════════════════════════════════════════════════════════

def test_parse_tool_calls_primary_fence():
    text = (
        "Sure thing, I'll move forward.\n"
        "```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```\n"
        "Let me know if that helps."
    )
    calls = llm_node.parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "move"
    assert calls[0]["params"] == {"vx": 0.2, "wz": 0, "duration_s": 2.0}


def test_parse_tool_calls_fallback_bare_json():
    text = (
        "Let's check telemetry real quick "
        '{"name": "telemetry", "params": {}}'
    )
    calls = llm_node.parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "telemetry"
    assert calls[0]["params"] == {}


def test_parse_tool_calls_malformed_skipped():
    r"""Regression: a malformed block must not swallow the next valid one.

    The buggy regex used DOTALL non-greedy ``\{.*?\}`` which would span
    from one fence to the next when the first body had no closing
    brace. The scan-based parser finds fence boundaries first, so each
    block is independent.
    """
    text = (
        "```tool_call\n"
        "{this is not valid json"
        "```\n"
        "```tool_call\n"
        '{"name": "chat", "params": {"text": "hi"}}\n'
        "```"
    )
    calls = llm_node.parse_tool_calls(text)
    assert len(calls) == 1, f"expected 1 valid call, got {len(calls)}: {calls}"
    assert calls[0]["name"] == "chat"
    assert calls[0]["params"] == {"text": "hi"}


def test_parse_tool_calls_empty_returns_empty_list():
    assert llm_node.parse_tool_calls("") == []
    assert llm_node.parse_tool_calls("just prose, no tools") == []
    assert llm_node.parse_tool_calls(None) == []  # type: ignore[arg-type]


def test_parse_tool_calls_multiple_returns_all_valid():
    text = (
        "```tool_call\n"
        '{"name": "telemetry", "params": {}}\n'
        "```\n"
        "```tool_call\n"
        '{"name": "chat", "params": {"text": "hi"}}\n'
        "```"
    )
    calls = llm_node.parse_tool_calls(text)
    assert len(calls) == 2
    assert {c["name"] for c in calls} == {"telemetry", "chat"}


# ══════════════════════════════════════════════════════════════════════════
# System-prompt builder
# ══════════════════════════════════════════════════════════════════════════

def test_build_system_prompt_contains_all_tools():
    manifest = {
        "tools": [
            {"name": "move", "description": "Drive the base.",
             "rate_class": "write", "parameters": {"type": "object"}},
            {"name": "telemetry", "description": "Read state.",
             "rate_class": "read", "parameters": {"type": "object"}},
        ],
    }
    prompt = llm_node.build_system_prompt(
        manifest, identity="You are Tank.", confirm=True,
    )
    assert "You are Tank." in prompt
    assert "**move**" in prompt
    assert "**telemetry**" in prompt
    assert "Drive the base." in prompt
    assert "Read state." in prompt
    assert "```tool_call" in prompt
    assert "confirmation" in prompt.lower()


def test_build_system_prompt_no_tools_falls_back_to_identity():
    prompt = llm_node.build_system_prompt(
        {"tools": []}, identity="Just me.", confirm=True,
    )
    assert prompt == "Just me."


# ══════════════════════════════════════════════════════════════════════════
# State machine — write-class tools
# ══════════════════════════════════════════════════════════════════════════

def test_state_machine_write_tool_awaits_then_executes_on_yes(llm_node_factory):
    """Move call → AWAIT_CONFIRM; user says 'yes' → EXECUTING → IDLE.

    The exec_mock fixture patches ``LlmNode._execute_tool`` for the
    whole test. With the previous ``_build_node`` helper the patch
    context manager exited at function return, so the second
    ``_on_intent`` call hit the unmocked real ``_execute_tool`` and
    the assertion at the end saw ``call_count == 0``.
    """
    engine = _RecordingEngine([
        "Moving now.\n```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```",
    ])
    node = llm_node_factory(engine)
    published = _capture_publisher(node)

    node._on_intent(String(data="please move forward"))
    assert node._state == llm_node.ST_AWAIT_CONFIRM
    assert llm_node.LlmNode._execute_tool.call_count == 0, \
        "must NOT execute before confirmation"
    assert any("move" in p.lower() for p in published), \
        f"confirmation text must mention the tool name, got: {published}"

    published.clear()
    node._on_intent(String(data="yes"))
    assert node._state == llm_node.ST_IDLE
    assert llm_node.LlmNode._execute_tool.call_count == 1, \
        "executes after confirmation"
    args, _ = llm_node.LlmNode._execute_tool.call_args
    assert args[0] == "move"
    assert args[1]["vx"] == 0.2


def test_state_machine_write_tool_rejects_on_no(llm_node_factory):
    engine = _RecordingEngine([
        "```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```",
    ])
    node = llm_node_factory(engine)
    published = _capture_publisher(node)
    node._on_intent(String(data="go forward"))
    assert node._state == llm_node.ST_AWAIT_CONFIRM
    node._on_intent(String(data="no"))
    assert node._state == llm_node.ST_IDLE
    assert llm_node.LlmNode._execute_tool.call_count == 0, \
        "must NOT execute on no"
    assert any("cancelled" in p.lower() for p in published)


def test_write_class_does_not_trigger_synthesis(llm_node_factory):
    """Regression: write-class tools must publish a terse 'Done.' and NOT
    call ``engine.prompt`` a second time for synthesis. Read-class tools
    DO trigger synthesis (see ``test_read_class_triggers...``).
    """
    engine = _RecordingEngine([
        # 1st prompt: tool-call decision
        "```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```",
    ])
    node = llm_node_factory(engine)
    published = _capture_publisher(node)
    node._on_intent(String(data="please move forward"))
    assert node._state == llm_node.ST_AWAIT_CONFIRM
    # Exactly one LLM call so far (the tool-decision one).
    assert len(engine.prompts) == 1, \
        f"write-class path should not synthesize, got {len(engine.prompts)} prompts"
    node._on_intent(String(data="yes"))
    # Still exactly one — confirmation + exec, no synthesis.
    assert len(engine.prompts) == 1, \
        "confirmation + exec must NOT trigger a 2nd LLM call"
    assert llm_node.LlmNode._execute_tool.call_count == 1
    assert published[-1] == "Done."


def test_state_machine_timeout_aborts_confirmation(llm_node_factory):
    """Use ``mock.patch`` on ``time.monotonic`` for deterministic time travel.

    ``time.sleep`` is unreliable on slow CI — the test should not depend
    on the OS actually pausing for >= 50 ms.
    """
    engine = _RecordingEngine([
        "```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```",
    ])
    node = llm_node_factory(engine, confirm_timeout_s=5.0)
    published = _capture_publisher(node)

    # Mock time.monotonic — 0 when entering AWAIT_CONFIRM, then a far-future
    # value when checking the timeout on the next user reply.
    times = iter([0.0, 100.0])
    with mock.patch("time.monotonic", side_effect=lambda: next(times)):
        node._on_intent(String(data="go"))
        assert node._state == llm_node.ST_AWAIT_CONFIRM
        node._on_intent(String(data="yes"))
    assert node._state == llm_node.ST_IDLE
    assert llm_node.LlmNode._execute_tool.call_count == 0, \
        "must NOT execute after timeout"
    assert any("timed out" in p.lower() for p in published)


# ══════════════════════════════════════════════════════════════════════════
# Read-class tool → 2nd LLM synthesis
# ══════════════════════════════════════════════════════════════════════════

def test_read_class_triggers_synthesis_with_tool_result(llm_node_factory):
    """Telemetry call → execute immediately → 2nd LLM call for synthesis."""
    engine = _RecordingEngine([
        # 1st prompt: tool-call decision
        "```tool_call\n"
        '{"name": "telemetry", "params": {}}\n'
        "```",
        # 2nd prompt: synthesis of result
        "Battery is at 52 percent.",
    ])
    node = llm_node_factory(engine)
    # Override _execute_tool on the instance to return a fake payload.
    with mock.patch.object(node, "_execute_tool",
                            return_value={"battery_pct": 52, "ok": True}):
        published = _capture_publisher(node)
        node._on_intent(String(data="how's the battery?"))
        # 2nd prompt fired
        assert len(engine.prompts) == 2
        # Synthesis system prompt must contain the tool result JSON
        synth_system = engine.prompts[1][0]
        assert "telemetry" in synth_system
        assert "52" in synth_system
        # And the published reply must be the synthesis text
        assert published[-1] == "Battery is at 52 percent."


# ══════════════════════════════════════════════════════════════════════════
# Plain-text and tools-disabled paths
# ══════════════════════════════════════════════════════════════════════════

def test_plain_text_reply_published_directly(llm_node_factory):
    engine = _RecordingEngine(["I'm feeling great today!"])
    node = llm_node_factory(engine)
    published = _capture_publisher(node)
    node._on_intent(String(data="how are you?"))
    assert llm_node.LlmNode._execute_tool.call_count == 0
    assert published == ["I'm feeling great today!"]
    assert node._state == llm_node.ST_IDLE


def test_tools_disabled_skips_parsing(llm_node_factory):
    engine = _RecordingEngine([
        "```tool_call\n"
        '{"name": "move", "params": {"vx": 0.2, "wz": 0, "duration_s": 2.0}}\n'
        "```",
    ])
    node = llm_node_factory(engine, tools_enabled=False)
    published = _capture_publisher(node)
    node._on_intent(String(data="go"))
    assert llm_node.LlmNode._execute_tool.call_count == 0, \
        "must NOT execute when tools disabled"
    # Raw text gets echoed back
    assert any("tool_call" in p for p in published)


# ══════════════════════════════════════════════════════════════════════════
# HTTP envelope — checks headers + body for the bridge
# ══════════════════════════════════════════════════════════════════════════

def test_execute_tool_uses_audit_id_envelope():
    """Direct call to ``_execute_tool`` checks the body envelope.

    Not using the ``llm_node_factory`` fixture here — we want to call
    ``_execute_tool`` directly without spinning up the rest of the node.
    """
    engine = _RecordingEngine([])
    with mock.patch.object(llm_node, "_load_manifest",
                            return_value=_FAKE_MANIFEST):
        node = llm_node.LlmNode(engine=engine)
        node._api_key = "secret-key"
        node._bridge_url = "http://bridge:8082"
        node._tools_enabled = True

        fake_resp = mock.Mock(status_code=200)
        fake_resp.json.return_value = {"vx_eff": 0.2}
        fake_resp.raise_for_status = mock.Mock()
        with mock.patch.object(llm_node.requests, "post",
                                return_value=fake_resp) as post_mock:
            node._execute_tool("move",
                               {"vx": 0.2, "wz": 0, "duration_s": 2.0})
        args, kwargs = post_mock.call_args
        assert args[0] == "http://bridge:8082/api/cmd/move"
        assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
        body = kwargs["json"]
        assert "audit_id" in body
        assert body["params"] == {"vx": 0.2, "wz": 0, "duration_s": 2.0}
        # audit_id must look like a uuid4
        import uuid as _uuid
        _uuid.UUID(body["audit_id"], version=4)
