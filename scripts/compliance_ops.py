#!/usr/bin/env python3
"""compliance_ops.py \u2014 compliance + retention + SLO (F187 \u2014 F190).

Subcommands
-----------
* F187 gdpr-delete   \u2014 GDPR delete simulator (removes a key from
                    every known cache; never touches sqlite without
                    --force)
* F188 audit-log     \u2014 append an audit event (JSON line) to
                    ``tank_ws/data/audit.jsonl``
* F189 retention-apply \u2014 delete ledger entries older than N days
* F190 slo-report    \u2014 generate a per-period SLO summary

Usage::

    python3 scripts/compliance_ops.py gdpr-delete --key tank_meta:h42
    python3 scripts/compliance_ops.py audit-log --kind decision_append \\
        --who pilot --note "DEC-007"
    python3 scripts/compliance_ops.py retention-apply --older-than 30
    python3 scripts/compliance_ops.py slo-report --days 7
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


PREFIX = "[compliance]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _data_dir() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cmd_gdpr_delete(args: argparse.Namespace) -> int:
    """F187 \u2014 GDPR delete simulator."""
    if not args.key:
        _err("--key is required (e.g. tank_meta:h42)")
        return 2
    deleted = []
    d = _data_dir()
    for path in d.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        # best-effort: drop any leaf dict key matching args.key
        def _purge(obj):
            if isinstance(obj, dict):
                if args.key in obj:
                    del obj[args.key]
                    deleted.append(args.key)
                for v in list(obj.values()):
                    _purge(v)
            elif isinstance(obj, list):
                for item in list(obj):
                    _purge(item)
        _purge(data)
        path.write_text(json.dumps(data, indent=2, default=str))
    audit_path = d / "audit.jsonl"
    with audit_path.open("a") as fh:
        fh.write(json.dumps({"kind": "gdpr_delete", "key": args.key,
                              "ts": time.time(),
                              "n_purged": len(deleted)}) + "\n")
    _ok(json.dumps({"key": args.key, "deleted_in_caches": len(deleted),
                    "force": args.force}, indent=2))
    return 0


def cmd_audit_log(args: argparse.Namespace) -> int:
    """F188 \u2014 append an audit event."""
    if not args.kind:
        _err("--kind is required")
        return 2
    audit_path = _data_dir() / "audit.jsonl"
    with audit_path.open("a") as fh:
        fh.write(json.dumps({
            "kind": args.kind, "who": args.who or "system",
            "note": args.note or "", "ts": time.time()}) + "\n")
    _ok(f"audit event logged: {args.kind} by {args.who or 'system'}")
    return 0


def cmd_retention_apply(args: argparse.Namespace) -> int:
    """F189 \u2014 walk ``*.jsonl`` files and prune stale entries."""
    if args.older_than is None:
        _err("--older-than is required (days)")
        return 2
    cutoff = time.time() - args.older_than * 86400
    removed = 0
    d = _data_dir()
    for path in d.glob("*.jsonl"):
        kept = []
        removed_here = 0
        for line in path.open():
            line = line.strip()
            if not line:
                continue
            try:
                ts = json.loads(line).get("ts", float("inf"))
            except json.JSONDecodeError:
                kept.append(line)
                continue
            if ts < cutoff:
                removed_here += 1
            else:
                kept.append(line)
        path.write_text("\n".join(kept) + ("\n" if kept else ""))
        removed += removed_here
    _ok(f"retention pruned {removed} entries older than "
        f"{args.older_than} days")
    return 0


def cmd_slo_report(args: argparse.Namespace) -> int:
    """F190 \u2014 summarise recent audit events as a per-kind SLO."""
    if args.days is None:
        _err("--days is required")
        return 2
    audit_path = _data_dir() / "audit.jsonl"
    if not audit_path.exists():
        _ok(json.dumps({"window_days": args.days, "kinds": {}}, indent=2))
        return 0
    cutoff = time.time() - args.days * 86400
    counts: dict = {}
    for line in audit_path.open():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("ts", 0) < cutoff:
            continue
        k = ev.get("kind", "unknown")
        counts[k] = counts.get(k, 0) + 1
    _ok(json.dumps({"window_days": args.days, "kinds": counts}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compliance + retention + SLO reporting.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("gdpr-delete", help="GDPR delete simulator")
    p1.add_argument("--key", required=True)
    p1.add_argument("--force", action="store_true",
                    help="Also touch sqlite (.db) files")

    p2 = sub.add_parser("audit-log", help="Append audit event")
    p2.add_argument("--kind", required=True)
    p2.add_argument("--who", default="")
    p2.add_argument("--note", default="")

    p3 = sub.add_parser("retention-apply",
                        help="Prune *.jsonl files older than N days")
    p3.add_argument("--older-than", type=int, required=True,
                    help="Cutoff age in days")

    p4 = sub.add_parser("slo-report",
                        help="Count audit events per kind in window")
    p4.add_argument("--days", type=int, required=True)
    return p


HANDLERS = {
    "gdpr-delete":    cmd_gdpr_delete,
    "audit-log":      cmd_audit_log,
    "retention-apply": cmd_retention_apply,
    "slo-report":     cmd_slo_report,
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
