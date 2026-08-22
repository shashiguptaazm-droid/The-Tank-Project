#!/usr/bin/env python3
"""The Tank Project — energy / ops budget CLI.

Hosts 3 features (F143-F145):

* ``watthour-out``   — Watt-hour accounting per day / per hour
* ``dock-windows``   — recommend a dock window given peak demand
* ``geofence-cost``  — estimate geofence area + implied drive cost
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path



LOG_PREFIX = "[budget]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F143 — watthour-out
# ---------------------------------------------------------------------------
def cmd_watthour_out(args: argparse.Namespace) -> int:
    """F143 — watt-hour accounting."""
    src = _repo_root() / "tank_ws" / "data" / "solar_yield.jsonl"
    if not src.exists():
        _err(f"{src} missing")
        return 1
    total_mWh = 0.0
    rows = 0
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        v = ev.get("vbat_mV")
        c = ev.get("current_mA")
        if v and c:
            total_mWh += (v * c) / 1000.0 / 3600.0
        rows += 1
    _ok(json.dumps({
        "samples":  rows,
        "watthours": round(total_mWh / 1000.0, 3),
        "window":   f"{args.window_hours}h",
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F144 — dock-windows
# ---------------------------------------------------------------------------
def cmd_dock_windows(_: argparse.Namespace) -> int:
    """F144 — dock windows."""
    # Heuristic: dock between hours of low expected motion demand.
    windows = [
        {"hour": h, "score": round(1.0 - abs(12 - h) / 12, 2)}
        for h in range(24)
    ]
    best = sorted(windows, key=lambda r: -r["score"])[:3]
    _ok(json.dumps({
        "top_3_dock_hours": [b["hour"] for b in best],
        "all":  windows,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F145 — geofence-cost
# ---------------------------------------------------------------------------
def cmd_geofence_cost(args: argparse.Namespace) -> int:
    """F145 — geofence cost."""
    radius = max(args.radius_m, 1.0)
    area = math.pi * radius * radius
    perimeter = 2 * math.pi * radius
    # crude joules: 5 W * distance / 0.4 m/s
    joules = 5.0 * perimeter / 0.4
    _ok(json.dumps({
        "radius_m":   round(radius, 2),
        "area_m2":    round(area, 1),
        "perimeter_m": round(perimeter, 2),
        "joules_lap": round(joules, 1),
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Budget CLI (F143-F145).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("watthour-out", help="F143 — watt-hour out")
    pw.add_argument("--window-hours", type=int, default=24)
    sub.add_parser("dock-windows", help="F144 — dock windows")
    pg = sub.add_parser("geofence-cost", help="F145 — geofence cost")
    pg.add_argument("--radius-m", type=float, default=20.0)
    return p


HANDLERS = {
    "watthour-out":  cmd_watthour_out,
    "dock-windows":  cmd_dock_windows,
    "geofence-cost": cmd_geofence_cost,
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
