"""FastAPI server for the Agent Framework, port :8085.

Routes:
  GET  /health                              (no auth)
  GET  /manifest                            bearer-auth → raw JSON
  GET  /manifest/openai                     bearer-auth → OpenAI tools
  GET  /manifest/anthropic                  bearer-auth → Anthropic tools
  GET  /manifest/summary                    bearer-auth → counts + categories
  POST /invoke                              bearer-auth (write)
  GET  /audit?limit=N&tool_name=X           bearer-auth (read)
  POST /audit/clear                         bearer-auth (admin only)

Auth model reuses tank_command_bridge's TANK_API_KEY / TANK_API_KEYS env
vars so a single token can drive both bridges.
"""
from __future__ import annotations
import hashlib
import os
import threading
import time
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Depends, Header
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from .registry import ToolRegistry
from .invoker import ToolInvoker
from .manifest import Manifest
from .audit import AuditLog
from .schemas import ToolCallRequest


def _load_tokens() -> dict:
    """Map role → token. Supports TANK_API_KEYS={json} or single TANK_API_KEY."""
    raw = os.environ.get("TANK_API_KEYS", "").strip()
    if raw:
        try:
            import json as _json
            return dict(_json.loads(raw))
        except Exception:
            pass
    single = os.environ.get("TANK_API_KEY", "").strip()
    return {"admin": single} if single else {}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


class _Bucket:
    """Per-token token-bucket rate-limiter (thread-safe)."""
    def __init__(self, capacity: int, refill_per_s: float):
        self.capacity = capacity
        self.refill_per_s = refill_per_s
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def take(self, n: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
            self.last_refill = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


def make_app(scripts_dir, audit_db):
    if not HAS_FASTAPI:
        raise RuntimeError("FastAPI not installed; pip install fastapi uvicorn")

    registry = ToolRegistry(scripts_dir=scripts_dir)
    registry.discover()
    invoker = ToolInvoker(registry)
    audit = AuditLog(db_path=audit_db)
    manifest = Manifest(registry=registry)
    tokens = _load_tokens()
    buckets = {}
    buckets_lock = threading.Lock()

    def _bucket_for(token_hash: str, write: bool):
        key = (token_hash, write)
        with buckets_lock:
            if key not in buckets:
                cap = 10 if write else 60
                buckets[key] = _Bucket(capacity=cap, refill_per_s=cap / 60)
            return buckets[key]

    @asynccontextmanager
    async def lifespan(app):
        # warmup already happened during registry.discover above
        yield

    app = FastAPI(
        title="TankOS Agent Framework",
        version="0.1.0",
        description=(
            f"Unified surface for {len(registry.list())} host-level CLI tools "
            f"+ future plugin slots. Bearer auth, audit log, per-token rate limit."
        ),
        lifespan=lifespan,
    )

    def _require_auth(authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization[len("Bearer "):].strip()
        if token not in tokens.values():
            raise HTTPException(status_code=401, detail="invalid token")
        for role, t in tokens.items():
            if t == token:
                return {"token": token, "role": role, "hash": _hash_token(token)}

    def _enforce_rate_limit(actor: dict, write: bool):
        bucket = _bucket_for(actor["hash"], write)
        if not bucket.take():
            raise HTTPException(status_code=429, detail="rate limited")

    @app.get("/health")
    def health():
        return {"status": "ok", "tools": len(registry.list()),
                "categories": registry.categories()}

    @app.get("/manifest")
    def manifest_raw(actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=False)
        return manifest.raw()

    @app.get("/manifest/openai")
    def manifest_openai(actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=False)
        return manifest.openai()

    @app.get("/manifest/anthropic")
    def manifest_anthropic(actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=False)
        return manifest.anthropic()

    @app.get("/manifest/summary")
    def manifest_summary(actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=False)
        return manifest.summary()

    @app.post("/invoke")
    def invoke(req: ToolCallRequest, actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=True)
        response = invoker.invoke(req)
        audit.record(
            request_id=response.request_id,
            tool_name=response.tool_name,
            args=req.args,
            actor_token_hash=actor["hash"],
            status=response.status,
            exit_code=response.exit_code,
            duration_ms=response.duration_ms,
        )
        return response.to_dict()

    @app.get("/audit")
    def audit_list(limit: int = 50, tool_name: Optional[str] = None,
                   actor=Depends(_require_auth)):
        _enforce_rate_limit(actor, write=False)
        records = audit.recent(limit=limit, tool_name=tool_name)
        return [asdict(r) for r in records]

    @app.post("/audit/clear")
    def audit_clear(actor=Depends(_require_auth)):
        if actor["role"] != "admin":
            raise HTTPException(status_code=403, detail="admin only")
        _enforce_rate_limit(actor, write=True)
        audit.clear()
        return {"cleared": True}

    return app


def main(scripts_dir=None, audit_db=None, port: int = 8085):
    """Entry point: parse sys.argv for [scripts_dir, audit_db, port]."""
    import sys as _sys
    if scripts_dir is None and len(_sys.argv) > 1:
        scripts_dir = _sys.argv[1]
    elif scripts_dir is None:
        scripts_dir = "/root/the tank project/scripts"
    if audit_db is None and len(_sys.argv) > 2:
        audit_db = _sys.argv[2]
    elif audit_db is None:
        audit_db = "/root/the tank project/tank_ws/data/agent_audit.db"
    if len(_sys.argv) > 3:
        port = int(_sys.argv[3])
    app = make_app(scripts_dir=Path(scripts_dir), audit_db=Path(audit_db))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
