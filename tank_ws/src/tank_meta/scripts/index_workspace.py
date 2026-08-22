#!/usr/bin/env python3
"""One-shot indexer for tank_meta: ingest workspace + content + docs into
the structured memory SQLite file.

Usage::

    python3 scripts/index_workspace.py --apply
    python3 scripts/index_workspace.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from tank_meta.code_indexer import index_directory as index_code_dir   # noqa: E402
from tank_meta.decisions_indexer import load_decisions_file            # noqa: E402
from tank_meta.hardware_indexer import load_hardware_file              # noqa: E402
from tank_meta.knowledge_indexer import index_directory as index_md_dir  # noqa: E402
from tank_meta.meta_store import MetaStore                              # noqa: E402


DEFAULT_DB = "/root/the tank project/tank_ws/data/meta.db"
REPO_ROOT = "/root/the tank project"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reindex workspace + content JSON + docs into meta.db"
    )
    parser.add_argument("--apply", action="store_true",
                        help="actually write to the database (default is dry-run)")
    parser.add_argument("--status", action="store_true",
                        help="just print current row counts and exit")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--workspace", default=os.path.join(REPO_ROOT, "tank_ws"))
    parser.add_argument("--content", default=os.path.join(REPO_ROOT, "tank_ws/src/tank_meta/content"))
    parser.add_argument("--docs", default=os.path.join(REPO_ROOT, "docs"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    store = MetaStore(args.db)

    if args.status:
        print(json.dumps({"db": args.db, "counts": store.counts()}, indent=2))
        store.close()
        return 0

    if not args.apply:
        print("Dry-run only. Re-run with --apply to write rows.")
        print(json.dumps({"would_index_workspace": args.workspace,
                          "would_index_content":   args.content,
                          "would_index_docs":      args.docs}, indent=2))
        store.close()
        return 0

    t0 = time.time()
    n_hw = load_hardware_file(os.path.join(args.content, "hardware.json"), store)
    n_dec = load_decisions_file(os.path.join(args.content, "decisions.json"), store)
    n_code = (index_code_dir(args.workspace, store, verbose=args.verbose)
              if os.path.isdir(args.workspace) else 0)
    n_know = (index_md_dir(args.docs, store, source_tag="docs", verbose=args.verbose)
              if os.path.isdir(args.docs) else 0)
    elapsed = time.time() - t0
    print(json.dumps({
        "db": args.db,
        "elapsed_sec": round(elapsed, 3),
        "added": {
            "hardware":  n_hw,
            "decisions": n_dec,
            "code":      n_code,
            "knowledge": n_know,
        },
        "counts": store.counts(),
    }, indent=2))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
