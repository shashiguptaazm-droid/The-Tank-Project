#!/usr/bin/env python3
"""tracing_ops.py \u2014 distributed tracing + log aggregation (F194 \u2014 F197).

Subcommands
-----------
* F194 trace-list       \u2014 list spans from ``tank_ws/data/traces.jsonl``
* F195 trace-export     \u2014 export spans \u2192 JSONL
* F196 tail-logs        \u2014 tail a single ``.log`` / ``.jsonl`` file
* F197 grep-trace       \u2014 trace-id grep across the topic stream

The trace log is append-only; no streaming daemon required.

Usage::

    python3 scripts/tracing_ops.py trace-list --limit 50
    python3 scripts/tracing_ops.py trace-export --out traces.jsonl
    python3 scripts/tracing_ops.py tail-logs --file tank_ws/data/audit.jsonl --n 5
    python3 scripts/tracing_ops.py grep-trace --tid abc-123
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator


PREFIX = "[tracing]"


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


def _trace_path() -> Path:
    return _data_dir() / "traces.jsonl"


def _iter_traces() -> Iterator[dict]:
    p = _trace_path()
    if not p.exists():
        return
    for line in p.open():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def cmd_trace_list(args: argparse.Namespace) -> int:
    """F194 \u2014 list the most-recent spans."""
    spans = list(_iter_traces())
    spans = spans[-args.limit:]
    _ok(json.dumps({"n": len(spans), "spans": spans}, indent=2))
    return 0


def cmd_trace_export(args: argparse.Namespace) -> int:
    """F195 \u2014 export spans \u2192 JSONL (out or stdout)."""
    spans = list(_iter_traces())
    if args.out:
        Path(args.out).write_text("\n".join(json.dumps(s) for s in spans))
        _ok(f"exported {len(spans)} spans \u2192 {args.out}")
    else:
        for s in spans:
            sys.stdout.write(json.dumps(s) + "\n")
    return 0


def cmd_tail_logs(args: argparse.Namespace) -> int:
    """F196 \u2014 tail the last N lines of a file (works on raw or JSONL)."""
    if not args.file:
        _err("--file is required")
        return 2
    p = Path(args.file)
    if not p.exists():
        _err(f"{args.file} does not exist")
        return 1
    lines = p.read_text().splitlines()
    tail = lines[-args.n:]
    _ok(json.dumps({"file": args.file, "n": len(tail), "tail": tail},
                   indent=2))
    return 0


def cmd_grep_trace(args: argparse.Namespace) -> int:
    """F197 \u2014 grep for a trace id across the trace stream."""
    if not args.tid:
        _err("--tid is required")
        return 2
    matches = [s for s in _iter_traces()
               if args.tid in str(s.get("trace_id", "")) ]
    _ok(json.dumps({"tid": args.tid, "n": len(matches),
                    "spans": matches}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Distributed tracing + log helpers.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("trace-list", help="List recent spans")
    p1.add_argument("--limit", type=int, default=50)

    p2 = sub.add_parser("trace-export", help="Export spans to JSONL")
    p2.add_argument("--out", default=None,
                    help="Path; omit for stdout")

    p3 = sub.add_parser("tail-logs", help="Tail a file")
    p3.add_argument("--file", required=True)
    p3.add_argument("--n", type=int, default=10)

    p4 = sub.add_parser("grep-trace", help="Trace-id grep")
    p4.add_argument("--tid", required=True)
    return p


HANDLERS = {
    "trace-list":    cmd_trace_list,
    "trace-export":  cmd_trace_export,
    "tail-logs":     cmd_tail_logs,
    "grep-trace":    cmd_grep_trace,
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
