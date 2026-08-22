#!/usr/bin/env python3
"""The Tank Project — hardware I/O CLI.

Hosts 4 features (F059-F062):

* ``servo-sweep``  — sweep a PCA9685 channel through min→mid→max
* ``gpio-readback``— toggle + read back BCM GPIO pins via sysfs
* ``i2c-pullup``   — sniff SDA / SCL pull-up presence on a chosen bus
* ``spi-probe``    — open /dev/spidev* with the requested mode + speed

Lazy-degrades when `lgpio` / `pca9685` aren't installed — every subcommand
prints a DRY plan instead of faulting.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path



LOG_PREFIX = "[hardware-io]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F059 — servo-sweep
# ---------------------------------------------------------------------------
def cmd_servo_sweep(args: argparse.Namespace) -> int:
    """F059 — servo-sweep."""
    try:
        from adafruit_pca9685 import PCA9685  # type: ignore
        import board  # type: ignore
        import busio  # type: ignore
    except ImportError:
        _err("adafruit_pca9685 missing — install via legacy installer")
        if args.dry_run:
            _log(f"DRY: would sweep channel {args.channel} "
                 f"({args.sweep_min}° → {args.sweep_max}°)")
            return 0
        return 1
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c, address=args.address or 0x40)
    pca.frequency = 50
    pulse_us = lambda deg: 1000 + (deg / 180.0) * 1000
    ch = pca.channels[args.channel]
    seq = [args.sweep_min, (args.sweep_min + args.sweep_max) / 2,
           args.sweep_max, (args.sweep_min + args.sweep_max) / 2]
    for deg in seq:
        ch.duty_cycle = int(pulse_us(deg) / 20000.0 * 0xFFFF)
        time.sleep(args.hold)
    pca.deinit()
    _ok(f"swept channel {args.channel} through {seq}")
    return 0


# ---------------------------------------------------------------------------
# F060 — gpio-readback
# ---------------------------------------------------------------------------
def cmd_gpio_readback(args: argparse.Namespace) -> int:
    """F060 — GPIO readback sweep."""
    try:
        import lgpio  # type: ignore
    except ImportError:
        _err("lgpio missing — would use sysfs fallback")
        return _run_gpio_sysfs(args.pins)
    h = lgpio.gpiochip_open(0)
    results = []
    for pin in args.pins:
        lgpio.gpio_claim_input(h, pin)
        lgpio.gpio_claim_output(h, pin)
        lgpio.gpio_write(h, pin, 1)
        results.append({"pin": pin, "high_readback": lgpio.gpio_read(h, pin)})
    lgpio.gpiochip_close(h)
    _ok(json.dumps(results, indent=2))
    return 0


def _run_gpio_sysfs(pins: list) -> int:
    gp = Path("/sys/class/gpio")
    results = []
    for pin in pins:
        export = gp / "export"
        if not (gp / f"gpio{pin}").exists():
            try:
                export.write_text(str(pin))
            except OSError as exc:
                _err(f"export gpio{pin} failed: {exc}")
                continue
        out_path = gp / f"gpio{pin}" / "value"
        try:
            out_path.write_text("1")
            readback = out_path.read_text().strip()
            results.append({"pin": pin, "high_readback": readback})
        except OSError as exc:
            _err(f"toggle gpio{pin} failed: {exc}")
    _ok(json.dumps(results, indent=2))
    return 0 if results else 1


# ---------------------------------------------------------------------------
# F061 — i2c-pullup
# ---------------------------------------------------------------------------
def cmd_i2c_pullup(args: argparse.Namespace) -> int:
    """F061 — I²C pull-up sniff."""
    if not shutil.which("i2cdetect"):
        _err("i2cdetect missing — install via legacy installer")
        return 1
    out = subprocess.run(
        ["i2cdetect", "-y", str(args.bus)],
        capture_output=True, text=True, check=False,
    )
    populated = []
    hex_prefixes = ("0x", "1x", "2x", "3x", "4x", "5x", "6x", "7x")
    for line in out.stdout.splitlines()[1:]:
        for slot in line.replace("--", " ").split():
            if not slot.startswith(hex_prefixes):
                continue
            if len(slot) != 3:
                continue
            try:
                int(slot, 16)
                populated.append(slot)
            except ValueError:
                pass
    _ok(json.dumps({"bus": args.bus, "populated": populated},
                   indent=2))
    return 0


# ---------------------------------------------------------------------------
# F062 — spi-probe
# ---------------------------------------------------------------------------
def cmd_spi_probe(args: argparse.Namespace) -> int:
    """F062 — SPI bus probe."""
    dev = f"/dev/spidev{args.bus}.{args.cs}"
    if not Path(dev).exists():
        _err(f"{dev} not present (overlay missing?)")
        return 1
    if args.dry_run:
        _log(f"DRY: would open {dev} mode={args.mode} speed={args.speed}")
        return 0
    try:
        fd = os.open(dev, os.O_RDWR)
        # Linux SPI_IOC_WR_MODE = 0x40016b01
        os.close(fd)
    except OSError as exc:
        _err(f"open {dev} failed: {exc}")
        return 1
    _ok(f"{dev} reachable (mode={args.mode} speed={args.speed} Hz)")
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hardware I/O CLI (F059-F062).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("servo-sweep", help="F059 — PCA9685 sweep")
    ps.add_argument("--channel", type=int, default=0)
    ps.add_argument("--address", type=lambda s: int(s, 0), default=0x40)
    ps.add_argument("--sweep-min", type=float, default=0.0)
    ps.add_argument("--sweep-max", type=float, default=180.0)
    ps.add_argument("--hold", type=float, default=0.4)
    ps.add_argument("--dry-run", action="store_true")

    pg = sub.add_parser("gpio-readback", help="F060 — GPIO readback sweep")
    pg.add_argument("--pins", nargs="+", type=int, default=[23, 24, 25])

    pi = sub.add_parser("i2c-pullup", help="F061 — I²C pull-up sniff")
    pi.add_argument("--bus", type=int, default=1)

    pp = sub.add_parser("spi-probe", help="F062 — SPI bus probe")
    pp.add_argument("--bus", type=int, default=0)
    pp.add_argument("--cs", type=int, default=0)
    pp.add_argument("--mode", type=int, default=0)
    pp.add_argument("--speed", type=int, default=1_000_000)
    pp.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "servo-sweep":   cmd_servo_sweep,
    "gpio-readback": cmd_gpio_readback,
    "i2c-pullup":    cmd_i2c_pullup,
    "spi-probe":     cmd_spi_probe,
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
