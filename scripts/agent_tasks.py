#!/usr/bin/env python3
"""agent_tasks.py \u2014 to-do list + habit tracker (F181 \u2014 F184).

Subcommands
-----------
* F181 todo-list      \u2014 open to-do items (sorted by priority)
* F182 todo-add       \u2014 add a to-do item
* F183 todo-complete  \u2014 mark complete
* F184 habit-streak   \u2014 show habit streak history

Cache: ``tank_ws/data/agent_tasks.json``.
Priority order: ``HIGH > MED > LOW``; an item's ``due_ts`` is used as a
secondary sort key.

Usage::

    python3 scripts/agent_tasks.py todo-list
    python3 scripts/agent_tasks.py todo-add --title "tank oil change" --priority HIGH
    python3 scripts/agent_tasks.py todo-complete --id 2
    python3 scripts/agent_tasks.py habit-streak --habit meditate
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PREFIX = "[agent-tasks]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "agent_tasks.json"


def _load() -> dict:
    p = _cache_path()
    if not p.exists():
        seed = {"todos": [], "habits": {}}
        p.write_text(json.dumps(seed, indent=2))
        return seed
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"todos": [], "habits": {}}


def _save(d: dict) -> None:
    _cache_path().write_text(json.dumps(d, indent=2))


_RANK = {"HIGH": 0, "MED": 1, "LOW": 2}


def cmd_todo_list(args: argparse.Namespace) -> int:
    """F181 \u2014 list open to-dos."""
    cache = _load()
    todos = sorted(
        [t for t in cache["todos"] if t.get("status") != "done"],
        key=lambda t: (_RANK.get(t.get("priority", "MED"), 1),
                       t.get("due_ts", float("inf"))))
    _ok(json.dumps({"n": len(todos), "todos": todos}, indent=2))
    return 0


def cmd_todo_add(args: argparse.Namespace) -> int:
    """F182 \u2014 add a to-do item."""
    if not args.title:
        _err("--title is required")
        return 2
    cache = _load()
    item = {"id": len(cache["todos"]) + 1, "title": args.title,
            "priority": args.priority,
            "due_ts": args.due_ts if args.due_ts else None,
            "status": "open",
            "created_ts": time.time()}
    cache["todos"].append(item)
    _save(cache)
    _ok(f"added to-do #{item['id']}: {args.title} ({args.priority})")
    return 0


def cmd_todo_complete(args: argparse.Namespace) -> int:
    """F183 \u2014 mark complete."""
    if args.id is None:
        _err("--id is required")
        return 2
    cache = _load()
    for t in cache["todos"]:
        if t.get("id") == args.id:
            t["status"] = "done"
            t["done_ts"] = time.time()
            break
    else:
        _err(f"to-do #{args.id} not found")
        return 1
    _save(cache)
    _ok(f"to-do #{args.id} marked done")
    return 0


def cmd_habit_streak(args: argparse.Namespace) -> int:
    """F184 \u2014 show habit streak history."""
    if not args.habit:
        _err("--habit is required")
        return 2
    cache = _load()
    habit = cache["habits"].get(args.habit, {})
    streak = habit.get("streak_days", 0)
    last_log_ts = habit.get("last_log_ts")
    last_log_age_h = (round((time.time() - last_log_ts) / 3600, 1)
                      if last_log_ts else None)
    _ok(json.dumps({"habit": args.habit, "streak_days": streak,
                    "last_log_age_h": last_log_age_h},
                   indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="To-do list + habit tracker (merged).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("todo-list", help="List open to-do items")

    pa = sub.add_parser("todo-add", help="Add a to-do item")
    pa.add_argument("--title", required=True)
    pa.add_argument("--priority", choices=["HIGH", "MED", "LOW"],
                    default="MED")
    pa.add_argument("--due-ts", type=float, default=None,
                    help="Unix timestamp; omit for no deadline")

    pc = sub.add_parser("todo-complete", help="Mark to-do done")
    pc.add_argument("--id", type=int, required=True)

    ph = sub.add_parser("habit-streak", help="Show habit streak")
    ph.add_argument("--habit", required=True)
    return p


HANDLERS = {
    "todo-list":      cmd_todo_list,
    "todo-add":       cmd_todo_add,
    "todo-complete":  cmd_todo_complete,
    "habit-streak":   cmd_habit_streak,
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
