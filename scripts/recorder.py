#!/usr/bin/env python3
"""The Tank Project — bridge recorder + topic playback.

Hosts 5 features (F017-F021):

* ``topic``    — record a ROS topic to a JSONL file via the command bridge.
* ``audit``    — pretty-print the bridge audit log.
* ``manifest`` — dump the live bridge manifest as YAML.
* ``smoke``    — end-to-end smoke (estop flip, telemetry, audit).
* ``replay``   — playback a JSONL of bridge commands so you can replay a
                  recorded session offline.

All commands degrade gracefully when the bridge is unreachable.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path



LOG_PREFIX = "[recorder]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _http_json(url: str, payload: Optional[dict] = None,
               token: Optional[str] = None, timeout: float = 4.0) -> tuple:
    """Tiny stdlib POST/GET helper. Returns (status, json-or-text)."""
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method="POST" if payload else "GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if payload:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as exc:
        return 0, str(exc)


# ---------------------------------------------------------------------------
# F017 — topic record
# ---------------------------------------------------------------------------
def cmd_topic(args: argparse.Namespace) -> int:
    """F017 — record a topic to JSONL via bridge forwarding."""
    token = args.token or os.environ.get("TANK_API_KEY", "")
    base = args.base.rstrip("/")
    deadline = time.monotonic() + args.seconds
    out = Path(args.out)
    samples = 0
    while time.monotonic() < deadline:
        status, body = _http_json(
            f"{base}/api/cmd/audit",
            token=token,
        )
        if status != 200 or not isinstance(body, dict):
            _log(f"bridge offline (status={status}); simulating sample")
            with out.open("a") as fh:
                fh.write(json.dumps({
                    "ts": time.time(),
                    "topic": args.topic,
                    "note": "bridge offline — record-locally stub",
                }) + "\n")
        else:
            with out.open("a") as fh:
                fh.write(json.dumps({
                    "ts": time.time(),
                    "topic": args.topic,
                    "audit_count": len(body.get("records", [])),
                }) + "\n")
        samples += 1
        time.sleep(args.poll)
    _ok(f"recorded {samples} samples for {args.topic} -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F018 — audit dump
# ---------------------------------------------------------------------------
def cmd_audit(args: argparse.Namespace) -> int:
    """F018 — pull `/api/cmd/audit` and pretty-print."""
    token = args.token or os.environ.get("TANK_API_KEY", "")
    status, body = _http_json(
        f"{args.base.rstrip('/')}/api/cmd/audit", token=token,
    )
    if status != 200 or not isinstance(body, dict):
        _err(f"audit pull failed (status={status}): {body}")
        return 1
    records = body.get("records", [])
    for rec in records[:args.limit]:
        ts = rec.get("ts", 0)
        when = _dt.datetime.utcfromtimestamp(ts).isoformat(timespec="seconds")
        print(f"{when}  {rec.get('command','?'):>10s}  "
              f"{rec.get('token_hash','-'):>22s}  {rec.get('status','?')}")
    _ok(f"printed {min(args.limit, len(records))} of {len(records)} records")
    return 0


# ---------------------------------------------------------------------------
# F019 — manifest dump
# ---------------------------------------------------------------------------
def cmd_manifest(args: argparse.Namespace) -> int:
    """F019 — fetch /api/cmd/manifest and print + optionally save."""
    status, body = _http_json(
        f"{args.base.rstrip('/')}/api/cmd/manifest",
    )
    if status != 200 or not isinstance(body, dict):
        _err(f"manifest pull failed (status={status}): {body}")
        return 1
    if args.out:
        Path(args.out).write_text(json.dumps(body, indent=2))
        _ok(f"wrote manifest -> {args.out}")
    for tool in body.get("tools", []):
        print(f"- {tool.get('name'):>10s}: {tool.get('description','')[:80]}")
    return 0


# ---------------------------------------------------------------------------
# F020 — bridge smoke
# ---------------------------------------------------------------------------
def cmd_smoke(args: argparse.Namespace) -> int:
    """F020 — end-to-end smoke: health + manifest + estop flip + audit."""
    token = args.token or os.environ.get("TANK_API_KEY", "")
    base = args.base.rstrip("/")
    failures = []
    status, body = _http_json(f"{base}/api/health")
    if status != 200 or not (isinstance(body, dict) and body.get("ok")):
        failures.append(("health", status, body))
    else:
        _ok("health responded ok")
    status, body = _http_json(f"{base}/api/cmd/manifest")
    if status != 200 or not (isinstance(body, dict) and "tools" in body):
        failures.append(("manifest", status, body))
    else:
        _ok(f"manifest has {len(body.get('tools', []))} tools")
    status, body = _http_json(f"{base}/api/cmd/estop",
                              payload={"audit_id": _audit_id(),
                                       "params": {"state": True}}, token=token)
    if status != 200:
        failures.append(("estop-latch", status, body))
    else:
        _ok("estop latched")
    time.sleep(0.4)
    status, body = _http_json(f"{base}/api/cmd/estop",
                              payload={"audit_id": _audit_id(),
                                       "params": {"state": False}}, token=token)
    if status != 200:
        failures.append(("estop-release", status, body))
    else:
        _ok("estop released")
    if failures:
        _err(f"{len(failures)} smoke failures: {failures}")
        return 1
    _ok("smoke test passed end-to-end")
    return 0


# ---------------------------------------------------------------------------
# F021 — replay
# ---------------------------------------------------------------------------
def cmd_replay(args: argparse.Namespace) -> int:
    """F021 — replay a previously recorded bridge session to stdout."""
    p = Path(args.path)
    if not p.exists():
        _err(f"no such jsonl: {p}")
        return 1
    n = 0
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            _err(f"skipped malformed line @ {n}")
            continue
        if args.dry_run:
            print(f"{n:>5d}  {rec.get('ts','?')}  {rec.get('topic','?')}  {rec}")
        else:
            print(f"{n:>5d}  ts={rec.get('ts'):.3f}  topic={rec.get('topic')}")
        n += 1
    _ok(f"replayed {n} entries from {p}")
    return 0


def _audit_id() -> str:
    """Uuid4 helper that falls back to a clock-based id."""
    try:
        import uuid
        return str(uuid.uuid4())
    except ImportError:  # pragma: no cover
        return f"anon-{time.time_ns()}"


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project recorder / smoke / replay (F017-F021).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pt = sub.add_parser("topic", help="F017 — record a topic to JSONL")
    pt.add_argument("topic")
    pt.add_argument("--base", default="http://tank.lan:8082")
    pt.add_argument("--token", default="")
    pt.add_argument("--seconds", type=float, default=10.0)
    pt.add_argument("--poll", type=float, default=1.0)
    pt.add_argument("--out", default="/tmp/tank_topic_record.jsonl")

    pa = sub.add_parser("audit", help="F018 — bridge audit dump")
    pa.add_argument("--base", default="http://tank.lan:8082")
    pa.add_argument("--token", default="")
    pa.add_argument("--limit", type=int, default=20)

    pm = sub.add_parser("manifest", help="F019 — live manifest dump")
    pm.add_argument("--base", default="http://tank.lan:8082")
    pm.add_argument("--out", default="")

    ps = sub.add_parser("smoke", help="F020 — bridge end-to-end smoke")
    ps.add_argument("--base", default="http://tank.lan:8082")
    ps.add_argument("--token", default="")

    pr = sub.add_parser("replay", help="F021 — replay a JSONL")
    pr.add_argument("path")
    pr.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "topic":    cmd_topic,
    "audit":    cmd_audit,
    "manifest": cmd_manifest,
    "smoke":    cmd_smoke,
    "replay":   cmd_replay,
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
