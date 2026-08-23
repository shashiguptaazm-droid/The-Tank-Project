"""
camera_manager.py — Unified Camera Interface
Supports: DFRobot AI Camera, ESP32 camera, USB camera fallback
Features: health monitoring, configurable FPS/resolution, reconnect, timestamps
"""
import cv2
import time
import json
import logging
import threading
import serial
import numpy as np
from datetime import datetime
from enum import Enum

logger = logging.getLogger("tank.vision.camera")


class CameraType(Enum):
    DFRobot = "dfrobot"
    ESP32 = "esp32"
    USB = "usb"


class CameraHealth:
    def __init__(self):
        self.frames_captured = 0
        self.frames_dropped = 0
        self.last_capture_time = 0
        self.avg_fps = 0
        self.last_error = None
        self.uptime_start = time.time()
        self.consecutive_failures = 0

    def record_success(self):
        self.frames_captured += 1
        now = time.time()
        if self.last_capture_time > 0:
            dt = now - self.last_capture_time
            self.avg_fps = 0.9 * self.avg_fps + 0.1 * (1.0 / dt) if dt > 0 else self.avg_fps
        self.last_capture_time = now
        self.consecutive_failures = 0

    def record_failure(self):
        self.frames_dropped += 1
        self.consecutive_failures += 1

    def is_healthy(self):
        return self.consecutive_failures < 5

    def to_dict(self):
        uptime = time.time() - self.uptime_start
        return {
            "frames_captured": self.frames_captured,
            "frames_dropped": self.frames_dropped,
            "avg_fps": round(self.avg_fps, 1),
            "uptime_s": round(uptime),
            "healthy": self.is_healthy(),
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }


class DFRobotCamera:
    def __init__(self, port="/dev/ttyACM0", baud=921600):
        self.port = port
        self.baud = baud
        self.serial_conn = None
        self.width = 640
        self.height = 480
        self.health = CameraHealth()

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baud, timeout=5)
            time.sleep(0.3)
            self.serial_conn.read(self.serial_conn.in_waiting)
            self.serial_conn.write(b"HELP\n")
            time.sleep(0.5)
            data = self.serial_conn.read(500).decode("utf-8", errors="replace")
            if "SNAP" in data:
                logger.info(f"DFRobot camera connected on {self.port}")
                return True
        except Exception as e:
            logger.error(f"DFRobot connect failed: {e}")
        return False

    def capture(self):
        if not self.serial_conn:
            return None, 0, 0
        try:
            self.serial_conn.read(self.serial_conn.in_waiting)
            self.serial_conn.write(b"SNAP\n")
            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = self.serial_conn.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break
            h = header.decode("utf-8", errors="replace").strip()
            if not h.startswith("FRAME:"):
                self.health.record_failure()
                return None, 0, 0
            parts = h.split(":")
            expected = int(parts[3])
            jpeg = b""
            dl = time.time() + 10
            while len(jpeg) < expected and time.time() < dl:
                chunk = self.serial_conn.read(min(expected - len(jpeg), 16384))
                if chunk:
                    jpeg += chunk
                    dl = time.time() + 2
            self.serial_conn.read(1)
            self.health.record_success()
            return jpeg, int(parts[1]), int(parts[2])
        except Exception as e:
            self.health.record_failure()
            self.health.last_error = str(e)
            return None, 0, 0

    def reconnect(self):
        self.disconnect()
        time.sleep(2)
        return self.connect()

    def disconnect(self):
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None

    def set_resolution(self, width, height):
        self.width = width
        self.height = height


class USBCamera:
    def __init__(self, device=0, width=640, height=480, fps=30):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.health = CameraHealth()

    def connect(self):
        try:
            self.cap = cv2.VideoCapture(self.device)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            if self.cap.isOpened():
                logger.info(f"USB camera connected on device {self.device}")
                return True
        except Exception as e:
            logger.error(f"USB camera connect failed: {e}")
        return False

    def capture(self):
        if not self.cap or not self.cap.isOpened():
            self.health.record_failure()
            return None, 0, 0
        try:
            ret, frame = self.cap.read()
            if ret:
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                self.health.record_success()
                return jpeg.tobytes(), frame.shape[1], frame.shape[0]
            self.health.record_failure()
            return None, 0, 0
        except Exception as e:
            self.health.record_failure()
            self.health.last_error = str(e)
            return None, 0, 0

    def reconnect(self):
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def disconnect(self):
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None


class CameraManager:
    def __init__(self, preferred_type=CameraType.DFRobot):
        self.preferred_type = preferred_type
        self.active_camera = None
        self.camera_type = None
        self.health = CameraHealth()
        self.timestamp = 0
        self.fps = 10
        self.resolution = (640, 480)
        self._lock = threading.Lock()
        self._running = False
        self._capture_thread = None
        self._latest_frame = None
        self._callbacks = []

        self.cameras = {
            CameraType.DFRobot: DFRobotCamera(),
            CameraType.USB: USBCamera(),
        }

    def start(self):
        self._running = True
        if self.active_camera is None:
            self._connect_best()
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

    def stop(self):
        self._running = False
        if self.active_camera:
            self.active_camera.disconnect()

    def _connect_best(self):
        order = [self.preferred_type] + [t for t in CameraType if t != self.preferred_type]
        for cam_type in order:
            cam = self.cameras.get(cam_type)
            if cam and cam.connect():
                self.active_camera = cam
                self.camera_type = cam_type
                logger.info(f"Camera active: {cam_type.value}")
                return True
        logger.error("No camera found!")
        return False

    def _capture_loop(self):
        while self._running:
            if not self.active_camera or not self.active_camera.health.is_healthy():
                logger.info("Camera unhealthy, attempting reconnect...")
                self._reconnect_with_backoff()

            jpeg, w, h = self.active_camera.capture() if self.active_camera else (None, 0, 0)
            if jpeg:
                self.timestamp = time.time()
                self._latest_frame = {"jpeg": jpeg, "width": w, "height": h, "timestamp": self.timestamp}
                for cb in self._callbacks:
                    cb(self._latest_frame)
            else:
                time.sleep(0.5)
                continue

            frame_time = 1.0 / self.fps
            time.sleep(max(0, frame_time - 0.01))

    def _reconnect_with_backoff(self):
        for delay in [2, 4, 8, 16]:
            time.sleep(delay)
            if self.active_camera and self.active_camera.reconnect():
                logger.info("Camera reconnected!")
                return
        self._connect_best()

    def get_frame(self):
        return self._latest_frame

    def on_frame(self, callback):
        self._callbacks.append(callback)

    def set_fps(self, fps):
        self.fps = max(1, min(30, fps))

    def set_resolution(self, width, height):
        self.resolution = (width, height)
        if self.active_camera:
            self.active_camera.set_resolution(width, height)

    def get_health(self):
        return {
            "type": self.camera_type.value if self.camera_type else "none",
            "fps": self.fps,
            "resolution": self.resolution,
            "timestamp": self.timestamp,
            "health": self.active_camera.health.to_dict() if self.active_camera else {},
        }

    def capture_single(self):
        if not self.active_camera:
            self._connect_best()
        if self.active_camera:
            return self.active_camera.capture()
        return None, 0, 0
