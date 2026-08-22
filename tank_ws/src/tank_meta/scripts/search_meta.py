#!/usr/bin/env python3
"""Offline search CLI for the structured coding-agent memory store.

Usage::

    python3 scripts/search_meta.py code "pan servo GPIO"
    python3 scripts/search_meta.py hardware fingerprint_sensor
    python3 scripts/search_meta.py decisions "pwm frequency"
    python3 scripts/search_meta.py knowledge "install ros humble"

The script prints JSON so the AI assistant (or a shell pipeline) can pipe
the result back into its context window.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Allow `python3 scripts/search_meta.py` from the repo root.
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PKG_PARENT if os.path.isdir(os.path.join(PKG_PARENT, "tank_meta")) else HERE)

from tank_meta.meta_store import MetaStore  # noqa: E402


DEFAULT_DB = "/root/the tank project/tank_ws/data/meta.db"


def cmd_code(args, store: MetaStore) -> int:
    rows = store.search_code(args.query, top_k=args.top_k)
    print(json.dumps([r.to_dict() for r in rows], indent=2))
    return 0 if rows else 1


def cmd_hardware(args, store: MetaStore) -> int:
    if args.all:
        rows = store.all_hardware()
        print(json.dumps([r.to_dict() for r in rows], indent=2))
        return 0
    row = store.find_hardware(args.component)
    if row is None:
        print(json.dumps({"hit": None, "component": args.component}, indent=2))
        return 1
    print(json.dumps({"hit": row.to_dict()}, indent=2))
    return 0


def cmd_decisions(args, store: MetaStore) -> int:
    rows = store.search_decisions(args.query, top_k=args.top_k)
    print(json.dumps([r.to_dict() for r in rows], indent=2))
    return 0 if rows else 1


def cmd_knowledge(args, store: MetaStore) -> int:
    rows = store.search_knowledge(args.query, top_k=args.top_k)
    print(json.dumps(rows, indent=2))
    return 0 if rows else 1


def cmd_status(_args, store: MetaStore) -> int:
    print(json.dumps({"counts": store.counts()}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline search across tank_meta's structured memory."
    )
    parser.add_argument("--db", default=DEFAULT_DB,
                        help=f"path to meta.db (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_code = sub.add_parser("code", help="search code_files")
    p_code.add_argument("query")
    p_code.add_argument("--top-k", type=int, default=5)
    p_code.set_defaults(fn=cmd_code)

    p_hw = sub.add_parser("hardware", help="lookup a hardware component")
    p_hw.add_argument("component", nargs="?")
    p_hw.add_argument("--all", action="store_true", help="dump every component")
    p_hw.set_defaults(fn=cmd_hardware)

    p_dec = sub.add_parser("decisions", help="search past decisions log")
    p_dec.add_argument("query")
    p_dec.add_argument("--top-k", type=int, default=5)
    p_dec.set_defaults(fn=cmd_decisions)

    p_know = sub.add_parser("knowledge", help="search the docs / knowledge table")
    p_know.add_argument("query")
    p_know.add_argument("--top-k", type=int, default=5)
    p_know.set_defaults(fn=cmd_knowledge)

    p_status = sub.add_parser("status", help="print row counts per table")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args()
    store = MetaStore(args.db)
    try:
        return args.fn(args, store)
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
