"""pytest suite for :mod:`tank_os.shell.terminal.engine`."""
from __future__ import annotations

import subprocess
import time
from typing import List, Tuple

import pytest

from tank_os.shell.terminal.ai_router import AIRouter, AIReply
from tank_os.shell.terminal.engine import (
    CommandResult, Executor, SubprocessExecutor, TerminalEngine,
)
from tank_os.shell.terminal.history import CommandHistory
from tank_os.shell.terminal.safety import CommandSafety, SafetyClass


# ───────────────────────────────────────────────────────────────────────────
# Test doubles
# ───────────────────────────────────────────────────────────────────────────

class _ScriptedAI:
    """Drop-in for :class:`AIRouter` that returns scripted replies."""

    def __init__(self, replies: List[AIReply]) -> None:
        self._replies = list(replies)
        self.calls: List[str] = []

    def natural_to_shell(self, text: str):
        self.calls.append(text)
        if not self._replies:
            return None
        return self._replies.pop(0)

    def explain_error(self, command: str, stderr: str) -> str:
        return f"AI: command {command!r} failed because {stderr!r}"


class _FakeExecutor(Executor):
    """Executor that returns a scripted (stdout, stderr, rc) tuple."""

    def __init__(self, scripts: List[Tuple[str, str, int]],
                 *, sleep_s: float = 0.0,
                 raise_timeout: bool = False) -> None:
        self._scripts = list(scripts)
        self.calls: List[str] = []
        self._sleep_s = sleep_s
        self._raise_timeout = raise_timeout

    def execute(self, command: str, *, timeout_s: float):
        self.calls.append(command)
        time.sleep(self._sleep_s)
        if self._raise_timeout:
            raise subprocess.TimeoutExpired(command, timeout_s)
        if not self._scripts:
            return "", "", 0
        return self._scripts.pop(0)


def _build_engine(*, ai=None, executor=None) -> TerminalEngine:
    if executor is None:
        executor = _FakeExecutor([])
    return TerminalEngine(
        safety=CommandSafety(),
        history=CommandHistory(),
        ai=ai or _ScriptedAI([]),
        executor_factory=lambda: executor,
        default_timeout_s=2.0,
    )


# ───────────────────────────────────────────────────────────────────────────
# parse
# ───────────────────────────────────────────────────────────────────────────

def test_parse_strips_exclamation_prefix():
    assert TerminalEngine.parse("!ls -la") == "ls -la"


def test_parse_preserves_sentence_without_prefix():
    assert TerminalEngine.parse("list files") == "list files"


def test_parse_returns_empty_on_blank():
    assert TerminalEngine.parse("") == ""
    assert TerminalEngine.parse("    ") == ""
    assert TerminalEngine.parse("!") == ""


def test_parse_strips_surrounding_whitespace():
    assert TerminalEngine.parse("   ! ls -la  ") == "ls -la"


# ───────────────────────────────────────────────────────────────────────────
# interpret
# ───────────────────────────────────────────────────────────────────────────

def test_interpret_empty_input_returns_error():
    engine = _build_engine()
    result = engine.interpret("")
    assert not result.command
    assert result.error == "empty input"


def test_interpret_blocks_known_dangerous_pattern():
    engine = _build_engine()
    result = engine.interpret("!rm -rf /")
    assert result.error.startswith("⛔")
    assert result.safety_class is SafetyClass.BLOCKED


def test_interpret_routes_natural_language_through_ai():
    ai = _ScriptedAI([AIReply(command="ls -la /tmp",
                              explanation="list /tmp")])
    engine = _build_engine(ai=ai)
    result = engine.interpret("show me /tmp")
    assert result.command == "ls -la /tmp"
    assert result.safety_class is SafetyClass.READ
    assert not result.pending_confirmation


def test_interpret_explicit_bang_skips_ai():
    ai = _ScriptedAI([AIReply(command="WRONG", explanation="x")])
    engine = _build_engine(ai=ai)
    result = engine.interpret("!ls -la /tmp")
    assert result.command == "ls -la /tmp"
    assert not ai.calls             # AI wasn't asked


def test_interpret_mutating_requires_confirmation():
    engine = _build_engine()
    result = engine.interpret("!mkdir build")
    assert result.pending_confirmation
    assert result.safety_class is SafetyClass.MUTATING


def test_interpret_dangerous_requires_confirmation():
    engine = _build_engine()
    # Real `sudo` + dangerous verb — `chown` is in DANGEROUS_VERBS,
    # and `_first_token` skips the `sudo` prefix to find `chown`.
    result = engine.interpret("!sudo chown root:root /etc/shadow")
    assert result.pending_confirmation
    assert result.safety_class is SafetyClass.DANGEROUS


