#!/usr/bin/env python3
"""The Tank Project — webhook CLI.

Hosts 3 features (F125-F127):

* ``incoming``  — bring up a stdlib HTTP listener for `INCOMING_WEBHOOK`
* ``replay``    — replay queued hits to AI tooling (offline-friendly)
* ``dedup``     — drop identical-FP rows from a JSONL of hits
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path



LOG_PREFIX = "[webhook]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F125 — incoming
# ---------------------------------------------------------------------------
def cmd_incoming(args: argparse.Namespace) -> int:
    """F125 — start webhook listener."""
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (stdlib name)
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length else b""
            fp = hashlib.sha256(body).hexdigest()[:16]
            with out_path.open("a") as fh:
                fh.write(json.dumps({
                    "fp":    fp,
                    "path":  self.path,
                    "body":  body.decode("utf-8", errors="replace")[:400],
                    "ts":    __import__("time").time(),
                }) + "\n")
            self.send_response(202)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, *a, **kw):  # noqa: A003
            _log(f"hit {self.path} ({len(a[0])} chars)")

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    _log(f"listening on :{args.port} -> {out_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _ok("shutting down")
        server.shutdown()
    return 0


# ---------------------------------------------------------------------------
def cmd_replay(args: argparse.Namespace) -> int:
    """F126 — replay queued hits."""
    p = Path(args.path)
    if not p.exists():
        _err(f"{p} missing")
        return 1
    sent = 0
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        print(f"#{sent:>4d}  fp={ev.get('fp')}  "
              f"path={ev.get('path')}  body={(ev.get('body','') or '')[:80]}")
        sent += 1
        if sent >= args.limit:
            break
    _ok(f"replayed {sent} entries from {p}")
    return 0


def cmd_dedup(args: argparse.Namespace) -> int:
    """F127 — dedup replay JSONL."""
    p = Path(args.path)
    if not p.exists():
        _err(f"{p} missing")
        return 1
    seen = set()
    kept = 0; dropped = 0
    out_path = p.with_suffix(".dedup.jsonl")
    with out_path.open("w") as out:
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            fp = ev.get("fp")
            if not fp:
                continue
            if fp in seen:
                dropped += 1
                continue
            seen.add(fp)
            out.write(line + "\n")
            kept += 1
    _ok(f"kept {kept}, dropped {dropped} -> {out_path}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Webhook CLI (F125-F127).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("incoming", help="F125 — receive webhook hits")
    pi.add_argument("--port", type=int, default=9090)
    pi.add_argument("--out", default="/tmp/tank_webhook.jsonl")
    pr = sub.add_parser("replay", help="F126 — replay")
    pr.add_argument("path")
    pr.add_argument("--limit", type=int, default=1000)
    pd = sub.add_parser("dedup", help="F127 — dedup JSONL")
    pd.add_argument("path")
    return p


HANDLERS = {
    "incoming": cmd_incoming,
    "replay":   cmd_replay,
    "dedup":    cmd_dedup,
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
