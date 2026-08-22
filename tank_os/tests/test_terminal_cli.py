"""pytest suite for :mod:`tank_os.shell.terminal.cli` — new TerminalREPL commands."""

from __future__ import annotations

import io
import sys
from typing import List, Optional

import pytest

from tank_os.shell.terminal.cli import (
    TerminalREPL,
    _bar,
    _fmt_bytes,
    _read_temps,
    _risk_icon,
    _close_matches,
    _HAS_PSUTIL,
)
from tank_os.shell.terminal.engine import (
    CommandResult,
    Executor,
    SubprocessExecutor,
    TerminalEngine,
)
from tank_os.shell.terminal.ai_router import AIRouter, AIReply
from tank_os.shell.terminal.history import CommandHistory
from tank_os.shell.terminal.safety import CommandSafety, SafetyClass


# ───────────────────────────────────────────────────────────────────────────
# Test doubles
# ───────────────────────────────────────────────────────────────────────────

class _FakeExecutor(Executor):
    """Executor that returns scripted outputs."""

    def __init__(self, scripts: Optional[List] = None):
        self._scripts = list(scripts) if scripts else [("", "", 0)]
        self.calls: List[str] = []

    def execute(self, command: str, *, timeout_s: float):
        self.calls.append(command)
        if self._scripts:
            return self._scripts.pop(0)
        return "", "", 0


def _build_repl(*, executor=None, registry_stub=None):
    """Build a TerminalREPL with injected dependencies for testing."""
    exe = executor or _FakeExecutor()
    engine = TerminalEngine(
        safety=CommandSafety(),
        history=CommandHistory(),
        executor_factory=lambda: exe,
        default_timeout_s=2.0,
    )
    repl = TerminalREPL(engine=engine)
    # Inject a fake ToolRegistry so _get_registry doesn't scan disk
    if registry_stub is not None:
        repl._registry = registry_stub
    return repl, exe


