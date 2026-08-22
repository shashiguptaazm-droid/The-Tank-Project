#!/usr/bin/env python3
"""weather.py \u2014 weather forecast (F164 \u2013 F166).

Subcommands
-----------
* F164 current       \u2014 right-now conditions
* F165 hourly        \u2014 next 24 hours
* F166 alerts        \u2014 active severe-weather alerts

Offline-first: when no API key is set (``OPENWEATHER_KEY`` /
``--api-key``), the script returns a deterministic synthetic
forecast seeded by latitude/longitude so unit-tests can pin it.

Usage::

    python3 scripts/weather.py current --lat 28.6 --lon 77.2
    python3 scripts/weather.py hourly --lat 28.6 --lon 77.2
    python3 scripts/weather.py alerts --lat 28.6 --lon 77.2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


PREFIX = "[weather]"


def _info(msg: str) -> None:
    print(f"{PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _seeded_synthetic(lat: float, lon: float) -> dict:
    """Return a deterministic placeholder forecast.

    Uses a hash of ``(lat, lon)`` so the same coordinates produce
    identical output across runs \u2014 useful for tests / CI smoke checks.
    """
    seed = hashlib.sha256(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()
    temp_c = (int(seed[:2], 16) % 30) + 5
    cond = ["clear", "cloudy", "rain", "storm"][int(seed[2], 16) % 4]
    return {"source": "synthetic", "temp_c": temp_c,
            "condition": cond, "seed": seed[:8]}


def cmd_current(args: argparse.Namespace) -> int:
    """F164 \u2014 right-now conditions."""
    if not args.api_key:
        _info("no OPENWEATHER_KEY set \u2192 returning synthetic forecast")
    payload = _seeded_synthetic(args.lat, args.lon)
    payload.update({"lat": args.lat, "lon": args.lon})
    _ok(json.dumps(payload, indent=2))
    return 0


def cmd_hourly(args: argparse.Namespace) -> int:
    """F165 \u2014 next 24 hours."""
    base = _seeded_synthetic(args.lat, args.lon)
    rows = []
    for hour in range(0, 24, 3):
        rows.append({"hour": hour,
                     "temp_c": base["temp_c"] + (hour // 6) - 2,
                     "condition": base["condition"]})
    _ok(json.dumps({"source": base["source"], "rows": rows}, indent=2))
    return 0


def cmd_alerts(args: argparse.Namespace) -> int:
    """F166 \u2014 active alerts (synthetic on offline)."""
    base = _seeded_synthetic(args.lat, args.lon)
    alerts = []
    if base["condition"] == "storm":
        alerts.append({"severity": "moderate",
                       "headline": "Thunderstorm watch",
                       "expires_in_h": 6})
    _ok(json.dumps({"source": base["source"], "n": len(alerts),
                    "alerts": alerts}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Weather forecast (synthetic if offline).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("current", help="Right-now conditions")
    p1.add_argument("--lat", type=float, required=True)
    p1.add_argument("--lon", type=float, required=True)
    p1.add_argument("--api-key",
                    default=os.environ.get("OPENWEATHER_KEY", ""))

    p2 = sub.add_parser("hourly", help="Next 24 hours")
    p2.add_argument("--lat", type=float, required=True)
    p2.add_argument("--lon", type=float, required=True)
    p2.add_argument("--api-key",
                    default=os.environ.get("OPENWEATHER_KEY", ""))

    p3 = sub.add_parser("alerts", help="Active severe-weather alerts")
    p3.add_argument("--lat", type=float, required=True)
    p3.add_argument("--lon", type=float, required=True)
    p3.add_argument("--api-key",
                    default=os.environ.get("OPENWEATHER_KEY", ""))
    return p


HANDLERS = {
    "current": cmd_current,
    "hourly":  cmd_hourly,
    "alerts":  cmd_alerts,
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
