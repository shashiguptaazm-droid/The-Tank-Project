"""Append-only sqlite-backed log store for :mod:`tank_log`.

This is a deliberately small surface area — every robot event lands in a
single ``topic_logs`` table, never overwritten. Optional ``topic_summary``
tables hold the periodic learner rollups.

Why not the persistent memory store from :mod:`tank_memory`? That one is
vector-similarity-focused (sentence-transformers). Logs are different:
they're *event streams* that want fast range queries and tail-window
counts, not nearest-neighbour recall.

Why not the structured coding memory from :mod:`tank_meta`? That one is
*curated knowledge*. Logs are *raw detail*.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS topic_logs (
    ts        REAL NOT NULL,
    topic     TEXT NOT NULL,
    msgtype   TEXT NOT NULL,
    source    TEXT NOT NULL,    -- node that wrote the log entry
    payload   TEXT,             -- JSON-stringified (cap 8 KB)
    truncated INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (ts, topic, source)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS topic_logs_ts_idx ON topic_logs(ts DESC);
CREATE INDEX IF NOT EXISTS topic_logs_topic_idx ON topic_logs(topic, ts DESC);

CREATE TABLE IF NOT EXISTS topic_summary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    window_sec   REAL NOT NULL,
    top_topic    TEXT NOT NULL,
    top_count    INTEGER NOT NULL,
    anomaly      TEXT,                 -- e.g. "wake_no_intent"
    counts_json  TEXT                  -- {"<topic>": <count>, ...}
);
CREATE INDEX IF NOT EXISTS topic_summary_ts_idx ON topic_summary(ts DESC);
"""


# Cap runaway publisher payloads so a single 5 MB message can't blow up the db.
PAYLOAD_CAP_BYTES = 8192


# ---------- result records -------------------------------------------------
@dataclass
class LogRow:
    ts: float
    topic: str
    msgtype: str
    source: str
    payload: str          # raw string (JSON or text)
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts":        self.ts,
            "topic":     self.topic,
            "msgtype":   self.msgtype,
            "source":    self.source,
            "payload":   self.payload,
            "truncated": self.truncated,
        }


