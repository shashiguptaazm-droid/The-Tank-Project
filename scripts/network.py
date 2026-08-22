#!/usr/bin/env python3
"""The Tank Project — network CLI.

Hosts 3 features (F024-F026):

* ``wifi``      — latency probe + AP scan via /proc/net/wireless
* ``bandwidth`` — periodic throughput sampler (icmp ping torrent of packets)
* ``vpn-lte``   — probe WireGuard / Tailscale / LTE interfaces

All operations are stdlib-only so the file works on a freshly-imaged Pi.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path



LOG_PREFIX = "[network]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F024 — wifi diag
# ---------------------------------------------------------------------------
def cmd_wifi(args: argparse.Namespace) -> int:
    """F024 — AP scan + latency probe."""
    info: dict = {"interfaces": [], "latency_ms": {}}
    # -- interface presence
    if Path("/proc/net/wireless").exists():
        for line in Path("/proc/net/wireless").read_text().splitlines()[2:]:
            parts = line.split()
            if parts:
                info["interfaces"].append({
                    "iface": parts[0].rstrip(":"),
                    "signal_dbm": parts[2],
                    "quality": parts[1].rstrip("."),
                })
    # -- latency
    if shutil.which("ping"):
        for host in args.probe:
            try:
                out = subprocess.run(
                    ["ping", "-c", "3", "-W", "2", host],
                    capture_output=True, text=True, check=False,
                )
                ms = [float(line.split("=")[-1].split()[0])
                      for line in out.stdout.splitlines()
                      if line.strip().startswith("time=")]
                if ms:
                    info["latency_ms"][host] = {
                        "avg":  round(statistics.mean(ms), 2),
                        "max":  max(ms),
                        "loss_pct": out.stdout.count("100% packet loss"),
                    }
            except Exception as exc:  # pragma: no cover
                info["latency_ms"][host] = {"error": str(exc)}
    if not info["interfaces"] and "error" not in info["latency_ms"]:
        _err("no Wi-Fi interfaces nor ping data collected")
        return 1
    _ok(json.dumps(info, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F025 — bandwidth sampler
# ---------------------------------------------------------------------------
def cmd_bandwidth(args: argparse.Namespace) -> int:
    """F025 — periodic rx/tx byte counter via /proc/net/dev."""
    rx_path = Path("/proc/net/dev")
    if not rx_path.exists():
        _err("/proc/net/dev missing — Linux-only")
        return 1
    def snap() -> dict:
        out = {}
        for line in rx_path.read_text().splitlines()[2:]:
            if ":" not in line:
                continue
            iface, rest = line.split(":", 1)
            iface = iface.strip()
            if iface not in args.iface:
                continue
            fields = rest.split()
            try:
                out[iface] = {
                    "rx_bytes": int(fields[0]),
                    "tx_bytes": int(fields[8]),
                }
            except (ValueError, IndexError):
                continue
        return out

    a = snap()
    series = []
    for n in range(args.count):
        time.sleep(args.every)
        b = snap()
        diff = {}
        for iface in (set(a) & set(b)):
            diff[iface] = {
                "rx_B_s":  (b[iface]["rx_bytes"] - a[iface]["rx_bytes"]) / args.every,
                "tx_B_s":  (b[iface]["tx_bytes"] - a[iface]["tx_bytes"]) / args.every,
            }
        series.append({"ts": time.time(), "delta": diff})
        _log(f"[{n + 1}/{args.count}] {diff}")
        a = b
    _ok(json.dumps({"iface_filter": args.iface, "samples": series}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F026 — vpn + lte probe
# ---------------------------------------------------------------------------
def cmd_vpn_lte(args: argparse.Namespace) -> int:
    """F026 — probe WireGuard, Tailscale, and LTE interfaces."""
    info: dict = {}
    # -- WireGuard
    wg = shutil.which("wg")
    if wg:
        out = subprocess.run([wg, "show"], capture_output=True, text=True,
                             check=False)
        info["wireguard"] = out.stdout.strip() or "<no peers>"
    else:
        info["wireguard"] = "wg binary missing"
    # -- Tailscale
    ts = shutil.which("tailscale")
    if ts:
        out = subprocess.run([ts, "status"], capture_output=True, text=True,
                             check=False)
        info["tailscale"] = out.stdout.strip().splitlines()[:3]
    else:
        info["tailscale"] = "tailscale CLI missing"
    # -- LTE: any interface named wwan0/wwpns0?
    try:
        devs = [d for d in Path("/sys/class/net").iterdir()
                if d.name.startswith(("wwan", "wwpns", "usb", "wwan0"))]
        info["lte_interfaces"] = [d.name for d in devs]
    except OSError:
        info["lte_interfaces"] = "<sysfs missing>"
    _ok(json.dumps(info, indent=2))
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project network CLI (F024-F026).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("wifi", help="F024 — AP scan + latency probe")
    pw.add_argument("--probe", nargs="*",
                    default=["1.1.1.1", "8.8.8.8", "tank.lan"])
    pb = sub.add_parser("bandwidth", help="F025 — bandwidth periodic sampler")
    pb.add_argument("--every", type=float, default=2.0)
    pb.add_argument("--count", type=int, default=5)
    pb.add_argument("--iface", nargs="*",
                    default=["wlan0", "eth0", "tailscale0", "wwan0"])
    sub.add_parser("vpn-lte", help="F026 — WireGuard + tailscale + LTE probe")
    return p


HANDLERS = {
    "wifi":      cmd_wifi,
    "bandwidth": cmd_bandwidth,
    "vpn-lte":   cmd_vpn_lte,
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
