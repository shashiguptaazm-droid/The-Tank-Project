#!/usr/bin/env python3
"""tank_learn.scripts.consolidate — ad-hoc consolidation runner.

Mirrors the systemd ``tank-learn-consolidation.timer`` (06:00 daily) but
exposed as an operator CLI for manual deepening, debugging, or forced
re-runs after a config change.

Examples
========
Standard run (operator prompt equivalent to the systemd tick)::
    python3 -m tank_learn.scripts.consolidate

Dry-run, view what would be promoted/archived/decayed without writing::
    python3 -m tank_learn.scripts.consolidate --dry-run

Force a deep re-consolidation with a longer window::
    python3 -m tank_learn.scripts.consolidate --force \\
        --window-days 30 --tau-days 21 --stale-days 120

Ingest any new discoveries first, then consolidate, then print summary::
    python3 -m tank_learn.scripts.consolidate --ingest-then-consolidate
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import List

from ..consolidation import (
    DEFAULT_DECAY_TAU_DAYS,
    DEFAULT_PROMOTE_WINDOW_DAYS,
    DEFAULT_STALE_DAYS,
    run_consolidation,
)
from ..discovery_store import DEFAULT_DB_PATH as DISCOVERY_DB_PATH
from ..ingest import ingest_discovery_summary
from ..memory_store import DEFAULT_DB_PATH, MemoryStore


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the sleep-time memory consolidation routine.",
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH,
                        help="Path to the memory SQLite DB.")
    parser.add_argument("--discovery-db", default=DISCOVERY_DB_PATH,
                        help="Discovery DB to ingest from.")
    parser.add_argument("--window-days", type=int,
                        default=DEFAULT_PROMOTE_WINDOW_DAYS,
                        help="Episodic→semantic promotion window.")
    parser.add_argument("--tau-days", type=float,
                        default=DEFAULT_DECAY_TAU_DAYS,
                        help="Ebbinghaus decay time constant (days).")
    parser.add_argument("--stale-days", type=float,
                        default=DEFAULT_STALE_DAYS,
                        help="Days uninterviewed before archive.")
    parser.add_argument("--force", action="store_true",
                        help="Force run (alias: skip clock window check).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute without writing to the DB.")
    parser.add_argument("--ingest-then-consolidate", action="store_true",
                        help="Run ingest_discovery_summary before"
                             " consolidation.")
    parser.add_argument("--since-ts", type=float, default=None,
                        help="Ingest only discoveries since this epoch.")
    args = parser.parse_args(argv)

    mem = MemoryStore(db_path=args.db)
    try:
        if args.ingest_then_consolidate:
            from ..discovery_store import DiscoveryStore
            discovery = DiscoveryStore(db_path=args.discovery_db)
            try:
                ing = ingest_discovery_summary(
                    mem, discovery,
                    since_ts=args.since_ts,
                    source_label="discovery",
                )
                print(json.dumps({"_ok": True, "event": "ingest",
                                  **ing.to_dict()}), flush=True)
            finally:
                discovery.close()

        if args.force:
            # Force == bypass any clock gate in future scheduler hooks.
            pass

        result = run_consolidation(
            mem,
            now_ts=time.time(),
            window_days=args.window_days,
            stale_days=args.stale_days,
            tau_days=args.tau_days,
            dry_run=args.dry_run,
        )
        print(json.dumps({
            "_ok": True,
            "force": args.force,
            "dry_run": args.dry_run,
            **result.to_dict(),
        }))
        return 0
    finally:
        mem.close()


if __name__ == "__main__":
    sys.exit(main())
