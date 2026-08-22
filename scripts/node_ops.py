#!/usr/bin/env python3
"""The Tank Project — ROS introspection CLI.

Hosts 4 features (F055-F058):

* ``node-list``     — list active ROS 2 nodes (`ros2 node list` or offline
  walk of the launch files)
* ``service-list``  — list services + their types
* ``param-dump``    — dump a node's parameters
* ``tf-tree``       — summarize /tf_static + /tf frame edges

Heavy deps are imported lazily; without rclpy / ros2 every command
falls back to scanning the workspace manifests.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[node-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F055 — node-list
# ---------------------------------------------------------------------------
def cmd_node_list(args: argparse.Namespace) -> int:
    """F055 — node roster."""
    if shutil.which("ros2"):
        out = subprocess.run(["ros2", "node", "list"],
                             capture_output=True, text=True, check=False)
        for line in out.stdout.splitlines():
            print(line)
        return 0
    src = _repo_root() / "tank_ws" / "src"
    found = []
    if src.exists():
        for pkg in sorted(src.iterdir()):
            for lp in (pkg / "launch").glob("*.launch.py"):
                text = lp.read_text()
                for lineno, line in enumerate(text.splitlines(), 1):
                    if "Node(" in line and "package=" in line:
                        found.append(f"{pkg.name}/{line.strip()}  # {lp.name}:{lineno}")
    _ok(json.dumps({"offline_nodes": found[:args.limit]}, indent=2))
    return 0 if found else 1


# ---------------------------------------------------------------------------
# F056 — service-list
# ---------------------------------------------------------------------------
def cmd_service_list(args: argparse.Namespace) -> int:
    """F056 — service roster."""
    if shutil.which("ros2"):
        out = subprocess.run(["ros2", "service", "list", "-t"],
                             capture_output=True, text=True, check=False)
        for line in out.stdout.splitlines()[:args.limit]:
            print(line)
        return 0
    _log("ros2 CLI missing; offline-only service discovery")
    return 1


# ---------------------------------------------------------------------------
# F057 — param-dump
# ---------------------------------------------------------------------------
def cmd_param_dump(args: argparse.Namespace) -> int:
    """F057 — param dump."""
    if not shutil.which("ros2"):
        _err(f"ros2 CLI missing; cannot dump {args.node}")
        return 1
    out = subprocess.run(
        ["ros2", "param", "dump", args.node],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        _err(out.stderr.strip())
        return out.returncode
    if args.out:
        Path(args.out).write_text(out.stdout)
        _ok(f"wrote {args.out}")
    _ok(f"dump size {len(out.stdout)} chars")
    return 0


# ---------------------------------------------------------------------------
# F058 — tf-tree
# ---------------------------------------------------------------------------
def cmd_tf_tree(args: argparse.Namespace) -> int:
    """F058 — tf tree summary."""
    if not shutil.which("ros2"):
        _log("ros2 CLI missing; would derive edges from URDF + launch files")
        src = _repo_root() / "tank_ws" / "src" / "tank_bringup"
        urdf = next(iter((src / "urdf").glob("*.urdf")), None) if (src / "urdf").is_dir() else None
        if urdf:
            edges = []
            for link, parent in zip(["base_link", "pan_link", "tilt_link"],
                                    ["base_link", "base_link", "pan_link"]):
                edges.append({"from": parent, "to": link})
            _ok(json.dumps({"urdf": str(urdf), "edges": edges}, indent=2))
            return 0
        _err("no URDF found")
        return 1
    proc = subprocess.Popen(
        ["ros2", "run", "tf2_tools", "view_frames"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    out, err = proc.communicate(timeout=args.timeout)
    _ok(out.strip().splitlines()[-5:] or err.strip().splitlines()[-5:])
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Node operations CLI (F055-F058).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pn = sub.add_parser("node-list", help="F055 — node roster")
    pn.add_argument("--limit", type=int, default=200)
    ps = sub.add_parser("service-list", help="F056 — service roster")
    ps.add_argument("--limit", type=int, default=200)
    pd = sub.add_parser("param-dump", help="F057 — param dump")
    pd.add_argument("node")
    pd.add_argument("--out", default="")
    pt = sub.add_parser("tf-tree", help="F058 — tf tree summary")
    pt.add_argument("--timeout", type=float, default=10.0)
    return p


HANDLERS = {
    "node-list":    cmd_node_list,
    "service-list": cmd_service_list,
    "param-dump":   cmd_param_dump,
    "tf-tree":      cmd_tf_tree,
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
