#!/usr/bin/env python3
"""emotion_audit CLI — list every emotion in the catalog.

Examples::

    python3 -m tank_emotions.scripts.emotion_audit
    python3 -m tank_emotions.scripts.emotion_audit --framework plutchik
    python3 -m tank_emotions.scripts.emotion_audit --json
"""
from __future__ import annotations

import argparse
import json
import sys

from .. import discover, summary_table, by_taxonomy, FRAMEWORKS


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Audit every emotion in the catalog.")
    p.add_argument("--framework", choices=FRAMEWORKS,
                   help="filter by framework")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.framework:
        rows = [
            {"name": e.name, "label": e.label, "valence": e.valence,
             "arousal": e.arousal, "safety": e.safety}
            for e in by_taxonomy(args.framework)
        ]
    else:
        rows = list(summary_table())

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"# {len(rows)} emotions" + (f" [{args.framework}]" if args.framework else ""))
    print(f"{'name':<16} {'label':<16} {'v':>6} {'a':>6}  {'safety':<5}")
    for r in rows:
        print(f"{r['name']:<16} {r['label']:<16} "
              f"{r['valence']:+.2f}  {r['arousal']:+.2f}  {'YES' if r['safety'] else '..':<5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
