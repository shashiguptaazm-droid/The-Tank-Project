#!/usr/bin/env python3
"""Standalone CLI to invoke one :class:`tank_log.learner.Learner` pass.

Usage::

    python3 scripts/learn_summary.py            # one pass, prints JSON
    python3 scripts/learn_summary.py --loop 60  # every 60s until Ctrl+C
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PKG_PARENT)

from tank_log.learner import Learner      # noqa: E402
from tank_log.log_store import LogStore   # noqa: E402

DEFAULT_DB = "/root/the tank project/tank_ws/data/log.db"


def main() -> int:
    p = argparse.ArgumentParser(description="Run tank_log learner passes")
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--window", type=float, default=60.0)
    p.add_argument("--lookback", type=float, default=60.0)
    p.add_argument("--loop", type=float, default=0.0,
                   help="if >0, run every N seconds until Ctrl+C")
    args = p.parse_args()

    store = LogStore(args.db)
    learner = Learner(store=store,
                      window_sec=args.window,
                      lookback_sec=args.lookback)
    try:
        if args.loop <= 0:
            print(json.dumps(learner.tick(), indent=2))
            return 0
        while True:
            print(json.dumps(learner.tick(), indent=2))
            time.sleep(args.loop)
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
