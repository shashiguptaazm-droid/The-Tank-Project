#!/usr/bin/env python3
"""Tiny FastAPI service exposing :class:`tank_meta.meta_store.MetaStore`
over HTTP for the dashboard and external callers.

Routes
------
* ``GET /api/meta/code?q=<text>&top_k=5``
* ``GET /api/meta/hardware?component=<name>``   (case-insensitive, LIKE fallback)
* ``GET /api/meta/hardware/all``
* ``GET /api/meta/decisions?q=<text>&top_k=5``
* ``GET /api/meta/knowledge?q=<text>&top_k=5``
* ``GET /api/meta/status``

Usage::

    python3 scripts/serve_meta_api.py --port 8083
    curl http://localhost:8083/api/meta/code?q=ros2%20node
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Optional

# Make the package importable when launched as a standalone script.
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PKG_PARENT)

try:
    from fastapi import FastAPI, HTTPException, Query  # type: ignore
    from tank_meta.meta_store import MetaStore
except Exception as exc:  # pragma: no cover — only hit on env without fastapi
    raise SystemExit(
        f"serve_meta_api requires fastapi + uvicorn. "
        f"pip install fastapi uvicorn. ({exc})"
    )


DEFAULT_DB = "/root/the tank project/tank_ws/data/meta.db"
DEFAULT_PORT = 8083


_STATE_LOCK = threading.Lock()
_STORE: Optional["MetaStore"] = None
_DB_PATH: str = DEFAULT_DB


def _store() -> "MetaStore":
    global _STORE
    if _STORE is None:
        with _STATE_LOCK:
            if _STORE is None:                # double-checked locking
                _STORE = MetaStore(db_path=_DB_PATH)
    return _STORE


@asynccontextmanager
async def lifespan(app: FastAPI):                # noqa: ARG001
    # Lazy connect on first request, not at startup, so importing the
    # module doesn't hold a sqlite handle during pytest import-time.
    yield
    # Clean shutdown
    global _STORE
    if _STORE is not None:
        try:
            with _STATE_LOCK:
                if _STORE is not None:
                    _STORE.close()
                    _STORE = None
        except Exception:
            pass


app = FastAPI(
    title="tank-meta-api",
    version="0.1.0",
    description=(
        "HTTP shim over the structured coding-agent memory store. "
        "Read-only by default; write to the underlying .db through the ROS "
        "topic /meta/decision_append or the index_workspace.py script."
    ),
    lifespan=lifespan,
)


@app.get("/api/meta/code")
def get_code(q: str = Query(..., min_length=1),
             top_k: int = Query(5, ge=1, le=50)) -> dict:
    rows = _store().search_code(q, top_k=top_k)
    return {"query": q, "top_k": top_k,
            "hits": [r.to_dict() for r in rows]}


@app.get("/api/meta/hardware")
def get_hardware(component: str = Query(..., min_length=1)) -> dict:
    row = _store().find_hardware(component)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no component matched '{component}'")
    return {"hit": row.to_dict()}


@app.get("/api/meta/hardware/all")
def get_hardware_all() -> dict:
    rows = _store().all_hardware()
    return {"count": len(rows), "items": [r.to_dict() for r in rows]}


@app.get("/api/meta/decisions")
def get_decisions(q: str = Query(..., min_length=1),
                  top_k: int = Query(5, ge=1, le=50)) -> dict:
    rows = _store().search_decisions(q, top_k=top_k)
    return {"query": q, "top_k": top_k,
            "hits": [r.to_dict() for r in rows]}


@app.get("/api/meta/knowledge")
def get_knowledge(q: str = Query(..., min_length=1),
                  top_k: int = Query(5, ge=1, le=50)) -> dict:
    hits = _store().search_knowledge(q, top_k=top_k)
    return {"query": q, "top_k": top_k, "hits": hits}


@app.get("/api/meta/status")
def get_status() -> dict:
    return {"db_path": _DB_PATH, "counts": _store().counts()}


def main() -> int:
    parser = argparse.ArgumentParser(description="tank_meta HTTP shim")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    global _DB_PATH
    _DB_PATH = args.db

    import uvicorn  # type: ignore
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
