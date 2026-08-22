#!/usr/bin/env python3
"""notify.py \u2014 cross-channel notifications (F185 \u2013 F186).

Subcommands
-----------
* F185 send          \u2014 send a notification through one or more channels
* F186 channels-list \u2014 list configured channels

Channels are offline-first: each channel writes to a JSON sink in
``tank_ws/data/notify_<channel>.json`` instead of calling a real
service. Real-call wiring belongs in ``tank_assistant``.

Usage::

    python3 scripts/notify.py send --title "ESOP pressed" \\
        --body "manual stop" --channel email slack
    python3 scripts/notify.py channels-list
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


PREFIX = "[notify]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _channel_sink(channel: str) -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"notify_{channel}.json"


def cmd_send(args: argparse.Namespace) -> int:
    """F185 \u2014 send a notification through one or more channels."""
    if not args.title or not args.channel:
        _err("--title and --channel are required")
        return 2
    payload = {"title": args.title, "body": args.body or "",
               "ts": time.time(), "severity": args.severity}
    delivered = []
    for ch in args.channel:
        sink = _channel_sink(ch)
        try:
            history = (json.loads(sink.read_text())
                       if sink.exists() else [])
        except json.JSONDecodeError:
            history = []
        history.append(payload)
        sink.write_text(json.dumps(history, indent=2))
        delivered.append(ch)
    _ok(json.dumps({"delivered_to": delivered,
                    "payload": payload}, indent=2))
    return 0


def cmd_channels_list(args: argparse.Namespace) -> int:
    """F186 \u2014 list configured channels."""
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    sinks = sorted(p.name[len("notify_"):-len(".json")]
                   for p in root.glob("notify_*.json"))
    _ok(json.dumps({"configured_channels": sinks,
                    "default_channels": ["email", "slack"]},
                   indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cross-channel notifications (offline-first).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("send", help="Send a notification")
    p1.add_argument("--title", required=True)
    p1.add_argument("--body", default="")
    p1.add_argument("--channel", nargs="+", required=True,
                    help="One or more of: email slack discord telegram pushover")
    p1.add_argument("--severity", choices=["info", "warn", "critical"],
                    default="info")

    sub.add_parser("channels-list",
                   help="List channels with at least one delivered event")
    return p


HANDLERS = {
    "send":           cmd_send,
    "channels-list":  cmd_channels_list,
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
