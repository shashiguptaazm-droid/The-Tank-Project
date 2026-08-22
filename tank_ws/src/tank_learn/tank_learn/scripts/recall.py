#!/usr/bin/env python3
"""tank_learn.scripts.recall — operator semantic-recall query CLI.

Examples
========
Top-k over the entire memory (facts + skills + episodes)::
    python3 -m tank_learn.scripts.recall --query "what is RAG?"

Only semantic facts::
    python3 -m tank_learn.scripts.recall \\
        --query "retrieval" --tier facts --top-k 5

Show the most proficient SKILLS only::
    python3 -m tank_learn.scripts.recall \\
        --query "audio" --tier skills --top-k 3

JSON output for piping to the ROS bridge::
    python3 -m tank_learn.scripts.recall \\
        --query "torrent" --json --top-k 10
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from ..memory_store import DEFAULT_DB_PATH, MemoryStore
from ..recall import recall


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Semantic recall over The Tank's long-term memory.",
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH,
                        help="Path to the memory SQLite DB.")
    parser.add_argument("--query", required=True,
                        help="Free-form query string.")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--tier", default="all",
                        choices=["all", "facts", "skills", "episodes"])
    parser.add_argument("--no-episodes", action="store_true",
                        help="Skip episodic memory tier.")
    parser.add_argument("--no-skills", action="store_true",
                        help="Skip skill tier.")
    parser.add_argument("--json", action="store_true",
                        help="Emit pure JSON (default: human table).")
    args = parser.parse_args(argv)

    store = MemoryStore(db_path=args.db)
    try:
        hits = recall(
            args.query, store,
            top_k=args.top_k,
            tier=args.tier,
            include_episodes=not args.no_episodes,
            include_skills=not args.no_skills,
        )
        if args.json:
            print(json.dumps({
                "_ok": True, "query": args.query,
                "tier": args.tier, "count": len(hits),
                "hits": [h.to_dict() for h in hits],
            }))
            return 0
        # Human-readable
        print(f"# query={args.query!r}  tier={args.tier}  hits={len(hits)}")
        for i, h in enumerate(hits, 1):
            print(f"{i:2d}. [{h.tier}] score={h.score:.3f}"
                  f"  conf/prof={h.confidence_or_proficiency:.2f}"
                  f"  key={h.key}")
            print(f"     snippet: {h.snippet}")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
