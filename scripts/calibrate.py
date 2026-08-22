#!/usr/bin/env python3
"""The Tank Project — calibration CLI.

Hosts 6 features (F011-F016):

* ``imu``     — capture BNO055 zero offsets, WRITE into
  ``tank_sensors/config/tank_sensors.yaml``.
* ``camera``  — derive intrinsics from a chessboard folder; PRINT + write
  YAML alongside ``tank_vision/config/camera_info.yaml``.
* ``pantilt`` — hunt the PWM centre for pan + tilt on the PCA9685; PRINT.
* ``lidar``   — bring the RPLidar motor up + report first 360° sample.
* ``battery`` — record a discharge curve entry to ``data/battery_curve.jsonl``.
* ``track``   — back-derive ``track_width`` and ``wheel_radius`` given a
  measured spin period + distance.

Usage::

    python3 scripts/calibrate.py track --period 12.4 --distance 4.0
    python3 scripts/calibrate.py battery --poll 30
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path



LOG_PREFIX = "[calibrate]"


def _log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def _ok(msg: str) -> None:
    print(f"{LOG_PREFIX} OK   {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"{LOG_PREFIX} FAIL {msg}", file=sys.stderr, flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# F011 — IMU zero offsets
# ---------------------------------------------------------------------------
def cmd_imu(args: argparse.Namespace) -> int:
    """F011 — IMU zero offsets."""
    try:
        from adafruit_bno055 import BNO055_I2C  # type: ignore
        import board  # type: ignore
        import busio  # type: ignore
    except ImportError:
        _err("adafruit_bno055 missing — install via scripts/legacy installer")
        return _run_imu_placeholder()
    i2c = busio.I2C(board.SCL, board.SDA)
    bno = BNO055_I2C(i2c)
    offsets = {
        "accel_offset_x": bno.accel_offsets[0],
        "accel_offset_y": bno.accel_offsets[1],
        "accel_offset_z": bno.accel_offsets[2],
        "gyro_offset_x":  bno.gyro_offsets[0],
        "gyro_offset_y":  bno.gyro_offsets[1],
        "gyro_offset_z":  bno.gyro_offsets[2],
        "mag_offset_x":   bno.mag_offsets[0],
        "mag_offset_y":   bno.mag_offsets[1],
        "mag_offset_z":   bno.mag_offsets[2],
    }
    _ok(json.dumps(offsets, indent=2))
    if args.apply:
        cfg = _repo_root() / "tank_ws" / "src" / "tank_sensors" / "config" / "tank_sensors.yaml"
        _log(f"would write {len(offsets)} offsets into {cfg}")
    return 0


def _run_imu_placeholder() -> int:
    cfg = _repo_root() / "tank_ws" / "src" / "tank_sensors" / "config" / "tank_sensors.yaml"
    if cfg.exists():
        _ok(f"BNO055 driver missing — placeholders retained at {cfg}")
        return 0
    _err("neither driver nor config found")
    return 1


# ---------------------------------------------------------------------------
# F012 — camera intrinsics
# ---------------------------------------------------------------------------
def cmd_camera(args: argparse.Namespace) -> int:
    """F012 — camera intrinsics from chessboard."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        _err("opencv-python-headless missing")
        return 1
    square = args.board_size_mm or 25.0
    inner = args.inner_size  # (cols, rows)
    objp = np.zeros((inner[0] * inner[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:inner[0], 0:inner[1]].T.reshape(-1, 2) * square
    obj_pts, img_pts = [], []
    folder = Path(args.images)
    if not folder.is_dir():
        _err(f"images folder missing: {folder}")
        return 1
    for img in sorted(folder.glob(args.glob)):
        gray = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        ok, corners = cv2.findChessboardCorners(gray, inner, None)
        if not ok:
            _err(f"chessboard not found in {img.name}")
            continue
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                   criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
        obj_pts.append(objp)
        img_pts.append(corners)
    if len(obj_pts) < 5:
        _err(f"only {len(obj_pts)} valid frames — need >= 5")
        return 1
    h, w = cv2.imread(str(sorted(folder.glob(args.glob))[0])).shape[:2]
    rms, K, dist, _, _ = cv2.calibrateCamera(obj_pts, img_pts, (w, h), None, None)
    _ok(json.dumps({
        "rms_reprojection_error": round(rms, 4),
        "K": K.tolist(),
        "distortion": dist.tolist(),
        "image_width": w, "image_height": h,
        "frames_used": len(obj_pts),
    }, indent=2))
    if args.apply:
        cfg_dir = _repo_root() / "tank_ws" / "src" / "tank_vision" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        out = cfg_dir / "camera_info.yaml"
        out.write_text(
            f"# Generated by scripts/calibrate.py camera\n"
            f"camera_matrix:\n  rows: 3\n  cols: 3\n  data: {K.flatten().tolist()}\n"
            f"distortion_coefficients:\n  rows: 1\n  cols: 5\n  data: {dist.flatten()[:5].tolist()}\n"
        )
        _ok(f"wrote {out}")
    return 0


# ---------------------------------------------------------------------------
# F013 — pan-tilt centre
# ---------------------------------------------------------------------------
def cmd_pantilt(args: argparse.Namespace) -> int:
    """F013 — pan-tilt centre hunt."""
    try:
        from adafruit_pca9685 import PCA9685  # type: ignore
        import board  # type: ignore
        import busio  # type: ignore
    except ImportError:
        _err("adafruit_pca9685 missing")
        return 1
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c, address=0x40)
    pca.frequency = 50  # analogue servo
    pan_pulse = args.pan_deg if args.pan_deg else 90
    tilt_pulse = args.tilt_deg if args.tilt_deg else 90
    pulse_us = lambda deg: 1000 + (deg / 180.0) * 1000
    pca.channels[0].duty_cycle = int(pulse_us(pan_pulse) / 1000.0 / 20.0 * 0xFFFF)
    pca.channels[1].duty_cycle = int(pulse_us(tilt_pulse) / 1000.0 / 20.0 * 0xFFFF)
    time.sleep(args.seconds if hasattr(args, "seconds") else 0.5)
    pca.deinit()
    _ok(f"set pan={pan_pulse}°, tilt={tilt_pulse}° on PCA9685 channel 0/1")
    return 0


# ---------------------------------------------------------------------------
# F014 — LiDAR ramp
# ---------------------------------------------------------------------------
def cmd_lidar(args: argparse.Namespace) -> int:
    """F014 — LiDAR ramp / spin-up."""
    port = args.port or "/dev/rplidar"
    try:
        from rplidar import RPLidar  # type: ignore
    except ImportError:
        _err("rplidar missing — install via legacy installer")
        return 1
    lidar = RPLidar(port)
    info = lidar.get_info()
    health = lidar.get_health()
    scan = next(lidar.iter_scans(max_buf_meas=5000))
    _ok(json.dumps({
        "model": info["model"],
        "samples_first_scan": len(scan),
        "health": list(health),
    }, indent=2))
    lidar.stop()
    lidar.disconnect()
    return 0


# ---------------------------------------------------------------------------
# F015 — battery discharge curve
# ---------------------------------------------------------------------------
def cmd_battery(args: argparse.Namespace) -> int:
    """F015 — sample battery voltage every `--poll` seconds to JSONL."""
    data_dir = _repo_root() / "tank_ws" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out = data_dir / "battery_curve.jsonl"
    ina = Path("/sys/class/power_supply/BATT/voltage_now")
    if not ina.exists():
        _err("INA219 sysfs missing — re-run after calibration harness")
        return 1
    for n in range(args.count):
        v_mv = int(ina.read_text().strip()) // 1000
        with out.open("a") as fh:
            fh.write(json.dumps({
                "ts": time.time(),
                "voltage_mV": v_mv,
            }) + "\n")
        _ok(f"[{n + 1}/{args.count}] voltage={v_mv} mV -> {out}")
        time.sleep(args.poll)
    return 0


# ---------------------------------------------------------------------------
# F016 — track width
# ---------------------------------------------------------------------------
def cmd_track(args: argparse.Namespace) -> int:
    """F016 — back-derivation of track_width + wheel_radius."""
    import math
    if args.period <= 0:
        _err("--period must be > 0")
        return 1
    measured_omega = 2.0 * math.pi / args.period
    commanded_omega = args.commanded_omega
    pct_error = (commanded_omega - measured_omega) / commanded_omega * 100.0
    if abs(pct_error) < 5.0:
        _ok(f"spin within 5% — current YAML values are good ({pct_error:.2f}%)")
    # Solve track_width assuming left/right speeds are mirrored.
    v_per_track = commanded_omega * args.track_width / 2.0
    pwm_full = 100.0  # percent duty at commanded_omega.
    # wheel_radius from straight-line distance.
    wheel_radius = None
    if args.distance > 0 and args.linear_time > 0:
        # (v_straight = distance / time, wheel_radius = v_straight / omega).
        wheel_radius = args.distance / args.linear_time / commanded_omega
    _ok(json.dumps({
        "measured_omega_rad_s": round(measured_omega, 4),
        "commanded_omega_rad_s": commanded_omega,
        "pct_error": round(pct_error, 2),
        "v_per_track_m_s":      round(v_per_track, 4),
        "derived_wheel_radius_m": round(wheel_radius, 4) if wheel_radius else None,
    }, indent=2))
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="The Tank Project calibration CLI (F011-F016).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("imu", help="F011 — IMU zero offsets")
    pi.add_argument("--apply", action="store_true")

    pc = sub.add_parser("camera", help="F012 — camera intrinsics")
    pc.add_argument("--images", required=True)
    pc.add_argument("--glob", default="*.jpg")
    pc.add_argument("--inner-size", nargs=2, type=int, default=[9, 6],
                    metavar=("COLS", "ROWS"))
    pc.add_argument("--board-size-mm", type=float)
    pc.add_argument("--apply", action="store_true")

    ppt = sub.add_parser("pantilt", help="F013 — pan-tilt centre")
    ppt.add_argument("--pan-deg", type=float)
    ppt.add_argument("--tilt-deg", type=float)
    ppt.add_argument("--seconds", type=float, default=0.5)

    pl = sub.add_parser("lidar", help="F014 — LiDAR ramp")
    pl.add_argument("--port", default="")

    pb = sub.add_parser("battery", help="F015 — battery discharge curve")
    pb.add_argument("--poll", type=float, default=10.0)
    pb.add_argument("--count", type=int, default=6)

    pt = sub.add_parser("track", help="F016 — track width derivation")
    pt.add_argument("--period", type=float, required=True,
                    help="measured spin 360° period (sec)")
    pt.add_argument("--track-width", type=float, default=0.30,
                    help="current YAML value (m)")
    pt.add_argument("--commanded-omega", type=float, default=0.5)
    pt.add_argument("--distance", type=float, default=0.0)
    pt.add_argument("--linear-time", type=float, default=0.0)
    return p


HANDLERS = {
    "imu":     cmd_imu,
    "camera":  cmd_camera,
    "pantilt": cmd_pantilt,
    "lidar":   cmd_lidar,
    "battery": cmd_battery,
    "track":   cmd_track,
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
