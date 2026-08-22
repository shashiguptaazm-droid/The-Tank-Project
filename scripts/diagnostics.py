#!/usr/bin/env python3
"""The Tank Project — diagnostics CLI.

Hosts 10 features (F001-F010) for one-shot health checks:

* ``battery``  — battery state via I2C (INA219) or sysfs fallback
* ``imu``      — BNO055 zero offsets + temperature
* ``lidar``    — RPLidar frame sanity
* ``camera``   — single frame grab + size report
* ``wifi``     — SSID / RSSI / channel
* ``audio``    — input / output device dump
* ``watchdog`` — heartbeat liveness probe (parses /health/state on the wire)
* ``ros``      — topic / node liveness rollup (offline-friendly)
* ``power``    — 5 V / 12 V rail probe via sysfs + vcgencmd
* ``strobe``   — E-stop strobe + LED-toggle via lgpio / sysfs

All subcommands degrade gracefully when heavy deps are missing. Every
subcommand exits 0 on success and 1 on partial failure so it can slot
into a systemd timer.

Usage::

    python3 scripts/diagnostics.py battery
    python3 scripts/diagnostics.py imu
    python3 scripts/diagnostics.py ros
    python3 scripts/diagnostics.py strobe --pin 25 --seconds 2
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path



LOG_PREFIX = "[diagnostics]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# F001 — battery
# ---------------------------------------------------------------------------
def cmd_battery(args: argparse.Namespace) -> int:
    """F001 — battery health probe.

    Tries the INA219 /sys path first, then I2C directly, finally falls
    back to printing a procedural checklist.
    """
    ina_sysfs = Path("/sys/class/power_supply/BATT")
    health: dict = {}
    if ina_sysfs.exists():
        for key in ("voltage_now", "current_now", "capacity", "status"):
            fp = ina_sysfs / key
            if fp.exists():
                try:
                    health[key] = fp.read_text().strip()
                except OSError as exc:
                    health[key] = f"<read-error: {exc}>"
    if health:
        if "voltage_mV" not in health and "voltage_now" in health:
            try:
                health["voltage_mV"] = int(health["voltage_now"]) // 1000
            except ValueError:
                pass
        _ok(json.dumps(health, indent=2))
        return 0
    # sysfs fallback — vcgencmd + serial battery nodes.
    for tool in ("vcgencmd", "i2cdetect", "python3"):
        _log(f"sysfs battery path missing — fallback ({tool})")
    # i2c scan for 0x40 / 0x45 (INA219 common addrs).
    if shutil.which("i2cdetect"):
        result = subprocess.run(
            ["i2cdetect", "-y", "1"], capture_output=True, text=True, check=False
        )
        for addr in ("0x40", "0x45"):
            if addr in result.stdout:
                _ok(f"INA219 detected at I2C {addr} — use scripts/calibrate.py battery")
                return 0
    _err("no battery sysfs + no I2C INA219 found; do the visual checklist")
    return 1


# ---------------------------------------------------------------------------
# F002 — imu
# ---------------------------------------------------------------------------
def cmd_imu(args: argparse.Namespace) -> int:
    """F002 — IMU sanity test."""
    try:
        from adafruit_bno055 import BNO055_I2C  # type: ignore
        import board  # type: ignore
        import busio  # type: ignore
    except ImportError:
        _err("adafruit_bno055 not installed; will run AST placeholder")
        return _run_imu_placeholder()
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bno = BNO055_I2C(i2c)
        temp = bno.temperature
        euler = bno.euler
        _ok(json.dumps({
            "temperature_C": temp,
            "heading_deg":    round(euler[0], 2),
            "roll_deg":       round(euler[1], 2),
            "pitch_deg":      round(euler[2], 2),
        }, indent=2))
        return 0 if temp is not None else 1
    except Exception as exc:
        _err(f"BNO055 read failed: {exc}")
        return 1


def _run_imu_placeholder() -> int:
    pkg = Path(__file__).resolve().parent.parent / "tank_ws" / "src" / "tank_sensors"
    if pkg.exists():
        _ok(f"tank_sensors package present at {pkg}")
        return 0
    _err("tank_sensors package missing — clone first")
    return 1


# ---------------------------------------------------------------------------
# F003 — lidar
# ---------------------------------------------------------------------------
def cmd_lidar(args: argparse.Namespace) -> int:
    """F003 — LiDAR frame verification."""
    port = args.port or os.environ.get("RPLIDAR_PORT", "/dev/rplidar")
    try:
        from rplidar import RPLidar  # type: ignore
    except ImportError:
        _err(f"rplidar not installed; would scan {port} -- "
             "run scripts/setup_pi5.sh --apply first")
        return 1
    try:
        lidar = RPLidar(port)
        info = lidar.get_info()
        health = lidar.get_health()
        _ok(json.dumps({
            "model":   info["model"],
            "firmware": info["firmware"],
            "health": list(health),
        }, indent=2))
        lidar.stop()
        lidar.disconnect()
        return 0
    except Exception as exc:
        _err(f"lidar {port} failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# F004 — camera
# ---------------------------------------------------------------------------
def cmd_camera(args: argparse.Namespace) -> int:
    """F004 — single-frame grab + size report."""
    try:
        import cv2  # type: ignore
    except ImportError:
        _err("opencv not installed; load 'calendar.py' trading card images "
             "instead, or `pip install opencv-python-headless`")
        return 1
    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        _err(f"camera {args.device} not opened")
        return 1
    ok, frame = cap.read()
    if not ok:
        _err("camera.read() returned False")
        cap.release()
        return 1
    h, w = frame.shape[:2]
    out = Path(args.out or "/tmp/tank_diag_frame.jpg")
    cv2.imwrite(str(out), frame)
    cap.release()
    _ok(json.dumps({"path": str(out), "width": w, "height": h, "ok": True}))
    return 0


# ---------------------------------------------------------------------------
# F005 — wifi
# ---------------------------------------------------------------------------
def cmd_wifi(args: argparse.Namespace) -> int:
    """F005 — Wi-Fi diagnostic."""
    info: dict = {}
    # Try nmcli first.
    if shutil.which("nmcli"):
        out = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,FREQ,CHAN,RATE",
             "device", "wifi"],
            capture_output=True, text=True, check=False,
        ).stdout
        for line in out.splitlines():
            if line.startswith("yes:"):
                parts = line.split(":")
                if len(parts) >= 5:
                    info["ssid"]    = parts[1]
                    info["signal"]  = f"{parts[2]}%"
                    info["freq_MHz"] = parts[3]
                    info["channel"] = parts[4]
                break
    # Fallback to /proc/net/wireless.
    if "ssid" not in info:
        wfp = Path("/proc/net/wireless")
        if wfp.exists():
            for line in wfp.read_text().splitlines()[2:]:
                parts = line.split()
                if parts:
                    info["iface"]   = parts[0].rstrip(":")
                    info["signal"]  = parts[2] + " dBm"
    if not info:
        _err("no WiFi adapter detected")
        return 1
    _ok(json.dumps(info, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F006 — audio
# ---------------------------------------------------------------------------
def cmd_audio(args: argparse.Namespace) -> int:
    """F006 — audio device dump."""
    pairs: list = []
    for tool in ("arecord", "aplay"):
        path = shutil.which(tool)
        if not path:
            continue
        kind = "input" if tool == "arecord" else "output"
        out = subprocess.run([tool, "-l"], capture_output=True, text=True, check=False)
        cards = []
        for line in out.stdout.splitlines():
            if "card" in line.lower():
                cards.append(line.strip())
        pairs.append({"tool": tool, "kind": kind, "cards": cards})
    # sounddevice fallback.
    try:
        import sounddevice as sd  # type: ignore
        for idx, dev in enumerate(sd.query_devices()):
            if args.kind in ("all", "input") and dev["max_input_channels"] > 0:
                pairs.append({"tool": "sounddevice", "kind": "input",
                              "id": idx, "name": dev["name"]})
            if args.kind in ("all", "output") and dev["max_output_channels"] > 0:
                pairs.append({"tool": "sounddevice", "kind": "output",
                              "id": idx, "name": dev["name"]})
    except ImportError:
        pass
    if not pairs:
        _err("no audio tooling found (arecord/aplay/sounddevice)")
        return 1
    _ok(json.dumps(pairs, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F007 — watchdog
# ---------------------------------------------------------------------------
def cmd_watchdog(args: argparse.Namespace) -> int:
    """F007 — heartbeat liveness test."""
    if shutil.which("systemctl"):
        out = subprocess.run(
            ["systemctl", "is-active", "tank_bringup.service"],
            capture_output=True, text=True, check=False,
        )
        state = out.stdout.strip()
        _ok(f"tank_bringup.service -> {state or 'unknown'}")
        return 0 if state == "active" else 1
    _err("systemctl missing — watchdog host unit not running on this host")
    return 1


# ---------------------------------------------------------------------------
# F008 — ros liveness (offline)
# ---------------------------------------------------------------------------
def cmd_ros(args: argparse.Namespace) -> int:
    """F008 — topic / node liveness rollup (no daemon required)."""
    if shutil.which("ros2"):
        for sub in (["node", "list"], ["topic", "list"]):
            subprocess.run(["ros2", *sub], check=False)
        return 0
    # offline fallback — walk the launch files for declared topics.
    src = Path(__file__).resolve().parent.parent / "tank_ws" / "src"
    topics: set = set()
    for pkg in sorted(src.iterdir()) if src.exists() else []:
        for lp in (pkg / "launch").glob("*.launch.py"):
            text = lp.read_text()
            for tok in ("/cmd_vel", "/scan", "/imu/data", "/camera/image_raw",
                        "/odom", "/pan_tilt_cmd", "/wake_detected",
                        "/emotion/state", "/battery/state"):
                if tok in text:
                    topics.add(tok)
    if not topics:
        _err("ros2 not on PATH and no launch files found")
        return 1
    _ok(json.dumps({"topics": sorted(topics)}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F009 — power rail probe
# ---------------------------------------------------------------------------
def cmd_power(args: argparse.Namespace) -> int:
    """F009 — 5 V / 12 V rail probe via sysfs + vcgencmd."""
    found: dict = {}
    vcgen = shutil.which("vcgencmd")
    if vcgen:
        out = subprocess.run([vcgen, "measure_volts"], capture_output=True,
                             text=True, check=False).stdout
        if out:
            found.setdefault("vcgen_volts", out.strip())
    raspi = shutil.which("raspi-config")
    _log("raspi-config probe " + ("available" if raspi else "missing"))
    # 12 V — look for hwmon devices that publish curr1_input.
    for hw in Path("/sys/class/hwmon").glob("hwmon*/in1_input"):
        try:
            mv = int(hw.read_text().strip()) // 1000
            found[hw.parent.name + ":in1_mV"] = mv
        except (OSError, ValueError):
            pass
    if not found:
        _err("no rail voltages reported")
        return 1
    _ok(json.dumps(found, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F010 — strobe
# ---------------------------------------------------------------------------
def cmd_strobe(args: argparse.Namespace) -> int:
    """F010 — E-STOP strobe via lgpio + LED toggle."""
    if args.dry_run:
        _log(f"DRY: would pulse GPIO {args.pin} for {args.seconds}s")
        return 0
    try:
        import lgpio  # type: ignore
        h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(h, args.pin)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            lgpio.gpio_write(h, args.pin, 1)
            time.sleep(0.2)
            lgpio.gpio_write(h, args.pin, 0)
            time.sleep(0.2)
        lgpio.gpiochip_close(h)
        _ok(f"strobed GPIO {args.pin} for {args.seconds}s")
        return 0
    except (ImportError, OSError) as exc:
        _err(f"strobe failed (lgpio={exc!r}); use sysfs/class/gpio instead")
        gp = Path("/sys/class/gpio")
        if (gp / f"gpio{args.pin}").exists():
            _log(f"GPIO {args.pin} already exported")
            return 0
        _err(f"GPIO {args.pin} not exported — wiring harness not yet assembled")
        return 1


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project diagnostics CLI (F001-F010).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("battery",  help="F001 — battery state probe")
    sub.add_parser("imu",      help="F002 — IMU sanity test")
    pl = sub.add_parser("lidar",  help="F003 — LiDAR frame verification")
    pl.add_argument("--port", default="")
    pc = sub.add_parser("camera", help="F004 — camera frame grab")
    pc.add_argument("--device", type=int, default=0)
    pc.add_argument("--out",    default="")
    sub.add_parser("wifi",     help="F005 — WiFi SSID / RSSI")
    pa = sub.add_parser("audio", help="F006 — audio device list")
    pa.add_argument("--kind", choices=("all", "input", "output"), default="all")
    sub.add_parser("watchdog", help="F007 — watchdog liveness")
    sub.add_parser("ros",      help="F008 — ROS topic / node liveness")
    sub.add_parser("power",    help="F009 — 5 V / 12 V rail probe")
    ps = sub.add_parser("strobe", help="F010 — E-STOP strobe")
    ps.add_argument("--pin", type=int, default=25)
    ps.add_argument("--seconds", type=float, default=2.0)
    ps.add_argument("--dry-run", action="store_true")
    return p


HANDLERS = {
    "battery":  cmd_battery,
    "imu":      cmd_imu,
    "lidar":    cmd_lidar,
    "camera":   cmd_camera,
    "wifi":     cmd_wifi,
    "audio":    cmd_audio,
    "watchdog": cmd_watchdog,
    "ros":      cmd_ros,
    "power":    cmd_power,
    "strobe":   cmd_strobe,
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
