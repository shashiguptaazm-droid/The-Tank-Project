#!/usr/bin/env python3
"""Standalone memory replay CLI.

Loads a ``.db`` from disk, runs a sentence-transformer embedding for
the query, and prints the top-K hits.  Useful for nightly recall audits
or for searching the database on a laptop that doesn't have ROS2
installed.

Examples::

    python3 scripts/replay_memory.py --db tank_ws/data/memory.db \\
                                     --query "what did the user ask yesterday?"
    python3 scripts/replay_memory.py --recent 30
    python3 scripts/replay_memory.py --export /tmp/memory_dump.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys

from tank_memory.memory_store import SqliteVecStore, InMemoryStore, VECTOR_DIM


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standalone memory replay")
    p.add_argument("--db", required=True, help="path to memory.db")
    p.add_argument("--query", default="")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--recent", type=int, default=0,
                   help="print N most recent events instead of querying")
    p.add_argument("--export", default="",
                   help="dump all events to a JSON Lines file at this path")
    p.add_argument("--model", default="all-MiniLM-L6-v2")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    store = SqliteVecStore(args.db, dim=VECTOR_DIM)

    if args.export:
        events = store.recent(n=max(store.count(), 1))
        with open(args.export, "w") as fh:
            for ev in events:
                fh.write(json.dumps({
                    "id":     ev.id,
                    "ts":     ev.ts,
                    "source": ev.source,
                    "text":   ev.text,
                    "meta":   ev.meta,
                }) + "\n")
        print(f"exported {len(events)} events to {args.export}")
        return 0

    if args.recent > 0:
        events = store.recent(n=args.recent)
        for ev in events:
            ts_str = ev.ts if isinstance(ev.ts, str) else f"{ev.ts:.3f}"
            print(f"[{ts_str}] {ev.source:10s}  {ev.text}")
        return 0

    if args.query:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print(
                "sentence-transformers is required for query; "
                "install with `pip install sentence-transformers`",
                file=sys.stderr,
            )
            return 1
        model = SentenceTransformer(args.model)
        q_vec = model.encode([args.query], normalize_embeddings=True)[0]
        hits = store.recall(q_vec, top_k=args.top_k)
        for rank, h in enumerate(hits, start=1):
            print(f"#{rank:>2}  score={h.score:.4f}  ts={h.ts:.3f}  "
                  f"src={h.source:10s}  text={h.text}")
        return 0

    print("nothing to do; pass --query, --recent, or --export", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
