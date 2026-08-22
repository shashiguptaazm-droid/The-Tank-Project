#!/usr/bin/env python3
"""The Tank Project — Prometheus-pull CLI.

Hosts 2 features (F049-F050):

* ``metrics`` — pull `/metrics` from an arbitrary exporter and dump the
                top-N samples that match a regular expression.
* ``health``  — scrape node_exporter + the tank side `/health/prometheus`
                endpoint and surface a `healthy: bool` summary.

Designed for 'is it alive right now' on-call checks.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path



LOG_PREFIX = "[prom]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _http_get_text(url: str, timeout: float = 4.0) -> tuple:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as exc:
        return 0, str(exc)


# ---------------------------------------------------------------------------
# F049 — metrics pull
# ---------------------------------------------------------------------------
def cmd_metrics(args: argparse.Namespace) -> int:
    """F049 — pull /metrics and print matching samples."""
    status, body = _http_get_text(args.url)
    if status != 200:
        _err(f"pull failed (status={status}): {body[:160]}")
        return 1
    pattern = re.compile(args.regex, re.IGNORECASE)
    samples = [line for line in body.splitlines()
               if line and not line.startswith("#") and pattern.search(line)]
    if args.json_out:
        rows = []
        for s in samples:
            name, _, rest = s.partition(" ")
            try:
                rows.append({"name": name, "value": float(rest.strip())})
            except ValueError:
                rows.append({"name": name, "raw": rest.strip()})
        Path(args.json_out).write_text(json.dumps(rows, indent=2))
        _ok(f"wrote {len(rows)} samples -> {args.json_out}")
    for s in samples[:args.top]:
        print(s)
    _ok(f"matched {len(samples)} samples (printed top {args.top})")
    return 0


# ---------------------------------------------------------------------------
# F050 — health scrape
# ---------------------------------------------------------------------------
def cmd_health(args: argparse.Namespace) -> int:
    """F050 — health scrape."""
    summary: dict = {}
    # node_exporter first
    status, body = _http_get_text(args.node_exporter)
    if status == 200:
        summary["node_exporter_up"] = True
        for line in body.splitlines():
            for needle in ("node_cpu_seconds_total", "node_memory_MemAvailable_bytes",
                           "node_filesystem_avail_bytes"):
                if line.startswith(needle) and not line.startswith("#"):
                    value_match = line.split(" ", 1)
                    if len(value_match) == 2:
                        summary.setdefault(needle,
                                           float(value_match[1].strip()))
    else:
        summary["node_exporter_up"] = False
    # tank health
    status, body = _http_get_text(args.tank_health)
    if status == 200:
        summary["tank_health_up"] = True
        _ok(body.strip().splitlines()[0])
    else:
        summary["tank_health_up"] = False
    healthy = (summary.get("node_exporter_up", False)
               and summary.get("tank_health_up", False))
    summary["healthy"] = healthy
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2))
    _ok(json.dumps(summary, indent=2))
    return 0 if healthy else 1


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project Prometheus helpers (F049-F050).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pm = sub.add_parser("metrics", help="F049 — metrics pull")
    pm.add_argument("--url", required=True)
    pm.add_argument("--regex", default=".*")
    pm.add_argument("--top", type=int, default=50)
    pm.add_argument("--json-out", default="")
    ph = sub.add_parser("health", help="F050 — health scrape")
    ph.add_argument("--node-exporter",
                    default="http://tank.lan:9100/metrics")
    ph.add_argument("--tank-health",
                    default="http://tank.lan:8080/health/prometheus")
    ph.add_argument("--out", default="")
    return p


HANDLERS = {
    "metrics": cmd_metrics,
    "health":  cmd_health,
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
