#!/usr/bin/env python3
"""Offline query CLI for the ``tank_log`` append-only log store.

Subcommands::

    python3 scripts/query_log.py recent            [--limit N]
    python3 scripts/query_log.py topic <name>     [--limit N]
    python3 scripts/query_log.py source <label>   [--limit N]
    python3 scripts/query_log.py counts           [--since-sec N]
    python3 scripts/query_log.py summary          [--limit N]
    python3 scripts/query_log.py status
    python3 scripts/query_log.py compact          [--max-age-days N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PKG_PARENT)

from tank_log.log_store import LogStore  # noqa: E402

DEFAULT_DB = "/root/the tank project/tank_ws/data/log.db"


def cmd_recent(args, store: LogStore) -> int:
    rows = store.recent(limit=args.limit)
    print(json.dumps([r.to_dict() for r in rows], indent=2))
    return 0 if rows else 1


def cmd_topic(args, store: LogStore) -> int:
    rows = store.by_topic(args.name, limit=args.limit)
    print(json.dumps([r.to_dict() for r in rows], indent=2))
    return 0 if rows else 1


def cmd_source(args, store: LogStore) -> int:
    rows = store.by_source(args.label, limit=args.limit)
    print(json.dumps([r.to_dict() for r in rows], indent=2))
    return 0 if rows else 1


def cmd_counts(args, store: LogStore) -> int:
    out = store.counts_per_topic(since_sec=args.since_sec)
    print(json.dumps(out, indent=2))
    return 0


def cmd_summary(args, store: LogStore) -> int:
    rows = store.recent_summaries(limit=args.limit)
    print(json.dumps(rows, indent=2))
    return 0 if rows else 1


def cmd_status(_args, store: LogStore) -> int:
    print(json.dumps(store.health(), indent=2))
    return 0


def cmd_compact(args, store: LogStore) -> int:
    removed = store.compact_age(max_age_days=args.max_age_days)
    print(json.dumps({"removed_rows": removed, "max_age_days": args.max_age_days},
                     indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the tank_log store")
    parser.add_argument("--db", default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_r = sub.add_parser("recent"); p_r.add_argument("--limit", type=int, default=20)
    p_r.set_defaults(fn=cmd_recent)
    p_t = sub.add_parser("topic"); p_t.add_argument("name")
    p_t.add_argument("--limit", type=int, default=20); p_t.set_defaults(fn=cmd_topic)
    p_s = sub.add_parser("source"); p_s.add_argument("label")
    p_s.add_argument("--limit", type=int, default=20); p_s.set_defaults(fn=cmd_source)
    p_c = sub.add_parser("counts"); p_c.add_argument("--since-sec", type=float, default=3600.0)
    p_c.set_defaults(fn=cmd_counts)
    p_sm = sub.add_parser("summary"); p_sm.add_argument("--limit", type=int, default=20)
    p_sm.set_defaults(fn=cmd_summary)
    p_st = sub.add_parser("status"); p_st.set_defaults(fn=cmd_status)
    p_cp = sub.add_parser("compact"); p_cp.add_argument("--max-age-days", type=float, default=30.0)
    p_cp.set_defaults(fn=cmd_compact)

    args = parser.parse_args()
    store = LogStore(args.db)
    try:
        return args.fn(args, store)
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
