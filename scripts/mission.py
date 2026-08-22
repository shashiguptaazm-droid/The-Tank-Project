#!/usr/bin/env python3
"""The Tank Project — mission / task-graph CLI.

Hosts 4 features (F078-F081):

* ``waypoint-edit``  — edit a JSON list of waypoints (add / remove / sort)
* ``mission-lint``   — validate that a mission file is well-formed
* ``task-graph``     — render a DAG of tasks to .dot (graphviz)
* ``recipe-trade``   — exchange a recipe with the marketplace stub
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path



LOG_PREFIX = "[mission]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F078 — waypoint-edit
# ---------------------------------------------------------------------------
def cmd_waypoint_edit(args: argparse.Namespace) -> int:
    """F078 — waypoint editor."""
    path = Path(args.mission)
    if path.exists():
        wp = json.loads(path.read_text())
    else:
        wp = {"waypoints": []}
    if args.add:
        for wp_str in args.add:
            x, y = wp_str.split(",")[:2]
            wp.setdefault("waypoints", []).append({"x": float(x), "y": float(y)})
    if args.sort:
        wp["waypoints"] = sorted(wp["waypoints"], key=lambda w: (w["x"], w["y"]))
    if args.clear:
        wp["waypoints"] = []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(wp, indent=2))
    _ok(f"{len(wp.get('waypoints', []))} waypoints -> {path}")
    return 0


# ---------------------------------------------------------------------------
# F079 — mission-lint
# ---------------------------------------------------------------------------
def cmd_mission_lint(args: argparse.Namespace) -> int:
    """F079 — mission lint."""
    bad = 0
    files = [Path(p) for p in args.files]
    for p in files:
        if not p.exists():
            _err(f"missing: {p}")
            bad += 1
            continue
        try:
            obj = json.loads(p.read_text())
        except json.JSONDecodeError as exc:
            _err(f"json parse: {p} ({exc})")
            bad += 1
            continue
        if not isinstance(obj, dict) or "waypoints" not in obj:
            _err(f"missing `waypoints` key: {p}")
            bad += 1
            continue
        wps = obj["waypoints"]
        if len(wps) < 2:
            _err(f"{p}: fewer than 2 waypoints")
            bad += 1
        for i, wp in enumerate(wps):
            if "x" not in wp or "y" not in wp:
                _err(f"{p}: waypoint[{i}] missing x/y")
                bad += 1
    _ok(f"{len(files) - bad}/{len(files)} missions valid")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
# F080 — task-graph
# ---------------------------------------------------------------------------
def cmd_task_graph(args: argparse.Namespace) -> int:
    """F080 — task DAG render."""
    path = Path(args.path)
    if not path.exists():
        _err(f"task file missing: {path}")
        return 1
    obj = json.loads(path.read_text())
    nodes = obj.get("nodes", [])
    edges = obj.get("edges", [])
    dot = ["digraph tank_mission {", "  rankdir=LR;"]
    for n in nodes:
        dot.append(f'  "{n["id"]}" [label="{n.get("label", n["id"])}"];')
    for e in edges:
        dot.append(f'  "{e["from"]}" -> "{e["to"]}";')
    dot.append("}")
    out = Path(args.out or "tank_ws/data/task_graph.dot")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(dot))
    _ok(f"task graph ({len(nodes)} nodes, {len(edges)} edges) -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F081 — recipe-trade
# ---------------------------------------------------------------------------
def cmd_recipe_trade(args: argparse.Namespace) -> int:
    """F081 — recipe marketplace exchange."""
    src = Path(args.from_)
    if not src.exists():
        _err(f"recipes file missing: {src}")
        return 1
    payload = json.loads(src.read_text())
    payload["marketed_at"] = payload.get("marketed_at", 0.0)
    payload["uuid"] = payload.get("uuid", f"recipe-{id(payload):x}")
    out = Path(args.out or "tank_ws/data/recipes_out.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str))
    _ok(f"recipe {payload['uuid']} -> {out}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mission planning CLI (F078-F081).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("waypoint-edit", help="F078 — waypoint editor")
    pw.add_argument("--mission", default="tank_ws/data/mission.json")
    pw.add_argument("--add", nargs="*", metavar="X,Y")
    pw.add_argument("--sort", action="store_true")
    pw.add_argument("--clear", action="store_true")
    pl = sub.add_parser("mission-lint", help="F079 — mission lint")
    pl.add_argument("files", nargs="+")
    pt = sub.add_parser("task-graph", help="F080 — task graph viz")
    pt.add_argument("--path", required=True)
    pt.add_argument("--out", default="")
    pr = sub.add_parser("recipe-trade", help="F081 — recipe trade")
    pr.add_argument("--from", dest="from_", required=True)
    pr.add_argument("--out", default="")
    return p


HANDLERS = {
    "waypoint-edit": cmd_waypoint_edit,
    "mission-lint":  cmd_mission_lint,
    "task-graph":    cmd_task_graph,
    "recipe-trade":  cmd_recipe_trade,
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
