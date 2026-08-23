#!/usr/bin/env python3
"""Dual Camera Manager — USB DFRobot + WiFi ESP32-S3 CAM.

Provides:
  - USB camera: /dev/ttyACM0 (SNAP protocol, 640x480 JPEG)
  - WiFi camera: 192.168.31.145 (ESPHome MJPEG stream)
  - Recording to disk (frames + video)
  - YOLO detection on both cameras
  - Face recognition on both cameras
  - Auto-reconnect for WiFi camera

Usage:
    dm = DualCamera()
    dm.start_recording()  # records continuously
    dm.capture_usb()      # single USB frame
    dm.capture_wifi()     # single WiFi frame
    dm.detect_all()       # YOLO + face on latest frame
"""

from __future__ import annotations

import os
import sys
import time
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger("dual_camera")

PROJECT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT / "data"
FRAMES_DIR = DATA_DIR / "frames"
RECORDINGS_DIR = DATA_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# WiFi camera config
WIFI_CAM_URL = "http://192.168.31.145"
WIFI_CAM_STREAM = f"{WIFI_CAM_URL}:81/stream"
WIFI_CAM_CAPTURE = f"{WIFI_CAM_URL}/camera"
WIFI_CAM_STATUS = f"{WIFI_CAM_URL}/status"

# USB camera config
USB_PORT = "/dev/ttyACM0"
USB_BAUD = 921600


@dataclass
class CameraFrame:
    source: str  # "usb" or "wifi"
    image: Optional[np.ndarray] = None
    timestamp: float = 0.0
    width: int = 0
    height: int = 0
    path: str = ""


@dataclass
class Detection:
    name: str
    confidence: float
    x: int
    y: int
    w: int = 0
    h: int = 0
    source: str = ""


