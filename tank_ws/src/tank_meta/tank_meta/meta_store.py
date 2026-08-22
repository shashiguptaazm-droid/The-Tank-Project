"""Code-aware knowledge store for The Tank Project coding agent.

This store sits separately from :mod:`tank_memory` — that one records
**event-style memory** (assistant turns, user utterances, recalled context).
This one records **structured knowledge** indexed by the coding agent:

* ``code_files``   — one row per Python file the agent can audit.
* ``hardware``     — one row per hardware component (component → bus/pin/driver).
* ``decisions``    — append-only log of past fixes & design decisions.
* ``knowledge``    — markdown notes / datasheets / docs snippets.

A single ``.db`` file is portable across laptops (no sqlite-vec needed;
we only do keyword LIKE search here, not vector recall — that path lives
in :mod:`tank_memory`).

Concurrency: one writer at a time via :class:`threading.Lock`. Readers
may run concurrently because SQLite + ``check_same_thread=False`` is safe
for read-only queries.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS code_files (
    path           TEXT PRIMARY KEY,
    module         TEXT,
    language       TEXT,
    purpose        TEXT,
    line_count     INTEGER,
    last_modified  REAL,
    functions_json TEXT,
    classes_json   TEXT,
    deps_json      TEXT,
    source         TEXT                    -- 'ast' or 'manual'
);

CREATE TABLE IF NOT EXISTS hardware (
    component  TEXT PRIMARY KEY,
    kind       TEXT,
    bus        TEXT,
    pin        TEXT,
    driver     TEXT,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id       TEXT PRIMARY KEY,
    ts       REAL,
    problem  TEXT,
    reason   TEXT,
    solution TEXT,
    result   TEXT
);

CREATE TABLE IF NOT EXISTS knowledge (
    id     TEXT PRIMARY KEY,
    title  TEXT,
    source TEXT,
    path   TEXT,
    text   TEXT,
    tags_json TEXT
);
"""


# ---------------------------------------------------------------------------
# Plain dataclasses — return objects, not dict sprawl.
# ---------------------------------------------------------------------------
@dataclass
class CodeFileRow:
    path: str
    module: str = ""
    language: str = "python"
    purpose: str = ""
    line_count: int = 0
    last_modified: float = 0.0
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    deps: List[str] = field(default_factory=list)
    source: str = "ast"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path":          self.path,
            "module":        self.module,
            "language":      self.language,
            "purpose":       self.purpose,
            "line_count":    self.line_count,
            "last_modified": self.last_modified,
            "functions":     list(self.functions),
            "classes":       list(self.classes),
            "deps":          list(self.deps),
            "source":        self.source,
        }


@dataclass
class HardwareRow:
    component: str
    kind: str = ""
    bus: str = ""
    pin: str = ""
    driver: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component, "kind": self.kind,
            "bus": self.bus, "pin": self.pin,
            "driver": self.driver, "notes": self.notes,
        }


@dataclass
class DecisionRow:
    id: str
    ts: float = 0.0
    problem: str = ""
    reason: str = ""
    solution: str = ""
    result: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "ts": self.ts,
            "problem": self.problem, "reason": self.reason,
            "solution": self.solution, "result": self.result,
        }


