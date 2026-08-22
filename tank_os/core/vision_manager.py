"""TankOS Vision Manager — camera, YOLO detections, face recognition, AprilTags, tracking."""

from __future__ import annotations
import logging, threading, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from tank_os.core.event_bus import Event, EventBus


@dataclass
class Detection:
    label: str; confidence: float; x: float; y: float; w: float; h: float


class VisionManager:
    _instance: Optional["VisionManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._camera_active = False
                cls._instance._last_frame: Any = None
                cls._instance._detections: List[Detection] = []
                cls._instance._yolo_available = False
                cls._instance._yolo_model: Any = None
                cls._instance._cap: Any = None
            return cls._instance

    def initialize(self) -> None:
        self._check_yolo()
        logger.info("VisionManager initialized")

    def _check_yolo(self) -> None:
        try:
            from ultralytics import YOLO  # noqa: F401
            self._yolo_available = True
        except ImportError:
            self._yolo_available = False

    def start_camera(self, device: str = "/dev/video0") -> bool:
        try:
            import cv2
            self._cap = cv2.VideoCapture(device)
            self._camera_active = self._cap.isOpened()
            if self._camera_active:
                self._bus.emit(Event("camera_started", {"device": device}))
            return self._camera_active
        except Exception as exc:
            logger.warning("Camera start failed: %s", exc)
            return False

    def stop_camera(self) -> None:
        try:
            if hasattr(self, '_cap') and self._cap:
                self._cap.release()
        except Exception: pass
        self._camera_active = False
        self._bus.emit(Event("camera_stopped", {}))

    def capture_frame(self) -> Optional[bytes]:
        if not self._camera_active: return None
        try:
            import cv2
            ret, frame = self._cap.read()
            if ret:
                _, buf = cv2.imencode('.jpg', frame)
                return buf.tobytes()
        except Exception: pass
        return None

    def detect_objects(self, frame: Any = None) -> List[Detection]:
        if not self._yolo_available: return []
        try:
            from ultralytics import YOLO
            if self._yolo_model is None:
                self._yolo_model = YOLO("yolov8n.pt")
            results = self._yolo_model(frame or self._last_frame)
            dets = []
            for r in results:
                for box in r.boxes:
                    dets.append(Detection(
                        label=r.names[int(box.cls[0])],
                        confidence=float(box.conf[0]),
                        x=float(box.xyxy[0][0]), y=float(box.xyxy[0][1]),
                        w=float(box.xyxy[0][2] - box.xyxy[0][0]),
                        h=float(box.xyxy[0][3] - box.xyxy[0][1]),
                    ))
            self._detections = dets
            self._bus.emit(Event("objects_detected", {"count": len(dets)}))
            return dets
        except Exception: return []

    @property
    def is_camera_active(self) -> bool: return self._camera_active
    @property
    def is_yolo_available(self) -> bool: return self._yolo_available
    @property
    def detections(self) -> List[Detection]: return list(self._detections)


logger = logging.getLogger("tank_os.vision_manager")