class DualCamera:
    """Manages USB + WiFi cameras with recording."""

    def __init__(self):
        self._wifi_connected = False
        self._wifi_cap = None
        self._recording = False
        self._record_thread = None
        self._yolo_model = None
        self._face_db = None
        self._latest_usb: Optional[CameraFrame] = None
        self._latest_wifi: Optional[CameraFrame] = None
        self._frame_count = 0
        self._recording_file = None
        self._recording_writer = None

    # ── YOLO ────────────────────────────────────────────────────────────
    def _get_yolo(self):
        if self._yolo_model is None:
            try:
                from ultralytics import YOLO
                self._yolo_model = YOLO("yolov8n.pt")
                logger.info("YOLO model loaded")
            except Exception as e:
                logger.error(f"YOLO load failed: {e}")
        return self._yolo_model

    def _get_face_db(self):
        if self._face_db is None:
            try:
                from tank_os.shell.terminal.face_db import FaceDB
                self._face_db = FaceDB()
            except Exception:
                pass
        return self._face_db

    # ── USB Camera (DFRobot) ────────────────────────────────────────────
    def capture_usb(self) -> Optional[CameraFrame]:
        """Capture frame from DFRobot USB camera via SNAP protocol."""
        try:
            import serial
            if not Path(USB_PORT).exists():
                return None

            s = serial.Serial(USB_PORT, USB_BAUD, timeout=5)
            time.sleep(0.3)
            s.read(s.in_waiting)
            time.sleep(0.1)
            s.read(s.in_waiting)
            s.write(b"SNAP\n")

            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = s.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break

            h = header.decode("utf-8", errors="replace").strip()
            if not h.startswith("FRAME:"):
                s.close()
                return None

            parts = h.split(":")
            w, h_px, expected = int(parts[1]), int(parts[2]), int(parts[3])
            jpeg = b""
            dl = time.time() + 10
            while len(jpeg) < expected and time.time() < dl:
                chunk = s.read(min(expected - len(jpeg), 16384))
                if chunk:
                    jpeg += chunk
                    dl = time.time() + 2
            s.read(1)
            s.close()

            if len(jpeg) < 500:
                return None

            # Decode JPEG
            img_array = np.frombuffer(jpeg, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                return None

            ts = time.time()
            path = str(FRAMES_DIR / "latest_usb.jpg")
            cv2.imwrite(path, img)

            frame = CameraFrame(source="usb", image=img, timestamp=ts,
                                width=w, height=h_px, path=path)
            self._latest_usb = frame
            return frame

        except Exception as e:
            logger.debug(f"USB capture error: {e}")
            return None

    # ── WiFi Camera (ESPHome) ───────────────────────────────────────────
    def _connect_wifi(self) -> bool:
        """Connect to WiFi camera MJPEG stream."""
        try:
            if self._wifi_cap and self._wifi_cap.isOpened():
                return True

            # Try multiple stream URLs
            urls = [
                WIFI_CAM_STREAM,
                f"{WIFI_CAM_URL}/stream",
                f"{WIFI_CAM_URL}:8080/stream",
                f"{WIFI_CAM_URL}/camera",
            ]

            for url in urls:
                try:
                    cap = cv2.VideoCapture(url)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            self._wifi_cap = cap
                            self._wifi_connected = True
                            logger.info(f"WiFi camera connected: {url}")
                            return True
                        cap.release()
                except Exception:
                    pass

            self._wifi_connected = False
            return False

        except Exception as e:
            logger.debug(f"WiFi connect error: {e}")
            self._wifi_connected = False
            return False

    def capture_wifi(self) -> Optional[CameraFrame]:
        """Capture frame from WiFi ESPHome camera."""
        if not self._wifi_connected:
            if not self._connect_wifi():
                return None

        try:
            if self._wifi_cap and self._wifi_cap.isOpened():
                ret, img = self._wifi_cap.read()
                if ret and img is not None:
                    ts = time.time()
                    path = str(FRAMES_DIR / "latest_wifi.jpg")
                    cv2.imwrite(path, img)
                    h, w = img.shape[:2]
                    frame = CameraFrame(source="wifi", image=img, timestamp=ts,
                                        width=w, height=h, path=path)
                    self._latest_wifi = frame
                    return frame
            # Reconnect
            self._wifi_cap = None
            self._wifi_connected = False
            return None
        except Exception as e:
            logger.debug(f"WiFi capture error: {e}")
            self._wifi_cap = None
            self._wifi_connected = False
            return None

    # ── Detection ───────────────────────────────────────────────────────
    def detect_yolo(self, frame: CameraFrame) -> List[Detection]:
        """Run YOLO on a frame."""
        model = self._get_yolo()
        if model is None or frame.image is None:
            return []

        try:
            results = model(frame.path if frame.path else frame.image, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    name = r.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    detections.append(Detection(
                        name=name, confidence=conf,
                        x=int((x1+x2)/2), y=int((y1+y2)/2),
                        w=int(x2-x1), h=int(y2-y1),
                        source=frame.source,
                    ))
            return detections
        except Exception as e:
            logger.debug(f"YOLO error: {e}")
            return []

    def detect_faces(self, frame: CameraFrame) -> List[Dict]:
        """Run face recognition on a frame."""
        db = self._get_face_db()
        if db is None or frame.path is None:
            return []

        try:
            return db.recognize_in_frame(frame.path)
        except Exception as e:
            logger.debug(f"Face detection error: {e}")
            return []

    def detect_all(self, source: str = "usb") -> Dict:
        """Run all detection on latest frame from given source."""
        if source == "wifi":
            frame = self.capture_wifi() or self._latest_wifi
        else:
            frame = self.capture_usb() or self._latest_usb

        if frame is None:
            return {"error": f"Camera '{source}' not available"}

        yolo = self.detect_yolo(frame)
        faces = self.detect_faces(frame)

        return {
            "source": frame.source,
            "timestamp": frame.timestamp,
            "width": frame.width,
            "height": frame.height,
            "path": frame.path,
            "yolo": [{"name": d.name, "confidence": d.confidence,
                       "x": d.x, "y": d.y} for d in yolo],
            "faces": faces,
        }

    # ── Recording ───────────────────────────────────────────────────────
    def start_recording(self, source: str = "wifi", fps: float = 5.0):
        """Start continuous recording from a camera source."""
        if self._recording:
            return

        self._recording = True
        self._record_thread = threading.Thread(
            target=self._record_loop, args=(source, fps), daemon=True)
        self._record_thread.start()
        logger.info(f"Recording started: {source} @ {fps}fps")

    def stop_recording(self):
        """Stop recording."""
        self._recording = False
        if self._recording_writer:
            self._recording_writer.release()
            self._recording_writer = None
        logger.info("Recording stopped")

    def _record_loop(self, source: str, fps: float):
        """Recording loop — saves frames + runs detection."""
        interval = 1.0 / fps
        date_str = time.strftime("%Y%m%d_%H%M%S")
        video_path = str(RECORDINGS_DIR / f"recording_{source}_{date_str}.mp4")
        detections_log = str(RECORDINGS_DIR / f"detections_{source}_{date_str}.jsonl")

        writer = None
        all_detections = []

        while self._recording:
            t0 = time.time()

            # Capture
            if source == "wifi":
                frame = self.capture_wifi()
            else:
                frame = self.capture_usb()

            if frame is None:
                time.sleep(1)
                continue

            # Initialize video writer
            if writer is None and frame.image is not None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(video_path, fourcc, fps,
                                         (frame.width, frame.height))

            # Write frame
            if writer and frame.image is not None:
                writer.write(frame.image)

            # Run detection every 2 seconds
            if self._frame_count % int(fps * 2) == 0:
                yolo = self.detect_yolo(frame)
                faces = self.detect_faces(frame)

                detection_entry = {
                    "timestamp": frame.timestamp,
                    "time": time.strftime("%H:%M:%S", time.localtime(frame.timestamp)),
                    "source": source,
                    "yolo": [{"name": d.name, "confidence": d.confidence,
                              "x": d.x, "y": d.y} for d in yolo],
                    "faces": faces,
                }
                all_detections.append(detection_entry)

                # Append to log file
                with open(detections_log, "a") as f:
                    f.write(json.dumps(detection_entry) + "\n")

            self._frame_count += 1

            # Maintain FPS
            elapsed = time.time() - t0
            if elapsed < interval:
                time.sleep(interval - elapsed)

        if writer:
            writer.release()

    # ── Status ──────────────────────────────────────────────────────────
    def status(self) -> str:
        """Get camera status."""
        usb_ok = Path(USB_PORT).exists()
        wifi_ok = self._wifi_connected

        # Quick WiFi check
        if not wifi_ok:
            try:
                import urllib.request
                req = urllib.request.Request(WIFI_CAM_URL,
                                             method="HEAD")
                resp = urllib.request.urlopen(req, timeout=3)
                wifi_ok = resp.status == 200
            except Exception:
                wifi_ok = False

        lines = [
            "Camera Status:",
            f"  USB (DFRobot): {'✅ Connected' if usb_ok else '❌ Not found'} on {USB_PORT}",
            f"  WiFi (ESPHome): {'✅ Connected' if wifi_ok else '❌ Offline'} @ {WIFI_CAM_URL}",
            f"  Recording: {'▶ Active' if self._recording else '⏹ Stopped'}",
            f"  Frames captured: {self._frame_count}",
        ]

        if self._latest_usb:
            lines.append(f"  Latest USB: {self._latest_usb.width}x{self._latest_usb.height}")
        if self._latest_wifi:
            lines.append(f"  Latest WiFi: {self._latest_wifi.width}x{self._latest_wifi.height}")

        return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Dual Camera Manager")
    parser.add_argument("command", choices=["status", "capture", "detect", "record", "stop"])
    parser.add_argument("--source", "-s", default="usb", choices=["usb", "wifi", "both"])
    parser.add_argument("--fps", type=float, default=5.0)
    args = parser.parse_args()

    dm = DualCamera()

    if args.command == "status":
        print(dm.status())

    elif args.command == "capture":
        if args.source == "both" or args.source == "usb":
            frame = dm.capture_usb()
            if frame:
                print(f"USB: {frame.width}x{frame.height} -> {frame.path}")
            else:
                print("USB: not available")
        if args.source == "both" or args.source == "wifi":
            frame = dm.capture_wifi()
            if frame:
                print(f"WiFi: {frame.width}x{frame.height} -> {frame.path}")
            else:
                print("WiFi: not available")

    elif args.command == "detect":
        result = dm.detect_all(args.source)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "record":
        dm.start_recording(args.source, args.fps)
        print(f"Recording {args.source} @ {args.fps}fps... (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            dm.stop_recording()

    elif args.command == "stop":
        dm.stop_recording()
