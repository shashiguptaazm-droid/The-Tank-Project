"""tank_learn.discovery_store — overnight AI-module discovery ledger.

Stores AI-module discoveries harvested by :mod:`tank_learn.discovery_learner`
between 03:00 and 08:00 daily. Three tables:

* ``model_registry``     — unique on ``(source, name)``; UPSERT semantics so
                          re-discoveries only bump ``last_seen_ts``.
* ``capability_ledger``  — unique on ``(source, module_name, capability)``;
                          powers ``What did the AI learn last night?`` \n                          questions from the operator.
* ``discovery_summary_log`` — one row per scheduled run with run-time stats
                              so the dashboard tile is a single fast ``O(1)``\n                              read.

Mirrors :mod:`tank_learn.feedback_store` for hermeticity and thread safety:
single persistent :class:`sqlite3.Connection`, :class:`threading.Lock`\nserialization, busy_timeout=5000ms, WAL journaling. No rclpy / network dep.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DB_PATH = "/root/the tank project/tank_ws/data/tank_discoveries.db"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ModuleRecord:
    """One discovered AI module ready for upsert."""

    source: str           # "pypi" | "hf" | "github"
    name: str
    url: str = ""
    summary: str = ""
    created_ts: float = 0.0
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "name": self.name,
            "url": self.url,
            "summary": self.summary,
            "created_ts": self.created_ts,
            "capabilities": list(self.capabilities),
        }


@dataclass
class DiscoverySummary:
    """One run of the overnight learner, written to discovery_summary_log."""

    started_ts: float
    finished_ts: float
    new_modules: int
    updated_modules: int
    new_capabilities: int
    sources_succeeded: List[str]
    sources_failed: Dict[str, str]
    window_open: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_ts": self.started_ts,
            "finished_ts": self.finished_ts,
            "new_modules": self.new_modules,
            "updated_modules": self.updated_modules,
            "new_capabilities": self.new_capabilities,
            "sources_succeeded": list(self.sources_succeeded),
            "sources_failed": dict(self.sources_failed),
            "window_open": self.window_open,
        }


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS model_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        name TEXT NOT NULL,
        url TEXT NOT NULL DEFAULT '',
        summary TEXT NOT NULL DEFAULT '',
        first_seen_ts REAL NOT NULL,
        last_seen_ts REAL NOT NULL,
        UNIQUE(source, name)
    )""",
    """CREATE TABLE IF NOT EXISTS capability_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        module_name TEXT NOT NULL,
        capability TEXT NOT NULL,
        first_seen_ts REAL NOT NULL,
        last_seen_ts REAL NOT NULL,
        UNIQUE(source, module_name, capability)
    )""",
    """CREATE TABLE IF NOT EXISTS discovery_summary_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_ts REAL NOT NULL,
        finished_ts REAL NOT NULL,
        new_modules INTEGER NOT NULL,
        updated_modules INTEGER NOT NULL,
        new_capabilities INTEGER NOT NULL,
        sources_succeeded_json TEXT NOT NULL,
        sources_failed_json TEXT NOT NULL,
        window_open INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS schema_meta (
        version INTEGER PRIMARY KEY
    )""",
    "INSERT OR IGNORE INTO schema_meta (version) VALUES (1)",
]


