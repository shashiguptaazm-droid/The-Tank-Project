#!/usr/bin/env python3
"""emotion_lookup CLI — print the descriptor for a named emotion.

Examples::

    python3 -m tank_emotions.scripts.emotion_lookup joy
    python3 -m tank_emotions.scripts.emotion_lookup fear
"""
from __future__ import annotations

import argparse
import json
import sys

from .. import get, companion_plan, instruction_text


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Look up an emotion descriptor + plan.")
    p.add_argument("name", help="canonical emotion name, e.g. 'joy'")
    p.add_argument("--json", action="store_true",
                   help="dump the raw descriptor as JSON")
    args = p.parse_args(argv)
    emo = get(args.name)
    if args.json:
        print(json.dumps(emo.to_dict(), indent=2, default=str))
        return 0
    plan = companion_plan(emo)
    print(f"name      : {emo.name}")
    print(f"label     : {emo.label}")
    print(f"valence   : {emo.valence:+.2f}")
    print(f"arousal   : {emo.arousal:+.2f}")
    print(f"decay_s   : {emo.decay_s}")
    print(f"safety    : {emo.safety}")
    print(f"taxonomy  : {[t['framework'] for t in emo.taxonomy]}")
    print(f"companion : {instruction_text(plan)}")
    if emo.transitions_out:
        print(f"-> {emo.transitions_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