def _capture_output(fn, arg: str = "") -> str:
    """Capture printed output from a do_ method."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        fn(arg)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


# ───────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ───────────────────────────────────────────────────────────────────────────

def test_bar_full():
    assert "█" in _bar(1.0, 10)
    assert "░" not in _bar(1.0, 10)


def test_bar_empty():
    assert "█" not in _bar(0.0, 10)
    assert "░" in _bar(0.0, 10)


def test_bar_half():
    bar = _bar(0.5, 20)
    assert bar.count("█") == 10
    assert bar.count("░") == 10


def test_bar_clamps_negative():
    bar = _bar(-1.0, 5)
    assert "█" not in bar


def test_fmt_bytes():
    assert _fmt_bytes(0) == "0.0 B"
    assert _fmt_bytes(1024) == "1.0 KB"
    assert _fmt_bytes(1048576) == "1.0 MB"


def test_risk_icon_known_tiers():
    assert _risk_icon("low") == "🟢"
    assert _risk_icon("medium") == "🟡"
    assert _risk_icon("high") == "🔴"


def test_risk_icon_unknown():
    assert _risk_icon("bogus") == "⚪"


def test_close_matches_basic():
    result = _close_matches("hellp", ["hello", "help", "world"])
    assert "hello" in result or "help" in result


def test_close_matches_empty():
    assert _close_matches("anything", []) == []


# ───────────────────────────────────────────────────────────────────────────
# Tab-completion
# ───────────────────────────────────────────────────────────────────────────

def test_complete_providers_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_providers("", "providers ", 0, 10) == []


def test_complete_status_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_status("", "status ", 0, 7) == []


def test_complete_network_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_network("", "network ", 0, 8) == []


def test_complete_system_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_system("", "system ", 0, 7) == []


def test_complete_health_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_health("", "health ", 0, 7) == []


def test_complete_ps_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_ps("", "ps ", 0, 3) == []


def test_complete_clear_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_clear("", "clear ", 0, 6) == []


def test_complete_env_returns_env_vars():
    repl, _ = _build_repl()
    results = repl.complete_env("", "", 0, 0)
    assert "PATH" in results
    assert "HOME" in results


def test_complete_env_filtered():
    repl, _ = _build_repl()
    results = repl.complete_env("PA", "", 0, 0)
    assert all(r.startswith("PA") for r in results)
    assert "PATH" in results


def test_complete_df_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_df("", "df ", 0, 3) == []


def test_complete_free_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_free("", "free ", 0, 5) == []


def test_complete_uptime_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_uptime("", "uptime ", 0, 7) == []


def test_complete_ai_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_ai("", "ai ", 0, 3) == []


def test_complete_history_returns_empty():
    repl, _ = _build_repl()
    assert repl.complete_history("", "history ", 0, 8) == []


# ───────────────────────────────────────────────────────────────────────────
# do_ask — AI chat
# ───────────────────────────────────────────────────────────────────────────

def test_do_ask_empty_prompt_shows_usage():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_ask, "")
    assert "Usage" in output or "ask" in output.lower()


def test_do_ask_with_prompt_uses_ai_manager():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_ask, "hello")
    # With local-stub, we should see a response or error
    assert "🤔" in output or "AI" in output or "stub" in output.lower()


# ───────────────────────────────────────────────────────────────────────────
# do_providers — AI provider status
# ───────────────────────────────────────────────────────────────────────────

def test_do_providers_shows_local_stub():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_providers)
    assert "local-stub" in output


# ───────────────────────────────────────────────────────────────────────────
# do_status — system dashboard
# ───────────────────────────────────────────────────────────────────────────

def test_do_status_outputs_hostname():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_status)
    assert "Host:" in output or "🏠" in output


def test_do_status_outputs_time():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_status)
    assert "Time:" in output or "🕐" in output


# ───────────────────────────────────────────────────────────────────────────
# do_system — system information
# ───────────────────────────────────────────────────────────────────────────

def test_do_system_outputs_basic_info():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_system)
    assert "OS:" in output or "💻" in output


# ───────────────────────────────────────────────────────────────────────────
# do_network — network status
# ───────────────────────────────────────────────────────────────────────────

def test_do_network_outputs_hostname():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_network)
    assert "Hostname:" in output


def test_do_network_outputs_service_ports():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_network)
    assert "8080" in output or "Dashboard" in output or "service" in output.lower()


# ───────────────────────────────────────────────────────────────────────────
# do_health — health diagnostics
# ───────────────────────────────────────────────────────────────────────────

def test_do_health_outputs():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_health)
    assert "🏥" in output or "Health" in output or "Diagnostics" in output


# ───────────────────────────────────────────────────────────────────────────
# do_ps — process listing
# ───────────────────────────────────────────────────────────────────────────

def test_do_ps_outputs():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_ps)
    assert "processes" in output.lower() or "PID" in output or "python" in output.lower()


# ───────────────────────────────────────────────────────────────────────────
# do_env — environment variables
# ───────────────────────────────────────────────────────────────────────────

def test_do_env_outputs_path():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_env)
    assert "PATH" in output


def test_do_env_filtered():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_env, "HOME")
    assert "HOME=" in output


def test_do_env_unknown_filter():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_env, "ZZZZZZZ_NONEXISTENT_VAR")
    assert "no vars matching" in output.lower()


# ───────────────────────────────────────────────────────────────────────────
# do_clear — clear screen
# ───────────────────────────────────────────────────────────────────────────

def test_do_clear_outputs_escape_sequence():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_clear)
    assert "\033" in output


# ───────────────────────────────────────────────────────────────────────────
# do_df / do_free / do_uptime — system shortcuts
# ───────────────────────────────────────────────────────────────────────────

def test_do_df_runs_shell():
    repl, exe = _build_repl(executor=_FakeExecutor([("Filesystem\n/dev/sda1  100G  50G\n", "", 0)]))
    output = _capture_output(repl.do_df)
    assert "dev/sda1" in output or "Filesystem" in output
    assert exe.calls == ["df -h"]


def test_do_free_runs_shell():
    repl, exe = _build_repl(executor=_FakeExecutor([("Mem: 16G\n", "", 0)]))
    output = _capture_output(repl.do_free)
    assert "Mem:" in output
    assert exe.calls == ["free -h"]


def test_do_uptime_runs_shell():
    repl, exe = _build_repl(executor=_FakeExecutor([("up 3 days\n", "", 0)]))
    output = _capture_output(repl.do_uptime)
    assert "up" in output
    assert exe.calls == ["uptime"]


# ───────────────────────────────────────────────────────────────────────────
# existing do_ commands from the original terminal
# ───────────────────────────────────────────────────────────────────────────

def test_do_explain_no_error():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_explain)
    assert "no recent" in output.lower() or "failed" in output.lower()


def test_do_history_empty():
    repl, _ = _build_repl()
    output = _capture_output(repl.do_history)
    assert "no history" in output.lower() or "yet" in output.lower()


def test_do_exit_returns_true():
    repl, _ = _build_repl()
    assert repl.do_exit("") is True


def test_do_quit_returns_true():
    repl, _ = _build_repl()
    assert repl.do_quit("") is True


# ───────────────────────────────────────────────────────────────────────────
# repl.intro banner
# ───────────────────────────────────────────────────────────────────────────

def test_intro_banner_contains_all_sections():
    repl, _ = _build_repl()
    banner = repl.intro
    assert "TankOS AI Terminal" in banner
    assert "1,166 Tools" in banner
    assert "provider" in banner.lower()
    assert "status" in banner.lower()
    assert "curiosity" in banner.lower()
    assert "knowledge" in banner.lower()
    assert "learning" in banner.lower()
    assert "network" in banner.lower()
    assert "health" in banner.lower()


# ───────────────────────────────────────────────────────────────────────────
# _read_temps (best-effort, graceful failure)
# ───────────────────────────────────────────────────────────────────────────

def test_read_temps_returns_list():
    temps = _read_temps()
    assert isinstance(temps, list)


def test_read_temps_max_length():
    temps = _read_temps()
    assert len(temps) <= 4


# ───────────────────────────────────────────────────────────────────────────
# _HAS_PSUTIL flag
# ───────────────────────────────────────────────────────────────────────────

def test_has_psutil_flag_is_bool():
    assert isinstance(_HAS_PSUTIL, bool)