# ---------- store ----------------------------------------------------------
class LogStore:
    """Thread-safe append-only sqlite store.

    Lock order rule: callers must NOT hold an external lock while calling
    methods on this store (and vice versa). All public methods take the
    store's own lock briefly for each sqlite operation so external
    mutexes cannot be nested inside.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        # Forward-compat migration: CREATE TABLE IF NOT EXISTS does not
        # add columns to an existing table. Older on-disk log.db files
        # have a topic_logs without the ``truncated`` column; add it now
        # so any subsequent INSERT (which writes 6 columns) does not crash.
        try:
            self._conn.execute(
                "ALTER TABLE topic_logs ADD COLUMN "
                "truncated INTEGER NOT NULL DEFAULT 0"
            )
            self._conn.commit()
        except sqlite3.OperationalError:
            # column already present — fine
            pass
        except Exception:
            pass
        self._conn.commit()

    # --- append ---
    def append(self, ts: float, topic: str, msgtype: str,
               source: str, payload: str) -> bool:
        """Append a row. Returns True if the payload was truncated to fit
        the 8 KB cap; False otherwise. The truncation flag is persisted
        in the ``truncated`` column so query_log can surface it without
        string tricks on the payload suffix."""
        truncated = 0
        if len(payload) > PAYLOAD_CAP_BYTES:
            payload = payload[: PAYLOAD_CAP_BYTES - 1] + "\u2026"
            truncated = 1
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO topic_logs "
                    "(ts, topic, msgtype, source, payload, truncated) "
                    "VALUES (?,?,?,?,?,?)",
                    (float(ts), str(topic), str(msgtype),
                     str(source), payload, int(truncated)),
                )
                self._conn.commit()
            except sqlite3.IntegrityError:
                pass   # idempotent on (ts,topic,source) duplicate
        return bool(truncated)

    def append_payload_dict(self, ts: float, topic: str, msgtype: str,
                            source: str, obj: Any) -> bool:
        """Convenience helper for callers with Python objects."""
        try:
            payload = json.dumps(obj, ensure_ascii=False, default=str)
        except Exception:
            payload = repr(obj)[:PAYLOAD_CAP_BYTES * 2]
        return self.append(ts, topic, msgtype, source, payload)

    # --- read ---
    def recent(self, limit: int = 50) -> List[LogRow]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, topic, msgtype, source, payload, truncated "
                "FROM topic_logs ORDER BY ts DESC LIMIT ?", (int(limit),)
            )
            rows = cur.fetchall()
        return [LogRow(ts=r[0], topic=r[1], msgtype=r[2], source=r[3],
                       payload=r[4], truncated=bool(r[5])) for r in rows]

    def by_topic(self, topic: str, limit: int = 50) -> List[LogRow]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, topic, msgtype, source, payload, truncated "
                "FROM topic_logs WHERE topic = ? "
                "ORDER BY ts DESC LIMIT ?",
                (str(topic), int(limit)),
            )
            rows = cur.fetchall()
        return [LogRow(ts=r[0], topic=r[1], msgtype=r[2], source=r[3],
                       payload=r[4], truncated=bool(r[5])) for r in rows]

    def topic_rows_since(self, topic: str, since_sec: float) -> List[LogRow]:
        """Return *all* rows for ``topic`` whose ts is within the trailing
        ``since_sec`` window. Use this for time-bounded checks like
        ``estop_stuck`` instead of by_topic(limit=N), which is row-bound
        and breaks at high message rates."""
        cutoff = max(0.0, time.time() - float(since_sec))
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, topic, msgtype, source, payload, truncated "
                "FROM topic_logs WHERE topic = ? AND ts >= ? "
                "ORDER BY ts DESC",
                (str(topic), float(cutoff)),
            )
            rows = cur.fetchall()
        return [LogRow(ts=r[0], topic=r[1], msgtype=r[2], source=r[3],
                       payload=r[4], truncated=bool(r[5])) for r in rows]

    def by_source(self, source: str, limit: int = 50) -> List[LogRow]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ts, topic, msgtype, source, payload, truncated "
                "FROM topic_logs WHERE source = ? "
                "ORDER BY ts DESC LIMIT ?",
                (str(source), int(limit)),
            )
            rows = cur.fetchall()
        return [LogRow(ts=r[0], topic=r[1], msgtype=r[2], source=r[3],
                       payload=r[4], truncated=bool(r[5])) for r in rows]

    def counts_per_topic(self, since_sec: float = 3600.0) -> Dict[str, int]:
        cutoff = max(0.0, time.time() - float(since_sec))
        with self._lock:
            cur = self._conn.execute(
                "SELECT topic, COUNT(*) FROM topic_logs "
                "WHERE ts >= ? GROUP BY topic ORDER BY COUNT(*) DESC",
                (cutoff,),
            )
            rows = cur.fetchall()
        return {str(t): int(c) for t, c in rows}

    def count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM topic_logs")
            (n,) = cur.fetchone()
            return int(n)

    def count_truncated(self, since_sec: float = 3600.0) -> int:
        cutoff = max(0.0, time.time() - float(since_sec))
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM topic_logs "
                "WHERE truncated = 1 AND ts >= ?", (cutoff,),
            )
            (n,) = cur.fetchone()
            return int(n)

    # --- summary ---
    def record_summary(self, ts: float, window_sec: float, top_topic: str,
                       top_count: int, anomaly: Optional[str],
                       counts: Dict[str, int]) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO topic_summary "
                "(ts, window_sec, top_topic, top_count, anomaly, counts_json) "
                "VALUES (?,?,?,?,?,?)",
                (float(ts), float(window_sec), str(top_topic), int(top_count),
                 anomaly, json.dumps(counts)),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def recent_summaries(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, ts, window_sec, top_topic, top_count, anomaly, counts_json "
                "FROM topic_summary ORDER BY ts DESC LIMIT ?", (int(limit),),
            )
            rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            try:
                counts = json.loads(r[6]) if r[6] else {}
            except Exception:
                counts = {}
            out.append({
                "id":         r[0],
                "ts":         r[1],
                "window_sec": r[2],
                "top_topic":  r[3],
                "top_count":  r[4],
                "anomaly":    r[5],
                "counts":     counts,
            })
        return out

    # --- maintenance ---
    def compact_age(self, max_age_days: float = 30.0) -> int:
        cutoff = time.time() - max_age_days * 86400.0
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM topic_logs WHERE ts < ?", (float(cutoff),),
            )
            removed = cur.rowcount
            cur2 = self._conn.execute(
                "DELETE FROM topic_summary WHERE ts < ?", (float(cutoff),),
            )
            self._conn.commit()
        return int(removed + cur2.rowcount)

    def health(self) -> Dict[str, Any]:
        with self._lock:
            (a,) = self._conn.execute(
                "SELECT COUNT(*) FROM topic_logs"
            ).fetchone()
            (b,) = self._conn.execute(
                "SELECT COUNT(*) FROM topic_summary"
            ).fetchone()
            (t,) = self._conn.execute(
                "SELECT COALESCE(MAX(ts), 0) FROM topic_logs"
            ).fetchone()
            (trunc,) = self._conn.execute(
                "SELECT COUNT(*) FROM topic_logs WHERE truncated = 1"
            ).fetchone()
        return {
            "topic_logs_rows":   int(a),
            "topic_summary_rows": int(b),
            "truncated_rows":    int(trunc),
            "max_ts":            float(t),
            "db_path":           self._db_path,
        }

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
