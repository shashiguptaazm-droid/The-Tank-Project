#!/usr/bin/env python3
"""3rd Perception Detection — Jetson pulls frames from ESP32-S3 CAM WiFi.

The ESP32-S3 CAM (USB-C on UNO Q) connects to WiFi directly.
The Jetson pulls frames via ESPHome native API or HTTP, runs YOLO, reports to system.

No deps needed on Jetson beyond what's already installed (opencv, ultralytics).

Usage:
    python3 perception_3rd_detection.py
"""
import json
import os
import struct
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
ESP32_ESPHOME_HOST = "192.168.31.145"  # ESP32-S3 CAM on UNO Q (WiFi)
ESP32_DFROBOT_HOST = "192.168.31.176"  # DFRobot AI Camera (CamWebServer)
YOLO_MODEL = "yolov8n.pt"
CONFIDENCE = 0.5
CAPTURE_INTERVAL_S = 2.0
JETSON_API = "http://127.0.0.1:8085"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def capture_frame():
    """Try ESP32-S3 CAM ESPHome, then DFRobot CamWebServer."""
    # 1. Try ESP32-S3 CAM ESPHome — use /api/camera_image
    for host, endpoints in [
        (ESP32_ESPHOME_HOST, ["/api/camera_image", "/api/camera_image?type=photo"]),
        (ESP32_DFROBOT_HOST, ["/capture", "/capture?2"]),
    ]:
        for ep in endpoints:
            try:
                url = f"http://{host}{ep}"
                req = urllib.request.urlopen(url, timeout=5)
                data = req.read()
                ct = req.headers.get("Content-Type", "")
                if data and len(data) > 500 and ("image" in ct or data[:2] == b'\xff\xd8'):
                    log(f"✅ Frame from {host}{ep} ({len(data)} bytes)")
                    return data
            except Exception:
                continue
    return None

def run_yolo(jpeg_bytes):
    """Run YOLOv8n on a JPEG frame."""
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO

        buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            return []

        model = YOLO(YOLO_MODEL)
        results = model(frame, conf=CONFIDENCE, device="cpu", verbose=False)

        detections = []
        for r in results:
            for box in r.boxes:
                name = r.names[int(box.cls[0])]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "class": name,
                    "confidence": round(conf, 3),
                    "bbox": [x1, y1, x2, y2],
                })
        return detections
    except Exception as e:
        log(f"YOLO error: {e}")
        return []

def report_detections(detections, frame_size):
    """POST detections to local Tank API."""
    try:
        payload = json.dumps({
            "source": "esp32cam_wifi",
            "node": "jetson",
            "timestamp": time.time(),
            "detection_count": len(detections),
            "detections": detections,
            "frame_size": frame_size,
        }).encode()
        req = urllib.request.Request(
            f"{JETSON_API}/api/detections",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # best effort

def main():
    log("🔭 3rd Perception Detection starting...")
    log(f"   ESP32-S3 CAM (ESPHome): {ESP32_ESPHOME_HOST}")
    log(f"   DFRobot (CamWebServer): {ESP32_DFROBOT_HOST}")
    log(f"   Model: {YOLO_MODEL}, confidence: {CONFIDENCE}")

    frame_count = 0
    detection_count = 0

    while True:
        try:
            jpeg = capture_frame()
            if jpeg:
                frame_count += 1
                dets = run_yolo(jpeg)
                detection_count += len(dets)
                report_detections(dets, len(jpeg))

                if dets:
                    names = [f"{d['class']}({d['confidence']:.0%})" for d in dets]
                    log(f"🔍 Frame #{frame_count}: {', '.join(names)}")
                elif frame_count % 10 == 0:
                    log(f"Frame #{frame_count}: no detections")
            else:
                if frame_count % 5 == 0:
                    log("⏳ Waiting for camera...")

            time.sleep(CAPTURE_INTERVAL_S)

        except KeyboardInterrupt:
            log(f"🛑 Stopped. {frame_count} frames, {detection_count} detections total.")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
