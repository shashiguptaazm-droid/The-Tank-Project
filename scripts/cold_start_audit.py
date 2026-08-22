#!/usr/bin/env python3
"""The Tank Project — cold-start / daily audit CLI.

Hosts 2 features (F022-F023):

* ``first`` — run every check once on first boot: prints a single
  checklist grouped by [hw / pkg / svc / cfg].
* ``daily`` — same categories but with last-runs file so the report is
  diff-style: items that have degraded show ``delta``.

This is intentionally **offline**: it never reaches out to anything, just
collects everything from disk + /sys + /proc.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import socket
import sys
import time
from pathlib import Path
from typing import Tuple


LOG_PREFIX = "[audit]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---- check helpers ----------------------------------------------------------
def check_apt() -> Tuple[str, str]:
    return ("apt:ros-humble-ros-base",
            "present" if shutil.which("ros2") else "MISSING")


def check_python_pkgs() -> Tuple[str, str]:
    miss = []
    for pkg in ("ultralytics", "sentence_transformers", "openwakeword",
                "openai", "piper", "whisper", "sqlite_vec"):
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            miss.append(pkg)
    return ("pip:ai-stack", "ok" if not miss else f"missing {miss}")


def check_i2c() -> Tuple[str, str]:
    if shutil.which("i2cdetect") is None:
        return ("i2c-tools", "i2cdetect missing")
    return ("i2c-tools", "i2cdetect present (run `sudo i2cdetect -y 1`)")


def check_workspace() -> Tuple[str, str]:
    ws = _repo_root() / "tank_ws"
    if not (ws / "src").is_dir():
        return ("colcon-workspace", "tank_ws/src missing")
    return ("colcon-workspace",
            f"{sum(1 for _ in (ws / 'src').iterdir())} packages")


def check_meta_db() -> Tuple[str, str]:
    db = _repo_root() / "tank_ws" / "data" / "meta.db"
    if db.exists():
        sz = db.stat().st_size
        return ("tank_meta.db", f"{sz} bytes @ {db}")
    return ("tank_meta.db", "missing — run index_workspace.py --apply")


def check_memory_db() -> Tuple[str, str]:
    db = _repo_root() / "tank_ws" / "data" / "memory.db"
    if db.exists():
        sz = db.stat().st_size
        return ("tank_memory.db", f"{sz} bytes @ {db}")
    return ("tank_memory.db", "missing — first chat primes it")


def check_disk() -> Tuple[str, str]:
    p = _repo_root()
    total, used, free = shutil.disk_usage(p)
    pct = used / total * 100
    return ("disk:repo", f"{free // (1024**3)} GiB free ({pct:.1f}% used)")


def check_gpu_mem() -> Tuple[str, str]:
    if shutil.which("vcgencmd") is None:
        return ("gpu-mem", "vcgencmd missing")
    out = os.popen("vcgencmd get_mem gpu 2>/dev/null").read().strip()
    return ("gpu-mem", out or "n/a")


def check_estop_unit() -> Tuple[str, str]:
    if shutil.which("systemctl") is None:
        return ("estop:unit", "systemctl missing")
    state = os.popen("systemctl is-active tank_estop.service 2>/dev/null").read().strip()
    return ("estop:unit", state or "not installed")


def check_docker_compose() -> Tuple[str, str]:
    return ("docker:compose",
            "available" if shutil.which("docker") else "docker missing")


def check_tailscale() -> Tuple[str, str]:
    state = os.popen("tailscale status 2>/dev/null | head -2").read().strip()
    return ("tailscale", state[:120] or "not installed")


def check_battery_sysfs() -> Tuple[str, str]:
    p = Path("/sys/class/power_supply/BATT/voltage_now")
    if p.exists():
        try:
            mv = int(p.read_text().strip()) // 1000
            return ("INA219", f"{mv} mV @ {p}")
        except (OSError, ValueError):
            return ("INA219", f"read-error @ {p}")
    return ("INA219", "sysfs missing — re-run legacy installer")


CHECKS = [check_apt, check_python_pkgs, check_i2c, check_workspace,
          check_meta_db, check_memory_db, check_disk, check_gpu_mem,
          check_estop_unit, check_docker_compose, check_tailscale,
          check_battery_sysfs]


def run_all() -> dict:
    now = _dt.datetime.utcnow().isoformat(timespec="seconds")
    results = {"ts": now, "host": socket.gethostname(), "checks": {}}
    for fn in CHECKS:
        try:
            key, val = fn()
        except Exception as exc:  # pragma: no cover - defensive
            key, val = fn.__name__, f"raised {exc!r}"
        results["checks"][key] = val
    return results


# ---------------------------------------------------------------------------
# F022 — first-boot audit
# ---------------------------------------------------------------------------
def cmd_first(args: argparse.Namespace) -> int:
    """F022 — comprehensive first-boot checklist."""
    results = run_all()
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=2))
        _ok(f"wrote {args.json_out}")
    width = max(len(k) for k in results["checks"])
    print(f"\n  The Tank cold-start audit — {results['ts']}\n")
    for k, v in results["checks"].items():
        flag = "OK" if "missing" not in v.lower() and "missing " not in v.lower() else "!!"
        print(f"  [{flag}]  {k:<{width}} : {v}\n")
    fails = sum(1 for v in results["checks"].values()
                if "missing" in v.lower() or "fail" in v.lower())
    _ok(f"{len(results['checks']) - fails}/{len(results['checks'])} checks passed")
    return 0 if fails == 0 else 1


# ---------------------------------------------------------------------------
# F023 — daily diff audit
# ---------------------------------------------------------------------------
def cmd_daily(args: argparse.Namespace) -> int:
    """F023 — daily diff against the last first-boot snapshot."""
    snap = Path(args.snapshot)
    if snap.exists():
        prev = json.loads(snap.read_text())
    else:
        prev = {"checks": {}}
    curr = run_all()
    diff = {}
    for k, v in curr["checks"].items():
        if v != prev["checks"].get(k):
            diff[k] = {"was": prev["checks"].get(k, "<absent>"), "now": v}
    out = Path(args.out).with_name((Path(args.out).stem or "daily_diff") + ".json")
    out.write_text(json.dumps({"ts": curr["ts"], "diff": diff}, indent=2))
    if not diff:
        _ok("no changes since last snapshot — system healthy")
        return 0
    _err(f"{len(diff)} regressions:")
    for k, both in diff.items():
        print(f"  - {k}: {both['was']!r} -> {both['now']!r}")
    return 1


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cold-start audit (F022) + daily diff audit (F023).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("first", help="F022 — first-boot audit")
    pf.add_argument("--json-out", default="/tmp/tank_cold_start.json")

    pd = sub.add_parser("daily", help="F023 — daily diff")
    pd.add_argument("--snapshot",
                    default=str(_repo_root() / "tank_ws" / "data" / "cold_start.json"))
    pd.add_argument("--out", default="./daily_diff.json")
    return p


HANDLERS = {
    "first": cmd_first,
    "daily": cmd_daily,
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
