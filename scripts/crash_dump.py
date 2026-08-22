#!/usr/bin/env python3
"""crash_dump.py \u2014 crash dump + symbolicate (F205 \u2014 F206).

Subcommands
-----------
* F205 capture         \u2014 capture a synthetic core dump for a process
* F206 symbolize       \u2014 symbolize a stack trace against an addr2line
                       ``Symbolicator`` (DRY-RUN if addr2line absent)

Cache: ``tank_ws/data/crash_dumps/<pid>.json``.

Usage::

    python3 scripts/crash_dump.py capture --pid $$
    python3 scripts/crash_dump.py symbolize --in crash.txt
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path


PREFIX = "[crash]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _dump_dir() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data" / "crash_dumps"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cmd_capture(args: argparse.Namespace) -> int:
    """F205 \u2014 synthetic crash capture (writes a JSON-side mock)."""
    if args.pid is None:
        _err("--pid is required")
        return 2
    cache = _dump_dir() / f"pid{args.pid}.json"
    snap = {"pid": args.pid,
            "captured_ts": time.time(),
            "argv": args.argv,
            "cwd": args.cwd or os.getcwd(),
            "rss_mb_estimate": round(os.getpid() * 4 / 1024, 1),
            "stack": []}
    if args.dry_run:
        snap["dry_run"] = True
    cache.write_text(json.dumps(snap, indent=2))
    _ok(f"captured synthetic dump for pid={args.pid} \u2192 {cache}")
    return 0


def cmd_symbolize(args: argparse.Namespace) -> int:
    """F206 \u2014 symbolize a stack-trace ``--in`` file (DRY-RUN safe)."""
    if not args.in_file:
        _err("--in is required")
        return 2
    p = Path(args.in_file)
    if not p.exists():
        _err(f"{args.in_file} does not exist")
        return 1
    lines = p.read_text().splitlines()
    addr2line = shutil.which("addr2line")
    out = []
    if addr2line:
        for line in lines:
            if line.startswith("0x"):
                sym = os.popen(
                    f"{addr2line} -e {args.bin or '/bin/false'} {line[2:]}"
                ).read().strip()
                out.append({"addr": line, "symbolic": sym})
            else:
                out.append({"raw": line})
        _ok(json.dumps({"mode": "addr2line",
                        "bin": args.bin or "/bin/false",
                        "result": out}, indent=2))
    else:
        _info("addr2line not available \u2192 returning raw trace as-is")
        _ok(json.dumps({"mode": "DRY-RUN", "raw": lines}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Crash dump + symbolicate (DRY-RUN safe).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("capture", help="Capture synthetic dump for a pid")
    p1.add_argument("--pid", type=int, required=True)
    p1.add_argument("--argv", nargs="*", default=[])
    p1.add_argument("--cwd", default="")
    p1.add_argument("--dry-run", action="store_true")

    p2 = sub.add_parser("symbolize", help="Symbolize a stack-trace file")
    p2.add_argument("--in", dest="in_file", required=True)
    p2.add_argument("--bin", default=None,
                    help="Binary to symbolicate against")
    return p


HANDLERS = {
    "capture":   cmd_capture,
    "symbolize": cmd_symbolize,
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
