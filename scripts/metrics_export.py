#!/usr/bin/env python3
"""The Tank Project — metrics export CLI.

Hosts 3 features (F128-F130):

* ``prom-snapshot``  — pull /metrics and persist a snapshot
* ``tsdb-bridge``    — convert Prometheus text -> InfluxDB JSONL
* ``otel-export``    — convert Prometheus text -> OTLP-pseudo JSONL
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path



LOG_PREFIX = "[metrics-export]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _http_get(url: str, timeout: float = 4.0) -> tuple:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as exc:
        return 0, str(exc)


# ---------------------------------------------------------------------------
# F128 — prom-snapshot
# ---------------------------------------------------------------------------
def cmd_prom_snapshot(args: argparse.Namespace) -> int:
    """F128 — Prometheus snapshot."""
    status, body = _http_get(args.url)
    if status != 200:
        _err(f"pull failed (status={status}, body={body[:200]!r})")
        return 1
    out = Path(args.out or f"/tmp/tank_prom_{int(time.time())}.txt")
    out.write_text(body)
    _ok(f"snapshot {len(body)} bytes -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F129 — tsdb-bridge (Prom -> InfluxDB JSONL)
# ---------------------------------------------------------------------------
def cmd_tsdb_bridge(args: argparse.Namespace) -> int:
    """F129 — Prom -> InfluxDB JSONL bridge."""
    src = Path(args.input or "/tmp/last_prom.txt")
    if not src.exists():
        _err(f"input missing: {src}")
        return 1
    out = Path(args.out or "tank_ws/data/influx.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = 0
    with out.open("w") as out_fh:
        for line in src.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            try:
                name, value = line.rsplit(" ", 1)
                f = float(value)
            except ValueError:
                continue
            out_fh.write(json.dumps({
                "measurement": name,
                "fields":      {"value": f},
                "time":        args.ts,
            }) + "\n")
            lines += 1
    _ok(f"converted {lines} samples -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F130 — otel-export
# ---------------------------------------------------------------------------
def cmd_otel_export(args: argparse.Namespace) -> int:
    """F130 — Prom -> OTLP JSONL bridge."""
    src = Path(args.input or "/tmp/last_prom.txt")
    if not src.exists():
        _err(f"input missing: {src}")
        return 1
    out = Path(args.out or "tank_ws/data/otel.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = 0
    ts_ns = int(args.ts * 1_000_000_000)
    pattern = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)"
                         r"(?:\{[^}]*\})?\s+([-+]?\d*\.?\d+)(?:[eE][-+]?\d+)?")
    with out.open("w") as out_fh:
        for line in src.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            m = pattern.match(line)
            if not m:
                continue
            name, value = m.group(1), float(m.group(2))
            out_fh.write(json.dumps({
                "resourceMetrics": [{
                    "scopeMetrics": [{
                        "metrics": [{
                            "name": name,
                            "gauge": {
                                "dataPoints": [{
                                    "timeUnixNano": str(ts_ns),
                                    "asDouble":    value,
                                }],
                            },
                        }],
                    }],
                }],
            }) + "\n")
            lines += 1
    _ok(f"converted {lines} samples -> {out}")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Metrics export CLI (F128-F130).")
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prom-snapshot", help="F128 — Prometheus snapshot")
    pp.add_argument("--url", required=True)
    pp.add_argument("--out", default="")
    pt = sub.add_parser("tsdb-bridge", help="F129 — Prom -> InfluxDB")
    pt.add_argument("--input", default="")
    pt.add_argument("--out", default="")
    pt.add_argument("--ts", type=float, default=0.0,
                    help="fixed timestamp (0 = now)")
    po = sub.add_parser("otel-export", help="F130 — Prom -> OTLP JSONL")
    po.add_argument("--input", default="")
    po.add_argument("--out", default="")
    po.add_argument("--ts", type=float, default=0.0)
    return p


HANDLERS = {
    "prom-snapshot": cmd_prom_snapshot,
    "tsdb-bridge":   cmd_tsdb_bridge,
    "otel-export":   cmd_otel_export,
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
