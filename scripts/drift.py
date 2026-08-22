#!/usr/bin/env python3
"""The Tank Project — drift + anomaly helpers.

Hosts 3 features (F093-F095):

* ``drift-24h``        — read topic_logs for the last 24h and rollup counts
* ``heatmap``          — render an hour-bucket ASCII heatmap of activity
* ``scheduler-replay`` — replay a captured `sched.jsonl` schedule locally
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path



LOG_PREFIX = "[drift]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F093 — drift-24h
# ---------------------------------------------------------------------------
def cmd_drift_24h(args: argparse.Namespace) -> int:
    """F093 — 24h drift summary."""
    db = _repo_root() / "tank_ws" / "data" / "log.db"
    if not db.exists():
        _err(f"log.db missing: {db}")
        return 1
    since = time.time() - args.hours * 3600
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT topic, count(*) FROM topic_logs "
            "WHERE ts >= ? GROUP BY topic ORDER BY 2 DESC",
            (since,),
        ).fetchall()
    total = sum(c for _, c in rows)
    _ok(json.dumps({
        "window_hours": args.hours,
        "total": total,
        "by_topic": rows[:args.top],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F094 — heatmap
# ---------------------------------------------------------------------------
def cmd_heatmap(args: argparse.Namespace) -> int:
    """F094 — hour-bucket ASCII heatmap."""
    db = _repo_root() / "tank_ws" / "data" / "log.db"
    if not db.exists():
        _err(f"log.db missing: {db}")
        return 1
    since = time.time() - args.hours * 3600
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT CAST(ts / 3600 AS INTEGER) AS bucket, count(*) "
            "FROM topic_logs WHERE ts >= ? GROUP BY bucket ORDER BY 1",
            (since,),
        ).fetchall()
    if not rows:
        _err("no rows in window")
        return 1
    counts = [c for _, c in rows]
    hi = max(counts)
    chars = " .,:;ox#%@"
    print(f"# heatmap of last {args.hours}h (max={hi} events/h)")
    print("hr | events (scaled 0..{hi})")
    for bucket, c in rows:
        idx = int(round((c / hi) * (len(chars) - 1))) if hi else 0
        bar = chars[idx] * args.width
        print(f"{bucket:>5d}h | {bar} ({c})")
    _ok(f"{len(rows)} hour-buckets rendered")
    return 0


# ---------------------------------------------------------------------------
# F095 — scheduler-replay
# ---------------------------------------------------------------------------
def cmd_scheduler_replay(args: argparse.Namespace) -> int:
    """F095 — scheduler replay."""
    p = Path(args.from_)
    if not p.exists():
        _err(f"schedule file missing: {p}")
        return 1
    n = 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = ev.get("ts", 0)
        # tiny deterministic replay loop: print + sleep relative to ts.
        when = ev.get("topic", "?")
        what = (ev.get("payload_text") or "")[:120]
        print(f"{ts:.3f}  {when:<32s}  {what}")
        n += 1
        if args.delay and n < args.max_events:
            time.sleep(args.delay)
    _ok(f"replayed {n} events from {p}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Drift / anomaly helpers (F093-F095).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("drift-24h", help="F093 — 24h drift")
    pd.add_argument("--hours", type=int, default=24)
    pd.add_argument("--top", type=int, default=20)
    ph = sub.add_parser("heatmap", help="F094 — heatmap")
    ph.add_argument("--hours", type=int, default=12)
    ph.add_argument("--width", type=int, default=40)
    pr = sub.add_parser("scheduler-replay", help="F095 — scheduler replay")
    pr.add_argument("--from", dest="from_", required=True)
    pr.add_argument("--delay", type=float, default=0.0)
    pr.add_argument("--max-events", type=int, default=10_000)
    return p


HANDLERS = {
    "drift-24h":       cmd_drift_24h,
    "heatmap":         cmd_heatmap,
    "scheduler-replay":cmd_scheduler_replay,
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
