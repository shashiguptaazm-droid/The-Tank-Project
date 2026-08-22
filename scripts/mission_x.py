#!/usr/bin/env python3
"""The Tank Project — mission X helpers.

Hosts 2 features (F099-F100):

* ``occupancy``         — collapse sonar / radar pings into a coarse
                          occupancy map (text)
* ``persistence-verify`` — verify every persistence file listed in
                            status.md §7 actually exists (or reports a gap)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path



LOG_PREFIX = "[mission-x]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F099 — occupancy
# ---------------------------------------------------------------------------
def cmd_occupancy(args: argparse.Namespace) -> int:
    """F099 — occupancy snapshot."""
    p = Path(args.from_)
    if not p.exists():
        _err(f"pings file missing: {p}")
        return 1
    bins = {}
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        r = obj.get("range", -1)
        th = obj.get("theta_deg", 0)
        if r < 0:
            continue
        bucket = (int(th // args.bin_deg), int(r // args.bin_m))
        bins[bucket] = bins.get(bucket, 0) + 1
    if not bins:
        _err("no pings parsed")
        return 1
    rows = sorted(((b[0], b[1], c) for b, c in bins.items()))
    _ok(json.dumps({
        "n_pings": len(rows),
        "bin_theta_deg": args.bin_deg,
        "bin_range_m":  args.bin_m,
        "top":          rows[:args.top],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F100 — persistence-verify
# ---------------------------------------------------------------------------
def cmd_persistence_verify(args: argparse.Namespace) -> int:
    """F100 — persistence verify."""
    rows = [
        ("memory.db",  _repo_root() / "tank_ws" / "data" / "memory.db"),
        ("meta.db",    _repo_root() / "tank_ws" / "data" / "meta.db"),
        ("hardware.json",
            _repo_root() / "tank_ws" / "src" / "tank_meta"
                          / "content" / "hardware.json"),
        ("decisions.json",
            _repo_root() / "tank_ws" / "src" / "tank_meta"
                          / "content" / "decisions.json"),
        ("project.json",
            _repo_root() / "tank_ws" / "src" / "tank_meta"
                          / "content" / "project.json"),
    ]
    report = []
    bad = 0
    for label, path in rows:
        ok = path.exists()
        if not ok:
            bad += 1
        report.append({
            "label":  label,
            "path":   str(path),
            "exists": ok,
            "bytes":  path.stat().st_size if ok else 0,
        })
        if ok and label.endswith(".db"):
            try:
                with sqlite3.connect(path) as con:
                    n = con.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
                    report[-1]["tables"] = n
            except sqlite3.Error as exc:
                report[-1]["sqlite_error"] = str(exc)
                bad += 1
    _ok(json.dumps({"missing": bad, "rows": report}, indent=2))
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mission X helpers (F099-F100).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    po = sub.add_parser("occupancy", help="F099 — occupancy snapshot")
    po.add_argument("--from", dest="from_", required=True)
    po.add_argument("--bin-deg", type=float, default=15.0)
    po.add_argument("--bin-m",  type=float, default=0.5)
    po.add_argument("--top", type=int, default=50)
    pp = sub.add_parser("persistence-verify", help="F100 — persistence verify")
    return p


HANDLERS = {
    "occupancy":          cmd_occupancy,
    "persistence-verify": cmd_persistence_verify,
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
