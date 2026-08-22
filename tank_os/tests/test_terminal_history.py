"""pytest suite for :mod:`tank_os.shell.terminal.history`."""
from __future__ import annotations

import threading
import time

import pytest

from tank_os.shell.terminal.history import CommandHistory, HistoryEntry


def test_append_records_command_and_exit_code():
    h = CommandHistory()
    h.append("ls -la", exit_code=0, success=True)
    h.append("false", exit_code=1, success=False, stderr="fail msg")
    recent = h.recent_strings()
    assert recent == ["ls -la", "false"]


def test_max_entries_caps_history():
    h = CommandHistory(max_entries=5)
    for i in range(20):
        h.append(f"cmd{i}")
    assert len(h.commands()) == 5
    assert h.commands()[0] == "cmd15"     # oldest retained
    assert h.commands()[-1] == "cmd19"   # newest


def test_recent_returns_last_n_in_order():
    h = CommandHistory()
    for i in range(10):
        h.append(f"cmd{i}")
    assert h.recent_strings(limit=3) == ["cmd7", "cmd8", "cmd9"]


def test_recent_with_zero_returns_empty():
    h = CommandHistory()
    assert h.recent_strings() == []


def test_recall_empty_query_returns_recent():
    h = CommandHistory()
    h.append("ls")
    h.append("cd /tmp")
    assert h.recall("") == ["ls", "cd /tmp"]


def test_recall_keyword_match_in_command():
    h = CommandHistory()
    h.append("rm -rf /tmp/foo", success=True)
    h.append("ls /tmp", success=True)
    h.append("mv /tmp/a /tmp/b", success=True)
    hits = h.recall("/tmp")
    assert "rm -rf /tmp/foo" in hits
    assert "ls /tmp" in hits
    assert "mv /tmp/a /tmp/b" in hits


def test_recall_includes_stderr_for_matching():
    h = CommandHistory()
    h.append("python -c 'x'", success=True)
    h.append("python -c 'y'", success=False, stderr="ImportError: no module")
    hits = h.recall("ImportError")
    assert hits == ["python -c 'y'"]


def test_recall_ranks_stronger_matches_first():
    h = CommandHistory()
    h.append("ls /tmp/foo/empty", success=True)
    h.append("ls /tmp", success=True)
    hits = h.recall("foo empty")
    # Only the one whose command has both tokens pops up.
    assert hits == ["ls /tmp/foo/empty"]


def test_recall_limit_caps_results():
    h = CommandHistory()
    for i in range(20):
        h.append(f"ls {i}", success=True)
    assert len(h.recall("ls", limit=5)) == 5


def test_clear_wipes_entries():
    h = CommandHistory()
    h.append("x")
    h.clear()
    assert h.commands() == []


def test_save_to_memory_invokes_memory_store():
    captured = []

    class _FakeMemory:
        def store(self, content, memory_type="episodic",
                  source="", tags=None):
            captured.append((content, memory_type, source))

    h = CommandHistory()
    assert h.save_to_memory(_FakeMemory(), "ls", "list stuff") is True
    assert len(captured) == 1
    assert "ls" in captured[0][0]
    assert captured[0][1] == "procedural"


def test_save_to_memory_swallows_errors():
    class _BoomMemory:
        def store(self, *a, **k):
            raise RuntimeError("disk full")
    h = CommandHistory()
    assert h.save_to_memory(_BoomMemory(), "x", "y") is False


def test_append_is_thread_safe():
    """Concurrent appends must not corrupt the bounded list."""
    h = CommandHistory(max_entries=500)

    def _worker(prefix):
        for i in range(50):
            h.append(f"{prefix}{i}")

    threads = [threading.Thread(target=_worker, args=(f"t{t}_",))
               for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)
    # 5 workers × 50 = 250 commands — well under the 500 bound.
    assert len(h.commands()) == 250
