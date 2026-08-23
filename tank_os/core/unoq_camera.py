#!/usr/bin/env python3
"""ESP32-S3 CAM Driver for UNO Q — USB serial camera capture.

Connects to the ESP32-S3 CAM module on /dev/ttyACM0 over USB serial.
Uses 'SNAP' command protocol (same as DFRobot camera on Jetson).

Integrated as a perception source for the UNO Q detection pipeline.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tank.unoq.camera")

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD = 921600
FRAME_DIR = Path("/home/arduino/tank-project/data/frames")


class ESP32CameraDriver:
    """Capture JPEG frames from ESP32-S3 CAM over USB serial."""

    def __init__(self, port: str = DEFAULT_PORT, baud: int = DEFAULT_BAUD):
        self.port = port
        self.baud = baud
        self._serial = None

    @property
    def connected(self) -> bool:
        return Path(self.port).exists()

    def _ensure_serial(self):
        if self._serial is None or not self._serial.is_open:
            import serial
            self._serial = serial.Serial(self.port, self.baud, timeout=5)
            time.sleep(0.3)
            self._serial.read(self._serial.in_waiting)  # drain boot noise

    def capture(self) -> Optional[Path]:
        """Capture a JPEG frame. Returns path to saved file, or None."""
        if not self.connected:
            logger.debug("ESP32 camera not connected at %s", self.port)
            return None

        try:
            self._ensure_serial()
            self._serial.write(b"SNAP\n")

            # Read header "FRAME:<w>:<h>:<size>\n"
            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = self._serial.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break

            h = header.decode("utf-8", errors="replace").strip()
            if not h.startswith("FRAME:"):
                logger.debug("Bad camera header: %s", h[:60])
                return None

            parts = h.split(":")
            if len(parts) < 4:
                return None
            expected = int(parts[3])
            width, height = int(parts[1]), int(parts[2])

            # Read JPEG bytes
            jpeg = b""
            dl = time.time() + 10
            while len(jpeg) < expected and time.time() < dl:
                chunk = self._serial.read(min(expected - len(jpeg), 16384))
                if chunk:
                    jpeg += chunk
                    dl = time.time() + 2  # reset timeout on data

            # Drain trailing newline
            self._serial.read(1)

            if len(jpeg) < 500:
                logger.debug("Frame too small: %d bytes", len(jpeg))
                return None

            FRAME_DIR.mkdir(parents=True, exist_ok=True)
            path = FRAME_DIR / "esp32cam_latest.jpg"
            path.write_bytes(jpeg)
            logger.debug("Captured %dx%d JPEG (%d bytes)", width, height, len(jpeg))
            return path

        except Exception as e:
            logger.debug("ESP32 camera error: %s", e)
            return None

    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None


# ── Quick test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    cam = ESP32CameraDriver()
    print(f"Camera port {cam.port}: {'connected' if cam.connected else 'MISSING'}")
    if cam.connected:
        print("Capturing...")
        path = cam.capture()
        if path:
            print(f"✅ Frame saved: {path} ({path.stat().st_size} bytes)")
        else:
            print("❌ No frame — firmware may need flashing")
        cam.close()