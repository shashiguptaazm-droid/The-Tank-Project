#!/usr/bin/env python3
"""CLI to review past surveillance alerts from ``AlertJournal``.

``AlertJournal`` writes one JSONL per UTC day under
``/var/lib/tank/surveillance/<YYYY-MM-DD>.jsonl``.

Usage::

    python3 scripts/surveillance_review.py list \\
        --day 2025-01-15

    python3 scripts/surveillance_review.py list \\
        --day today --severity critical --label person

    python3 scripts/surveillance_review.py summary \\
        --day 2025-01-15

    python3 scripts/surveillance_review.py export \\
        --day 2025-01-15 --out /tmp/alerts.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import List

# Same path setup as run_patrol.py — go to the inner Python package dir.
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "tank_patrol"))
sys.path.insert(0, PKG_DIR)

from surveillance import AlertJournal  # noqa: E402


def _day_or_today(s: str) -> str:
    if s == "today":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return s


def _filter(events: List[dict], *, severity: str | None,
            label: str | None) -> List[dict]:
    out = []
    for ev in events:
        if severity and ev.get("severity") != severity:
            continue
        if label and ev.get("label") != label:
            continue
        out.append(ev)
    return out


def _cmd_list(args, journal: AlertJournal) -> int:
    day = _day_or_today(args.day)
    events = journal.read_day(day)
    events = _filter(events,
                     severity=args.severity,
                     label=args.label)
    if not events:
        print(f"# no events matched day={day} "
              f"severity={args.severity or '*'} label={args.label or '*'}")
        return 1
    print(f"# day={day}  count={len(events)}")
    for ev in events:
        print(json.dumps(ev, ensure_ascii=False))
    return 0


def _cmd_summary(args, journal: AlertJournal) -> int:
    day = _day_or_today(args.day)
    events = journal.read_day(day)
    if not events:
        print(f"# no events on day={day}")
        return 1
    sev_counts: dict = {}
    lbl_counts: dict = {}
    for ev in events:
        sev = ev.get("severity", "?")
        lbl = ev.get("label", "?")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
        lbl_counts[lbl] = lbl_counts.get(lbl, 0) + 1
    print(f"# day={day}  total={len(events)}")
    print("# by severity:")
    for s, c in sorted(sev_counts.items()):
        print(f"#   {s:>9s}  {c}")
    print("# by label:")
    for s, c in sorted(lbl_counts.items()):
        print(f"#   {s:>9s}  {c}")
    return 0


def _cmd_export(args, journal: AlertJournal) -> int:
    day = _day_or_today(args.day)
    events = journal.read_day(day)
    events = _filter(events,
                     severity=args.severity,
                     label=args.label)
    with open(args.out, "w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"# wrote {len(events)} events to {args.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Review surveillance alerts")
    p.add_argument("--base-dir", default=AlertJournal.DIR,
                   help=f"override base dir (default: {AlertJournal.DIR})")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_l = sub.add_parser("list", help="print events")
    p_l.add_argument("--day", default="today")
    p_l.add_argument("--severity", choices=("info", "warning", "critical"))
    p_l.add_argument("--label")
    p_l.set_defaults(fn=_cmd_list)

    p_s = sub.add_parser("summary", help="tally by severity/label")
    p_s.add_argument("--day", default="today")
    p_s.set_defaults(fn=_cmd_summary)

    p_e = sub.add_parser("export", help="write JSONL out")
    p_e.add_argument("--day", default="today")
    p_e.add_argument("--severity", choices=("info", "warning", "critical"))
    p_e.add_argument("--label")
    p_e.add_argument("--out", required=True)
    p_e.set_defaults(fn=_cmd_export)

    args = p.parse_args()
    journal = AlertJournal(base_dir=args.base_dir)
    return args.fn(args, journal)


if __name__ == "__main__":
    raise SystemExit(main())
