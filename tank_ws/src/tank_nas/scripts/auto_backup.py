#!/usr/bin/env python3
"""Auto-backup — nightly rclone/tar of dynamic state to /var/tank/backups/.

Captures:
    data/memory.db       (sqlite-vec episodic memory)
    recordings/          (security camera clips)
    nvs/                 (model files)
    (optionally) cloud-upload via rclone

Invoke from a systemd timer or cron.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys


def parse_args():
    p = argparse.ArgumentParser(description="tank nightly auto-backup")
    p.add_argument("--source", default=[
        os.path.expanduser("~/the-tank-project/tank_ws/data"),
        os.path.expanduser("~/the-tank-project/tank_ws/recordings"),
    ], nargs="*")
    p.add_argument("--dest", default=os.path.expanduser("~/the-tank-project/backups"))
    p.add_argument("--rclone-remote", default="")
    p.add_argument("--keep-days", type=int, default=10)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    os.makedirs(args.dest, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(args.dest, f"backup-{stamp}.tar.gz")
    cmd = ["tar", "czf", out]
    for s in args.source:
        if os.path.exists(s):
            cmd += ["-C", os.path.dirname(s) or ".", os.path.basename(s)]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)
    if args.rclone_remote:
        subprocess.run(["rclone", "copy", out, args.rclone_remote + "/"], check=True)
    # Prune older than keep-days
    cutoff = datetime.datetime.now() - datetime.timedelta(days=args.keep_days)
    for f in os.listdir(args.dest):
        path = os.path.join(args.dest, f)
        if not f.startswith("backup-") or not f.endswith(".tar.gz"):
            continue
        ts = f[len("backup-"):-len(".tar.gz")]
        try:
            d = datetime.datetime.strptime(ts, "%Y%m%d-%H%M%S")
        except Exception:
            continue
        if d < cutoff:
            print(f"pruning {path}")
            os.remove(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
