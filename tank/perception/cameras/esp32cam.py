"""Tank — ESP32-S3 CAM Camera Driver (3rd Perception Node).

Runs on the Arduino UNO Q board (Qualcomm QRB2210 + STM32U585).
Captures frames from the ESP32-S3 CAM connected via USB-C,
which runs ESPHome firmware and serves MJPEG snapshots over WiFi.

Hardware chain:
  ESP32-S3 CAM (USB-C, ESPHome) → WiFi HTTP → UNO Q (ARM64) → YOLOv8n → Jetson (Tailscale)

The UNO Q also has a USB LTE modem (Quectel EG800AK) for cellular failover.

ESPHome endpoints (192.168.31.145):
  - GET /capture          → JPEG snapshot
  - GET :81/stream        → MJPEG live stream
  - GET /status           → JSON device status
  - GET /                 → Web dashboard
"""
from __future__ import annotations

import io
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("tank.perception.camera.esp32cam")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False
    logger.warning("OpenCV not installed — ESP32 CAM will run in simulation mode")


class ESP32CAMDriver:
    """ESPHome-based ESP32-S3 CAM driver for the UNO Q perception node.

    Fetches JPEG snapshots from the ESPHome web server running on the
    ESP32-S3 CAM module connected to the UNO Q via USB-C.
    """

    # ESPHome default endpoints
    CAPTURE_URL = "http://{host}/capture"
    STREAM_URL = "http://{host}:81/stream"
    STATUS_URL = "http://{host}/status"
    SNAPSHOT_URL = "http://{host}/capture"

    def __init__(
        self,
        host: str = "192.168.31.145",
        resolution: Tuple[int, int] = (640, 480),
        fps: int = 30,
        timeout_s: float = 5.0,
    ):
        self.host = host
        self.resolution = resolution
        self.fps = fps
        self.timeout_s = timeout_s
        self._connected = False
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._last_frame = None
        self._error_count = 0
        self._last_error = None
        self._device_info: Dict[str, Any] = {}

    # ── Connection ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Probe the ESPHome device and verify it responds."""
        try:
            url = self.STATUS_URL.format(host=self.host)
            req = urllib.request.urlopen(url, timeout=self.timeout_s)
            data = json.loads(req.read().decode())
            self._device_info = data
            self._connected = True
            logger.info(
                f"ESP32-S3 CAM connected: {self.host} — "
                f"flash={data.get('flash_size', '?')}, "
                f"psram={data.get('psram_size', '?')}"
            )
            return True
        except urllib.error.URLError:
            # ESPHome may not have /status — try /capture as fallback
            try:
                url = self.CAPTURE_URL.format(host=self.host)
                req = urllib.request.urlopen(url, timeout=self.timeout_s)
                content_type = req.headers.get("Content-Type", "")
                if "image" in content_type:
                    self._connected = True
                    logger.info(f"ESP32-S3 CAM reachable at {self.host} (no /status)")
                    return True
            except Exception:
                pass
            logger.warning(f"ESP32-S3 CAM not reachable at {self.host}")
            return False
        except Exception as e:
            logger.error(f"ESP32-S3 CAM connect failed: {e}")
            return False

    # ── Frame Capture ───────────────────────────────────────────────────

    def read_frame(self) -> Optional[Any]:
        """Capture a single JPEG snapshot from the ESPHome server.

        Returns an OpenCV BGR frame (numpy array) or None on failure.
        """
        if not self._connected:
            return None

        url = self.CAPTURE_URL.format(host=self.host)
        try:
            t0 = time.time()
            req = urllib.request.urlopen(url, timeout=self.timeout_s)
            jpeg_bytes = req.read()
            elapsed = time.time() - t0

            if not jpeg_bytes:
                self._error_count += 1
                self._last_error = "empty response"
                return None

            self._frame_count += 1
            self._last_frame_time = time.time()

            if not CV2_AVAILABLE:
                # Simulation mode — return placeholder
                return f"esp32cam_frame_{self._frame_count}"

            # Decode JPEG → numpy array
            buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is None:
                self._error_count += 1
                self._last_error = "JPEG decode failed"
                return None

            self._last_frame = frame
            if self._frame_count % 30 == 1:
                logger.info(
                    f"ESP32-S3 CAM frame #{self._frame_count}: "
                    f"{frame.shape[1]}x{frame.shape[0]} in {elapsed*1000:.0f}ms"
                )
            return frame

        except urllib.error.URLError as e:
            self._error_count += 1
            self._last_error = f"network: {e}"
            if self._error_count % 10 == 1:
                logger.warning(f"ESP32-S3 CAM capture failed ({self._error_count} total): {e}")
            return None
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"ESP32-S3 CAM capture error: {e}")
            return None

    def get_frame_bytes(self) -> bytes:
        """Capture a JPEG frame and return raw bytes."""
        if not self._connected:
            return b""
        url = self.CAPTURE_URL.format(host=self.host)
        try:
            req = urllib.request.urlopen(url, timeout=self.timeout_s)
            return req.read()
        except Exception:
            return b""

    def get_frame_pil(self):
        """Capture a frame and return as PIL Image (for GUI display)."""
        if not CV2_AVAILABLE:
            return None
        frame = self.read_frame()
        if frame is None or not isinstance(frame, np.ndarray):
            return None
        from PIL import Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    # ── Stream (MJPEG) ──────────────────────────────────────────────────

    def stream_url(self) -> str:
        """Return the MJPEG stream URL for external viewers."""
        return self.STREAM_URL.format(host=self.host)

    def read_stream_frame(self) -> Optional[Any]:
        """Read one frame from the MJPEG stream endpoint."""
        url = self.STREAM_URL.format(host=self.host)
        try:
            req = urllib.request.urlopen(url, timeout=self.timeout_s)
            # Read until we get a complete JPEG frame
            chunks = []
            boundary = b"--frame"
            while True:
                line = req.readline()
                if not line or boundary in line:
                    break
                chunks.append(line)
            if not chunks:
                return None
            jpeg_bytes = b"".join(chunks).strip()
            if not CV2_AVAILABLE or not jpeg_bytes:
                return jpeg_bytes
            buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.debug(f"MJPEG stream read failed: {e}")
            return None

    # ── Device Info ─────────────────────────────────────────────────────

    def get_device_info(self) -> Dict[str, Any]:
        """Query the ESPHome device for firmware / hardware info."""
        if self._device_info:
            return self._device_info
        url = self.STATUS_URL.format(host=self.host)
        try:
            req = urllib.request.urlopen(url, timeout=self.timeout_s)
            self._device_info = json.loads(req.read().decode())
            return self._device_info
        except Exception:
            return {"host": self.host, "status": "unknown"}

    # ── Cleanup ─────────────────────────────────────────────────────────

    def disconnect(self) -> None:
        self._connected = False
        self._last_frame = None
        logger.info("ESP32-S3 CAM disconnected")

    # ── Health ──────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def health(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "connected": self._connected,
            "frames": self._frame_count,
            "errors": self._error_count,
            "last_error": self._last_error,
            "resolution": list(self.resolution),
            "stream_url": self.stream_url() if self._connected else None,
            "device": self._device_info,
        }


# ── Standalone test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cam = ESP32CAMDriver(host="192.168.31.145")
    print(f"Connecting to ESP32-S3 CAM at {cam.host}...")
    if cam.connect():
        print("✅ Connected!")
        print(f"   Stream: {cam.stream_url()}")
        print(f"   Device: {cam.get_device_info()}")

        frame = cam.read_frame()
        if frame is not None:
            if isinstance(frame, str):
                print(f"   Frame: {frame} (simulation)")
            else:
                print(f"   Frame: {frame.shape[1]}x{frame.shape[0]}")
                # Save test frame
                cv2.imwrite("/tmp/esp32cam_test.jpg", frame)
                print("   Saved: /tmp/esp32cam_test.jpg")
        else:
            print("   ❌ No frame captured")
    else:
        print("❌ Cannot connect — is the ESP32-S3 CAM online?")
        print(f"   Expected at: http://{cam.host}/capture")
    print(f"\nHealth: {json.dumps(cam.health(), indent=2)}")
