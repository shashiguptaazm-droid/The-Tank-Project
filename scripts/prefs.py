#!/usr/bin/env python3
"""The Tank Project — `tank_personalize` companion CLI.

Hosts 2 features (F047-F048):

* ``prefs``  — dump the Preferences store (motion/privacy/audio sections)
               at a target port via the personalize HTTP API (`/api/prefs`)
               OR directly from a sqlite file when the API is unreachable.
* ``persona``— dump the persona (name/tone/backstory) via `/api/persona`
               OR from a JSON snapshot at ``data/persona.json``.

Designed to work with the existing API surface (port 8084, env var
`TANK_API_KEY`). On failure it falls back to the on-disk source of truth
so this CLI also doubles as a portable audit tool.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path



LOG_PREFIX = "[prefs-cli]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _http_get(url: str, token: Optional[str] = None,
              timeout: float = 2.0) -> tuple:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body.decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as exc:
        return 0, str(exc)


# ---------------------------------------------------------------------------
# F047 — prefs dump
# ---------------------------------------------------------------------------
def cmd_prefs(args: argparse.Namespace) -> int:
    """F047 — prefs dump from /api/prefs."""
    token = args.token or os.environ.get("TANK_API_KEY", "")
    base = f"http://{args.host}:{args.port}"
    section = f"/{args.section}" if args.section else ""
    status, body = _http_get(f"{base}/api/prefs{section}", token)
    if status == 200 and isinstance(body, dict):
        _ok(json.dumps(body, indent=2))
        return 0
    _err(f"live API unreachable (status={status}); falling back to disk")
    db = _repo_root() / "tank_ws" / "data" / "prefs.db"
    if not db.exists():
        _err(f"no on-disk prefs.db at {db}")
        return 1
    with sqlite3.connect(db) as con:
        cols = [r[1] for r in con.execute("PRAGMA table_info(prefs)").fetchall()]
        if not cols:
            _err(f"prefs table missing columns in {db}; aborting")
            return 1
        if args.section and "section" in cols and "key" in cols:
            rows = con.execute(
                "SELECT key FROM prefs WHERE section = ?",
                (args.section,),
            ).fetchall()
        elif "section" in cols and "key" in cols:
            rows = con.execute(
                "SELECT section, key FROM prefs ORDER BY section, key"
            ).fetchall()
        else:
            _err(f"prefs schema is {cols!r}; expected (section, key, value)")
            return 1
    if not rows:
        _err("no rows")
        return 1
    for row in rows:
        print("  ".join(str(c) for c in row))
    return 0


# ---------------------------------------------------------------------------
# F048 — persona history
# ---------------------------------------------------------------------------
def cmd_persona(args: argparse.Namespace) -> int:
    """F048 — persona dump."""
    token = args.token or os.environ.get("TANK_API_KEY", "")
    base = f"http://{args.host}:{args.port}"
    status, body = _http_get(f"{base}/api/persona", token)
    if status == 200 and isinstance(body, dict):
        _ok(json.dumps(body, indent=2, default=str))
        return 0
    _err(f"live API unreachable (status={status}); falling back to disk")
    snap = _repo_root() / "tank_ws" / "data" / "persona.json"
    if not snap.exists():
        _err(f"no persona snapshot at {snap}")
        return 1
    _ok(json.dumps(json.loads(snap.read_text()), indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project personalize CLI (F047-F048).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prefs", help="F047 — prefs dump")
    pp.add_argument("--host", default="tank.lan")
    pp.add_argument("--port", type=int, default=8084)
    pp.add_argument("--section", default="",
                    help="empty = motion/privacy/audio; otherwise section name")
    pp.add_argument("--token", default="")
    ppe = sub.add_parser("persona", help="F048 — persona dump")
    ppe.add_argument("--host", default="tank.lan")
    ppe.add_argument("--port", type=int, default=8084)
    ppe.add_argument("--token", default="")
    return p


HANDLERS = {
    "prefs":   cmd_prefs,
    "persona": cmd_persona,
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
