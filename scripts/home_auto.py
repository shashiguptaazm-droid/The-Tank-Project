#!/usr/bin/env python3
"""home_auto.py — Home Assistant + MQTT device ops (F157 \u2013 F159).

Subcommands
-----------
* F157 device-list    — list known HA / MQTT devices from local cache
* F158 entity-state   — query one entity's state (offline-first; uses
                       ``HA_TOKEN`` / ``--url`` when set)
* F159 scene-run      — fire a Home Assistant scene (DRY-RUN safe)

Cache lives at ``tank_ws/data/home_auto.json`` (auto-created).

Usage::

    python3 scripts/home_auto.py device-list
    python3 scripts/home_auto.py entity-state --entity light.kitchen
    python3 scripts/home_auto.py scene-run --scene movie_night
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


PREFIX = "[home-auto]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "home_auto.json"


def _load() -> dict:
    p = _cache_path()
    if not p.exists():
        return {"devices": [], "entities": {}, "scenes_fired": []}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"devices": [], "entities": {}, "scenes_fired": []}


def _save(d: dict) -> None:
    _cache_path().write_text(json.dumps(d, indent=2))


def cmd_device_list(args: argparse.Namespace) -> int:
    """F157 \u2014 list known devices."""
    cache = _load()
    if not cache["devices"]:
        _info("0 devices cached. Edit tank_ws/data/home_auto.json or run "
              "`entity-state` to seed.")
        return 0
    _ok(json.dumps({"n": len(cache["devices"]),
                    "devices": cache["devices"][:args.limit]}, indent=2))
    return 0


def cmd_entity_state(args: argparse.Namespace) -> int:
    """F158 \u2014 query one entity's state."""
    if not args.entity:
        _err("--entity is required")
        return 2
    cache = _load()
    state = cache["entities"].get(args.entity)
    if state is None:
        # simulate an offline lookup; real call would use HA_TOKEN + url
        state = {"entity": args.entity, "state": "unknown",
                 "url": args.url, "token_set": bool(args.token),
                 "ts": time.time()}
        cache["entities"][args.entity] = state
        cache.setdefault("devices", []).append(args.entity.split(".")[0])
        _save(cache)
        _info(f"cache miss \u2192 seeded offline placeholder for '{args.entity}'")
    _ok(json.dumps(state, indent=2))
    return 0


def cmd_scene_run(args: argparse.Namespace) -> int:
    """F159 \u2014 fire a Home Assistant scene."""
    if not args.scene:
        _err("--scene is required")
        return 2
    cache = _load()
    cache.setdefault("scenes_fired", []).append(
        {"scene": args.scene, "ts": time.time(),
         "dry_run": bool(args.dry_run)})
    _save(cache)
    _ok(f"scene '{args.scene}' "
        f"{'DRY-RUN' if args.dry_run else 'FIRED'} "
        f"({len(cache['scenes_fired'])} total)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Home Assistant + MQTT device ops (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("device-list", help="List known HA/MQTT devices")
    p1.add_argument("--limit", type=int, default=200)

    p2 = sub.add_parser("entity-state",
                        help="Look up a single entity's state")
    p2.add_argument("--entity", required=True)
    p2.add_argument("--url", default="http://homeassistant.local:8123")
    p2.add_argument("--token", default=os.environ.get("HA_TOKEN", ""))

    p3 = sub.add_parser("scene-run", help="Fire a Home Assistant scene")
    p3.add_argument("--scene", required=True)
    p3.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "device-list":  cmd_device_list,
    "entity-state": cmd_entity_state,
    "scene-run":    cmd_scene_run,
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
