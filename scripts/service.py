#!/usr/bin/env python3
"""The Tank Project — service facade.

Hosts 3 features (F041-F043):

* ``facade``  — wrapper around ``systemctl`` so scripts can call
                ``python3 scripts/service.py facade start tank_meta``
                without dictating the exact unit name pattern.
* ``restart`` — restart every ``tank_*`` unit in dependency-friendly order
                (meta → memory → motion → bringup last).
* ``status``  — pretty-print a summary table of all ``tank_*`` units.

This file deliberately targets ``systemctl`` only — it does NOT auto-start
anything. Pair it with the systemd units inside each tank_* package.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[service]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# Ordered bringup sequence: meta first (everything depends on it), then
# sensors/memory/etc, then bringup last.
UNIT_ORDER = [
    "tank_meta.service",
    "tank_memory.service",
    "tank_health.service",
    "tank_speech.service",
    "tank_text.service",
    "tank_assistant.service",
    "tank_log.service",
    "tank_motion.service",
    "tank_sensors.service",
    "tank_vision.service",
    "tank_dock.service",
    "tank_security.service",
    "tank_display.service",
    "tank_command_bridge.service",
    "tank_personalize.service",
    "tank_dashboard.service",
    "tank_navigation.service",
    "tank_patrol.service",
    "tank_bringup.service",
]


def _check_systemctl() -> bool:
    if shutil.which("systemctl"):
        return True
    _err("systemctl missing — running on a non-systemd host")
    return False


# ---------------------------------------------------------------------------
# F041 — facade
# ---------------------------------------------------------------------------
def cmd_facade(args: argparse.Namespace) -> int:
    """F041 — wrapper around `systemctl <action> <unit>`."""
    if not _check_systemctl():
        return 1
    action = args.action
    unit   = args.unit
    out = subprocess.run(["systemctl", action, unit],
                         capture_output=True, text=True, check=False)
    _log(out.stdout.strip() or out.stderr.strip())
    return out.returncode


# ---------------------------------------------------------------------------
# F042 — restart every tank_* unit
# ---------------------------------------------------------------------------
def cmd_restart(args: argparse.Namespace) -> int:
    """F042 — restart all `tank_*` units in order."""
    if not _check_systemctl():
        return 1
    fails = []
    for unit in reversed(UNIT_ORDER):
        if args.dry_run:
            _log(f"DRY: would run `systemctl restart {unit}`")
            continue
        out = subprocess.run(
            ["systemctl", "restart", unit],
            capture_output=True, text=True, check=False,
        )
        state = out.stdout.strip() or out.stderr.strip() or "restarted"
        _log(f"{unit} -> {state}")
        if out.returncode != 0 and not args.ignore_errors:
            fails.append(unit)
    if fails:
        _err(f"units failed: {fails}")
        return 1
    _ok("every tank_* unit restarted")
    return 0


# ---------------------------------------------------------------------------
# F043 — status summary
# ---------------------------------------------------------------------------
def cmd_status(args: argparse.Namespace) -> int:
    """F043 — status summary table."""
    if not _check_systemctl():
        return 1
    rows = []
    for unit in UNIT_ORDER:
        out = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, check=False,
        )
        rows.append({
            "unit": unit,
            "state": out.stdout.strip() or "inactive/missing",
        })
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rows, indent=2))
        _ok(f"wrote {args.json_out}")
    headers = ("UNIT", "STATE")
    print("\n  ".join([f"{h:<28}" for h in headers]))
    for r in rows:
        print(f"  {r['unit']:<28} {r['state']:<28}")
    bad = sum(1 for r in rows if r["state"] not in ("active", "running"))
    _ok(f"{len(rows) - bad}/{len(rows)} units active")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project service facade (F041-F043).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("facade", help="F041 — systemctl wrapper")
    pa.add_argument("action", choices=("start", "stop", "restart", "enable",
                                       "disable", "status"))
    pa.add_argument("unit")
    pr = sub.add_parser("restart", help="F042 — restart all tank_* units")
    pr.add_argument("--dry-run", action="store_true")
    pr.add_argument("--ignore-errors", action="store_true")
    ps = sub.add_parser("status", help="F043 — status summary")
    ps.add_argument("--json-out", default="")
    return p


HANDLERS = {
    "facade":  cmd_facade,
    "restart": cmd_restart,
    "status":  cmd_status,
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
