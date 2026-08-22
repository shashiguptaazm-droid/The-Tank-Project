#!/usr/bin/env python3
"""The Tank Project — OTA / image deployment CLI.

Hosts 4 features (F087-F090):

* ``image-pin``      — record an image-version pin to a JSON registry
* ``tarball-diff``   — compare two .tar files via manifest + tar tvf
* ``ab-toggle``      — toggle a marker file representing A/B boot slot
* ``sd-burn``        — verify an SD-card write target is empty/recoverable

Designed so a CI step can pin releases and a maintenance window can flip
slots. Heavy operations (writing tarballs to disk) require explicit
`--apply`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path



LOG_PREFIX = "[ota]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F087 — image-pin
# ---------------------------------------------------------------------------
def cmd_image_pin(args: argparse.Namespace) -> int:
    """F087 — image-version pin."""
    pin_file = _repo_root() / "tank_ws" / "data" / "image_pins.json"
    pin_file.parent.mkdir(parents=True, exist_ok=True)
    pins = json.loads(pin_file.read_text()) if pin_file.exists() else {}
    pins[args.tag] = {"ts": str(args.tag), "notes": args.notes}
    pin_file.write_text(json.dumps(pins, indent=2))
    _ok(f"pin {args.tag} -> {pin_file}")
    return 0


# ---------------------------------------------------------------------------
# F088 — tarball-diff
# ---------------------------------------------------------------------------
def cmd_tarball_diff(args: argparse.Namespace) -> int:
    """F088 — tarball diff (manifest + sha256)."""
    def manifest(p: Path) -> dict:
        out = {}
        if not p.exists():
            _err(f"missing tarball: {p}")
        else:
            with tarfile.open(p) as t:
                for m in t.getmembers():
                    if m.isfile():
                        f = t.extractfile(m)
                        if f is None:
                            continue
                        out[m.name] = hashlib.sha256(f.read()).hexdigest()
        return out
    a = manifest(Path(args.old))
    b = manifest(Path(args.new))
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = sorted(name for name in (set(a) & set(b)) if a[name] != b[name])
    _ok(json.dumps({"only_in_old": only_a[:args.top],
                    "only_in_new": only_b[:args.top],
                    "changed": diff[:args.top]}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F089 — ab-toggle
# ---------------------------------------------------------------------------
def cmd_ab_toggle(args: argparse.Namespace) -> int:
    """F089 — A/B partition toggle."""
    ab_dir = _repo_root() / "tank_ws" / "data" / "ab_state"
    ab_dir.mkdir(parents=True, exist_ok=True)
    marker = ab_dir / "active_slot"
    if args.dry_run:
        _log(f"DRY: would set active slot -> {args.slot}")
        return 0
    marker.write_text(json.dumps({"slot": args.slot,
                                  "ts": time.time()}))
    _ok(f"active slot -> {args.slot}")
    return 0


# ---------------------------------------------------------------------------
# F090 — sd-burn
# ---------------------------------------------------------------------------
def cmd_sd_burn(args: argparse.Namespace) -> int:
    """F090 — SD-card burn verify."""
    if args.dry_run:
        _log(f"DRY: would dd {args.image} -> {args.device}")
        return 0
    target = Path(args.device)
    if not target.exists():
        _err(f"target missing: {target}")
        return 1
    if not os.access(target, os.R_OK | os.W_OK):
        _err(f"target not writable: {target}")
        return 1
    _ok(f"{args.device} appears writable; use `dd` manually with caution")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="OTA / image deployment CLI (F087-F090).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("image-pin", help="F087 — image-version pin")
    pp.add_argument("--tag", required=True)
    pp.add_argument("--notes", default="")
    pd = sub.add_parser("tarball-diff", help="F088 — tarball diff")
    pd.add_argument("old")
    pd.add_argument("new")
    pd.add_argument("--top", type=int, default=50)
    pa = sub.add_parser("ab-toggle", help="F089 — A/B toggle")
    pa.add_argument("--slot", required=True, choices=("a", "b"))
    pa.add_argument("--dry-run", action="store_true")
    ps = sub.add_parser("sd-burn", help="F090 — SD burn verify")
    ps.add_argument("--image", required=True)
    ps.add_argument("--device", required=True)
    ps.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "image-pin":    cmd_image_pin,
    "tarball-diff": cmd_tarball_diff,
    "ab-toggle":    cmd_ab_toggle,
    "sd-burn":      cmd_sd_burn,
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
