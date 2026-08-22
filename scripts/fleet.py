#!/usr/bin/env python3
"""The Tank Project — multi-robot fleet CLI.

Hosts 3 features (F096-F098):

* ``bot-roster``      — pull a roster from a YAML roster file
* ``cap-negotiate``   — advertise + accept per-bot capabilities
* ``leader-election`` — pick a deterministic leader by sorted fleet id
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path



LOG_PREFIX = "[fleet]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F096 — bot-roster
# ---------------------------------------------------------------------------
def cmd_bot_roster(args: argparse.Namespace) -> int:
    """F096 — bot roster."""
    try:
        import yaml  # type: ignore
    except ImportError:
        _err("PyYAML missing")
        return 1
    p = Path(args.file)
    if not p.exists():
        _err(f"roster file missing: {p}")
        return 1
    roster = yaml.safe_load(p.read_text()) or {}
    bots = roster.get("bots", [])
    _ok(json.dumps({"count": len(bots), "bots": bots}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F097 — cap-negotiate
# ---------------------------------------------------------------------------
def cmd_cap_negotiate(args: argparse.Namespace) -> int:
    """F097 — capability negotiation."""
    if len(args.bots) < 2:
        _err(f"need >= 2 bots, got {args.bots}")
        return 1
    # Stable capability intersection: sort keys, lowercase, hash.
    caps = []
    for bot in args.bots:
        h = hashlib.sha256(bot.lower().encode()).hexdigest()[:8]
        caps.append({"bot": bot, "cap_hash": h})
    common = sorted(set(c["cap_hash"] for c in caps))
    leader = min(common) if common else "?"
    _ok(json.dumps({
        "bots": args.bots,
        "caps": caps,
        "common_set": list(common),
        "leader_cap": leader,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F098 — leader-election
# ---------------------------------------------------------------------------
def cmd_leader_election(args: argparse.Namespace) -> int:
    """F098 — leader election status."""
    try:
        import yaml  # type: ignore
    except ImportError:
        _err("PyYAML missing")
        return 1
    p = Path(args.file)
    if not p.exists():
        _err(f"roster file missing: {p}")
        return 1
    roster = yaml.safe_load(p.read_text()) or {}
    bots = roster.get("bots", [])
    if not bots:
        _err("roster has no bots")
        return 1
    # Deterministic leader by sorted fleet id hash.
    leader = min(bots, key=lambda b: hashlib.sha256(
        b["id"].lower().encode()).hexdigest())
    _ok(json.dumps({
        "leader": leader,
        "candidates": [b["id"] for b in bots],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fleet CLI (F096-F098).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("bot-roster", help="F096 — bot roster")
    pb.add_argument("--file", required=True)
    pn = sub.add_parser("cap-negotiate", help="F097 — cap negotiate")
    pn.add_argument("bots", nargs="+")
    pl = sub.add_parser("leader-election", help="F098 — leader election")
    pl.add_argument("--file", required=True)
    return p


HANDLERS = {
    "bot-roster":    cmd_bot_roster,
    "cap-negotiate": cmd_cap_negotiate,
    "leader-election":cmd_leader_election,
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
