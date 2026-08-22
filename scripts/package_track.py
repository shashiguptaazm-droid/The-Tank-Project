#!/usr/bin/env python3
"""package_track.py \u2014 package & shipment tracking (F174 \u2013 F177).

Subcommands
-----------
* F174 track          \u2014 track a single package by id
* F175 deliveries-today \u2014 list packages arriving today
* F176 redirect       \u2014 mark a redirect requested (simulated)
* F177 mark-delivered \u2014 mark a package delivered in the local ledger

Local ledger: ``tank_ws/data/packages.json`` \u2014 scanned on each call.

Usage::

    python3 scripts/package_track.py track --id 1Z999AA10123456784
    python3 scripts/package_track.py deliveries-today
    python3 scripts/package_track.py redirect --id 1Z999AA10123456784 --address "new addr"
    python3 scripts/package_track.py mark-delivered --id 1Z999AA10123456784
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


PREFIX = "[pkg-track]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _cache_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "packages.json"


def _load() -> list:
    p = _cache_path()
    if not p.exists():
        starter = [
            {"id": "1Z-DEMO-001", "carrier": "ups",
             "eta_date": datetime.now().strftime("%Y-%m-%d"),
             "status": "in_transit"},
        ]
        p.write_text(json.dumps(starter, indent=2))
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return []


def _save(packages: list) -> None:
    _cache_path().write_text(json.dumps(packages, indent=2))


def cmd_track(args: argparse.Namespace) -> int:
    """F174 \u2014 track a single package."""
    if not args.id:
        _err("--id is required")
        return 2
    pkgs = _load()
    hit = next((p for p in pkgs if p.get("id") == args.id), None)
    if hit is None:
        _info(f"local ledger miss for '{args.id}' (would call carrier API "
              f"{args.carrier})")
        _ok(json.dumps({"id": args.id, "carrier": args.carrier,
                        "synthetic_status": "in_transit"}, indent=2))
        return 0
    _ok(json.dumps(hit, indent=2))
    return 0


def cmd_deliveries_today(args: argparse.Namespace) -> int:
    """F175 \u2014 list packages arriving today."""
    today = datetime.now().strftime("%Y-%m-%d")
    pkgs = [p for p in _load() if p.get("eta_date") == today]
    _ok(json.dumps({"date": today, "n": len(pkgs), "packages": pkgs},
                   indent=2))
    return 0


def cmd_redirect(args: argparse.Namespace) -> int:
    """F176 \u2014 mark a redirect requested."""
    if not args.id or not args.address:
        _err("--id and --address are required")
        return 2
    pkgs = _load()
    for p in pkgs:
        if p.get("id") == args.id:
            p["redirect_requested"] = args.address
            p["redirect_ts"] = time.time()
            break
    else:
        pkgs.append({"id": args.id, "carrier": "unknown",
                     "redirect_requested": args.address,
                     "redirect_ts": time.time()})
    _save(pkgs)
    _ok(f"redirect recorded for '{args.id}' \u2192 {args.address}")
    return 0


def cmd_mark_delivered(args: argparse.Namespace) -> int:
    """F177 \u2014 mark a package delivered."""
    if not args.id:
        _err("--id is required")
        return 2
    pkgs = _load()
    for p in pkgs:
        if p.get("id") == args.id:
            p["status"] = "delivered"
            p["delivered_ts"] = time.time()
            break
    else:
        pkgs.append({"id": args.id, "status": "delivered",
                     "delivered_ts": time.time()})
    _save(pkgs)
    _ok(f"marked '{args.id}' delivered")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Package & shipment tracking (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("track", help="Track a single package")
    p1.add_argument("--id", required=True)
    p1.add_argument("--carrier", default="ups")

    p2 = sub.add_parser("deliveries-today",
                        help="List packages arriving today")

    p3 = sub.add_parser("redirect", help="Mark a redirect requested")
    p3.add_argument("--id", required=True)
    p3.add_argument("--address", required=True)

    p4 = sub.add_parser("mark-delivered",
                        help="Mark a package delivered in the ledger")
    p4.add_argument("--id", required=True)
    return p


HANDLERS = {
    "track":            cmd_track,
    "deliveries-today": cmd_deliveries_today,
    "redirect":         cmd_redirect,
    "mark-delivered":   cmd_mark_delivered,
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
