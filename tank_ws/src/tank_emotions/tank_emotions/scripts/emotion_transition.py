#!/usr/bin/env python3
"""emotion_transition CLI — score the plausibility of A -> B.

Examples::

    python3 -m tank_emotions.scripts.emotion_transition fear relief
    python3 -m tank_emotions.scripts.emotion_transition joy sadness
"""
from __future__ import annotations

import argparse
import json
import sys

from .. import get, transition_score


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Score the plausibility of a->b emotion transition.",
    )
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    emo_a = get(args.a)
    emo_b = get(args.b)
    sc = transition_score(emo_a, emo_b)
    if args.json:
        print(json.dumps(sc.to_dict(), indent=2))
        return 0
    print(f"{sc.a} -> {sc.b}   score={sc.score:.2f}   {sc.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
