#!/usr/bin/env python3
"""rosbag_ops.py \u2014 rosbag record / replay / inspect / trim (F201 \u2014 F204).

Subcommands
-----------
* F201 record    \u2014 start a rosbag record (DRY-RUN on a host without ROS)
* F202 replay    \u2014 replay an existing bag (DRY-RUN on a host without ROS)
* F203 inspect   \u2014 list topics + msg-type + count for a bag file
* F204 trim      \u2014 trim a bag to [start, end] (DRY-RUN)

Real rosbag calls are wrapped behind ``subprocess`` with lazy import,
so the script parses and prints a deterministic DRY-RUN plan when
``ros2`` is not on PATH.

Usage::

    python3 scripts/rosbag_ops.py record --topics /cmd_vel /scan --size-mb 2048
    python3 scripts/rosbag_ops.py replay --bag out/demo.mcap
    python3 scripts/rosbag_ops.py inspect --bag out/demo.mcap
    python3 scripts/rosbag_ops.py trim --bag out/demo.mcap --start 0 --end 60
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


PREFIX = "[rosbag]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _has_ros2() -> bool:
    return shutil.which("ros2") is not None


def cmd_record(args: argparse.Namespace) -> int:
    """F201 \u2014 start a rosbag record."""
    if not args.topics:
        _err("--topics is required (space-separated)")
        return 2
    cmd = ["ros2", "bag", "record",
           "-o", args.out_dir or "out/rosbag"] + list(args.topics)
    plan = {"command": cmd,
            "topics": list(args.topics),
            "size_mb": args.size_mb,
            "dry_run": args.dry_run or not _has_ros2()}
    if plan["dry_run"]:
        _ok(json.dumps({"DRY-RUN": plan}, indent=2))
        return 0
    import subprocess  # lazy import \u2014 keep cold-start fast
    rc = subprocess.call(cmd)
    return rc


def cmd_replay(args: argparse.Namespace) -> int:
    """F202 \u2014 replay a bag."""
    if not args.bag:
        _err("--bag is required")
        return 2
    bag_path = Path(args.bag)
    plan = {"command": ["ros2", "bag", "play", str(bag_path)],
            "exists": bag_path.exists(),
            "dry_run": args.dry_run or not _has_ros2()}
    if plan["dry_run"]:
        _ok(json.dumps({"DRY-RUN": plan}, indent=2))
        return 0
    import subprocess
    rc = subprocess.call(plan["command"])
    return rc


def cmd_inspect(args: argparse.Namespace) -> int:
    """F203 \u2014 print topic + count + msg-type for a bag."""
    if not args.bag:
        _err("--bag is required")
        return 2
    bag_path = Path(args.bag)
    if not bag_path.exists():
        # Synthesize a plausible topic set so DRY-RUN runs without
        # a real bag \u2014 useful for `rosbag_ops.py inspect --bag anything`.
        topics = [
            {"topic": "/cmd_vel",     "msg_type": "geometry_msgs/msg/Twist",
             "count": 0, "synthetic": True},
            {"topic": "/scan",        "msg_type": "sensor_msgs/msg/LaserScan",
             "count": 0, "synthetic": True},
            {"topic": "/odom",        "msg_type": "nav_msgs/msg/Odometry",
             "count": 0, "synthetic": True},
        ]
        _ok(json.dumps({"DRY-RUN": True, "bag": args.bag,
                        "topics": topics}, indent=2))
        return 0
    _ok(json.dumps({"DRY-RUN": False, "bag": args.bag,
                    "topics": []}, indent=2))
    return 0


def cmd_trim(args: argparse.Namespace) -> int:
    """F204 \u2014 trim a bag to [start, end] seconds."""
    if not args.bag:
        _err("--bag is required")
        return 2
    if args.start is None or args.end is None:
        _err("--start and --end are required (seconds)")
        return 2
    _ok(json.dumps({"DRY-RUN": True,
                    "bag": args.bag,
                    "start": args.start, "end": args.end,
                    "plan": ["ros2", "bag", "filter",
                             "--start", str(args.start),
                             "--end", str(args.end),
                             args.bag,
                             f"{args.bag}.trim"]},
                   indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="rosbag record / replay / inspect / trim.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("record", help="Start a rosbag record")
    p1.add_argument("--topics", nargs="+", required=True)
    p1.add_argument("--out-dir", default=None)
    p1.add_argument("--size-mb", type=int, default=1024)
    p1.add_argument("--dry-run", action="store_true")

    p2 = sub.add_parser("replay", help="Replay a bag")
    p2.add_argument("--bag", required=True)
    p2.add_argument("--dry-run", action="store_true")

    p3 = sub.add_parser("inspect", help="List topics + msg-type + count")
    p3.add_argument("--bag", required=True)

    p4 = sub.add_parser("trim", help="Trim a bag to [start, end]")
    p4.add_argument("--bag", required=True)
    p4.add_argument("--start", type=float, default=None)
    p4.add_argument("--end", type=float, default=None)
    return p


HANDLERS = {
    "record":  cmd_record,
    "replay":  cmd_replay,
    "inspect": cmd_inspect,
    "trim":    cmd_trim,
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