# ---------------------------------------------------------------------------
# DiscoveryStore
# ---------------------------------------------------------------------------
class DiscoveryStore:
    """Hermetic SQLite-WAL store for overnight AI-module discoveries.

    Public entry points:

    * :meth:`upsert_module`     — UNIQUE-violation safe insert/update
    * :meth:`add_capability`    — UNIQUE-violation safe capability row insert
    * :meth:`write_summary`     — append a :class:`DiscoverySummary` to the log
    * :meth:`latest_summary`    — read the most recent :class:`DiscoverySummary`
    * :meth:`modules`           — paginated registry rows for the dashboard
    * :meth:`capabilities`      — paginated capability rows for the dashboard
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = str(db_path) if db_path is not None else DEFAULT_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            for stmt in SCHEMA_STATEMENTS:
                self._conn.execute(stmt)
            self._conn.commit()

    def upsert_module(
        self, rec: ModuleRecord,
        *, now_ts: Optional[float] = None,
    ) -> Tuple[bool, bool]:
        """Insert-or-update ``(source, name)``.

        Returns ``(was_new, existed)`` so the caller can distinguish a fresh
        discovery from a re-confirmation of an existing row.
        """
        now = now_ts if now_ts is not None else time.time()
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM model_registry WHERE source = ? AND name = ?",
                (rec.source, rec.name),
            )
            existing = cur.fetchone()
            if existing is None:
                self._conn.execute(
                    "INSERT INTO model_registry\n"
                    " (source, name, url, summary, first_seen_ts, last_seen_ts)\n"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (rec.source, rec.name, rec.url, rec.summary, now, now),
                )
                self._conn.commit()
                return (True, False)
            self._conn.execute(
                "UPDATE model_registry\n"
                " SET url = ?, summary = ?, last_seen_ts = ?\n"
                " WHERE source = ? AND name = ?",
                (rec.url, rec.summary, now, rec.source, rec.name),
            )
            self._conn.commit()
            return (False, True)

    def add_capability(
        self, source: str, module_name: str, capability: str,
        *, now_ts: Optional[float] = None,
    ) -> bool:
        """Insert-or-update a ``(source, module_name, capability)`` triple.

        Returns ``True`` iff a fresh row was created.
        """
        now = now_ts if now_ts is not None else time.time()
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM capability_ledger\n"
                " WHERE source = ? AND module_name = ? AND capability = ?",
                (source, module_name, capability),
            )
            if cur.fetchone() is not None:
                self._conn.execute(
                    "UPDATE capability_ledger SET last_seen_ts = ?\n"
                    " WHERE source = ? AND module_name = ? AND capability = ?",
                    (now, source, module_name, capability),
                )
                self._conn.commit()
                return False
            self._conn.execute(
                "INSERT INTO capability_ledger\n"
                " (source, module_name, capability, first_seen_ts, last_seen_ts)\n"
                " VALUES (?, ?, ?, ?, ?)",
                (source, module_name, capability, now, now),
            )
            self._conn.commit()
            return True

    def write_summary(self, summary: DiscoverySummary) -> int:
        """Append a :class:`DiscoverySummary` row. Returns the new row id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO discovery_summary_log\n"
                " (started_ts, finished_ts, new_modules, updated_modules,\n"
                "  new_capabilities, sources_succeeded_json,\n"
                "  sources_failed_json, window_open)\n"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    summary.started_ts, summary.finished_ts,
                    summary.new_modules, summary.updated_modules,
                    summary.new_capabilities,
                    json.dumps(summary.sources_succeeded),
                    json.dumps(summary.sources_failed),
                    1 if summary.window_open else 0,
                ),
            )
            self._conn.commit()
            return cur.lastrowid or 0

    def latest_summary(self) -> Optional[Dict[str, Any]]:
        """Read the most-recent :class:`DiscoverySummary` as a dict."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT started_ts, finished_ts, new_modules, updated_modules,\n"
                "       new_capabilities, sources_succeeded_json,\n"
                "       sources_failed_json, window_open\n"
                " FROM discovery_summary_log ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "started_ts":             row[0],
            "finished_ts":            row[1],
            "new_modules":            row[2],
            "updated_modules":        row[3],
            "new_capabilities":       row[4],
            "sources_succeeded":      json.loads(row[5]),
            "sources_failed":         json.loads(row[6]),
            "window_open":            bool(row[7]),
        }

    def modules(
        self, *, source: Optional[str] = None,
        since_ts: Optional[float] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Paginated model_registry rows ordered by ``last_seen_ts``."""
        sql = (
            "SELECT source, name, url, summary, first_seen_ts, last_seen_ts\n"
            " FROM model_registry"
        )
        args: List[Any] = []
        clauses: List[str] = []
        if source:
            clauses.append("source = ?")
            args.append(source)
        if since_ts is not None:
            clauses.append("last_seen_ts >= ?")
            args.append(since_ts)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY last_seen_ts DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [
            {
                "source":        r[0],
                "name":          r[1],
                "url":           r[2],
                "summary":       r[3],
                "first_seen_ts": r[4],
                "last_seen_ts":  r[5],
            }
            for r in rows
        ]

    def capabilities(
        self, *, since_ts: Optional[float] = None, limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Paginated capability_ledger rows ordered by ``last_seen_ts``."""
        sql = (
            "SELECT source, module_name, capability, first_seen_ts, last_seen_ts\n"
            " FROM capability_ledger"
        )
        args: List[Any] = []
        clauses: List[str] = []
        if since_ts is not None:
            clauses.append("last_seen_ts >= ?")
            args.append(since_ts)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY last_seen_ts DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [
            {
                "source":        r[0],
                "module_name":   r[1],
                "capability":    r[2],
                "first_seen_ts": r[3],
                "last_seen_ts":  r[4],
            }
            for r in rows
        ]

    def close(self) -> None:
        """Idempotent close — second call is a silent no-op."""
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except sqlite3.ProgrammingError:
                pass

    def __enter__(self) -> "DiscoveryStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


__all__ = [
    "DEFAULT_DB_PATH", "SCHEMA_VERSION",
    "ModuleRecord", "DiscoverySummary",
    "SCHEMA_STATEMENTS", "DiscoveryStore",
]
