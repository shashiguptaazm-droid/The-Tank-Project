"""Tank — USB Camera Driver (OpenCV).

Works with any V4L2 USB webcam on Linux.
Provides YOLO-ready frame capture.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.camera.usb")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not installed — camera will run in simulation mode")


class USBCamera:
    """USB webcam interface for YOLO detection."""

    def __init__(self, device: int = 0, resolution: tuple = (640, 480), fps: int = 30):
        self.device = device
        self.resolution = resolution
        self.fps = fps
        self._cap = None
        self._connected = False
        self._frame_count = 0

    def connect(self) -> bool:
        if not CV2_AVAILABLE:
            logger.warning("OpenCV unavailable — simulating camera")
            self._connected = True
            return True
        try:
            self._cap = cv2.VideoCapture(self.device)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            self._connected = self._cap.isOpened()
            if self._connected:
                logger.info(f"Camera connected: device={self.device} res={self.resolution}")
            return self._connected
        except Exception as e:
            logger.error(f"Camera connect failed: {e}")
            return False

    def read_frame(self) -> Optional[Any]:
        if not self._connected:
            return None
        if not CV2_AVAILABLE:
            self._frame_count += 1
            return f"simulated_frame_{self._frame_count}"
        ret, frame = self._cap.read()
        if ret:
            self._frame_count += 1
            return frame
        return None

    def get_frame_bytes(self) -> bytes:
        frame = self.read_frame()
        if frame is None:
            return b""
        if not CV2_AVAILABLE:
            return b"simulated"
        _, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes()

    def disconnect(self) -> None:
        if self._cap:
            self._cap.release()
        self._connected = False
        logger.info("Camera disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def health(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "connected": self._connected,
            "frames": self._frame_count,
            "resolution": self.resolution,
        }
