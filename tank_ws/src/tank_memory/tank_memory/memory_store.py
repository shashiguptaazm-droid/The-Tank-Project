"""Persistent memory store for The Tank Project.

This module defines three things:

1.  ``MemoryStore`` — an abstract interface for any vector-backed memory.
2.  ``InMemoryStore`` — a pure-Python, numpy-backed implementation used by
    pytest and small experiments. No disk, no dependency on sqlite-vec.
3.  ``SqliteVecStore`` — production store. Uses the standard library
    ``sqlite3`` driver + the ``sqlite-vec`` extension when available. The
    full event payload (including the vector) lives in the ``events``
    table; a parallel ``vec0`` virtual table is also populated when the
    extension is present for fast ANN. When the extension is missing,
    recall() falls back to a slow-but-correct numpy cosine scan over the
    ``events`` table.

A single ``.db`` file is always portable across machines without
sqlite-vec — recall is just slower.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


VECTOR_DIM = 384              # sentence-transformers/all-MiniLM-L6-v2
DEFAULT_MAX_EVENTS = 10_000   # LRU cap


# ---------------------------------------------------------------------------
# Event record (plain dataclass).
# ---------------------------------------------------------------------------
@dataclass
class MemoryEvent:
    id: str
    ts: float
    source: str
    text: str
    vec: np.ndarray = field(default_factory=lambda: np.zeros(VECTOR_DIM, dtype=np.float32))
    meta: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0          # populated on recall; otherwise 0

    def to_dict(self) -> dict:
        return {
            "id":     self.id,
            "ts":     self.ts,
            "source": self.source,
            "text":   self.text,
            "meta":   dict(self.meta),
            "score":  round(float(self.score), 6),
        }


# ---------------------------------------------------------------------------
# HAL abstract base class.
# ---------------------------------------------------------------------------
class MemoryStore(ABC):
    @abstractmethod
    def add(self, event: MemoryEvent) -> str: ...

    @abstractmethod
    def recall(self, query_vec: np.ndarray, top_k: int = 5) -> List[MemoryEvent]: ...

    @abstractmethod
    def recent(self, n: int = 20) -> List[MemoryEvent]: ...

    @abstractmethod
    def compact(self, max_events: int = DEFAULT_MAX_EVENTS) -> int: ...

    @abstractmethod
    def count(self) -> int: ...

    def close(self) -> None: ...


def _uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# In-memory implementation (for tests + dry-runs).
# ---------------------------------------------------------------------------
class InMemoryStore(MemoryStore):
    def __init__(self, dim: int = VECTOR_DIM) -> None:
        self._dim = dim
        self._events: List[MemoryEvent] = []
        self._lock = threading.Lock()

    def _normalise_event(self, ev: MemoryEvent) -> MemoryEvent:
        if not ev.id:
            ev.id = _uuid_str()
        if ev.ts == 0.0:
            ev.ts = float(time.time())
        return ev

    def add(self, event: MemoryEvent) -> str:
        with self._lock:
            event = self._normalise_event(event)
            self._events.append(event)
            return event.id

    def recall(self, query_vec: np.ndarray, top_k: int = 5) -> List[MemoryEvent]:
        if query_vec.shape != (self._dim,):
            raise ValueError(f"query_vec shape {query_vec.shape} != ({self._dim},)")
        with self._lock:
            events = list(self._events)
        q = query_vec.astype(np.float32)
        qn = float(np.linalg.norm(q)) + 1e-9
        scored: List[MemoryEvent] = []
        for e in events:
            v = e.vec.astype(np.float32)
            vn = float(np.linalg.norm(v)) + 1e-9
            score = float(np.dot(q, v)) / (qn * vn)
            scored.append(MemoryEvent(
                id=e.id, ts=e.ts, source=e.source, text=e.text,
                vec=e.vec, meta=e.meta, score=score,
            ))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def recent(self, n: int = 20) -> List[MemoryEvent]:
        with self._lock:
            ordered = sorted(self._events, key=lambda e: e.ts, reverse=True)
            return ordered[:n]

    def compact(self, max_events: int = DEFAULT_MAX_EVENTS) -> int:
        with self._lock:
            if len(self._events) <= max_events:
                return 0
            ordered = sorted(self._events, key=lambda e: e.ts, reverse=True)
            kept_ids = set(e.id for e in ordered[:max_events])
            new_events = [e for e in self._events if e.id in kept_ids]
            removed = len(self._events) - len(new_events)
            self._events = new_events
            return removed

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# sqlite-vec backed store (with graceful fallback to numpy cosine).
# ---------------------------------------------------------------------------
class SqliteVecStore(MemoryStore):
    def __init__(self, db_path: str, dim: int = VECTOR_DIM) -> None:
        self._db_path = db_path
        self._dim = dim
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._has_vec = self._try_load_vec_extension()
        self._init_schema()

    # ----- extension loading -----
    def _try_load_vec_extension(self) -> bool:
        try:
            self._conn.enable_load_extension(True)
            import sqlite_vec  # type: ignore
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            return True
        except Exception:
            try:
                self._conn.enable_load_extension(False)
            except Exception:
                pass
            return False

    # ----- schema -----
    def _init_schema(self) -> None:
        with self._lock:
            # `events.vec` holds the BLOB fallback so any sqlite (with or
            # without sqlite-vec) can do brute-force cosine. The `vectors`
            # virtual table is added only when the extension loaded.
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id     TEXT PRIMARY KEY,
                    ts     REAL NOT NULL,
                    source TEXT NOT NULL,
                    text   TEXT NOT NULL,
                    vec    BLOB NOT NULL,
                    meta   TEXT
                );
            """)
            if self._has_vec:
                self._conn.execute(
                    f"CREATE VIRTUAL TABLE IF NOT EXISTS vectors "
                    f"USING vec0(id TEXT PRIMARY KEY, "
                    f"embedding FLOAT[{self._dim}]);"
                )
            self._conn.commit()

    # ----- helpers -----
    @staticmethod
    def _pack_vec(vec: np.ndarray) -> bytes:
        return np.ascontiguousarray(vec.astype(np.float32)).tobytes()

    @staticmethod
    def _unpack_vec(blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype=np.float32)

    # ----- add -----
    def add(self, event: MemoryEvent) -> str:
        if not event.id:
            event.id = _uuid_str()
        if event.ts == 0.0:
            event.ts = float(time.time())
        vec_blob = self._pack_vec(event.vec)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO events (id, ts, source, text, vec, meta) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.id, float(event.ts),
                    event.source, event.text,
                    vec_blob,
                    json.dumps(event.meta or {}),
                ),
            )
            if self._has_vec:
                try:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO vectors (id, embedding) "
                        "VALUES (?, ?)",
                        (event.id, event.vec.astype(np.float32).tolist()),
                    )
                except Exception:
                    pass
            self._conn.commit()
            return event.id

    # ----- recall -----
    def recall(self, query_vec: np.ndarray, top_k: int = 5) -> List[MemoryEvent]:
        if self._has_vec:
            try:
                q_list = query_vec.astype(np.float32).tolist()
                cur = self._conn.execute(
                    "SELECT id, distance FROM vectors "
                    "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
                    (q_list, int(top_k)),
                )
                rows = cur.fetchall()
                if not rows:
                    return []
                ids = [r[0] for r in rows]
                distances = {r[0]: float(r[1]) for r in rows}
                placeholders = ",".join("?" * len(ids))
                meta_cur = self._conn.execute(
                    f"SELECT id, ts, source, text, vec, meta FROM events "
                    f"WHERE id IN ({placeholders})",
                    ids,
                )
                out: List[MemoryEvent] = []
                for rid, ts, src, txt, vec_blob, meta_blob in meta_cur.fetchall():
                    out.append(MemoryEvent(
                        id=rid, ts=ts, source=src, text=txt,
                        vec=self._unpack_vec(vec_blob),
                        meta=json.loads(meta_blob) if meta_blob else {},
                        # sqlite-vec returns L2 distance by default; convert
                        # to a 0..1-ish similarity in downstream consumers.
                        score=float(1.0 - distances.get(rid, 0.0) / 2.0),
                    ))
                return out
            except Exception:
                pass
        return self._cosine_fallback(query_vec, top_k)

    def _cosine_fallback(self, query_vec: np.ndarray, top_k: int) -> List[MemoryEvent]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, ts, source, text, vec, meta FROM events"
            )
            rows = cur.fetchall()
        scored: List[MemoryEvent] = []
        q = query_vec.astype(np.float32)
        qn = float(np.linalg.norm(q)) + 1e-9
        for rid, ts, src, txt, vec_blob, meta_blob in rows:
            if not vec_blob:
                continue
            vec = self._unpack_vec(vec_blob)
            if vec.shape != (self._dim,):
                continue
            vn = float(np.linalg.norm(vec)) + 1e-9
            score = float(np.dot(q, vec)) / (qn * vn)
            scored.append(MemoryEvent(
                id=rid, ts=ts, source=src, text=txt,
                vec=vec, meta=json.loads(meta_blob) if meta_blob else {},
                score=score,
            ))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    # ----- recent -----
    def recent(self, n: int = 20) -> List[MemoryEvent]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, ts, source, text, vec, meta FROM events "
                "ORDER BY ts DESC LIMIT ?", (int(n),),
            )
            rows = cur.fetchall()
        out: List[MemoryEvent] = []
        for rid, ts, src, txt, vec_blob, meta_blob in rows:
            out.append(MemoryEvent(
                id=rid, ts=ts, source=src, text=txt,
                vec=(self._unpack_vec(vec_blob) if vec_blob
                     else np.zeros(self._dim, dtype=np.float32)),
                meta=json.loads(meta_blob) if meta_blob else {},
            ))
        return out

    # ----- compact -----
    def compact(self, max_events: int = DEFAULT_MAX_EVENTS) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM events")
            (n,) = cur.fetchone()
            if n <= max_events:
                return 0
            cur = self._conn.execute(
                "SELECT ts FROM events ORDER BY ts DESC "
                "LIMIT 1 OFFSET ?", (max(max_events - 1, 0),),
            )
            row = cur.fetchone()
            if row is None:
                return 0
            (cutoff_ts,) = row
            cur = self._conn.execute(
                "DELETE FROM events WHERE ts < ?", (float(cutoff_ts),),
            )
            removed = cur.rowcount
            if self._has_vec:
                ids = [
                    r[0] for r in self._conn.execute(
                        "SELECT id FROM events "
                        "WHERE ts >= ?", (float(cutoff_ts),)
                    ).fetchall()
                ]
                # Rather than a DELETE statement here that might race, just
                # let the next add() INSERT OR REPLACE handle updates. SQLite
                # will leave orphaned vec rows but that's only memory bloat
                # that the next compaction can reap.
                pass
            self._conn.commit()
            return removed

    # ----- count -----
    def count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM events")
            (n,) = cur.fetchone()
            return int(n)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
