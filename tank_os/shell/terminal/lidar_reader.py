#!/usr/bin/env python3
"""LiDAR reader — LDROBOT LD14/LD19 protocol parser.

Reads distance measurements from /dev/ttyUSB0 at 115200 baud.
Returns min distance, angle map, and nearest object info.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import serial


@dataclass
class LidarPoint:
    angle: float  # degrees
    distance: int  # mm
    confidence: int  # 0-255


@dataclass
class LidarScan:
    points: List[LidarPoint]
    min_distance: int  # mm
    min_angle: float  # degrees
    nearest_object: str  # description
    timestamp: float


def _parse_packet(data: bytes) -> List[LidarPoint]:
    """Parse a single LD14/LD19 packet into distance points."""
    points = []
    # LD14 packet: header(2) + start_angle(2) + 12 measurements(3bytes each) + end_angle(2) + crc(2)
    # Each measurement: distance_lsb, distance_msb, confidence
    if len(data) < 10:
        return points

    try:
        start_angle = struct.unpack_from("<H", data, 2)[0] / 100.0  # centidegrees -> degrees
        # 12 measurements, each 3 bytes (2 bytes distance + 1 byte confidence)
        for i in range(12):
            offset = 4 + i * 3
            if offset + 3 > len(data):
                break
            dist = struct.unpack_from("<H", data, offset)[0]  # mm
            conf = data[offset + 2]
            angle = start_angle + (i * 3.0)  # ~3 degrees apart
            if angle >= 360:
                angle -= 360
            points.append(LidarPoint(angle=angle, distance=dist, confidence=conf))
    except struct.error:
        pass

    return points


def read_lidar(timeout_s: float = 2.0) -> Optional[LidarScan]:
    """Read one full scan from the LiDAR. Returns None on failure."""
    try:
        s = serial.Serial("/dev/ttyUSB0", 115200, timeout=0.1)
    except Exception:
        return None

    all_points = []
    deadline = time.time() + timeout_s
    buf = b""

    try:
        while time.time() < deadline:
            chunk = s.read(200)
            if not chunk:
                continue
            buf += chunk

            # Find 0xAA55 headers
            while True:
                idx = buf.find(b"\xaa\x55")
                if idx == -1:
                    buf = buf[-10:]  # keep last few bytes for alignment
                    break
                if idx > 0:
                    buf = buf[idx:]
                # Need at least 18 bytes for a full packet
                if len(buf) < 18:
                    break
                packet = buf[:18]
                buf = buf[18:]
                pts = _parse_packet(packet)
                all_points.extend(pts)
    finally:
        s.close()

    if not all_points:
        return None

    # Find nearest object
    valid = [p for p in all_points if p.distance > 0 and p.confidence > 50]
    if not valid:
        valid = [p for p in all_points if p.distance > 0]

    if not valid:
        return LidarScan(
            points=all_points, min_distance=0, min_angle=0,
            nearest_object="nothing in range", timestamp=time.time()
        )

    nearest = min(valid, key=lambda p: p.distance)

    # Describe direction
    angle = nearest.angle
    if 345 <= angle or angle <= 15:
        direction = "directly ahead"
    elif 15 < angle <= 45:
        direction = "slightly right"
    elif 45 < angle <= 135:
        direction = "to the right"
    elif 135 < angle <= 180:
        direction = "behind right"
    elif 180 < angle <= 225:
        direction = "behind left"
    elif 225 < angle <= 315:
        direction = "to the left"
    else:
        direction = "slightly left"

    dist_m = nearest.distance / 1000.0
    desc = f"{dist_m:.2f}m {direction} (angle={nearest.angle:.0f}°, confidence={nearest.confidence})"

    return LidarScan(
        points=all_points,
        min_distance=nearest.distance,
        min_angle=nearest.angle,
        nearest_object=desc,
        timestamp=time.time(),
    )


def get_distance() -> str:
    """Quick one-liner: returns distance string for the agent."""
    scan = read_lidar(timeout_s=1.5)
    if scan is None:
        return "LiDAR not available on /dev/ttyUSB0"
    if scan.min_distance == 0:
        return "No objects detected by LiDAR"
    return f"Nearest object: {scan.nearest_object}"


def get_position_map() -> str:
    """Returns a simple position map from LiDAR scan."""
    scan = read_lidar(timeout_s=2.0)
    if scan is None:
        return "LiDAR not available"
    if not scan.points:
        return "No LiDAR data"

    # Create 8-direction bins
    dirs = {"N": [], "NE": [], "E": [], "SE": [], "S": [], "SW": [], "W": [], "NW": []}
    for p in scan.points:
        if p.distance == 0:
            continue
        a = p.angle
        if 337.5 <= a or a < 22.5:
            dirs["N"].append(p.distance)
        elif 22.5 <= a < 67.5:
            dirs["NE"].append(p.distance)
        elif 67.5 <= a < 112.5:
            dirs["E"].append(p.distance)
        elif 112.5 <= a < 157.5:
            dirs["SE"].append(p.distance)
        elif 157.5 <= a < 202.5:
            dirs["S"].append(p.distance)
        elif 202.5 <= a < 247.5:
            dirs["SW"].append(p.distance)
        elif 247.5 <= a < 292.5:
            dirs["W"].append(p.distance)
        elif 292.5 <= a < 337.5:
            dirs["NW"].append(p.distance)

    lines = ["Position map (distances in meters):"]
    for d in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        vals = dirs[d]
        if vals:
            avg = sum(vals) / len(vals) / 1000.0
            lines.append(f"  {d}: {avg:.2f}m ({len(vals)} points)")
        else:
            lines.append(f"  {d}: clear")

    return "\n".join(lines)
