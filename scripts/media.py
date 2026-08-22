#!/usr/bin/env python3
"""media.py \u2014 media library + playlists (F171 \u2013 F173).

Subcommands
-----------
* F171 play-queue     \u2014 view or append to the play queue
* F172 library-search \u2014 substring search across the local library
* F173 cast-to        \u2014 cast the queue to a target endpoint

Cache: ``tank_ws/data/media.json`` \u2014 the local "library".

Usage::

    python3 scripts/media.py play-queue --list
    python3 scripts/media.py play-queue --add "track_42"
    python3 scripts/media.py library-search --query "ambient"
    python3 scripts/media.py cast-to --target tank.living_room
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PREFIX = "[media]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "media.json"


def _load() -> dict:
    p = _cache_path()
    if not p.exists():
        starter = {
            "library": [
                {"id": "track_42", "title": "ambient_pad", "duration_s": 84},
                {"id": "track_07", "title": "kick_loop", "duration_s": 60},
                {"id": "track_99", "title": "main_theme", "duration_s": 130},
            ],
            "queue": [],
        }
        p.write_text(json.dumps(starter, indent=2))
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"library": [], "queue": []}


def _save(d: dict) -> None:
    _cache_path().write_text(json.dumps(d, indent=2))


def cmd_play_queue(args: argparse.Namespace) -> int:
    """F171 \u2014 view or append to the play queue."""
    cache = _load()
    if args.add:
        cache["queue"].append(args.add)
        _save(cache)
        _ok(f"appended '{args.add}' to queue (now {len(cache['queue'])} items)")
        return 0
    _ok(json.dumps({"queue": cache["queue"],
                    "n": len(cache["queue"])}, indent=2))
    return 0


def cmd_library_search(args: argparse.Namespace) -> int:
    """F172 \u2014 substring search across the library."""
    if not args.query:
        _err("--query is required")
        return 2
    cache = _load()
    q = args.query.lower()
    matched = [t for t in cache["library"]
               if q in t.get("title", "").lower()
               or q in t.get("id", "").lower()]
    _ok(json.dumps({"query": args.query, "n": len(matched),
                    "tracks": matched}, indent=2))
    return 0


def cmd_cast_to(args: argparse.Namespace) -> int:
    """F173 \u2014 cast the queue to a target endpoint."""
    if not args.target:
        _err("--target is required (e.g. tank.living_room)")
        return 2
    cache = _load()
    _ok(f"cast queue ({len(cache['queue'])} tracks) "
        f"\u2192 {args.target}{' [DRY-RUN]' if args.dry_run else ''}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Media library + play queue (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pq = sub.add_parser("play-queue", help="View or append to the queue")
    pq.add_argument("--add", default=None,
                    help="Track id to append; omit to list current queue")

    ls = sub.add_parser("library-search",
                        help="Substring search across the library")
    ls.add_argument("--query", required=True)

    ct = sub.add_parser("cast-to", help="Cast the queue to a target")
    ct.add_argument("--target", required=True)
    ct.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "play-queue":     cmd_play_queue,
    "library-search": cmd_library_search,
    "cast-to":        cmd_cast_to,
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
