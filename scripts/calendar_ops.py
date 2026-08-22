#!/usr/bin/env python3
"""calendar_ops.py \u2014 daily / weekly calendar (F160 \u2013 F163).

Subcommands
-----------
* F160 today          \u2014 list today's events
* F161 week           \u2014 list the next 7 days
* F162 add-event      \u2014 append an event to the local cache
* F163 search         \u2014 case-insensitive substring search

Cache: ``tank_ws/data/calendar.json``.

Usage::

    python3 scripts/calendar_ops.py today
    python3 scripts/calendar_ops.py week
    python3 scripts/calendar_ops.py add-event --title "lab deploy" --start 14:00 --duration 60
    python3 scripts/calendar_ops.py search --query "deploy"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


PREFIX = "[calendar]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "calendar.json"


def _load() -> list:
    p = _cache_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return []


def _save(events: list) -> None:
    _cache_path().write_text(json.dumps(events, indent=2))


def cmd_today(args: argparse.Namespace) -> int:
    """F160 \u2014 list today's events."""
    today = datetime.now().strftime("%Y-%m-%d")
    events = [e for e in _load() if e.get("date") == today]
    _ok(json.dumps({"date": today, "n": len(events), "events": events},
                   indent=2))
    return 0


def cmd_week(args: argparse.Namespace) -> int:
    """F161 \u2014 list the next 7 days of events."""
    base = datetime.now()
    week = [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    events = [e for e in _load() if e.get("date") in week]
    _ok(json.dumps({"window": week, "n": len(events), "events": events},
                   indent=2))
    return 0


def cmd_add_event(args: argparse.Namespace) -> int:
    """F162 \u2014 append an event to the local cache."""
    if not args.title or not args.start:
        _err("--title and --start are required (HH:MM, 24h)")
        return 2
    events = _load()
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    event = {"id": len(events) + 1, "title": args.title,
             "date": date, "start": args.start,
             "duration_min": args.duration, "ts": time.time()}
    events.append(event)
    _save(events)
    _ok(f"added event #{event['id']}: {args.title} @ {date} {args.start}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """F163 \u2014 case-insensitive search over title + body."""
    if not args.query:
        _err("--query is required")
        return 2
    q = args.query.lower()
    events = _load()
    matched = [e for e in events
               if q in e.get("title", "").lower()
               or q in str(e.get("body", "")).lower()]
    _ok(json.dumps({"query": args.query, "n": len(matched),
                    "events": matched}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Daily / weekly calendar (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("today", help="List today's events")

    sub.add_parser("week", help="List next-7-day events")

    pa = sub.add_parser("add-event", help="Append an event to the cache")
    pa.add_argument("--title", required=True)
    pa.add_argument("--start", required=True,
                     help="HH:MM (24-hour)")
    pa.add_argument("--duration", type=int, default=30)
    pa.add_argument("--date", default=None,
                     help="YYYY-MM-DD (default: today)")
    pa.add_argument("--body", default="")

    ps = sub.add_parser("search", help="Substring search over events")
    ps.add_argument("--query", required=True)
    return p


HANDLERS = {
    "today":     cmd_today,
    "week":      cmd_week,
    "add-event": cmd_add_event,
    "search":    cmd_search,
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
