"""
yolo_detector.py - Object Detection (Features 41-60)
"""
import time, math, logging
from typing import Dict, Any, List, Optional, Tuple
logger = logging.getLogger("tank.ai.detection")
try:
    import cv2, numpy as np; CV2_AVAILABLE = True
except ImportError: cv2 = np = None; CV2_AVAILABLE = False
try:
    from ultralytics import YOLO; YOLO_AVAILABLE = True
except ImportError: YOLO_AVAILABLE = False

PERSON_CLASSES = {0: "person"}
VEHICLE_CLASSES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

class Detection:
    def __init__(self, class_id, class_name, confidence, bbox, center):
        self.class_id = class_id; self.class_name = class_name
        self.confidence = confidence; self.bbox = bbox; self.center = center
        self.area = bbox[2]*bbox[3]; self.distance_est = 0; self.size_est = 0; self.timestamp = time.time()
    def to_dict(self):
        return {"class": self.class_name, "confidence": round(self.confidence,3), "bbox": list(self.bbox), "center": list(self.center), "area": self.area, "distance_est": self.distance_est}

class YOLODetector:
    def __init__(self, model_path="yolov8n.pt", confidence_threshold=0.5, device="cuda"):
        self.model_path = model_path; self.confidence_threshold = confidence_threshold
        self.device = device; self.model = None; self.frame_count = 0; self.total_detections = 0
        self.detection_history = []; self.class_filter = None
        self.load_model()
    def load_model(self):
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(self.model_path)
                logger.info(f"YOLO loaded: {self.model_path}")
            except Exception as e: logger.error(f"YOLO load failed: {e}")
    def detect(self, frame, class_filter=None):
        if not CV2_AVAILABLE or frame is None: return []
        self.frame_count += 1; detections = []
        if self.model and YOLO_AVAILABLE:
            try:
                results = self.model(frame, conf=self.confidence_threshold, device=self.device, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        if class_filter and cls_id not in class_filter: continue
                        if self.class_filter and cls_id not in self.class_filter: continue
                        conf = float(box.conf[0])
                        x1,y1,x2,y2 = map(int, box.xyxy[0])
                        cx,cy = (x1+x2)//2, (y1+y2)//2
                        name = r.names.get(cls_id, f"class_{cls_id}")
                        det = Detection(cls_id, name, conf, (x1,y1,x2,y2), (cx,cy))
                        det.distance_est = self._estimate_distance(frame, det)
                        detections.append(det)
            except Exception as e: logger.error(f"YOLO error: {e}")
        self.total_detections += len(detections)
        self.detection_history.append([d.to_dict() for d in detections])
        if len(self.detection_history) > 100: self.detection_history.pop(0)
        return detections
    def _estimate_distance(self, frame, det):
        h, w = frame.shape[:2]; ph = det.bbox[3] - det.bbox[1]
        if ph <= 0: return 999
        focal = w / 2.0; real_h = 1.7
        return round((real_h * focal) / ph, 2)
    def detect_persons(self, frame): return self.detect(frame, class_filter=set(PERSON_CLASSES.keys()))
    def detect_vehicles(self, frame): return self.detect(frame, class_filter=set(VEHICLE_CLASSES.keys()))
    def get_statistics(self):
        return {"frames": self.frame_count, "detections": self.total_detections, "avg_per_frame": round(self.total_detections/max(1,self.frame_count),2)}
    def get_status(self):
        return {"model": self.model_path, "loaded": self.model is not None, "device": self.device, "stats": self.get_statistics()}
