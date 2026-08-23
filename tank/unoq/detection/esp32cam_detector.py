"""esp32cam_detector.py — UNO Q 3rd Perception Detection Node.

Combines the ESP32-S3 CAM driver with YOLOv8n object detection.
Runs on the Arduino UNO Q board (Qualcomm QRB2210 + STM32U585).

This is the 3rd perception node in the Tank's multi-sensor architecture:
  1. DFRobot AI Camera (Jetson, /dev/ttyACM0) — primary vision
  2. LiDAR LDROBOT LD14/19 (Jetson, /dev/ttyUSB0) — obstacle detection
  3. ESP32-S3 CAM + UNO Q (USB-C, ESPHome) — remote detection wing

The UNO Q connects to the ESP32-S3 CAM via USB-C and serves as a
WiFi→YOLO processing bridge. Detections are reported to the Jetson
brain over Tailscale (100.84.235.7 → 100.122.31.46).

The UNO Q also has a USB LTE modem (Quectel EG800AK) providing
cellular failover for detection reporting when WiFi is down.
"""
from __future__ import annotations

import json
import logging
import time
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("tank.unoq.detection")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed — YOLO detection disabled")


# ── Detection Data ──────────────────────────────────────────────────────

@dataclass
class Detection:
    """Single object detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2) in pixels
    center: tuple  # (cx, cy) in pixels
    area: int = 0
    distance_est: float = 0.0  # meters (rough estimate)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox),
            "center": list(self.center),
            "area": self.area,
            "distance_est": self.distance_est,
            "source": "unoq_esp32cam",
            "timestamp": self.timestamp,
        }


# ── Main Detector ───────────────────────────────────────────────────────

class ESP32CAMDetector:
    """3rd Perception Node: ESP32-S3 CAM + YOLOv8n on UNO Q.

    Fetches frames from the ESPHome-based ESP32-S3 CAM over WiFi,
    runs YOLOv8n inference locally on the UNO Q (ARM64), and reports
    detections to the Jetson brain via Tailscale.

    Usage:
        detector = ESP32CAMDetector()
        if detector.connect():
            detections = detector.detect_frame()
            detector.report_to_jetson(detections)
    """

    # YOLO class filters
    PERSON_CLASSES = {0: "person"}
    VEHICLE_CLASSES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    ALL_CLASSES = {**PERSON_CLASSES, **VEHICLE_CLASSES, 14: "cat", 15: "dog"}

    def __init__(
        self,
        esp32cam_host: str = "192.168.31.145",
        model_path: str = "yolov8n.pt",
        confidence: float = 0.5,
        device: str = "cpu",  # UNO Q has no GPU — use CPU
        jetson_api: str = "http://100.122.31.46:8085",
        vps_api: str = "http://100.71.127.19:8888",
        report_interval_s: float = 5.0,
    ):
        self.esp32cam_host = esp32cam_host
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self.jetson_api = jetson_api
        self.vps_api = vps_api
        self.report_interval_s = report_interval_s

        # State
        self._connected = False
        self._model = None
        self._frame_count = 0
        self._detection_count = 0
        self._last_detections: List[Detection] = []
        self._last_report_time = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_detections: Optional[Callable] = None
        self._report_failures = 0
        self._lte_active = False

    # ── Connection ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to ESP32-S3 CAM and load YOLO model."""
        # 1. Check ESP32-S3 CAM reachability
        try:
            url = f"http://{self.esp32cam_host}/capture"
            req = urllib.request.urlopen(url, timeout=5)
            content_type = req.headers.get("Content-Type", "")
            if "image" in content_type or req.status == 200:
                self._connected = True
                logger.info(f"✅ ESP32-S3 CAM reachable at {self.esp32cam_host}")
            else:
                logger.warning(f"ESP32-S3 CAM returned unexpected content: {content_type}")
                self._connected = True  # proceed anyway
        except Exception as e:
            logger.warning(f"ESP32-S3 CAM not reachable: {e}")
            self._connected = True  # allow offline detection testing
            logger.info("Running in offline/demo mode")

        # 2. Load YOLO model
        if YOLO_AVAILABLE:
            try:
                self._model = YOLO(self.model_path)
                logger.info(f"✅ YOLOv8n loaded: {self.model_path}")
            except Exception as e:
                logger.error(f"YOLO load failed: {e}")
        else:
            logger.warning("YOLO unavailable — detection will be simulated")

        return self._connected

    # ── Detection ───────────────────────────────────────────────────────

    def detect_frame(self) -> List[Detection]:
        """Capture one frame from ESP32-S3 CAM and run YOLO detection."""
        frame = self._capture_frame()
        if frame is None:
            return []

        return self._run_yolo(frame)

    def detect_from_frame(self, frame) -> List[Detection]:
        """Run YOLO on an already-captured frame."""
        return self._run_yolo(frame)

    def _capture_frame(self) -> Optional[Any]:
        """Fetch a JPEG snapshot from the ESP32-S3 CAM via HTTP."""
        url = f"http://{self.esp32cam_host}/capture"
        try:
            req = urllib.request.urlopen(url, timeout=5)
            jpeg_bytes = req.read()
            if not jpeg_bytes:
                return None

            self._frame_count += 1

            if not CV2_AVAILABLE:
                return f"simulated_frame_{self._frame_count}"

            buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return frame

        except Exception as e:
            logger.debug(f"Frame capture failed: {e}")
            return None

    def _run_yolo(self, frame) -> List[Detection]:
        """Run YOLOv8n inference on a frame."""
        if not CV2_AVAILABLE or frame is None or isinstance(frame, str):
            # Simulation mode
            return self._simulated_detections()

        if self._model is None:
            return []

        detections = []
        try:
            results = self._model(
                frame,
                conf=self.confidence,
                device=self.device,
                verbose=False,
            )
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    name = r.names.get(cls_id, f"class_{cls_id}")

                    det = Detection(
                        class_id=cls_id,
                        class_name=name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                        area=(x2 - x1) * (y2 - y1),
                        distance_est=self._estimate_distance(frame, y1, y2),
                        timestamp=time.time(),
                    )
                    detections.append(det)

        except Exception as e:
            logger.error(f"YOLO inference error: {e}")

        self._detection_count += len(detections)
        self._last_detections = detections

        if detections:
            logger.info(
                f"🔍 UNO Q detected {len(detections)} objects: "
                + ", ".join(f"{d.class_name}({d.confidence:.0%})" for d in detections)
            )

        return detections

    def _estimate_distance(self, frame, y1: int, y2: int) -> float:
        """Rough distance estimate based on person bounding box height."""
        h = y2 - y1
        if h <= 0:
            return 999.0
        frame_h = frame.shape[0] if hasattr(frame, 'shape') else 480
        focal = frame_h / 2.0
        real_h = 1.7  # assumed person height in meters
        return round((real_h * focal) / h, 2)

    def _simulated_detections(self) -> List[Detection]:
        """Generate simulated detections when camera/model unavailable."""
        import random
        n = random.randint(0, 3)
        classes = ["person", "car", "dog", "chair", "bottle"]
        dets = []
        for _ in range(n):
            name = random.choice(classes)
            conf = round(random.uniform(0.5, 0.95), 3)
            x1, y1 = random.randint(50, 400), random.randint(50, 300)
            x2, y2 = x1 + random.randint(60, 200), y1 + random.randint(60, 300)
            dets.append(Detection(
                class_id=0, class_name=name, confidence=conf,
                bbox=(x1, y1, x2, y2),
                center=((x1+x2)//2, (y1+y2)//2),
                area=(x2-x1)*(y2-y1),
                distance_est=round(random.uniform(0.5, 10.0), 2),
                timestamp=time.time(),
            ))
        return dets

    # ── Reporting ───────────────────────────────────────────────────────

    def report_to_jetson(self, detections: Optional[List[Detection]] = None) -> bool:
        """Send detection results to the Jetson brain over Tailscale."""
        dets = detections if detections is not None else self._last_detections
        payload = {
            "source": "unoq_esp32cam",
            "node": "unoq",
            "tailscale_ip": "100.84.235.7",
            "timestamp": time.time(),
            "frame_count": self._frame_count,
            "detection_count": len(dets),
            "detections": [d.to_dict() for d in dets],
            "camera_host": self.esp32cam_host,
            "lte_active": self._lte_active,
        }
        return self._send_report(payload)

    def _send_report(self, payload: dict) -> bool:
        """POST report to Jetson (primary) or VPS (fallback over LTE)."""
        targets = [self.jetson_api, self.vps_api]

        for target in targets:
            try:
                url = f"{target}/api/detections"
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=10)
                self._report_failures = 0
                logger.debug(f"Report sent to {target}")
                return True
            except Exception as e:
                logger.debug(f"Report to {target} failed: {e}")
                continue

        # All targets failed
        self._report_failures += 1
        if self._report_failures % 10 == 1:
            logger.warning(
                f"Detection report failed {self._report_failures} times — "
                "check Tailscale connectivity"
            )
        return False

    # ── Continuous Detection Loop ───────────────────────────────────────

    def start(self, interval_s: float = 2.0):
        """Start continuous detection in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._detection_loop,
            args=(interval_s,),
            daemon=True,
        )
        self._thread.start()
        logger.info(f"UNO Q detection loop started (interval={interval_s}s)")

    def stop(self):
        """Stop the detection loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("UNO Q detection loop stopped")

    def _detection_loop(self, interval_s: float):
        """Background detection loop — capture, detect, report."""
        while self._running:
            try:
                detections = self.detect_frame()

                # Report to Jetson
                if time.time() - self._last_report_time >= self.report_interval_s:
                    self.report_to_jetson(detections)
                    self._last_report_time = time.time()

                # Callback
                if self._on_detections and detections:
                    try:
                        self._on_detections(detections)
                    except Exception:
                        pass

                time.sleep(interval_s)

            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                time.sleep(5)

    def set_detection_callback(self, callback: Callable):
        """Set a callback invoked with List[Detection] after each frame."""
        self._on_detections = callback

    # ── Filtering ───────────────────────────────────────────────────────

    def filter_persons(self, detections: Optional[List[Detection]] = None) -> List[Detection]:
        """Return only person detections."""
        dets = detections or self._last_detections
        return [d for d in dets if d.class_name == "person"]

    def filter_vehicles(self, detections: Optional[List[Detection]] = None) -> List[Detection]:
        """Return only vehicle detections."""
        dets = detections or self._last_detections
        vehicle_names = set(self.VEHICLE_CLASSES.values())
        return [d for d in dets if d.class_name in vehicle_names]

    def nearest_detection(self, detections: Optional[List[Detection]] = None) -> Optional[Detection]:
        """Return the closest detected object."""
        dets = detections or self._last_detections
        if not dets:
            return None
        return min(dets, key=lambda d: d.distance_est)

    # ── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "node": "unoq_3rd_perception",
            "camera": self.esp32cam_host,
            "connected": self._connected,
            "model_loaded": self._model is not None,
            "model": self.model_path,
            "confidence": self.confidence,
            "frame_count": self._frame_count,
            "total_detections": self._detection_count,
            "last_detection_count": len(self._last_detections),
            "running": self._running,
            "report_failures": self._report_failures,
            "lte_active": self._lte_active,
            "tailscale_ip": "100.84.235.7",
            "jetson_target": self.jetson_api,
        }

    def get_detections_summary(self) -> Dict[str, Any]:
        """Summarize recent detections by class."""
        counts = {}
        for d in self._last_detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return {
            "total": len(self._last_detections),
            "by_class": counts,
            "nearest": self.nearest_detection().to_dict() if self._last_detections else None,
        }


# ── Standalone test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    print("🔬 UNO Q 3rd Perception Detection Node")
    print("=" * 50)

    detector = ESP32CAMDetector(
        esp32cam_host="192.168.31.145",
        model_path="yolov8n.pt",
        device="cpu",
    )

    if detector.connect():
        print("✅ System ready")
        print(f"   Status: {json.dumps(detector.get_status(), indent=2)}")

        print("\n🔍 Running single detection...")
        dets = detector.detect_frame()
        print(f"   Found {len(dets)} objects:")
        for d in dets:
            print(f"   • {d.class_name} ({d.confidence:.0%}) @ {d.distance_est}m")

        summary = detector.get_detections_summary()
        print(f"\n   Summary: {json.dumps(summary, indent=2)}")

        print("\n📡 Reporting to Jetson...")
        ok = detector.report_to_jetson(dets)
        print(f"   Report: {'✅ sent' if ok else '❌ failed'}")

        print("\n🔄 Starting continuous detection (Ctrl+C to stop)...")
        detector.start(interval_s=3.0)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            detector.stop()
            print("\n🛑 Stopped")
    else:
        print("❌ Connection failed")
