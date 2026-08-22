#!/usr/bin/env python3
"""The Tank Project — i18n ops CLI.

Hosts 3 features (F131-F133):

* ``locale-list``      — list everything in tank_ws/locales/
* ``locale-test``      — sanity-check a single locale file's structure
* ``translate-cache``  — generate a translation cache skeleton
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path



LOG_PREFIX = "[i18n-ops]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _locales_dir() -> Path:
    return _repo_root() / "tank_ws" / "locales"


# ---------------------------------------------------------------------------
# F131 — locale-list
# ---------------------------------------------------------------------------
def cmd_locale_list(_: argparse.Namespace) -> int:
    """F131 — locale list."""
    d = _locales_dir()
    if not d.is_dir():
        _log(f"locales dir missing: {d}")
        return 0
    rows = []
    for path in sorted(d.glob("*.json")):
        rows.append({
            "name":  path.stem,
            "size":  path.stat().st_size,
            "keys":  len(json.loads(path.read_text())) if path.stat().st_size else 0,
        })
    if not rows:
        _log(f"locales dir empty: {d}")
        return 0
    _ok(json.dumps(rows, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F132 — locale-test
# ---------------------------------------------------------------------------
def cmd_locale_test(args: argparse.Namespace) -> int:
    """F132 — locale file sanity test."""
    p = _locales_dir() / f"{args.locale}.json"
    if not p.exists():
        _err(f"{p} missing")
        return 1
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        _err(f"json parse: {exc}")
        return 1
    if not isinstance(data, dict):
        _err(f"top-level is not dict: {type(data).__name__}")
        return 1
    n_keys = len(data)
    empty = [k for k, v in data.items() if not v]
    _ok(json.dumps({"locale": args.locale, "n_keys": n_keys,
                    "empty_keys": empty[:10]}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F133 — translate-cache
# ---------------------------------------------------------------------------
def cmd_translate_cache(args: argparse.Namespace) -> int:
    """F133 — generate a translation cache skeleton."""
    out = _repo_root() / "tank_ws" / "data" / "translate_cache.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.build or not out.exists():
        with out.open("w") as fh:
            for lang in ("en", "es", "fr", "de", "ja"):
                fh.write(json.dumps({
                    "locale": lang, "key": "warmup", "source": "hello",
                    "target": "", "ts": 0,
                }) + "\n")
        _ok(f"cache re-built → {out}")
        return 0
    _log(f"cache exists ({out.stat().st_size} bytes); pass --build to overwrite")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="i18n ops CLI (F131-F133).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("locale-list", help="F131 — locale list")
    pt = sub.add_parser("locale-test", help="F132 — locale test")
    pt.add_argument("--locale", required=True)
    pc = sub.add_parser("translate-cache", help="F133 — translate-cache")
    pc.add_argument("--build", action="store_true")
    return p


HANDLERS = {
    "locale-list":      cmd_locale_list,
    "locale-test":      cmd_locale_test,
    "translate-cache":  cmd_translate_cache,
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
