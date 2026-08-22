#!/usr/bin/env python3
"""The Tank Project — UX polish CLI.

Hosts 2 features (F091-F092):

* ``soundboard``      — list + play a soundboard cue
* ``dashboard-theme`` — rotate the dashboard theme via config write
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path



LOG_PREFIX = "[ux-polish]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F091 — soundboard
# ---------------------------------------------------------------------------
def cmd_soundboard(args: argparse.Namespace) -> int:
    """F091 — soundboard."""
    board_dir = _repo_root() / "tank_ws" / "data" / "soundboard"
    cues = sorted(board_dir.glob("*.wav")) + sorted(board_dir.glob("*.mp3"))
    _ok(f"available cues: {[c.stem for c in cues]}")
    target = next((c for c in cues if c.stem == args.cue), None)
    if target is None:
        _err(f"cue not found: {args.cue}")
        return 1
    if args.dry_run:
        _log(f"DRY: would play {target}")
        return 0
    player = shutil.which("aplay") or shutil.which("paplay") or shutil.which("ffplay")
    if not player:
        _err("no audio player found")
        return 1
    code = subprocess.call([player, str(target)])
    return 0 if code == 0 else 1


# ---------------------------------------------------------------------------
# F092 — dashboard-theme
# ---------------------------------------------------------------------------
def cmd_dashboard_theme(args: argparse.Namespace) -> int:
    """F092 — dashboard theme rotate."""
    cfg = _repo_root() / "tank_ws" / "src" / "tank_dashboard" / "dashboard" / "theme.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    themes = ("dawn", "dusk", "wave", "mono", "rose")
    if args.theme not in themes:
        _err(f"theme must be in {themes!r}")
        return 1
    cfg.write_text(json.dumps({"theme": args.theme, "ts": time.time()}, indent=2))
    _ok(f"theme={args.theme} -> {cfg}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="UX polish CLI (F091-F092).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("soundboard", help="F091 — soundboard")
    pb.add_argument("--cue", default="hi")
    pb.add_argument("--dry-run", action="store_true")
    pt = sub.add_parser("dashboard-theme", help="F092 — dashboard theme")
    pt.add_argument("--theme", default="dawn")
    return p


HANDLERS = {
    "soundboard":      cmd_soundboard,
    "dashboard-theme": cmd_dashboard_theme,
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