# ---------------------------------------------------------------------------
# Store.
# ---------------------------------------------------------------------------
class MetaStore:
    """Thread-safe sqlite store. Single-writer, multi-reader."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ----- code ----------------------------------------------------
    def upsert_code(self, row: CodeFileRow) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO code_files "
                "(path, module, language, purpose, line_count, "
                " last_modified, functions_json, classes_json, "
                " deps_json, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    row.path, row.module, row.language, row.purpose,
                    row.line_count, float(row.last_modified),
                    json.dumps(row.functions), json.dumps(row.classes),
                    json.dumps(row.deps), row.source,
                ),
            )
            self._conn.commit()

    def search_code(self, query: str, top_k: int = 10) -> List[CodeFileRow]:
        """Very simple keyword search — match against module + functions
        + classes + deps + purpose. Sorted by relevance score = total
        keyword hits (higher is better). Adequate for a coding agent
        hinting tool."""
        with self._lock:
            cur = self._conn.execute("SELECT * FROM code_files")
            rows = cur.fetchall()
        out: List[CodeFileRow] = []
        q_tokens = [t for t in query.lower().split() if t]
        cols = ["path", "module", "language", "purpose", "functions", "classes", "deps"]
        for r in rows:
            payload = {
                "path":   r[0], "module": r[1] or "",
                "language": r[2] or "", "purpose": r[3] or "",
                "functions": r[6] or "[]",
                "classes":   r[7] or "[]",
                "deps":      r[8] or "[]",
            }
            score = 0
            for tok in q_tokens:
                for c in cols:
                    if c in ("functions", "classes", "deps"):
                        sample = " ".join(json.loads(payload[c])).lower()
                    else:
                        sample = str(payload[c]).lower()
                    if tok in sample:
                        score += 1
            if score > 0:
                out.append(CodeFileRow(
                    path=r[0], module=r[1] or "", language=r[2] or "",
                    purpose=r[3] or "", line_count=r[4] or 0,
                    last_modified=r[5] or 0.0,
                    functions=json.loads(r[6] or "[]"),
                    classes=json.loads(r[7] or "[]"),
                    deps=json.loads(r[8] or "[]"),
                    source=r[9] or "ast",
                ))
        out.sort(key=lambda cf: (
            -sum(1 for t in q_tokens if t in cf.purpose.lower()),
            -len(cf.functions) - len(cf.classes),
        ))
        return out[:top_k]

    # ----- hardware ------------------------------------------------
    def upsert_hardware(self, row: HardwareRow) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO hardware "
                "(component, kind, bus, pin, driver, notes) "
                "VALUES (?,?,?,?,?,?)",
                (row.component, row.kind, row.bus, row.pin,
                 row.driver, row.notes),
            )
            self._conn.commit()

    def find_hardware(self, component: str) -> Optional[HardwareRow]:
        """Case-insensitive lookup; falls back to LIKE search."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT component, kind, bus, pin, driver, notes "
                "FROM hardware WHERE LOWER(component) = LOWER(?)",
                (component,),
            )
            row = cur.fetchone()
            if row is None:
                cur = self._conn.execute(
                    "SELECT component, kind, bus, pin, driver, notes "
                    "FROM hardware WHERE component LIKE ? LIMIT 1",
                    (f"%{component}%",),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return HardwareRow(component=row[0], kind=row[1] or "",
                           bus=row[2] or "", pin=row[3] or "",
                           driver=row[4] or "", notes=row[5] or "")

    def all_hardware(self) -> List[HardwareRow]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT component, kind, bus, pin, driver, notes "
                "FROM hardware ORDER BY component"
            )
            rows = cur.fetchall()
        return [HardwareRow(*row) for row in rows]

    # ----- decisions -----------------------------------------------
    def upsert_decision(self, row: DecisionRow) -> None:
        if not row.ts:
            row.ts = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO decisions "
                "(id, ts, problem, reason, solution, result) "
                "VALUES (?,?,?,?,?,?)",
                (row.id, float(row.ts), row.problem, row.reason,
                 row.solution, row.result),
            )
            self._conn.commit()

    def search_decisions(self, query: str, top_k: int = 10) -> List[DecisionRow]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM decisions ORDER BY ts DESC")
            rows = cur.fetchall()
        out: List[DecisionRow] = []
        q_tokens = [t for t in query.lower().split() if t]
        for r in rows:
            blob = " ".join(str(x or "") for x in r[2:]).lower()
            score = sum(1 for t in q_tokens if t in blob)
            if score > 0:
                out.append((score, DecisionRow(
                    id=r[0], ts=r[1], problem=r[2] or "",
                    reason=r[3] or "", solution=r[4] or "",
                    result=r[5] or "",
                )))
        out.sort(key=lambda x: (-x[0], -x[1].ts))
        return [d for _, d in out[:top_k]]

    # ----- knowledge ----------------------------------------------
    def upsert_knowledge(self, kid: str, title: str, source: str,
                         path: str, text: str, tags: List[str]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO knowledge "
                "(id, title, source, path, text, tags_json) "
                "VALUES (?,?,?,?,?,?)",
                (kid, title, source, path, text, json.dumps(tags)),
            )
            self._conn.commit()

    def search_knowledge(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, title, source, path, text, tags_json FROM knowledge"
            )
            rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        q_tokens = [t for t in query.lower().split() if t]
        for r in rows:
            blob = " ".join(str(x or "") for x in r[1:5]).lower()
            tags_blob = " ".join(json.loads(r[5] or "[]")).lower() if r[5] else ""
            blob = blob + " " + tags_blob
            score = sum(1 for t in q_tokens if t in blob)
            if score > 0:
                out.append((score, {
                    "id": r[0], "title": r[1] or "",
                    "source": r[2] or "", "path": r[3] or "",
                    "text": r[4] or "",
                    "tags": json.loads(r[5] or "[]"),
                    "_score": score,
                }))
        out.sort(key=lambda x: -x[0])
        return [d for _, d in out[:top_k]]

    # ----- maintenance ---------------------------------------------
    def counts(self) -> Dict[str, int]:
        with self._lock:
            out = {}
            for tbl in ("code_files", "hardware", "decisions", "knowledge"):
                cur = self._conn.execute(f"SELECT COUNT(*) FROM {tbl}")  # nosec
                (n,) = cur.fetchone()
                out[tbl] = int(n)
        return out

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
