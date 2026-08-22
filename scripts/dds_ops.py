#!/usr/bin/env python3
"""The Tank Project — DDS ops CLI.

Hosts 3 features (F116-F118):

* ``qos-profile``     — emit a DDS QoS XML profile
* ``topic-tune``      — emit a per-topic Qos override YAML
* ``peer-discovery``  — list expectations for peer bride
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path



LOG_PREFIX = "[dds-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F116 — qos-profile
# ---------------------------------------------------------------------------
def cmd_qos_profile(args: argparse.Namespace) -> int:
    """F116 — DDS QoS XML profile emit."""
    template = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<dds xmlns="http://www.omg.org/dds" version="1.2">\n'
        f'  <qos_profile name="{args.name}">\n'
        f'    <reliability><kind>RELIABLE</kind></reliability>\n'
        f'    <history><kind>KEEP_LAST</kind><depth>{args.depth}</depth></history>\n'
        f'    <durability><kind>VOLATILE</kind></durability>\n'
        f'  </qos_profile>\n'
        '</dds>\n')
    out = _repo_root() / "tank_ws" / "src" / f"qos_{args.name}.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template)
    _ok(f"wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# F117 — topic-tune
# ---------------------------------------------------------------------------
def cmd_topic_tune(args: argparse.Namespace) -> int:
    """F117 — per-topic QoS override."""
    cfg = {
        "topic": args.topic,
        "reliability":     args.reliability,
        "history_depth":   args.depth,
        "rate_limit_hz":   args.rate_limit,
    }
    out = Path(args.out or "tank_ws/data/topic_qos.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(json.dumps(cfg) + "\n")
    _ok(f"appended tune for {args.topic} -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F118 — peer-discovery
# ---------------------------------------------------------------------------
def cmd_peer_discovery(_: argparse.Namespace) -> int:
    """F118 — DDS peer discovery."""
    if shutil.which("ros2"):
        out = subprocess.run(["ros2", "doctor", "--report"],
                             capture_output=True, text=True, check=False)
        _log(out.stdout.strip().splitlines()[:20] or
             "no peers reported")
        return 0
    # offline fallback: parse /etc/hosts + CYCLONEDDS_URI
    peers = []
    if Path("/etc/hosts").exists():
        for line in Path("/etc/hosts").read_text().splitlines():
            if line.strip().startswith("#") or not line.strip():
                continue
            fields = line.split()
            if len(fields) >= 2:
                peers.append({"name_or_ip": fields[0],
                              "host":      fields[-1]})
    dds_uri = os.environ.get("CYCLONEDDS_URI") or os.environ.get("ROS_DISCOVERY_SERVER")
    _ok(json.dumps({"peers": peers[:16], "dds_uri": dds_uri}, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DDS ops CLI (F116-F118).")
    sub = p.add_subparsers(dest="cmd", required=True)

    pq = sub.add_parser("qos-profile", help="F116 — DDS QoS XML profile")
    pq.add_argument("--name", default="sensor_data")
    pq.add_argument("--depth", type=int, default=10)

    pt = sub.add_parser("topic-tune", help="F117 — per-topic QoS tune")
    pt.add_argument("--topic", required=True)
    pt.add_argument("--reliability", choices=("best_effort", "reliable"),
                    default="reliable")
    pt.add_argument("--depth", type=int, default=10)
    pt.add_argument("--rate-limit", type=float, default=20.0)
    pt.add_argument("--out", default="")

    sub.add_parser("peer-discovery", help="F118 — DDS peer discovery")
    return p


HANDLERS = {
    "qos-profile":    cmd_qos_profile,
    "topic-tune":     cmd_topic_tune,
    "peer-discovery": cmd_peer_discovery,
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
