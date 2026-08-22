#!/usr/bin/env python3
"""Stand-alone CLI for planning a patrol trajectory without spinning up ROS.

Useful when you want to verify a waypoints file or tune random-walk bounds
without booting the whole Pi 5 stack.

Usage::

    python3 scripts/run_patrol.py waypoint \\
        --waypoints /path/to/waypoints.json \\
        --start-x 0.0 --start-y 0.0 \\
        --max-legs 10 \\
        --pretty                # print a 2-D ASCII trail

    python3 scripts/run_patrol.py random \\
        --bounds -5 -5 5 5 \\
        --start-x 0.0 --start-y 0.0 \\
        --max-legs 20
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

# This script lives at:
#   <repo>/tank_ws/src/tank_patrol/scripts/run_patrol.py
# The actual Python package (with __init__.py) is at:
#   <repo>/tank_ws/src/tank_patrol/tank_patrol/   — one level deeper.
# Insert that into sys.path so ``import patrol_modes`` resolves cleanly.
HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.abspath(os.path.join(HERE, os.pardir, "tank_patrol"))
sys.path.insert(0, PKG_DIR)

from patrol_modes import (  # noqa: E402
    Pose2D,
    RandomWalkPatrol,
    WaypointPatrol,
    load_waypoints_json,
)


def _cmd_waypoint(args) -> int:
    waypoints = load_waypoints_json(args.waypoints)
    mode = WaypointPatrol(waypoints, loop=args.loop)
    cur = Pose2D(args.start_x, args.start_y)
    goal = mode.reset(cur)
    print("# mode=waypoint file={}".format(args.waypoints))
    print("# poses={} loop={} max_legs={}".format(
        len(waypoints), args.loop, args.max_legs))
    for i in range(args.max_legs):
        if goal is None:
            break
        print("leg {:>3}  cur=({:+.2f},{:+.2f})  ->  ({:+.2f},{:+.2f})  "
              "yaw={:+.2f}  speed={:.2f}  label={}".format(
                  i,
                  cur.x, cur.y,
                  goal.target.x, goal.target.y,
                  goal.target.yaw,
                  goal.speed,
                  goal.label,
              ))
        cur = goal.target
        if mode.done():
            print("# patrol complete (loop=False)")
            break
        goal = mode.next_goal(cur)
    if args.pretty and len(waypoints) <= 30:
        _print_ascii_trail(waypoints)
    return 0


def _cmd_random(args) -> int:
    bounds = (args.bounds[0], args.bounds[1], args.bounds[2], args.bounds[3])
    mode = RandomWalkPatrol(bounds=bounds, seed=args.seed)
    cur = Pose2D(args.start_x, args.start_y)
    goal = mode.reset(cur)
    print("# mode=random bounds={} seed={} max_legs={}".format(
        bounds, args.seed, args.max_legs))
    for i in range(args.max_legs):
        if goal is None:
            break
        print("leg {:>3}  cur=({:+.2f},{:+.2f})  ->  ({:+.2f},{:+.2f})  "
              "speed={:.2f}".format(
                  i, cur.x, cur.y, goal.target.x, goal.target.y, goal.speed))
        cur = goal.target
        goal = mode.next_goal(cur)
    return 0


def _print_ascii_trail(waypoints) -> None:
    xs = [p.x for p in waypoints]
    ys = [p.y for p in waypoints]
    if not xs:
        return
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    span = max(xmax - xmin, ymax - ymin, 1.0)
    W, H = 60, 16
    grid = [[" "] * W for _ in range(H)]
    for i, p in enumerate(waypoints):
        cx = int((p.x - xmin) / span * (W - 1))
        # ASCII y is inverted (top == high y)
        cy = int((ymax - p.y) / span * (H - 1))
        cx = max(0, min(W - 1, cx))
        cy = max(0, min(H - 1, cy))
        marker = "0"
        if 1 <= i <= 9:
            marker = str(i)
        elif i >= 10:
            marker = "+"
        grid[cy][cx] = marker
    print("#")
    print("# ASCII trail (markers 0..9 = waypoint order):")
    for row in grid:
        print("#   " + "".join(row).rstrip())


def main() -> int:
    p = argparse.ArgumentParser(
        description="Offline patrol trajectory preview (no ROS)."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_w = sub.add_parser("waypoint", help="plan a waypoint patrol")
    p_w.add_argument("--waypoints", required=True,
                     help="JSON file: [{name, x, y, yaw?}, ...]")
    p_w.add_argument("--start-x", type=float, default=0.0)
    p_w.add_argument("--start-y", type=float, default=0.0)
    p_w.add_argument("--max-legs", type=int, default=20)
    p_w.add_argument("--loop", action="store_true", default=True,
                     help="loop over waypoints (default: True)")
    p_w.add_argument("--no-loop", dest="loop", action="store_false")
    p_w.add_argument("--pretty", action="store_true",
                     help="print an ASCII trail (only when <=30 waypoints)")
    p_w.set_defaults(fn=_cmd_waypoint)

    p_r = sub.add_parser("random", help="plan a random walk")
    p_r.add_argument("--bounds", type=float, nargs=4,
                     metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
                     default=[-5.0, -5.0, 5.0, 5.0])
    p_r.add_argument("--start-x", type=float, default=0.0)
    p_r.add_argument("--start-y", type=float, default=0.0)
    p_r.add_argument("--max-legs", type=int, default=20)
    p_r.add_argument("--seed", type=int, default=42)
    p_r.set_defaults(fn=_cmd_random)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
