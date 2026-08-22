"""Bounded command history with lexical recall.

Keeps the last :pyattr:`max_entries` commands in a local in-process
log. We deliberately do NOT push every ``ls``/``cd`` into the global
``MemoryManager`` — the episodic vector store would be drowned in
low-signal commands. The :meth:`save_to_memory` hook is exposed for
the engine to opt in (e.g. whenever the AI explains a fix, the
explanation itself is worth remembering).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HistoryEntry:
    ts: float
    command: str
    exit_code: Optional[int] = None
    success: bool = False
    stderr: str = ""


class CommandHistory:
    def __init__(self, max_entries: int = 1000) -> None:
        self._entries: List[HistoryEntry] = []
        self._max = max_entries
        self._lock = threading.Lock()

    def append(self, command: str, *,
               exit_code: Optional[int] = None,
               success: bool = False,
               stderr: str = "") -> None:
        e = HistoryEntry(
            ts=time.time(), command=command,
            exit_code=exit_code, success=success, stderr=stderr[:2000],
        )
        with self._lock:
            self._entries.append(e)
            if len(self._entries) > self._max:
                # Drop a chunk at once to avoid slice on every append.
                drop = len(self._entries) - self._max
                self._entries = self._entries[drop:]

    def recent(self, limit: int = 50) -> List[HistoryEntry]:
        with self._lock:
            return list(self._entries[-limit:])

    def recall(self, query: str, limit: int = 10) -> List[str]:
        tokens = [t for t in (query or "").lower().split() if t]
        with self._lock:
            if not tokens:
                return [e.command for e in self._entries[-limit:]]
            scored: List[tuple] = []
            for e in self._entries:
                haystack = (e.command + " " + e.stderr).lower()
                score = sum(1 for t in tokens if t in haystack)
                if score > 0:
                    scored.append((score, e))
            scored.sort(key=lambda x: (-x[0], -x[1].ts))
            return [e.command for _, e in scored[:limit]]

    def recent_strings(self, limit: int = 50) -> List[str]:
        return [e.command for e in self.recent(limit)]

    def commands(self) -> List[str]:
        """Full history list, oldest → newest."""
        with self._lock:
            return [e.command for e in self._entries]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def save_to_memory(self, memory, command: str, explanation: str) -> bool:
        """Opt-in: store an AI-produced explanation as a procedural memory.

        Returns True on success; False (silently) if memory is unavailable
        or the call fails.
        """
        try:
            memory.store(
                content=f"command: {command}\nexplanation: {explanation}",
                memory_type="procedural",
                source="terminal_ai",
            )
            return True
        except Exception:                                       # noqa: BLE001
            return False
