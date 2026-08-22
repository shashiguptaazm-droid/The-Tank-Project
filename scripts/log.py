#!/usr/bin/env python3
"""The Tank Project — `tank_log` query CLI.

Hosts 3 features (F044-F046):

* ``grep``           — full-text grep over the topic_log store
* ``topic-summary``  — rollup row-count by topic for `learn_summary.py`
* ``emotion-history``— dump the latest N rows from `/emotion/state` log

All access is via sqlite3 stdlib (no rclpy).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path



LOG_PREFIX = "[log-cli]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _log_db() -> Path:
    # `tank_log` package writes to data/log.db.
    candidate = _repo_root() / "tank_ws" / "data" / "log.db"
    return candidate if candidate.exists() else candidate


# ---------------------------------------------------------------------------
# F044 — full-text grep
# ---------------------------------------------------------------------------
def cmd_grep(args: argparse.Namespace) -> int:
    """F044 — grep a pattern through `topic_logs.payload_text`."""
    db = _log_db()
    if not db.exists():
        _err(f"log.db missing at {db}")
        return 1
    with sqlite3.connect(db) as con:
        like = f"%{args.pattern}%"
        rows = con.execute(
            "SELECT ts, topic, source, payload_text FROM topic_logs "
            "WHERE payload_text LIKE ? ORDER BY ts DESC LIMIT ?",
            (like, args.limit),
        ).fetchall()
    if not rows:
        _err(f"no matches for {args.pattern!r}")
        return 1
    for ts, topic, source, payload in rows:
        line = (payload or "")[:args.width]
        print(f"{ts:.3f}  {topic:>32s}  {source:>10s}  {line}")
    _ok(f"{len(rows)} matches")
    return 0


# ---------------------------------------------------------------------------
# F045 — topic summary
# ---------------------------------------------------------------------------
def cmd_topic_summary(args: argparse.Namespace) -> int:
    """F045 — topic row-count rollup."""
    db = _log_db()
    if not db.exists():
        _err(f"log.db missing at {db}")
        return 1
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT topic, count(*) FROM topic_logs "
            "WHERE ts > ? GROUP BY topic ORDER BY 2 DESC",
            (args.since_ts,),
        ).fetchall()
    total = sum(c for _, c in rows)
    _ok(json.dumps({"total": total, "topics": rows[:args.top]}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F046 — emotion-history
# ---------------------------------------------------------------------------
def cmd_emotion_history(args: argparse.Namespace) -> int:
    """F046 — dump latest emotion_state rows."""
    db = _log_db()
    if not db.exists():
        _err(f"log.db missing at {db}")
        return 1
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT ts, payload_text FROM topic_logs "
            "WHERE topic = '/emotion/state' ORDER BY ts DESC LIMIT ?",
            (args.limit,),
        ).fetchall()
    last_ts = None
    buckets: list = []
    for ts, payload in reversed(rows):
        if last_ts is None:
            last_ts = ts
            buckets.append((ts, payload))
            continue
        if ts - last_ts > args.merge_gap_s:
            break
        buckets.append((ts, payload))
        last_ts = ts
    _ok(json.dumps({
        "n_recent": len(rows),
        "n_in_gap": len(buckets),
        "history": [{"ts": t, "text": (p or "")[:120]} for t, p in buckets],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project log query helper (F044-F046).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pg = sub.add_parser("grep", help="F044 — grep the topic_log store")
    pg.add_argument("pattern")
    pg.add_argument("--limit", type=int, default=200)
    pg.add_argument("--width", type=int, default=180)
    pts = sub.add_parser("topic-summary", help="F045 — topic row-count rollup")
    pts.add_argument("--since-ts", type=float, default=0.0)
    pts.add_argument("--top", type=int, default=20)
    pe = sub.add_parser("emotion-history", help="F046 — emotion state history")
    pe.add_argument("--limit", type=int, default=500)
    pe.add_argument("--merge-gap-s", type=float, default=8.0)
    return p


HANDLERS = {
    "grep":            cmd_grep,
    "topic-summary":   cmd_topic_summary,
    "emotion-history": cmd_emotion_history,
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
