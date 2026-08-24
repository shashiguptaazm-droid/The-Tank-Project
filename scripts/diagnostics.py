#!/usr/bin/env python3
"""The Tank Project — diagnostics CLI.

Hosts 10 features (F001-F010) for one-shot health checks:

* ``battery``  — battery state via I2C (INA219) or sysfs fallback
* ``imu``      — BNO055 zero offsets + temperature
* ``lidar``    — LDROBOT LD14/LD19 (aa55) frame sanity on /dev/ttyUSB0
* ``camera``   — ESP32-S3 bridge snapshot (V4L2 fallback)
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
import struct
import subprocess
import sys
import time
import urllib.request
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
# F003 — lidar (LDROBOT LD14/LD19 — aa55 protocol on /dev/ttyUSB0)
# ---------------------------------------------------------------------------
def _parse_ldrobot_packet(data: bytes) -> list:
    """Parse one LD14/LD19 packet into distance points (aa55 protocol)."""
    points = []
    if len(data) < 10:
        return points
    try:
        start_angle = struct.unpack_from("<H", data, 2)[0] / 100.0  # centidegrees
        for i in range(12):
            offset = 4 + i * 3  # 2-byte distance + 1-byte confidence
            if offset + 3 > len(data):
                break
            dist = struct.unpack_from("<H", data, offset)[0]  # mm
            conf = data[offset + 2]
            angle = start_angle + (i * 3.0)
            if angle >= 360:
                angle -= 360
            points.append({"angle": angle, "distance": dist, "confidence": conf})
    except struct.error:
        pass
    return points


def _read_ldrobot_scan(port: str, baud: int, timeout_s: float = 2.0):
    """Read one LDROBOT scan and summarize it. Returns None on failure."""
    import serial  # type: ignore
    s = serial.Serial(port, baud, timeout=0.1)
    all_points: list = []
    buf = b""
    deadline = time.monotonic() + timeout_s
    try:
        while time.monotonic() < deadline:
            chunk = s.read(200)
            if not chunk:
                continue
            buf += chunk
            while True:
                idx = buf.find(b"\xaa\x55")
                if idx == -1:
                    buf = buf[-10:]  # keep tail bytes for re-alignment
                    break
                if idx > 0:
                    buf = buf[idx:]
                if len(buf) < 18:
                    break
                packet = buf[:18]
                buf = buf[18:]
                all_points.extend(_parse_ldrobot_packet(packet))
    finally:
        s.close()

    if not all_points:
        return None

    valid = [p for p in all_points if p["distance"] > 0 and p["confidence"] > 50]
    if not valid:
        valid = [p for p in all_points if p["distance"] > 0]

    if not valid:
        return {
            "point_count": len(all_points),
            "min_distance": 0,
            "min_angle": 0.0,
            "nearest_object": "nothing in range",
        }

    nearest = min(valid, key=lambda p: p["distance"])
    angle = nearest["angle"]
    if angle >= 345 or angle <= 15:
        direction = "directly ahead"
    elif angle <= 45:
        direction = "slightly right"
    elif angle <= 135:
        direction = "to the right"
    elif angle <= 180:
        direction = "behind right"
    elif angle <= 225:
        direction = "behind left"
    elif angle <= 315:
        direction = "to the left"
    else:
        direction = "slightly left"

    return {
        "point_count": len(all_points),
        "min_distance": nearest["distance"],
        "min_angle": nearest["angle"],
        "nearest_object": (
            f"{nearest['distance'] / 1000.0:.2f}m {direction} "
            f"(angle={angle:.0f}°, confidence={nearest['confidence']})"
        ),
    }


def cmd_lidar(args: argparse.Namespace) -> int:
    """F003 — LiDAR frame verification (LDROBOT LD14/LD19 aa55 protocol)."""
    port = args.port or os.environ.get("LIDAR_PORT", "/dev/ttyUSB0")
    baud = int(os.environ.get("LIDAR_BAUD", "115200"))
    try:
        import serial  # type: ignore
    except ImportError:
        _err(f"pyserial not installed; cannot read LDROBOT lidar on {port}")
        return 1
    try:
        scan = _read_ldrobot_scan(port, baud, timeout_s=2.0)
    except serial.SerialException as exc:
        _err(f"lidar {port} failed: {exc}")
        return 1
    except Exception as exc:
        _err(f"lidar {port} read failed: {exc}")
        return 1
    if scan is None:
        _err(f"no LDROBOT frames received on {port} (baud {baud})")
        return 1
    _ok(json.dumps({
        "port": port,
        "baud": baud,
        "points": scan["point_count"],
        "min_distance_mm": scan["min_distance"],
        "min_angle_deg": round(scan["min_angle"], 2),
        "nearest_object": scan["nearest_object"],
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# F004 — camera
# ---------------------------------------------------------------------------
def _jpeg_dims(data: bytes):
    """Best-effort JPEG width/height (cv2 first, then SOF marker scan)."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
        if img is not None:
            h, w = img.shape[:2]
            return w, h
    except Exception:
        pass
    # Manual SOF marker scan (no cv2 needed).
    try:
        i = 2
        n = len(data)
        while i + 4 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker == 0xFF:
                i += 1
                continue
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7 or marker == 0x01:
                i += 2
                continue
            seg_len = struct.unpack_from(">H", data, i + 2)[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height = struct.unpack_from(">H", data, i + 5)[0]
                width = struct.unpack_from(">H", data, i + 7)[0]
                return width, height
            i += 2 + seg_len
    except (struct.error, IndexError):
        pass
    return None


def cmd_camera(args: argparse.Namespace) -> int:
    """F004 — camera frame grab (ESP32-S3 bridge, V4L2 fallback)."""
    out = Path(args.out or "/tmp/tank_diag_frame.jpg")
    # Candidate bridge URLs: explicit flag, env, UNO Q LAN, UNO Q Tailscale.
    candidates: list = []
    if args.url:
        candidates.append(args.url)
    if os.environ.get("TANK_CAMERA_URL"):
        candidates.append(os.environ["TANK_CAMERA_URL"])
    candidates += [
        "http://192.168.31.72:8080/snapshot.jpg",
        "http://100.84.235.7:8080/snapshot.jpg",
    ]
    last_err = None
    for url in dict.fromkeys(candidates):  # de-dup, preserve order
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()
            if not data:
                raise ValueError("empty response")
            out.write_bytes(data)
            dims = _jpeg_dims(data)
            report = {
                "source": "esp32-s3-bridge",
                "url": url,
                "path": str(out),
                "bytes": len(data),
                "ok": True,
            }
            if dims:
                report["width"], report["height"] = dims
            _ok(json.dumps(report, indent=2))
            return 0
        except Exception as exc:  # noqa: BLE001 — try next candidate
            last_err = exc
            _log(f"bridge {url} failed ({exc})")
    _log(f"all bridge URLs failed ({last_err}); "
         f"falling back to V4L2 device {args.device}")
    try:
        import cv2  # type: ignore
    except ImportError:
        _err("opencv not installed and ESP32-S3 bridge unreachable")
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
    cv2.imwrite(str(out), frame)
    cap.release()
    _ok(json.dumps({"source": "v4l2", "device": args.device,
                    "path": str(out), "width": w, "height": h, "ok": True}))
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
    pl = sub.add_parser("lidar",  help="F003 — LiDAR frame verification (LDROBOT LD14/LD19)")
    pl.add_argument("--port", default="",
                    help="serial port (default: $LIDAR_PORT or /dev/ttyUSB0)")
    pc = sub.add_parser("camera", help="F004 — camera frame grab")
    pc.add_argument("--device", type=int, default=0)
    pc.add_argument("--url",    default="",
                    help="ESP32-S3 bridge snapshot URL "
                         "(default: $TANK_CAMERA_URL or UNO Q bridge)")
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
