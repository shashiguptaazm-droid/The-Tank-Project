#!/usr/bin/env python3
"""The Tank Project — backup CLI.

Hosts 3 features (F035-F037):

* ``snapshot`` — freeze every ``data/*.db`` to a timestamped folder
* ``restore``  — copy a snapshot back into ``data/`` after a sanity compare
* ``push``     — push the snapshot to a NAS mount via shutil.copytree

Everything is stdlib-only so it works on a fresh SD card after a re-image.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import filecmp
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path



LOG_PREFIX = "[backup]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _data_dbs() -> list:
    return sorted((_repo_root() / "tank_ws" / "data").glob("*.db"))


# ---------------------------------------------------------------------------
# F035 — snapshot every data/*.db
# ---------------------------------------------------------------------------
def cmd_snapshot(args: argparse.Namespace) -> int:
    """F035 — snapshot every data/*.db with a timestamped folder."""
    target_root = Path(args.target)
    ts = _dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    target = target_root / ts
    target.mkdir(parents=True, exist_ok=True)
    snapshotted = []
    for db in _data_dbs():
        with sqlite3.connect(db) as con:
            try:
                con.execute("PRAGMA wal_checkpoint(FULL);")
            except sqlite3.OperationalError:
                pass
        out = target / db.name
        if args.dry_run:
            _log(f"DRY: would copy {db} -> {out}")
            continue
        shutil.copy2(db, out)
        snapshotted.append(str(out))
    _ok(json.dumps({"target": str(target), "files": snapshotted}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F036 — restore from snapshot
# ---------------------------------------------------------------------------
def cmd_restore(args: argparse.Namespace) -> int:
    """F036 — restore a snapshot back into data/."""
    src = Path(args.from_)
    if not src.is_dir():
        _err(f"snapshot folder missing: {src}")
        return 1
    dst = _repo_root() / "tank_ws" / "data"
    dst.mkdir(parents=True, exist_ok=True)
    for db in src.glob("*.db"):
        target = dst / db.name
        if target.exists() and not args.force:
            if filecmp.cmp(str(target), str(db), shallow=False):
                _log(f"identical: {db.name} (skipped)")
                continue
            _err(f"{db.name} differs — rerun with --force to overwrite")
            return 1
        if args.dry_run:
            _log(f"DRY: would restore {db.name} -> {target}")
            continue
        shutil.copy2(db, target)
        _ok(f"restored {db.name} -> {target}")
    return 0


# ---------------------------------------------------------------------------
# F037 — push snapshot to NAS mount
# ---------------------------------------------------------------------------
def cmd_push(args: argparse.Namespace) -> int:
    """F037 — push the most recent snapshot to a NAS mount."""
    src_root = Path(args.source)
    mounts = [m for m in args.mount if Path(m).is_dir()]
    if not mounts:
        _err(f"no NAS mounts available from {args.mount}")
        return 1
    if not src_root.is_dir():
        _err(f"snapshot root missing: {src_root}")
        return 1
    snaps = sorted(p for p in src_root.iterdir() if p.is_dir())
    if not snaps:
        _err(f"no snapshots in {src_root}")
        return 1
    latest = snaps[-1]
    results = []
    for mount in mounts:
        target = Path(mount) / "tank_snapshots" / latest.name
        if args.dry_run:
            _log(f"DRY: would copy {latest} -> {target}")
            results.append(str(target))
            continue
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(latest, target, dirs_exist_ok=True)
        results.append(str(target))
        _ok(f"pushed {latest.name} -> {target}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project backup helper (F035-F037).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("snapshot", help="F035 — db snapshot folder")
    ps.add_argument("--target",
                    default=str(_repo_root() / "tank_ws" / "data" / "snapshots"))
    ps.add_argument("--dry-run", action="store_true")
    pr = sub.add_parser("restore", help="F036 — restore from snapshot")
    pr.add_argument("--from", dest="from_", required=True)
    pr.add_argument("--force", action="store_true")
    pr.add_argument("--dry-run", action="store_true")
    pp = sub.add_parser("push", help="F037 — push latest snapshot to NAS")
    pp.add_argument("--source",
                    default=str(_repo_root() / "tank_ws" / "data" / "snapshots"))
    pp.add_argument("--mount", nargs="*",
                    default=["/mnt/nas", "/var/tank/media"])
    pp.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "snapshot": cmd_snapshot,
    "restore":  cmd_restore,
    "push":     cmd_push,
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
