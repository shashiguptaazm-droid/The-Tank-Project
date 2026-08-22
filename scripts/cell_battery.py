#!/usr/bin/env python3
"""The Tank Project — Li-ion cell battery CLI.

Hosts 3 features (F140-F142):

* ``cell-tap``        — read individual cell voltages via sysfs
* ``cycle-count``     — pull cycle count from BMS sysfs
* ``bms-state``       — aggregate the BMS state (charge / discharge / balance)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path



LOG_PREFIX = "[cell-battery]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _read_int(path: Path) -> Optional[int]:
    try:
        v = int(path.read_text().strip())
        return v
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------
# F140 — cell-tap
# ---------------------------------------------------------------------------
def cmd_cell_tap(args: argparse.Namespace) -> int:
    """F140 — cell-tap."""
    n = max(args.count, 1)
    readings = []
    cells_dir = Path("/sys/class/power_supply")
    for i in range(n):
        # Try a few common patterns: BMS0/CELL{i}, then CELL{i}, then
        # `/sys/devices/.../bq40z50/<cell{i}_voltage>`.
        candidates = [
            cells_dir / f"BMS{i}" / "voltage_now",
            cells_dir / f"CELL{i}" / "voltage_now",
            cells_dir / "BQ40Z50" / "voltage_now",
        ]
        found = None
        for c in candidates:
            if c.exists():
                found = c
                break
        if found is None:
            readings.append({"cell": i, "voltage_mV": None,
                             "note": "no sysfs cell node"})
            continue
        readings.append({"cell": i, "voltage_mV":
                        _read_int(found), "source": str(found)})
    _ok(json.dumps({"cells": n, "readings": readings}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F141 — cycle-count
# ---------------------------------------------------------------------------
def cmd_cycle_count(_: argparse.Namespace) -> int:
    """F141 — cycle-count."""
    candidates = [
        Path("/sys/class/power_supply/BATT/cycle_count"),
        Path("/sys/class/power_supply/BMS0/cycle_count"),
        Path("/sys/class/power_supply/BQ40Z50/cycle_count"),
    ]
    for c in candidates:
        v = _read_int(c)
        if v is not None:
            _ok(json.dumps({"cycles": v, "source": str(c)}, indent=2))
            return 0
    _err("no cycle_count sysfs node found")
    return 1


# ---------------------------------------------------------------------------
# F142 — bms-state
# ---------------------------------------------------------------------------
def cmd_bms_state(_: argparse.Namespace) -> int:
    """F142 — bms-state aggregate."""
    out = {}
    for key, fname in (("voltage_mV", "voltage_now"),
                       ("current_mA", "current_now"),
                       ("capacity_pct", "capacity"),
                       ("status", "status")):
        p = Path(f"/sys/class/power_supply/BATT/{fname}")
        if p.exists():
            try:
                if fname in ("voltage_now", "current_now"):
                    out[key] = int(p.read_text().strip()) // 1000
                else:
                    out[key] = p.read_text().strip()
            except (OSError, ValueError):
                out[key] = None
    _ok(json.dumps(out, indent=2))
    return 0 if any(v is not None for v in out.values()) else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cell battery CLI (F140-F142).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("cell-tap", help="F140 — cell-tap")
    pc.add_argument("--count", type=int, default=6)
    sub.add_parser("cycle-count", help="F141 — cycle count")
    sub.add_parser("bms-state", help="F142 — BMS state")
    return p


HANDLERS = {
    "cell-tap":    cmd_cell_tap,
    "cycle-count": cmd_cycle_count,
    "bms-state":   cmd_bms_state,
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
