"""SQLite WAL-mode audit log for every ToolInvoker call.

Schema:
  audit(audit_id PK, request_id, tool_name, args_json,
        actor_token_hash, status, exit_code, duration_ms, ts)
  idx_audit_ts(ts), idx_audit_tool(tool_name)

WAL mode + NORMAL synchronous keeps writes crash-safe without slowing
down the rate of reads.
"""
from __future__ import annotations
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .schemas import AuditRecord


class AuditLog:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_once()

    def _conn(self):
        c = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    def _init_once(self):
        with self._lock:
            c = self._conn()
            try:
                c.execute("""
                CREATE TABLE IF NOT EXISTS audit (
                    audit_id TEXT PRIMARY KEY,
                    request_id TEXT,
                    tool_name TEXT,
                    args_json TEXT,
                    actor_token_hash TEXT,
                    status TEXT,
                    exit_code INTEGER,
                    duration_ms INTEGER,
                    ts REAL
                )""")
                c.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit(tool_name)")
            finally:
                c.close()

    def record(self, *, request_id, tool_name, args,
               actor_token_hash, status, exit_code, duration_ms) -> AuditRecord:
        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        ts = time.time()
        rec = AuditRecord(
            audit_id=audit_id, request_id=request_id, tool_name=tool_name,
            args=args, actor_token_hash=actor_token_hash, status=status,
            exit_code=exit_code, duration_ms=duration_ms, ts=ts,
        )
        with self._lock:
            c = self._conn()
            try:
                c.execute(
                    "INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (audit_id, request_id, tool_name, json.dumps(args),
                     actor_token_hash, status, exit_code, duration_ms, ts),
                )
            finally:
                c.close()
        return rec

    def recent(self, limit: int = 100, tool_name: Optional[str] = None) -> List[AuditRecord]:
        with self._lock:
            c = self._conn()
            try:
                if tool_name:
                    rows = c.execute(
                        "SELECT audit_id, request_id, tool_name, args_json, "
                        "actor_token_hash, status, exit_code, duration_ms, ts "
                        "FROM audit WHERE tool_name = ? ORDER BY ts DESC LIMIT ?",
                        (tool_name, limit),
                    ).fetchall()
                else:
                    rows = c.execute(
                        "SELECT audit_id, request_id, tool_name, args_json, "
                        "actor_token_hash, status, exit_code, duration_ms, ts "
                        "FROM audit ORDER BY ts DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            finally:
                c.close()
        out = []
        for r in rows:
            try:
                args = json.loads(r[3]) if r[3] else {}
            except Exception:
                args = {}
            out.append(AuditRecord(
                audit_id=r[0], request_id=r[1], tool_name=r[2],
                args=args, actor_token_hash=r[4], status=r[5],
                exit_code=r[6], duration_ms=r[7], ts=r[8],
            ))
        return out

    def clear(self):
        with self._lock:
            c = self._conn()
            try:
                c.execute("DELETE FROM audit")
            finally:
                c.close()
