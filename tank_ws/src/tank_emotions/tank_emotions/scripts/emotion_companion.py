#!/usr/bin/env python3
"""emotion_companion CLI — describe how the AI should respond to text.

Examples::

    echo "I'm ecstatic" | python3 -m tank_emotions.scripts.emotion_companion
    python3 -m tank_emotions.scripts.emotion_companion --text "I'm furious"
"""
from __future__ import annotations

import argparse
import json
import sys

from .. import discover, score_text, dominant
from .. import get, companion_plan, instruction_text


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Companion plan for the dominant emotion in TEXT.")
    p.add_argument("--text", help="if omitted, read from stdin")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    text = args.text
    if not text:
        text = sys.stdin.read()
    emo_name = dominant(text)
    emo = get(emo_name)
    plan = companion_plan(emo)
    payload = {
        "scores":   score_text(text),
        "dominant": emo_name,
        "emotion":  emo.to_dict(),
        "plan":     plan.to_dict(),
    }
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
        return 0
    print(f"# text: {text.strip()!r}")
    print(f"# dominant: {emo_name} ({emo.label})")
    print(f"# companion: {instruction_text(plan)}")
    if emo.transitions_out:
        print(f"# transitions_out: {emo.transitions_out}")
    if plan.phrases:
        for ph in plan.phrases:
            print(f"  • {ph}")
    if plan.do_not:
        print("# do NOT:")
        for ph in plan.do_not:
            print(f"  ✗ {ph}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
