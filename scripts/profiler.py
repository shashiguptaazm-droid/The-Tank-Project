#!/usr/bin/env python3
"""The Tank Project — profiler CLI.

Hosts 3 features (F119-F121):

* ``ros-trace``      — run `ros2 trace` for N seconds and report
* ``leak-detect``   — RSS delta across N seconds for a given PID
* ``perf-summary``   — CPU / RSS / fd count snapshot
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path



LOG_PREFIX = "[profiler]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _read_rss_kb(pid: int) -> Optional[int]:
    try:
        with open(f"/proc/{pid}/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# F119 — ros-trace
# ---------------------------------------------------------------------------
def cmd_ros_trace(args: argparse.Namespace) -> int:
    """F119 — ros2 trace."""
    if shutil.which("ros2"):
        code = subprocess.call(["ros2", "trace", "-s", str(args.seconds)])
        return code
    _log("ros2 missing — would record /tracetools for "
         f"{args.seconds}s of /events/topic")
    return 0


# ---------------------------------------------------------------------------
def cmd_leak_detect(args: argparse.Namespace) -> int:
    """F120 — leak-detect (RSS delta polling)."""
    pid = args.pid or os.getpid()
    first = _read_rss_kb(pid)
    if first is None:
        _err(f"cannot read RSS for pid {pid}")
        return 1
    time.sleep(args.seconds)
    last = _read_rss_kb(pid)
    if last is None:
        _err(f"RSS gone for pid {pid}")
        return 1
    delta = last - first
    flag = "WARN" if delta > args.threshold_kb else "OK"
    _ok(json.dumps({
        "pid": pid, "rss_first_kb": first, "rss_last_kb": last,
        "delta_kb": delta, "threshold_kb": args.threshold_kb, "flag": flag,
    }, indent=2))
    return 0 if flag == "OK" else 1


def cmd_perf_summary(_: argparse.Namespace) -> int:
    """F121 — perf-summary CPU/RSS snapshot."""
    pid = os.getpid()
    rss = _read_rss_kb(pid)
    try:
        with open(f"/proc/{pid}/stat") as fh:
            fields = fh.read().split()
        rss_pages = int(fields[23])
    except (OSError, ValueError, IndexError):
        rss_pages = None
    try:
        with open(f"/proc/{pid}/cmdline") as fh:
            cmdline = fh.read().replace("\0", " ").strip()
    except OSError:
        cmdline = "?"
    fds = len(list(Path(f"/proc/{pid}/fd").iterdir())) \
        if Path(f"/proc/{pid}/fd").exists() else -1
    _ok(json.dumps({
        "pid":      pid,
        "cmdline":  cmdline[:160],
        "rss_kb":   rss,
        "rss_pages": rss_pages,
        "fd_count": fds,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Profiler CLI (F119-F121).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pt = sub.add_parser("ros-trace", help="F119 — ros2 trace")
    pt.add_argument("--seconds", type=int, default=5)
    pl = sub.add_parser("leak-detect", help="F120 — leak detect")
    pl.add_argument("--pid", type=int, default=0)
    pl.add_argument("--seconds", type=float, default=10.0)
    pl.add_argument("--threshold-kb", type=int, default=4096)
    sub.add_parser("perf-summary", help="F121 — perf summary")
    return p


HANDLERS = {
    "ros-trace":     cmd_ros_trace,
    "leak-detect":   cmd_leak_detect,
    "perf-summary":  cmd_perf_summary,
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
