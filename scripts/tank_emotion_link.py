#!/usr/bin/env python3
"""The Tank Project — emotion ↔ state bridge.

Hosts 1 feature (F150):

* ``emotion-link`` — given a free-form query, return the matching
                     ``tank_emotions`` descriptor + companion plan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path



LOG_PREFIX = "[emotion-link]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def cmd_emotion_link(args: argparse.Namespace) -> int:
    """F150 — emotion-link."""
    try:
        from tank_emotions import discover, dominant, companion_plan
    except ImportError as exc:
        _err(f"tank_emotions package missing or unimportable: {exc}")
        return 1
    text = args.text or args.query
    emo_name = dominant(text or "")
    emo = discover().get(emo_name)
    if emo is None:
        _err(f"emotion not resolvable for {text!r}")
        return 1
    plan = companion_plan(emo)
    _ok(json.dumps({
        "input": text,
        "dominant": emo_name,
        "emotion":  emo.to_dict(),
        "plan":     plan.to_dict(),
    }, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="emotion-link CLI (F150).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pe = sub.add_parser("emotion-link", help="F150 — emotion link")
    pe.add_argument("--text", default="")
    pe.add_argument("--query", default="")
    return p


HANDLERS = {
    "emotion-link": cmd_emotion_link,
}


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
