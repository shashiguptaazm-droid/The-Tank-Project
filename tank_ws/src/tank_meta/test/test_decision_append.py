"""pytest for the new wiring:

* /meta/decision_append (write-side) — appends to decisions.json + meta.db.
* rag_node builds a non-empty structured context block from tank_meta.
* serve_meta_api FastAPI app responds on /api/meta/code (skipped if no fastapi).
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest


# -----------------------------------------------------------------------
# 1. Decisions-append: persist + recall after append
# -----------------------------------------------------------------------
def test_decision_append_round_trip(tmp_path):
    from tank_meta.meta_store import DecisionRow, MetaStore
    from tank_meta.decisions_indexer import append_decision, load_decisions_file

    db = str(tmp_path / "meta.db")
    decisions = tmp_path / "decisions.json"
    decisions.write_text('{"schema_version": 1, "decisions": []}')

    store = MetaStore(db)
    n0 = load_decisions_file(str(decisions), store)
    assert n0 == 0
    new = DecisionRow(id="DEC-T-1", ts=12345.0,
                      problem="led flicker",
                      reason="PWM @ 1 kHz refresh conflict",
                      solution="switched to 200 Hz + dithering",
                      result="stable output, no flicker")
    n_file = append_decision(str(decisions), new)
    assert n_file == 1
    # Re-load from JSON and refresh the store
    n_loaded = load_decisions_file(str(decisions), store)
    assert n_loaded == 1
    # Now also push via direct DB upsert (the ROS path would do the same).
    store.upsert_decision(new)
    hits = store.search_decisions("flicker PWM led")
    assert hits
    ids = sorted({h.id for h in hits})
    assert "DEC-T-1" in ids
    store.close()


# -----------------------------------------------------------------------
# 2. rag_node wiring — without spinning rclpy. We rely on the fact that
#    RagNode (the ROS node class) builds the structured prompt block via
#    its MetaHalInterface and renders it correctly.
# -----------------------------------------------------------------------
class _StubMeta:
    """Stub MetaStore-like object that returns canned rows for keyword tests."""
    def __init__(self):
        self.calls = []

    def search_code(self, query, top_k=1):
        self.calls.append(("search_code", query, top_k))
        return []  # no answer

    def find_hardware(self, component):
        self.calls.append(("find_hardware", component))
        return None

    def search_decisions(self, query, top_k=1):
        self.calls.append(("search_decisions", query, top_k))
        return []

    def close(self):
        pass


# RagNode itself depends on rclpy + the heavy sentence-transformers import;
# import the module directly so we exercise just _meta_context_block and
# the impostor wiring.
def test_rag_meta_context_block_handles_missing_meta():
    """If meta is None the block returns the disabled-sentinel string."""
    # Import RagNode lazily.
    import sys as _sys
    SRC = "/root/the tank project/tank_ws/src/tank_assistant"
    if SRC not in _sys.path:
        _sys.path.insert(0, SRC)

    # Build a fake instance without calling __init__.
    import importlib
    try:
        rag_mod = importlib.import_module("tank_assistant.rag_node")
    except Exception:
        pytest.skip("rag_node couldn't be imported (likely missing rclpy)")

    rag = rag_mod.RagNode.__new__(rag_mod.RagNode)
    rag._meta = None
    out = rag._meta_context_block("PWM frequency")
    assert "structured knowledge disabled" in out


def test_rag_meta_context_block_calls_meta_handles():
    rag_mod = __import__("importlib").import_module("tank_assistant.rag_node")
    rag = rag_mod.RagNode.__new__(rag_mod.RagNode)
    meta = _StubMeta()
    rag._meta = meta
    rag._lock = __import__("threading").Lock()
    rag._meta_top_k = 1
    out = rag._meta_context_block("PWM frequency problem")
    # Should have hit search_code + find_hardware + search_decisions once each
    methods = [c[0] for c in meta.calls]
    assert "search_code" in methods
    assert "find_hardware" in methods
    assert "search_decisions" in methods
    assert "no structured match" in out


# -----------------------------------------------------------------------
# 3. serve_meta_api — only run if fastapi installed.
# -----------------------------------------------------------------------
def test_serve_meta_api_endpoints_or_skip():
    try:
        from fastapi.testclient import TestClient  # type: ignore
    except Exception:
        pytest.skip("fastapi not installed")

    import sys as _sys
    SRC = "/root/the tank project/tank_ws/src/tank_meta"
    if SRC not in _sys.path:
        _sys.path.insert(0, SRC)

    # Build a fresh MetaStore + assert endpoints serve real rows.
    import importlib
    from tank_meta.meta_store import HardwareRow, MetaStore
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "meta.db")
    store = MetaStore(db)
    store.upsert_hardware(HardwareRow(component="fan_test",
                                      kind="fan", bus="GPIO",
                                      pin="GPIO14"))
    s = importlib.import_module("tank_meta.scripts.serve_meta_api")
    # Point the lazy singleton at our temp DB
    s._DB_PATH = db
    s._STORE = store
    client = TestClient(s.app)
    r = client.get("/api/meta/hardware", params={"component": "FAN_TEST"})
    assert r.status_code == 200
    assert r.json()["hit"]["component"] == "fan_test"
    r2 = client.get("/api/meta/status")
    assert r2.status_code == 200
    body = r2.json()
    assert body["counts"]["hardware"] == 1
    store.close()
