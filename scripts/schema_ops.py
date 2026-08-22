#!/usr/bin/env python3
"""schema_ops.py \u2014 schema introspection + dry-run (F191 \u2014 F193).

Subcommands
-----------
* F191 list               \u2014 list every ``.db`` under ``tank_ws/`` with
                          table count + row count per table
* F192 migrate-dry-run    \u2014 show what a named migration would touch
                          (looks for ``migrations/<name>.sql``)
* F193 reindex            \u2014 ``REINDEX`` every indexed table in a db

Cache: ``tank_ws/data/migrations/`` for sql files.

Usage::

    python3 scripts/schema_ops.py list
    python3 scripts/schema_ops.py migrate-dry-run --name add_decision_index --db meta.db
    python3 scripts/schema_ops.py reindex --db meta.db
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


PREFIX = "[schema]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent / "tank_ws"


def _resolve_db(name: str) -> Path:
    p = Path(name)
    if not p.is_absolute():
        p = _workspace_root() / "data" / name
    return p


def cmd_list(args: argparse.Namespace) -> int:
    """F191 \u2014 list every sqlite db under tank_ws/."""
    root = _workspace_root()
    dbs = sorted(root.rglob("*.db"))
    rows = []
    for db in dbs:
        try:
            con = sqlite3.connect(db)
            tables = sorted(r[0] for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'").fetchall())
            counts = {t: con.execute(
                f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}
            con.close()
        except sqlite3.Error as exc:
            rows.append({"path": str(db), "error": str(exc)})
            continue
        rows.append({"path": str(db), "tables": tables,
                     "row_counts": counts})
    _ok(json.dumps({"n": len(rows), "databases": rows}, indent=2))
    return 0


def cmd_migrate_dry_run(args: argparse.Namespace) -> int:
    """F192 \u2014 show what a named migration file would touch."""
    if not args.name:
        _err("--name is required")
        return 2
    sql_path = _workspace_root() / "data" / "migrations" / f"{args.name}.sql"
    if not sql_path.exists():
        _info(f"no migration file at {sql_path} \u2192 "
              f"would create empty placeholder")
        sql_body = ""
    else:
        sql_body = sql_path.read_text()

    db_path = _resolve_db(args.db) if args.db else _workspace_root() / "data" / "meta.db"
    tables = []
    if db_path.exists():
        try:
            con = sqlite3.connect(db_path)
            tables = sorted(r[0] for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'").fetchall())
            con.close()
        except sqlite3.Error as exc:
            _err(f"db read failed: {exc}")
            return 1
    referenced_lower = sql_body.lower()
    touched = [t for t in tables if t.lower() in referenced_lower]

    _ok(json.dumps({"name": args.name, "db": str(db_path),
                    "tables_in_db": tables,
                    "tables_touched_by_sql": touched,
                    "sql_chars": len(sql_body)}, indent=2))
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    """F193 \u2014 REINDEX every indexed table in a db."""
    if not args.db:
        _err("--db is required (e.g. meta.db)")
        return 2
    db_path = _resolve_db(args.db)
    if not db_path.exists():
        _err(f"{args.db} does not exist")
        return 1
    try:
        con = sqlite3.connect(db_path)
        tables_before = sorted(r[0] for r in con.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table'").fetchall())
        for t in tables_before:
            con.execute(f"REINDEX {t}")
        con.commit()
        con.close()
    except sqlite3.Error as exc:
        _err(f"REINDEX failed: {exc}")
        return 1
    _ok(f"REINDEX complete on {args.db} ({len(tables_before)} tables)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Schema introspection + dry-run + reindex.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List every .db under tank_ws/")

    p2 = sub.add_parser("migrate-dry-run",
                        help="What a migration would touch")
    p2.add_argument("--name", required=True)
    p2.add_argument("--db", default=None,
                    help="default: meta.db")

    p3 = sub.add_parser("reindex", help="REINDEX a db")
    p3.add_argument("--db", required=True)
    return p


HANDLERS = {
    "list":            cmd_list,
    "migrate-dry-run": cmd_migrate_dry_run,
    "reindex":         cmd_reindex,
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
