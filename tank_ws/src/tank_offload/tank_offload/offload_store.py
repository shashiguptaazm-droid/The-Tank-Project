"""SQLite-backed manifest of offload events.

Each :class:`Item` represents one file the policy decided to push to
the VPS. The store tracks the lifecycle:

    pending   \u2192 staging \u2192 uploaded
                    \u2193
                dead_letter  (after retries exhausted)

Design rules followed (per STATUS.md \u00a79):

* ``journal_mode=WAL`` + ``synchronous=NORMAL`` so reads don't block
  the worker thread.
* ``INSERT OR REPLACE`` (not separate INSERT + UPDATE which trips the
  PK constraint on retries).
* Per-store ``threading.Lock`` so dashboard PUTs and queued worker
  writes can't race.
* Status transitions are strict:

  pending \u2192 staging | uploaded | dead_letter
  staging \u2192 uploaded | pending (retry) | dead_letter
  uploaded/dead_letter \u2192 terminal (no transition out)

The schema is intentionally narrow: one row per file. We don't
store arbitrary file content (it's already on the VPS) \u2014 just the
provenance, dimensions, current status, retry count, and a UUID.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sqlite3
import threading
import time
import uuid as _uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


# Status strings \u2014 stored verbatim; used by the worker to gate moves.
STATUS_PENDING = "pending"
STATUS_STAGING = "staging"
STATUS_UPLOADED = "uploaded"
STATUS_DEAD_LETTER = "dead_letter"
ALL_STATUSES: tuple = (STATUS_PENDING, STATUS_STAGING,
                        STATUS_UPLOADED, STATUS_DEAD_LETTER)

# Valid status transitions (from \u2192 allowed set).
_VALID_TRANSITIONS: Dict[str, frozenset] = {
    STATUS_PENDING:   frozenset({STATUS_STAGING, STATUS_UPLOADED,
                                  STATUS_DEAD_LETTER, STATUS_PENDING}),
    STATUS_STAGING:   frozenset({STATUS_UPLOADED, STATUS_PENDING,
                                  STATUS_DEAD_LETTER}),
    STATUS_UPLOADED:  frozenset(),  # terminal
    STATUS_DEAD_LETTER: frozenset(),  # terminal
}


def new_uuid() -> str:
    """4-byte compact UUID \u2014\u2014 short enough that the staging filename
    stays readable by humans debugging by hand."""
    return _uuid.uuid4().hex[:12]


@dataclass
class Item:
    """One row in the manifest."""

    uuid: str
    original_path: str
    size_bytes: int = 0
    kind: str = "recording"      # one of policy.ALL_KINDS
    status: str = STATUS_PENDING
    retry_count: int = 0
    next_retry_ts: float = 0.0
    staged_path: str = ""
    remote_path: str = ""
    last_error: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "original_path": self.original_path,
            "size_bytes": self.size_bytes,
            "kind": self.kind,
            "status": self.status,
            "retry_count": self.retry_count,
            "next_retry_ts": self.next_retry_ts,
            "staged_path": self.staged_path,
            "remote_path": self.remote_path,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Item":
        return cls(
            uuid=row["uuid"],
            original_path=row["original_path"],
            size_bytes=int(row["size_bytes"] or 0),
            kind=row["kind"] or "recording",
            status=row["status"] or STATUS_PENDING,
            retry_count=int(row["retry_count"] or 0),
            next_retry_ts=float(row["next_retry_ts"] or 0.0),
            staged_path=row["staged_path"] or "",
            remote_path=row["remote_path"] or "",
            last_error=row["last_error"] or "",
            created_at=float(row["created_at"] or 0.0),
            updated_at=float(row["updated_at"] or 0.0),
        )


class OffloadStore:
    """Thread-safe SQLite store. Schema is created on init."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    # ----- schema -----
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=5.0,
                               check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS manifest ("
                    "uuid          TEXT PRIMARY KEY,"
                    "original_path TEXT NOT NULL,"
                    "size_bytes    INTEGER NOT NULL,"
                    "kind          TEXT NOT NULL,"
                    "status        TEXT NOT NULL,"
                    "retry_count   INTEGER NOT NULL DEFAULT 0,"
                    "next_retry_ts REAL NOT NULL DEFAULT 0,"
                    "staged_path   TEXT NOT NULL DEFAULT '',"
                    "remote_path   TEXT NOT NULL DEFAULT '',"
                    "last_error    TEXT NOT NULL DEFAULT '',"
                    "created_at    REAL NOT NULL DEFAULT 0,"
                    "updated_at    REAL NOT NULL DEFAULT 0)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_manifest_status_retry "
                "ON manifest(status, next_retry_ts)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_manifest_kind "
                "ON manifest(kind)")

    # ----- transitions -----
    @staticmethod
    def validate_transition(current: str, new: str) -> bool:
        """Return True if ``current \u2192 new`` is legal."""
        if current not in _VALID_TRANSITIONS:
            return False
        return new in _VALID_TRANSITIONS[current]

    # ----- writes (all guarded by self._lock) -----
    def enqueue(self, original_path: str, size_bytes: int,
                kind: str, *, uuid: Optional[str] = None) -> Item:
        """Add a fresh row in :data:`STATUS_PENDING`."""
        now = time.time()
        item = Item(
            uuid=uuid or new_uuid(),
            original_path=original_path,
            size_bytes=int(size_bytes),
            kind=kind,
            status=STATUS_PENDING,
            created_at=now,
            updated_at=now,
        )
        self._write_row(item)
        return item

    def transition(self, uuid: str, *, to_status: str,
                   **fields: Any) -> Item:
        """Atomically move ``uuid`` to ``to_status``, updating any
        of the optional fields (``staged_path``, ``remote_path``,
        ``last_error``, ``retry_count``, ``next_retry_ts``).

        Raises :class:`ValueError` if the move is illegal.
        """
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT status FROM manifest WHERE uuid=?",
                (uuid,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"unknown uuid {uuid!r}")
            current_status = row["status"]
            if to_status != current_status \
                    and not self.validate_transition(current_status, to_status):
                raise ValueError(
                    f"illegal transition {current_status} \u2192 {to_status}")
            ts_now = time.time()
            # Build the dynamic UPDATE.
            sets = ["status=?", "updated_at=?"]
            params: List[Any] = [to_status, ts_now]
            for k in ("staged_path", "remote_path", "last_error"):
                if k in fields and fields[k] is not None:
                    sets.append(f"{k}=?")
                    params.append(str(fields[k]))
            if "retry_count" in fields and fields["retry_count"] is not None:
                sets.append("retry_count=?")
                params.append(int(fields["retry_count"]))
            if "next_retry_ts" in fields and fields["next_retry_ts"] is not None:
                sets.append("next_retry_ts=?")
                params.append(float(fields["next_retry_ts"]))
            params.append(uuid)
            with conn:
                conn.execute(
                    f"UPDATE manifest SET {', '.join(sets)} "
                    f"WHERE uuid=?",
                    params)
        return self.get(uuid)  # type: ignore[return-value]

    def record_retry(self, uuid: str, error: str,
                     next_delay_sec: float) -> Item:
        """Increment retry_count and schedule next_retry_ts."""
        # Read current, mutate, write back \u2014 the lock keeps it atomic.
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT status, retry_count FROM manifest WHERE uuid=?",
                (uuid,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"unknown uuid {uuid!r}")
            new_retry = int(row["retry_count"] or 0) + 1
            now = time.time()
            with conn:
                conn.execute(
                    "UPDATE manifest SET status=?, retry_count=?, "
                    "last_error=?, next_retry_ts=?, updated_at=? "
                    "WHERE uuid=?",
                    (STATUS_PENDING, new_retry, error[:500],
                     now + max(0.0, next_delay_sec), now, uuid))
        return self.get(uuid)  # type: ignore[return-value]

    def _write_row(self, item: Item) -> None:
        with self._lock, self._connect() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO manifest("
                    "uuid, original_path, size_bytes, kind, status, "
                    "retry_count, next_retry_ts, staged_path, "
                    "remote_path, last_error, created_at, updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (item.uuid, item.original_path, item.size_bytes,
                     item.kind, item.status, item.retry_count,
                     item.next_retry_ts, item.staged_path,
                     item.remote_path, item.last_error,
                     item.created_at, item.updated_at))

    # ----- reads (read-only; no lock needed) -----
    def get(self, uuid: str) -> Optional[Item]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM manifest WHERE uuid=?",
                (uuid,))
            row = cur.fetchone()
        return Item.from_row(row) if row else None

    def get_by_path(self, original_path: str) -> Optional[Item]:
        """Look up the most recent row whose ``original_path`` matches.

        Used by the worker thread to avoid re-enqueueing a file that
        we have already committed to (staging / uploaded) before the
        policy walks the same glob again.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM manifest WHERE original_path=? "
                "ORDER BY updated_at DESC LIMIT 1",
                (original_path,))
            row = cur.fetchone()
        return Item.from_row(row) if row else None

    def list_by_status(self, status: str, *, limit: int = 100) -> List[Item]:
        if status not in ALL_STATUSES:
            raise ValueError(f"unknown status {status!r}")
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM manifest WHERE status=? "
                "ORDER BY updated_at DESC LIMIT ?",
                (status, int(limit)))
            return [Item.from_row(r) for r in cur.fetchall()]

    def list_uploads(self, *, limit: int = 50) -> List[Item]:
        return self.list_by_status(STATUS_UPLOADED, limit=limit)

    def list_pending(self) -> List[Item]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM manifest WHERE status=? "
                "ORDER BY next_retry_ts ASC, updated_at ASC",
                (STATUS_PENDING,))
            return [Item.from_row(r) for r in cur.fetchall()]

    def due_for_retry(self, now: Optional[float] = None) -> List[Item]:
        """Pending items whose ``next_retry_ts`` has elapsed."""
        ts = now if now is not None else time.time()
        pending = self.list_pending()
        return [it for it in pending if it.next_retry_ts <= ts]

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {s: 0 for s in ALL_STATUSES}
        with self._connect() as conn:
            for row in conn.execute(
                "SELECT status, COUNT(*) c FROM manifest GROUP BY status"
            ).fetchall():
                out[row["status"]] = int(row["c"])
        return out

    def oldest_uploaded_at(self) -> Optional[float]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MIN(created_at) FROM manifest "
                "WHERE status=?"
            , (STATUS_UPLOADED,)).fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])

    def total_uploaded_bytes(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(size_bytes),0) FROM manifest "
                "WHERE status=?"
            , (STATUS_UPLOADED,)).fetchone()
        return int(row[0] or 0)

    # ----- maintenance -----
    def delete(self, uuid: str) -> bool:
        with self._lock, self._connect() as conn:
            with conn:
                cur = conn.execute(
                    "DELETE FROM manifest WHERE uuid=?",
                    (uuid,))
                return cur.rowcount > 0

    def truncate(self, statuses: Iterable[str]) -> int:
        n = 0
        with self._lock, self._connect() as conn:
            for s in statuses:
                if s not in ALL_STATUSES:
                    continue
                with conn:
                    cur = conn.execute(
                        "DELETE FROM manifest WHERE status=?",
                        (s,))
                    n += cur.rowcount
        return n