def test_interpret_reclassifies_ai_expansion_to_dangerous():
    """If the AI expands an NL goal to a dangerous verb, we MUST re-classify."""
    ai = _ScriptedAI([AIReply(command="sudo rm -rf /tmp/foo",
                              explanation="x")])
    engine = _build_engine(ai=ai)
    result = engine.interpret("delete that tmp folder please")
    assert result.safety_class is SafetyClass.DANGEROUS
    assert result.pending_confirmation


# ───────────────────────────────────────────────────────────────────────────
# run
# ───────────────────────────────────────────────────────────────────────────

def test_run_uses_injected_executor_and_records_history():
    exe = _FakeExecutor([("hello\n", "", 0)])
    engine = _build_engine(executor=exe)
    result = engine.run("echo hello")
    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    assert exe.calls == ["echo hello"]
    assert engine.get_history()[-1] == "echo hello"


def test_run_records_stderr_and_failure_in_history():
    exe = _FakeExecutor([("", "Permission denied", 1)])
    engine = _build_engine(executor=exe)
    result = engine.run("cat /etc/shadow")
    assert result.exit_code == 1
    assert "denied" in result.stderr
    history = engine.get_history()
    assert history[-1] == "cat /etc/shadow"


def test_run_falls_through_safety_classification():
    engine = _build_engine()
    result = engine.run("rm -rf /")
    assert result.error.startswith("⛔")
    assert result.exit_code is None


def test_run_handles_timeout_from_executor():
    exe = _FakeExecutor([], raise_timeout=True)
    engine = _build_engine(executor=exe)
    result = engine.run("sleep 10")
    assert result.timed_out
    assert result.exit_code is None


def test_run_handles_executor_exception():
    class _CrashExecutor(Executor):
        def execute(self, command, *, timeout_s):
            raise OSError("spawn failed")
    engine = _build_engine(executor=_CrashExecutor())
    result = engine.run("any-cmd")
    assert result.exit_code is None
    assert "spawn failed" in result.error


# ───────────────────────────────────────────────────────────────────────────
# confirm_and_run flow
# ───────────────────────────────────────────────────────────────────────────

def test_confirm_and_run_without_pending_returns_error():
    engine = _build_engine()
    result = engine.confirm_and_run(allowed=True)
    assert result.error == "no command awaiting confirmation"


def test_confirm_and_run_yes_executes():
    exe = _FakeExecutor([("ok\n", "", 0)])
    engine = _build_engine(executor=exe)
    engine.interpret("!mkdir build")  # pending
    result = engine.confirm_and_run(allowed=True)
    assert result.exit_code == 0
    assert exe.calls == ["mkdir build"]


def test_confirm_and_run_no_skips_execution():
    exe = _FakeExecutor([])
    engine = _build_engine(executor=exe)
    engine.interpret("!mkdir build")
    result = engine.confirm_and_run(allowed=False)
    assert "cancelled" in result.error
    assert exe.calls == []           # executor never invoked


# ───────────────────────────────────────────────────────────────────────────
# History
# ───────────────────────────────────────────────────────────────────────────

def test_history_recall_returns_relevant_command():
    exe = _FakeExecutor([
        ("", "", 0),
        ("", "", 0),
        ("", "", 0),
    ])
    engine = _build_engine(executor=exe)
    engine.run("rm -rf /tmp/leftover")
    engine.run("grep -r TODO docs/")
    engine.run("ls /tmp")
    hits = engine.recall_history("TODO")
    assert "grep -r TODO docs/" in hits


def test_explain_last_error_returns_ai_text():
    exe = _FakeExecutor([("", "Unterminated quote", 1)])
    ai = _ScriptedAI([])
    engine = _build_engine(ai=ai, executor=exe)
    engine.run("echo hi")  # capture a failed history entry
    explanation = engine.explain_last_error()
    assert explanation.startswith("AI:")
    assert "echo hi" in explanation


def test_explain_last_error_when_no_failures():
    exe = _FakeExecutor([("ok\n", "", 0)])
    engine = _build_engine(executor=exe)
    engine.run("echo hi")
    assert engine.explain_last_error() == ""


# ───────────────────────────────────────────────────────────────────────────
# Real subprocess (no Qt, no PTY) — confirms the wiring works at all.
# ───────────────────────────────────────────────────────────────────────────

def test_subprocess_executor_runs_echo():
    out, err, rc = SubprocessExecutor().execute("echo hello", timeout_s=2.0)
    assert rc == 0
    assert out.strip() == "hello"
    assert err == ""
