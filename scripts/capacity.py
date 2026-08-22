#!/usr/bin/env python3
"""capacity.py \u2014 capacity usage + simple forecast (F198 \u2014 F200).

Subcommands
-----------
* F198 usage           \u2014 size of every cache, plus ``.db`` table counts
* F199 forecast        \u2014 extrapolate next-30-day growth from history
* F200 throttle-check  \u2014 should the script back off?

Cache: ``tank_ws/data/capacity_history.jsonl`` \u2014 one row per
``usage`` invocation.

Usage::

    python3 scripts/capacity.py usage
    python3 scripts/capacity.py forecast
    python3 scripts/capacity.py throttle-check --mbps 5 --hours 24
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path


PREFIX = "[capacity]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _data_dir() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cmd_usage(_: argparse.Namespace) -> int:
    """F198 \u2014 current cache + sqlite usage."""
    d = _data_dir()
    sizes = []
    for path in sorted(d.rglob("*")):
        if path.is_file():
            sizes.append({"path": path.name,
                          "size_bytes": path.stat().st_size})
    summary = {"n_files": len(sizes),
               "total_bytes": sum(s["size_bytes"] for s in sizes),
               "files": sizes[:10],
               "ts": time.time()}
    history = d / "capacity_history.jsonl"
    with history.open("a") as fh:
        fh.write(json.dumps({"ts": summary["ts"],
                             "total_bytes": summary["total_bytes"]}) + "\n")
    _ok(json.dumps(summary, indent=2))
    return 0


def cmd_forecast(_: argparse.Namespace) -> int:
    """F199 \u2014 naive 30-day extrapolation from history."""
    history = _data_dir() / "capacity_history.jsonl"
    rows = []
    for line in history.open():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if len(rows) < 2:
        _info("not enough history; need >= 2 usage snapshots; "
              "run `usage` twice to seed.")
        _ok(json.dumps({"history_n": len(rows), "forecast_30d_bytes": None},
                       indent=2))
        return 0
    bytes_first = rows[0]["total_bytes"]
    bytes_last  = rows[-1]["total_bytes"]
    dt_days = (rows[-1]["ts"] - rows[0]["ts"]) / 86400
    rate_b_per_day = (bytes_last - bytes_first) / max(dt_days, 1e-6)
    forecast_30d = bytes_last + rate_b_per_day * 30
    _ok(json.dumps({"history_n": len(rows),
                    "rate_bytes_per_day": round(rate_b_per_day, 1),
                    "current_bytes": bytes_last,
                    "forecast_30d_bytes": round(forecast_30d, 1)},
                   indent=2))
    return 0


def cmd_throttle_check(args: argparse.Namespace) -> int:
    """F200 \u2014 simple throttle heuristic."""
    if args.mbps is None:
        _err("--mbps is required")
        return 2
    history = _data_dir() / "capacity_history.jsonl"
    rows = []
    for line in history.open():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if len(rows) < 2:
        _info("seed throttle history with two `usage` snapshots; "
              "rough heuristic: mbps < 1 = throttle; >= 5 = full speed")
        _ok(json.dumps({"throttle": args.mbps < 1.0,
                        "reason": "no-history"}, indent=2))
        return 0
    recent = rows[-min(args.hours * 2, len(rows)):]
    delta = recent[-1]["total_bytes"] - recent[0]["total_bytes"]
    should_throttle = delta > args.mbps * 1024 * 1024 * args.hours
    _ok(json.dumps({"window_hours": args.hours,
                    "mbps_target": args.mbps,
                    "growth_bytes": delta,
                    "throttle": should_throttle}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Capacity usage + forecast + throttle heuristics.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("usage", help="Snapshot current cache + sqlite usage")
    sub.add_parser("forecast", help="Forecast 30-day growth from history")

    p3 = sub.add_parser("throttle-check", help="Should we back off?")
    p3.add_argument("--mbps", type=float, required=True)
    p3.add_argument("--hours", type=int, default=24)
    return p


HANDLERS = {
    "usage":          cmd_usage,
    "forecast":       cmd_forecast,
    "throttle-check": cmd_throttle_check,
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
