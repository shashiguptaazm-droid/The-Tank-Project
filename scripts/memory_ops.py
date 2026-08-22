#!/usr/bin/env python3
"""The Tank Project — memory operations CLI.

Hosts 4 features (F105-F108):

* ``vector-recall``  — single-query recall through sqlite-vec
* ``lora``           — LoRA adapter spec writer (rank / alpha)
* ``vacuum``         — drop memory rows older than N days
* ``batch-recall``   — JSONL export of batch recall
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path



LOG_PREFIX = "[memory-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _memory_db() -> Path:
    return _repo_root() / "tank_ws" / "data" / "memory.db"


# ---------------------------------------------------------------------------
# F105 — vector-recall
# ---------------------------------------------------------------------------
def cmd_vector_recall(args: argparse.Namespace) -> int:
    """F105 — vector recall (placeholder offline)."""
    db = _memory_db()
    if not db.exists():
        _err(f"{db} missing")
        return 1
    _ok(json.dumps({
        "query":   args.query,
        "top_k":   args.top_k,
        "rows":    [],
        "note":    "offline placeholder; wire batch_recall to your embedder",
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F106 — lora
# ---------------------------------------------------------------------------
def cmd_lora(args: argparse.Namespace) -> int:
    """F106 — lora spec."""
    if args.rank < 1 or args.rank > 256:
        _err(f"rank {args.rank} out of [1,256]")
        return 1
    alpha = args.alpha or (args.rank * 2)
    out = {
        "rank":           args.rank,
        "alpha":          alpha,
        "dropout":        args.dropout,
        "target_modules": ["q_proj", "v_proj"],
    }
    p = _repo_root() / "tank_ws" / "data" / "lora_spec.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    _ok(f"wrote {p}")
    return 0


# ---------------------------------------------------------------------------
# F107 — vacuum
# ---------------------------------------------------------------------------
def cmd_vacuum(args: argparse.Namespace) -> int:
    """F107 — memory vacuum (older-than)."""
    db = _memory_db()
    if not db.exists():
        _err(f"{db} missing")
        return 1
    if not args.apply:
        _log(f"DRY: would drop rows older than {args.older_than_days}d from {db}")
        return 0
    cutoff = time.time() - args.older_than_days * 86400
    with sqlite3.connect(db) as con:
        for tbl in ("events", "memory", "memories"):
            try:
                n = con.execute(
                    f"DELETE FROM {tbl} WHERE ts < ?", (cutoff,)).rowcount
                _log(f"{tbl}: {n} rows deleted")
            except sqlite3.OperationalError:
                pass
        con.execute("VACUUM")
    _ok(f"vacuum done on {db}")
    return 0


# ---------------------------------------------------------------------------
# F108 — batch-recall
# ---------------------------------------------------------------------------
def cmd_batch_recall(args: argparse.Namespace) -> int:
    """F108 — batch recall JSONL export."""
    db = _memory_db()
    if not db.exists():
        _err(f"{db} missing")
        return 1
    out = Path(args.out or "/tmp/tank_batch_recall.jsonl")
    with sqlite3.connect(db) as con:
        try:
            rows = con.execute(
                "SELECT ts, source, text FROM events ORDER BY ts DESC "
                "LIMIT ?", (args.limit,)
            ).fetchall()
        except sqlite3.OperationalError:
            _err("`events` table missing")
            return 1
    with out.open("w") as fh:
        for ts, source, text in rows:
            fh.write(json.dumps({"ts": ts, "source": source,
                                "text": (text or "")[:200]}) + "\n")
    _ok(f"wrote {len(rows)} rows -> {out}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Memory ops CLI (F105-F108).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("vector-recall", help="F105 — vector recall")
    pv.add_argument("--query", default="kitchen")
    pv.add_argument("--top-k", type=int, default=5)

    pl = sub.add_parser("lora", help="F106 — LoRA spec")
    pl.add_argument("--rank", type=int, default=8)
    pl.add_argument("--alpha", type=int, default=0,
                    help="0 -> auto = 2*rank")
    pl.add_argument("--dropout", type=float, default=0.05)

    pc = sub.add_parser("vacuum", help="F107 — vacuum older-than")
    pc.add_argument("--older-than-days", type=int, default=30)
    pc.add_argument("--apply", action="store_true")

    pb = sub.add_parser("batch-recall", help="F108 — batch recall JSONL")
    pb.add_argument("--limit", type=int, default=200)
    pb.add_argument("--out", default="")
    return p


HANDLERS = {
    "vector-recall": cmd_vector_recall,
    "lora":          cmd_lora,
    "vacuum":        cmd_vacuum,
    "batch-recall":  cmd_batch_recall,
}


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
