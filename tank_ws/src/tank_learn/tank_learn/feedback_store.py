"""``tank_learn.feedback_store`` — SQLite-WAL persistence for the OS feedback loop.

Why SQLite in WAL mode?
~~~~~~~~~~~~~~~~~~~~~~~
* RAM footprint on Jetson stays low (no Postgres, no daemon to manage).
* ``PRAGMA journal_mode=WAL`` allows concurrent readers + one writer,
  so the dashboard uvicorn pool can read while the ROS node writes.

Phase-1 design (THIS revision)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Single persistent ``sqlite3.Connection`` per :class:`FeedbackStore`,
serialized by ``threading.Lock``. Each FeedbackStore instance owns
one connection for its entire lifetime.

Why ONE persistent connection (not per-call short-lived)?
  Across three fix attempts on the previous per-call design, cold-
  cache race windows surfaced as ``sqlite3.OperationalError: no
  such table: ‹name›`` even after busy_timeout + WAL + autocommit
  per-statement. The robust answer under contention is to keep one
  connection that never closes until the store is destroyed —
  eliminating the cross-connection WAL visibility race. Lock-protected
  round-trips are fast (WAL writes are sub-millisecond). Cross-process
  concurrency (dashboard process + ROS node process = two stores =
  two connections) is still safe via ``busy_timeout`` + WAL.

Tables
~~~~~~
* ``feedback_log``           — every dispatch (reward=0) + every reward update.
* ``intent_grammar_weights`` — per-cid weight used by :mod:`tank_speech.intent_router`.
* ``iq_history``             — append-only IQ samples read by :mod:`tank_iq`.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default location: <workspace>/tank_ws/data/os_memory.db.  Override
# via FeedbackStore(db_path=...) for tests + benches.
DEFAULT_DB_PATH = "/root/the tank project/tank_ws/data/os_memory.db"


SCHEMA_VERSION = 1

# Schema is applied per-statement (no executescript, no BEGIN/COMMIT)
# so each CREATE TABLE / CREATE INDEX commits atomically under
# autocommit mode. See ``_init_schema`` below for the full rationale.
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS feedback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    intent_text TEXT NOT NULL DEFAULT '',
    plugin_name TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    reward INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'auto',
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_feedback_plugin ON feedback_log (plugin_name);
CREATE INDEX IF NOT EXISTS idx_feedback_reward ON feedback_log (reward);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback_log (ts);

CREATE TABLE IF NOT EXISTS intent_grammar_weights (
    cid TEXT PRIMARY KEY,
    weight REAL NOT NULL DEFAULT 1.0,
    updated_ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    sample_count INTEGER NOT NULL DEFAULT 0,
    negative_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS iq_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    plugin_name TEXT NOT NULL,
    iq_score REAL NOT NULL,
    sub_accuracy REAL,
    sub_uptime REAL,
    sub_latency REAL,
    sub_user_reward REAL,
    note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_iq_plugin ON iq_history (plugin_name);
CREATE INDEX IF NOT EXISTS idx_iq_ts ON iq_history (ts);

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _split_statements(sql: str) -> List[str]:
    """Split a multi-statement SQL script on ``;`` boundaries.

    Strips SQL line comments (``-- ...``) and skips empty fragments.
    Each output statement is independently executable. The split is
    naive (no string-literal awareness) — fine for schemas that hold
    only ``CREATE TABLE`` / ``CREATE INDEX`` statements.
    """
    fragments: List[str] = []
    for raw in sql.split(";"):
        kept: List[str] = []
        for line in raw.splitlines():
            if line.lstrip().startswith("--"):
                continue
            kept.append(line)
        cleaned = "\n".join(kept).strip()
        if cleaned:
            fragments.append(cleaned)
    return fragments


_SCHEMA_STATEMENTS: List[str] = _split_statements(SCHEMA)


@dataclass
class FeedbackRow:
    """In-memory snapshot of one ``feedback_log`` row."""
    id: int
    ts: str
    intent_text: str
    plugin_name: str
    confidence: float
    reward: int
    source: str
    note: str

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> "FeedbackRow":
        return cls(
            id=int(row["id"]),
            ts=str(row["ts"] or ""),
            intent_text=str(row["intent_text"] or ""),
            plugin_name=str(row["plugin_name"] or ""),
            confidence=float(row["confidence"] or 0.0),
            reward=int(row["reward"] or 0),
            source=str(row["source"] or "auto"),
            note=str(row["note"] or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "intent_text": self.intent_text,
            "plugin_name": self.plugin_name,
            "confidence": self.confidence,
            "reward": self.reward,
            "source": self.source,
            "note": self.note,
        }


def _validate_reward(value: Any) -> int:
    """Reward must be one of -1 / 0 / +1. Coerces ints and True/False."""
    if value in (True, False):
        return 1 if value else -1
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"reward must be -1, 0, or +1 (got {value!r})") from exc
    if n not in (-1, 0, 1):
        raise ValueError(f"reward must be -1, 0, or +1 (got {n})")
    return n


class FeedbackStore:
    """Hermetic SQLite-WAL feedback store for The Tank OS.

    Pure-Python — no rclpy dependency, suitable for unit tests + the
    FastAPI dashboard. The ROS 2 node wrapper lives in
    :mod:`tank_learn.feedback_node`.

    Implementation: ONE persistent :class:`sqlite3.Connection`,
    every operation guarded by a :class:`threading.Lock`. Multiple
    threads serialise through the lock; multiple processes
    coordinate via ``busy_timeout`` + WAL pragmas.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = str(db_path or DEFAULT_DB_PATH)
        parent = Path(self._db_path).parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # ":memory:" / read-only mounts may have no writable parent.
            pass
        self._lock = threading.Lock()
        # check_same_thread=False is required because threads traverse
        # the same connection (via lock).  isolation_level=None means
        # each statement auto-commits — no implicit transactions.
        self._conn = sqlite3.connect(
            self._db_path,
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        # Per-connection pragmas. busy_timeout handles cross-process
        # contention; journal_mode=WAL enables concurrent readers +
        # 1 writer; synchronous=NORMAL is the WAL-recommended
        # durability setting (avoids fsync-per-commit on Jetson SD).
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        # Schema DDL — each statement autocommit. Lock-held init
        # blocks any other FeedbackStore operation on this instance
        # until schema is fully applied.
        with self._lock:
            self._init_schema()

    # ─── internal helpers ──────────────────────────────────────────────
    def _init_schema(self) -> None:
        """Apply schema DDL on the persistent connection.

        No ``executescript``: that helper COMMITS any pending
        transaction before running, which interferes with explicit
        BEGIN/COMMIT wrappers in the prior design. Per-statement
        autocommit (autocommit = isolation_level=None) is robust
        and well-tested for DDL.
        """
        for stmt in _SCHEMA_STATEMENTS:
            self._conn.execute(stmt)
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value)"
            " VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )

    def close(self) -> None:
        """Close the persistent connection — idempotent.

        Detaches ``self._conn`` BEFORE calling ``.close()`` so a
        ``ProgrammingError: Connection closed`` (which SQLite raises
        if the connection is already closed) cannot leak through. Safe
        to call from ``__del__``, signal handlers, or twice in a row.
        """
        with self._lock:
            conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except sqlite3.ProgrammingError:
                pass

    def __enter__(self) -> "FeedbackStore":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any,
                 exc_tb: Any) -> None:
        self.close()

    # ─── introspection ──────────────────────────────────────────────────
    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def schema_version(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM schema_meta"
                " WHERE key = 'schema_version'",
            ).fetchone()
        return int(row["value"]) if row else 0

    # ─── feedback_log ──────────────────────────────────────────────────
    def record_dispatch(self, intent_text: str,
                        plugin_name: str,
                        confidence: float = 0.0,
                        source: str = "auto",
                        note: str = "") -> int:
        if not plugin_name:
            raise ValueError("plugin_name is required")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO feedback_log"
                " (intent_text, plugin_name, confidence, reward, source, note)"
                " VALUES (?, ?, ?, 0, ?, ?)",
                ((intent_text or "")[:500],
                 plugin_name,
                 float(confidence),
                 (source or "auto")[:32],
                 (note or "")[:200]),
            )
            return int(cur.lastrowid)

    def record_reward(self, dispatch_id: int, reward: Any,
                      source: str = "user",
                      note: str = "") -> bool:
        r = _validate_reward(reward)
        with self._lock:
            cur = self._conn.execute(
                "UPDATE feedback_log"
                " SET reward = ?, source = ?, note = ? WHERE id = ?",
                (r, (source or "user")[:32], (note or "")[:200],
                 int(dispatch_id)),
            )
            return cur.rowcount > 0

    def record_dispatch_with_reward(self, intent_text: str,
                                    plugin_name: str,
                                    reward: Any,
                                    confidence: float = 0.0,
                                    source: str = "user",
                                    note: str = "") -> int:
        r = _validate_reward(reward)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO feedback_log"
                " (intent_text, plugin_name, confidence, reward, source, note)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                ((intent_text or "")[:500],
                 plugin_name,
                 float(confidence),
                 r,
                 (source or "user")[:32],
                 (note or "")[:200]),
            )
            return int(cur.lastrowid)

    def recent(self, limit: int = 50) -> List[FeedbackRow]:
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM feedback_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [FeedbackRow.from_db_row(r) for r in rows]

    def by_plugin(self, plugin_name: str,
                  limit: int = 100) -> List[FeedbackRow]:
        if not plugin_name:
            return []
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM feedback_log WHERE plugin_name = ?"
                " ORDER BY id DESC LIMIT ?",
                (plugin_name, limit),
            ).fetchall()
        return [FeedbackRow.from_db_row(r) for r in rows]

    def plugin_stats(self, plugin_name: str) -> Dict[str, Any]:
        if not plugin_name:
            return {"plugin_name": "", "total_dispatches": 0, "rated": 0,
                    "positive": 0, "negative": 0, "approval_rate": 0.0,
                    "avg_confidence": 0.0, "last_dispatch_ts": ""}
        with self._lock:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN reward =  1 THEN 1 ELSE 0 END) AS positive,
                    SUM(CASE WHEN reward = -1 THEN 1 ELSE 0 END) AS negative,
                    AVG(confidence) AS avg_confidence,
                    MAX(ts) AS last_dispatch_ts
                FROM feedback_log
                WHERE plugin_name = ?
                """,
                (plugin_name,),
            ).fetchone()
        total = int(row["total"] or 0)
        positive = int(row["positive"] or 0)
        negative = int(row["negative"] or 0)
        rated = positive + negative
        approval = (positive / rated) if rated else 0.0
        return {
            "plugin_name": plugin_name,
            "total_dispatches": total,
            "rated": rated,
            "positive": positive,
            "negative": negative,
            "approval_rate": round(approval, 3),
            "avg_confidence": round(float(row["avg_confidence"] or 0.0), 3),
            "last_dispatch_ts": str(row["last_dispatch_ts"] or ""),
        }

    def all_plugin_stats(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT plugin_name FROM feedback_log
                GROUP BY plugin_name
                ORDER BY plugin_name
                """,
            ).fetchall()
        return [self.plugin_stats(r["plugin_name"]) for r in rows]

    # ─── intent_grammar_weights ────────────────────────────────────────
    def grammar_weight(self, cid: str) -> float:
        if not cid:
            return 1.0
        with self._lock:
            row = self._conn.execute(
                "SELECT weight FROM intent_grammar_weights WHERE cid = ?",
                (cid,),
            ).fetchone()
        return float(row["weight"]) if row else 1.0

    def update_grammar_weight(self, cid: str, new_weight: float,
                              *, increment_negative: bool = False) -> float:
        if not cid:
            raise ValueError("cid is required")
        if not (0.05 <= float(new_weight) <= 5.0):
            raise ValueError(
                f"weight must be in [0.05, 5.0] (got {new_weight})"
            )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO intent_grammar_weights
                    (cid, weight, sample_count, negative_count)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(cid) DO UPDATE SET
                    weight = excluded.weight,
                    sample_count = sample_count + 1,
                    negative_count = negative_count + ?,
                    updated_ts = CURRENT_TIMESTAMP
                """,
                (cid, float(new_weight),
                 1 if increment_negative else 0,
                 1 if increment_negative else 0),
            )
        return float(new_weight)

    def all_grammar_weights(self) -> Dict[str, float]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT cid, weight FROM intent_grammar_weights"
                " ORDER BY cid",
            ).fetchall()
        return {r["cid"]: float(r["weight"]) for r in rows}

    # ─── iq_history ────────────────────────────────────────────────────
    def record_iq(self, plugin_name: str, iq_score: float,
                  sub_accuracy: Optional[float] = None,
                  sub_uptime: Optional[float] = None,
                  sub_latency: Optional[float] = None,
                  sub_user_reward: Optional[float] = None,
                  note: str = "") -> int:
        if not plugin_name:
            raise ValueError("plugin_name is required")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO iq_history"
                " (plugin_name, iq_score, sub_accuracy, sub_uptime,"
                "  sub_latency, sub_user_reward, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (plugin_name, float(iq_score),
                 float(sub_accuracy) if sub_accuracy is not None else None,
                 float(sub_uptime) if sub_uptime is not None else None,
                 float(sub_latency) if sub_latency is not None else None,
                 float(sub_user_reward) if sub_user_reward is not None else None,
                 (note or "")[:200]),
            )
            return int(cur.lastrowid)

    def recent_iq(self, plugin_name: Optional[str] = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            if plugin_name:
                rows = self._conn.execute(
                    "SELECT * FROM iq_history WHERE plugin_name = ?"
                    " ORDER BY id DESC LIMIT ?",
                    (plugin_name, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM iq_history ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def current_iq(self, plugin_name: str) -> Optional[float]:
        if not plugin_name:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT iq_score FROM iq_history WHERE plugin_name = ?"
                " ORDER BY id DESC LIMIT 1",
                (plugin_name,),
            ).fetchone()
        return float(row["iq_score"]) if row else None


__all__ = [
    "DEFAULT_DB_PATH",
    "SCHEMA_VERSION",
    "SCHEMA",
    "FeedbackRow",
    "FeedbackStore",
]
