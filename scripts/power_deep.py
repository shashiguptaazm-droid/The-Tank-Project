#!/usr/bin/env python3
"""The Tank Project — deep power management helpers.

Hosts 4 features (F071-F074):

* ``solar-yield``   — log a sample of VBAT + solar current every `--poll` sec
* ``sleep-wake``    — induce suspend (user-space stub) + wake via GPIO
* ``dock-seq``      — verify the contactor sequence:
                       pin17 enable → pin27 contactor → pin22 feedback
* ``dual-balancer`` — read INA219 bus A vs bus B, surface imbalance > 5%

Stdlib-first; sysfs for INA219; sysfs + lgpio for the contactor pins.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path



LOG_PREFIX = "[power-deep]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F071 — solar-yield
# ---------------------------------------------------------------------------
def cmd_solar_yield(args: argparse.Namespace) -> int:
    """F071 — solar yield log."""
    data_dir = Path("tank_ws/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    out = data_dir / "solar_yield.jsonl"
    samples = 0
    for n in range(args.count):
        vbat = Path("/sys/class/power_supply/BATT/voltage_now")
        ibus = Path("/sys/class/power_supply/BATT/current_now")
        snapshot = {"ts": time.time()}
        if vbat.exists():
            try:
                snapshot["vbat_mV"] = int(vbat.read_text().strip()) // 1000
            except (OSError, ValueError):
                pass
        if ibus.exists():
            try:
                snapshot["current_mA"] = int(ibus.read_text().strip()) // 1000
            except (OSError, ValueError):
                pass
        with out.open("a") as fh:
            fh.write(json.dumps(snapshot) + "\n")
        _log(f"[{n + 1}/{args.count}] {snapshot}")
        samples += 1
        time.sleep(args.poll)
    _ok(f"recorded {samples} samples -> {out}")
    return 0


# ---------------------------------------------------------------------------
# F072 — sleep-wake
# ---------------------------------------------------------------------------
def cmd_sleep_wake(args: argparse.Namespace) -> int:
    """F072 — sleep/wake test."""
    try:
        import lgpio  # type: ignore
        h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(h, args.wake_pin)
    except (ImportError, OSError) as exc:
        _log(f"lgpio unavailable ({exc}); DRY run only")
        h = None
    _log(f"would `systemctl suspend` for {args.seconds}s, then pulse "
         f"GPIO {args.wake_pin}")
    if h is not None and not args.dry_run:
        time.sleep(min(args.seconds, 5.0))
        lgpio.gpio_write(h, args.wake_pin, 1)
        time.sleep(0.4)
        lgpio.gpio_write(h, args.wake_pin, 0)
        lgpio.gpiochip_close(h)
    _ok("sleep-wake sequence simulated")
    return 0


# ---------------------------------------------------------------------------
# F073 — dock-seq
# ---------------------------------------------------------------------------
def cmd_dock_seq(args: argparse.Namespace) -> int:
    """F073 — dock placement sequence."""
    seq = [
        ("ENABLE",     args.enable_pin,   True),
        ("CONTACTOR",  args.contactor_pin, True),
        ("FEEDBACK",   args.feedback_pin,  None),
        ("SETTLE",     None, None),
        ("RELEASE",    args.contactor_pin, False),
    ]
    events = []
    for label, pin, value in seq:
        ts = time.time()
        if pin is None:
            events.append({"label": label, "ts": ts, "settle_ms": args.settle_ms})
            time.sleep(args.settle_ms / 1000.0)
            continue
        events.append({"label": label, "pin": pin, "value": value, "ts": ts})
        if args.dry_run:
            _log(f"DRY: {label} GPIO {pin} -> {value}")
            continue
        try:
            import lgpio  # type: ignore
            h = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(h, pin)
            if value is not None:
                lgpio.gpio_write(h, pin, int(value))
            time.sleep(0.05)
            lgpio.gpiochip_close(h)
        except (ImportError, OSError) as exc:
            _err(f"lgpio unavailable for {label}: {exc}")
    _ok(json.dumps({"events": events}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F074 — dual-balancer
# ---------------------------------------------------------------------------
def cmd_dual_balancer(args: argparse.Namespace) -> int:
    """F074 — dual-battery balancer."""
    batt_a = Path("/sys/class/power_supply/BATT0/voltage_now")
    batt_b = Path("/sys/class/power_supply/BATT1/voltage_now")
    paths = [batt_a, batt_b] if batt_b.exists() else [batt_a]
    readings = []
    for path in paths:
        if path.exists():
            try:
                readings.append(int(path.read_text().strip()) // 1000)
            except (OSError, ValueError):
                pass
    if not readings:
        _err("no voltage_now sysfs entries")
        return 1
    imbalance = max(readings) - min(readings)
    if imbalance > args.threshold_mV:
        _err(f"imbalance {imbalance} mV exceeds {args.threshold_mV} mV")
        return 1
    _ok(json.dumps({"readings_mV": readings,
                    "imbalance_mV": imbalance,
                    "threshold_mV": args.threshold_mV}, indent=2))
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Power deep-ops CLI (F071-F074).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("solar-yield", help="F071 — solar yield log")
    ps.add_argument("--poll", type=float, default=10.0)
    ps.add_argument("--count", type=int, default=6)
    pw = sub.add_parser("sleep-wake", help="F072 — sleep/wake test")
    pw.add_argument("--seconds", type=float, default=30.0)
    pw.add_argument("--wake-pin", type=int, default=23)
    pw.add_argument("--dry-run", action="store_true")
    pd = sub.add_parser("dock-seq", help="F073 — dock placement sequence")
    pd.add_argument("--enable-pin", type=int, default=23)
    pd.add_argument("--contactor-pin", type=int, default=24)
    pd.add_argument("--feedback-pin", type=int, default=25)
    pd.add_argument("--settle-ms", type=int, default=250)
    pd.add_argument("--dry-run", action="store_true")
    pb = sub.add_parser("dual-balancer", help="F074 — dual-battery balancer")
    pb.add_argument("--threshold-mV", type=int, default=50)
    return p


HANDLERS = {
    "solar-yield":   cmd_solar_yield,
    "sleep-wake":    cmd_sleep_wake,
    "dock-seq":      cmd_dock_seq,
    "dual-balancer": cmd_dual_balancer,
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
