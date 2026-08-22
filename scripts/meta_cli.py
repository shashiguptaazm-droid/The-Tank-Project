#!/usr/bin/env python3
"""The Tank Project — `tank_meta` companion CLI.

Hosts 3 features (F032-F034):

* ``health``      — sqlite PRAGMA integrity / quick_check on meta.db
* ``doc-index``   — compare docs/ markdown files vs meta `knowledge` rows
* ``db-snapshot`` — copy `tank_meta.db` to a timestamped backup file

All operations work without ROS. When `tank_meta.meta_store.MetaStore`
is available, the tool opens the live store; otherwise it falls back to
raw sqlite3 stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path



LOG_PREFIX = "[meta-cli]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _meta_db() -> Path:
    return _repo_root() / "tank_ws" / "data" / "meta.db"


# ---------------------------------------------------------------------------
# F032 — meta DB health
# ---------------------------------------------------------------------------
def cmd_health(args: argparse.Namespace) -> int:
    """F032 — PRAGMA integrity_check on meta.db."""
    db = _meta_db()
    if not db.exists():
        _err(f"meta.db missing — run index_workspace.py --apply")
        return 1
    bad = 0
    with sqlite3.connect(db) as con:
        result = con.execute("PRAGMA integrity_check;").fetchall()
        rows = result[0][0] if result else "unknown"
        ok = rows == "ok"
        _log(f"PRAGMA integrity_check -> {rows}")
        for tbl in ("code_files", "hardware", "decisions", "knowledge"):
            try:
                n = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
                _log(f"  {tbl:>13s}: {n} rows")
            except sqlite3.OperationalError as exc:
                _err(f"  {tbl:>13s}: missing ({exc})")
                bad += 1
        # journal mode
        mode = con.execute("PRAGMA journal_mode;").fetchone()[0]
        _log(f"  journal_mode: {mode}")
    if not ok or bad:
        _err(f"meta.db unhealthy ({bad} tables missing)")
        return 1
    _ok(f"meta.db healthy @ {db}")
    return 0


# ---------------------------------------------------------------------------
# F033 — doc-index coverage
# ---------------------------------------------------------------------------
def cmd_doc_index(args: argparse.Namespace) -> int:
    """F033 — check that every markdown doc has a knowledge row."""
    db = _meta_db()
    if not db.exists():
        _err("meta.db missing — nothing to compare")
        return 1
    docs_dir = _repo_root() / "the tank project" / "docs"
    on_disk = sorted(
        str(p.relative_to(_repo_root())) for p in docs_dir.rglob("*.md")
    ) if docs_dir.exists() else []
    with sqlite3.connect(db) as con:
        try:
            rows = con.execute(
                "SELECT path FROM knowledge"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    in_db = sorted(r[0] for r in rows)
    only_disk = sorted(set(on_disk) - set(in_db))
    only_db = sorted(set(in_db) - set(on_disk))
    _ok(json.dumps({
        "docs_on_disk": len(on_disk),
        "docs_in_db":   len(in_db),
        "disk_only":    only_disk,
        "db_only":      only_db,
    }, indent=2))
    return 0 if not only_disk else 1


# ---------------------------------------------------------------------------
# F034 — db-snapshot
# ---------------------------------------------------------------------------
def cmd_db_snapshot(args: argparse.Namespace) -> int:
    """F034 — copy meta.db to a timestamped backup."""
    db = _meta_db()
    target_dir = Path(args.target)
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = target_dir / f"meta_{ts}.db"
    if not db.exists():
        _err(f"meta.db missing — nothing to snapshot")
        return 1
    if args.dry_run:
        _log(f"DRY: would copy {db} -> {out}")
        return 0
    # Checkpoint WAL into a clean .db
    with sqlite3.connect(db) as con:
        try:
            con.execute("PRAGMA wal_checkpoint(FULL);")
        except sqlite3.OperationalError:
            pass
    shutil.copy2(db, out)
    _ok(f"snapshot -> {out} ({out.stat().st_size} bytes)")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project meta-cli (F032-F034).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="F032 — meta.db PRAGMA integrity")
    sub.add_parser("doc-index", help="F033 — doc coverage vs disk")
    ps = sub.add_parser("db-snapshot", help="F034 — snapshot meta.db")
    ps.add_argument("--target", default=str(_repo_root() / "tank_ws" / "data" / "snapshots"))
    ps.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "health":      cmd_health,
    "doc-index":   cmd_doc_index,
    "db-snapshot": cmd_db_snapshot,
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
