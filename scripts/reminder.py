#!/usr/bin/env python3
"""reminder.py \u2014 reminders + alarms (F178 \u2013 F180).

Subcommands
-----------
* F178 set          \u2014 schedule a reminder (delivered via tank_assistant
                    emotion fan-out when the timer fires)
* F179 list         \u2014 list active reminders
* F180 snooze       \u2014 snooze a reminder by N minutes

Cache: ``tank_ws/data/reminders.json``.

Usage::

    python3 scripts/reminder.py set --title "check tank logs" --in-min 15
    python3 scripts/reminder.py list
    python3 scripts/reminder.py snooze --id 3 --min 10
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PREFIX = "[reminder]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "reminders.json"


def _load() -> list:
    p = _cache_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return []


def _save(items: list) -> None:
    _cache_path().write_text(json.dumps(items, indent=2))


def cmd_set(args: argparse.Namespace) -> int:
    """F178 \u2014 schedule a reminder."""
    if not args.title or args.in_min is None:
        _err("--title and --in-min are required")
        return 2
    items = _load()
    item = {"id": len(items) + 1, "title": args.title,
            "fire_at": time.time() + args.in_min * 60,
            "snoozed_min": 0, "created_ts": time.time()}
    items.append(item)
    _save(items)
    _ok(f"reminder #{item['id']} '{args.title}' fires "
        f"in {args.in_min} min")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """F179 \u2014 list active reminders (sorted by fire_at)."""
    items = sorted(_load(), key=lambda i: i.get("fire_at", 0))
    now = time.time()
    enriched = [{
        "id": i["id"], "title": i["title"],
        "in_min": round((i["fire_at"] - now) / 60, 1),
        "snoozed_min": i.get("snoozed_min", 0),
    } for i in items]
    _ok(json.dumps({"now": now, "n": len(enriched),
                    "reminders": enriched}, indent=2))
    return 0


def cmd_snooze(args: argparse.Namespace) -> int:
    """F180 \u2014 snooze a reminder by N minutes."""
    if args.id is None or args.min is None:
        _err("--id and --min are required")
        return 2
    items = _load()
    for item in items:
        if item.get("id") == args.id:
            item["fire_at"] = item.get("fire_at", time.time()) + args.min * 60
            item["snoozed_min"] = item.get("snoozed_min", 0) + args.min
            break
    else:
        _err(f"reminder #{args.id} not found")
        return 1
    _save(items)
    _ok(f"reminder #{args.id} snoozed +{args.min} min")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Reminders + alarms (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("set", help="Schedule a reminder")
    p1.add_argument("--title", required=True)
    p1.add_argument("--in-min", type=int, required=True)

    sub.add_parser("list", help="List active reminders")

    p3 = sub.add_parser("snooze", help="Snooze a reminder by N minutes")
    p3.add_argument("--id", type=int, required=True)
    p3.add_argument("--min", type=int, required=True)
    return p


HANDLERS = {
    "set":    cmd_set,
    "list":   cmd_list,
    "snooze": cmd_snooze,
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
