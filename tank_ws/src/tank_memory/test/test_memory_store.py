"""pytest cases for the memory store HAL.

Uses ``InMemoryStore`` + numpy — no sqlite-vec, no sentence-transformers,
no ROS required.

Run with::

    cd tank_ws/src/tank_memory
    python3 -m pytest test/test_memory_store.py -v
"""
import math
import os
import tempfile
import json

import numpy as np
import pytest

from tank_memory.memory_store import (
    InMemoryStore,
    MemoryEvent,
    SqliteVecStore,
    VECTOR_DIM,
)


def random_vec(seed: int) -> np.ndarray:
    """A reproducible unit-norm vector."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(VECTOR_DIM).astype(np.float32)
    v /= np.linalg.norm(v) + 1e-9
    return v


def make_event(seed: int, source: str = "test", text: str = "",
               vec: np.ndarray = None) -> MemoryEvent:
    if not text:
        text = f"event {seed}"
    return MemoryEvent(
        id="", ts=float(seed + 1), source=source,
        text=text,
        vec=(vec if vec is not None else random_vec(seed)),
    )


def test_add_returns_id():
    store = InMemoryStore()
    eid = store.add(make_event(seed=1))
    assert isinstance(eid, str) and len(eid) > 0
    assert store.count() == 1


def test_recent_orders_by_ts_desc():
    store = InMemoryStore()
    for s in [10, 1, 5, 7]:
        store.add(make_event(seed=s))
    events = store.recent(n=10)
    timestamps = [e.ts for e in events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_recall_returns_top_k_by_cosine():
    store = InMemoryStore()
    a = random_vec(1)
    a_like = a + 0.01 * random_vec(99)
    a_like /= np.linalg.norm(a_like) + 1e-9
    b = random_vec(2)
    store._events.append(
        MemoryEvent(id="id_a",     ts=1.0, source="t",
                    text="A",      vec=a, meta={})
    )
    store._events.append(
        MemoryEvent(id="id_alike", ts=2.0, source="t",
                    text="A_like", vec=a_like, meta={})
    )
    store._events.append(
        MemoryEvent(id="id_b",     ts=3.0, source="t",
                    text="B",      vec=b, meta={})
    )
    hits = store.recall(query_vec=a, top_k=2)
    texts = [h.text for h in hits]
    assert "B" not in texts
    assert "A" in texts and "A_like" in texts


def test_compact_drops_oldest_events_lru():
    store = InMemoryStore()
    for s in range(1, 7):                  # ts = 2..7 (1+1 through 6+1)
        store.add(make_event(seed=s))
    assert store.count() == 6
    pruned = store.compact(max_events=3)
    assert pruned == 3
    assert store.count() == 3
    kept_ts = sorted(e.ts for e in store._events)
    # Most recent three by ts are seeds 4, 5, 6 -> ts 5, 6, 7
    assert kept_ts == [5.0, 6.0, 7.0]


def test_recall_rejects_wrong_dim():
    store = InMemoryStore()
    with pytest.raises(ValueError):
        store.recall(np.zeros(VECTOR_DIM + 1, dtype=np.float32), top_k=1)


def test_recall_returns_empty_when_no_events():
    store = InMemoryStore()
    assert store.recall(random_vec(0), top_k=5) == []


def test_export_round_trip_somewhere_consistent():
    store = InMemoryStore()
    for s in range(1, 4):
        store.add(make_event(seed=s))
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "memory.jsonl")
        events_out = sorted(store.recent(n=10), key=lambda e: -e.ts)
        with open(path, "w") as fh:
            for ev in events_out:
                fh.write(json.dumps({"id": ev.id, "ts": ev.ts,
                                     "text": ev.text, "source": ev.source,
                                     "meta": ev.meta}) + "\n")
        with open(path) as fh:
            rows = [json.loads(l) for l in fh]
        assert len(rows) == 3
        assert sorted(r["text"] for r in rows) == ["event 1", "event 2", "event 3"]


def test_sqlitevecstore_creates_db_and_roundtrip(tmp_path):
    """Smoke test on the real sqlite-backed store.

    When sqlite-vec isn't installed, the BLOB-fallback cosine path must
    still produce top-k hits.
    """
    db = str(tmp_path / "memory.db")
    store = SqliteVecStore(db_path=db, dim=VECTOR_DIM)
    a = random_vec(1)
    a_like = a + 0.01 * random_vec(99)
    a_like /= np.linalg.norm(a_like) + 1e-9
    b = random_vec(2)
    store.add(MemoryEvent(id="id_a", ts=1.0, source="t",
                          text="A", vec=a, meta={}))
    store.add(MemoryEvent(id="id_alike", ts=2.0, source="t",
                          text="A_like", vec=a_like, meta={}))
    store.add(MemoryEvent(id="id_b", ts=3.0, source="t",
                          text="B", vec=b, meta={}))
    assert store.count() == 3
    hits = store.recall(query_vec=a, top_k=2)
    assert len(hits) == 2
    texts = {h.text for h in hits}
    assert "B" not in texts
    # Compaction removes oldest two by ts (B/A_like < A)
    removed = store.compact(max_events=1)
    assert removed == 2
    assert store.count() == 1
    store.close()


def test_sqlitevecstore_recent_includes_vectors(tmp_path):
    """recent() must populate vec so downstream validity checks pass."""
    db = str(tmp_path / "memory.db")
    store = SqliteVecStore(db_path=db, dim=VECTOR_DIM)
    vec = random_vec(7)
    store.add(MemoryEvent(id="x", ts=10.0, source="t", text="hello",
                          vec=vec, meta={}))
    recent = store.recent(n=5)
    assert len(recent) == 1
    assert recent[0].text == "hello"
    assert recent[0].vec.shape == (VECTOR_DIM,)
    np.testing.assert_allclose(recent[0].vec, vec, rtol=1e-6)
    store.close()
