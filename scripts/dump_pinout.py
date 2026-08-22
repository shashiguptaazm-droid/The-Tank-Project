#!/usr/bin/env python3
"""Dump the GPIO / I²C / UART / camera wiring used by The Tank Project.

This script reads the YAML configs in
``tank_ws/src/tank_bringup/config/`` and prints Markdown tables that can be
pasted into ``WIRING.md`` so docs and code never drift.

Usage::

    python3 scripts/dump_pinout.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import yaml


def banner(text: str) -> str:
    return f"\n{'=' * (len(text) + 4)}\n  {text}\n{'=' * (len(text) + 4)}\n"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())["/**"]["ros__parameters"]


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    cfg_dir = repo / "tank_ws" / "src" / "tank_bringup" / "config"

    try:
        motion   = load_yaml(cfg_dir / "tank_motion.yaml")
        sensors  = load_yaml(cfg_dir / "tank_sensors.yaml")
        vision   = load_yaml(cfg_dir / "tank_vision.yaml")
    except FileNotFoundError as exc:
        print(f"missing config: {exc}", file=sys.stderr)
        return 1

    print(banner("GPIO (BCM numbering)"))
    mc = motion["motor_controller"]
    print(dedent("""\
        | Function      | Pin |
        |---------------|-----|
        | dir_left_pin  | %3d |
        | pwm_left_pin  | %3d |
        | dir_right_pin | %3d |
        | pwm_right_pin | %3d |""" % (
        mc["dir_left_pin"],  mc["pwm_left_pin"],
        mc["dir_right_pin"], mc["pwm_right_pin"],
    )))

    print(banner("I²C (bus 1)"))
    imu = sensors["imu_publisher"]
    pt  = motion["pan_tilt_controller"]
    print(dedent("""\
        | Device              | Address        | Notes              |
        |---------------------|----------------|--------------------|
        | BNO055 IMU          | 0x%02x          | rate=%.0f Hz        |
        | PCA9685 PWM board   | 0x%02x          | %d Hz             |""" % (
        imu["i2c_address"], imu["rate_hz"],
        pt["i2c_address"],  pt["pwm_frequency"],
    )))

    print(banner("UART"))
    lid = sensors["lidar_publisher"]
    print(dedent(f"""\
        | Device    | Path      | Baud    |
        |-----------|-----------|---------|
        | RPLidar   | {lid['port']:9s} | {lid['baudrate']:7d} |"""))

    print(banner("Camera"))
    cam = vision["camera_publisher"]
    print(f"  device    : {cam['device']}")
    print(f"  width x h : {cam['width']} x {cam['height']}")
    print(f"  fps       : {cam['fps']}")
    print(f"  frame_id  : {cam['frame_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
