"""
yolo_engine.py — YOLO Inference Engine
TensorRT + CUDA acceleration, confidence filtering, class filtering,
object tracking, person/obstacle detection, GPU/CPU/RAM monitoring.
"""
import cv2
import time
import json
import logging
import threading
import numpy as np
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger("tank.ai.inference")


class PerformanceMetrics:
    def __init__(self):
        self.inference_times = []
        self.fps_history = []
        self.total_frames = 0
        self.total_inferences = 0
        self.gpu_util = 0
        self.cpu_util = 0
        self.ram_util = 0
        self.last_fps = 0
        self._start = time.time()

    def record_inference(self, inference_time_ms):
        self.inference_times.append(inference_time_ms)
        if len(self.inference_times) > 100:
            self.inference_times = self.inference_times[-100:]
        self.total_inferences += 1
        if len(self.inference_times) > 0:
            self.last_fps = 1000.0 / np.mean(self.inference_times)

    def get_stats(self):
        avg_ms = np.mean(self.inference_times) if self.inference_times else 0
        p95_ms = np.percentile(self.inference_times, 95) if self.inference_times else 0
        return {
            "avg_inference_ms": round(avg_ms, 2),
            "p95_inference_ms": round(p95_ms, 2),
            "last_fps": round(self.last_fps, 1),
            "total_inferences": self.total_inferences,
            "gpu_util_pct": self.gpu_util,
            "cpu_util_pct": self.cpu_util,
            "ram_util_pct": self.ram_util,
        }


class ObjectTracker:
    def __init__(self, max_disappeared=10):
        self.next_id = 0
        self.objects = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared

    def update(self, detections):
        if len(detections) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return self.objects

        new_centroids = []
        for det in detections:
            cx = (det["x1"] + det["x2"]) / 2
            cy = (det["y1"] + det["y2"]) / 2
            new_centroids.append((cx, cy))

        if len(self.objects) == 0:
            for i, centroid in enumerate(new_centroids):
                self.objects[self.next_id] = {
                    "centroid": centroid,
                    "label": detections[i]["label"],
                    "confidence": detections[i]["confidence"],
                    "bbox": (detections[i]["x1"], detections[i]["y1"], detections[i]["x2"], detections[i]["y2"]),
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "hit_count": 1,
                }
                self.disappeared[self.next_id] = 0
                self.next_id += 1
        else:
            obj_ids = list(self.objects.keys())
            obj_centroids = [self.objects[oid]["centroid"] for oid in obj_ids]

            D = np.zeros((len(obj_centroids), len(new_centroids)))
            for i, oc in enumerate(obj_centroids):
                for j, nc in enumerate(new_centroids):
                    D[i][j] = np.linalg.norm(np.array(oc) - np.array(nc))

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                obj_id = obj_ids[row]
                self.objects[obj_id]["centroid"] = new_centroids[col]
                self.objects[obj_id]["label"] = detections[col]["label"]
                self.objects[obj_id]["confidence"] = detections[col]["confidence"]
                self.objects[obj_id]["bbox"] = (detections[col]["x1"], detections[col]["y1"], detections[col]["x2"], detections[col]["y2"])
                self.objects[obj_id]["last_seen"] = time.time()
                self.objects[obj_id]["hit_count"] += 1
                self.disappeared[obj_id] = 0
                used_rows.add(row)
                used_cols.add(col)

            for row in set(range(D.shape[0])) - used_rows:
                obj_id = obj_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]

            for col in set(range(D.shape[1])) - used_cols:
                cx, cy = new_centroids[col]
                self.objects[self.next_id] = {
                    "centroid": (cx, cy),
                    "label": detections[col]["label"],
                    "confidence": detections[col]["confidence"],
                    "bbox": (detections[col]["x1"], detections[col]["y1"], detections[col]["x2"], detections[col]["y2"]),
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "hit_count": 1,
                }
                self.disappeared[self.next_id] = 0
                self.next_id += 1

        return self.objects

    def get_tracked_objects(self):
        return {
            oid: {
                "id": oid,
                "label": obj["label"],
                "confidence": obj["confidence"],
                "centroid": obj["centroid"],
                "bbox": obj["bbox"],
                "age_s": round(time.time() - obj["first_seen"], 1),
                "hits": obj["hit_count"],
            }
            for oid, obj in self.objects.items()
        }


class YOLOEngine:
    def __init__(self, model_path="yolov8n.pt", use_tensorrt=False):
        self.model_path = model_path
        self.model = None
        self.use_tensorrt = use_tensorrt
        self.tracker = ObjectTracker()
        self.metrics = PerformanceMetrics()
        self.confidence_threshold = 0.5
        self.iou_threshold = 0.45
        self.class_filter = None
        self.person_detection = True
        self.obstacle_detection = True
        self.device = "cuda" if self._check_cuda() else "cpu"
        self._lock = threading.Lock()

    def _check_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def load(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            if self.use_tensorrt and self.device == "cuda":
                try:
                    self.model.export(format="engine")
                    self.model = YOLO(f"{self.model_path}.engine")
                    logger.info("TensorRT engine loaded")
                except:
                    logger.info("TensorRT export failed, using PyTorch")
            logger.info(f"YOLO loaded: {self.model_path} on {self.device}")
            return True
        except Exception as e:
            logger.error(f"YOLO load failed: {e}")
            return False

    def infer(self, frame):
        if self.model is None:
            return []
        with self._lock:
            start = time.time()
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )
            inference_ms = (time.time() - start) * 1000
            self.metrics.record_inference(inference_ms)

            detections = []
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = r.names[cls]

                    if self.class_filter and name not in self.class_filter:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    detections.append({
                        "label": name,
                        "class_id": cls,
                        "confidence": round(conf, 3),
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                        "cx": round((x1 + x2) / 2, 1),
                        "cy": round((y1 + y2) / 2, 1),
                        "width": round(x2 - x1, 1),
                        "height": round(y2 - y1, 1),
                    })

            self.tracker.update(detections)
            return detections

    def infer_and_annotate(self, frame):
        detections = self.infer(frame)
        annotated = frame.copy()
        colors = {
            "person": (0, 0, 255), "car": (255, 0, 0), "dog": (0, 255, 0),
            "cat": (255, 255, 0), "chair": (128, 0, 128), "bottle": (0, 128, 255),
        }
        for det in detections:
            color = colors.get(det["label"], (0, 255, 0))
            cv2.rectangle(annotated, (int(det["x1"]), int(det["y1"])), (int(det["x2"]), int(det["y2"])), color, 2)
            label = f"{det['label']} {det['confidence']:.0%}"
            cv2.putText(annotated, label, (int(det["x1"]), int(det["y1"]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return annotated, detections

    def detect_persons(self, frame):
        self.class_filter = {"person"}
        detections = self.infer(frame)
        self.class_filter = None
        return detections

    def detect_obstacles(self, frame, min_size=500):
        detections = self.infer(frame)
        obstacles = [d for d in detections if d["width"] * d["height"] > min_size]
        return obstacles

    def get_detections_for_nav(self, frame):
        detections = self.infer(frame)
        result = {
            "persons": [d for d in detections if d["label"] == "person"],
            "obstacles": [d for d in detections if d["width"] * d["height"] > 500],
            "objects": detections,
            "tracked": self.tracker.get_tracked_objects(),
        }
        return result

    def set_confidence(self, threshold):
        self.confidence_threshold = max(0.1, min(0.95, threshold))

    def set_class_filter(self, classes):
        self.class_filter = set(classes) if classes else None

    def update_system_metrics(self):
        try:
            import psutil
            self.metrics.cpu_util = psutil.cpu_percent(interval=0.1)
            self.metrics.ram_util = psutil.virtual_memory().percent
            if self.device == "cuda":
                try:
                    import torch
                    self.metrics.gpu_util = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100 if torch.cuda.max_memory_allocated() > 0 else 0
                except:
                    pass
        except:
            pass

    def get_status(self):
        self.update_system_metrics()
        return {
            "model": self.model_path,
            "device": self.device,
            "confidence": self.confidence_threshold,
            "class_filter": list(self.class_filter) if self.class_filter else None,
            "loaded": self.model is not None,
            "tracked_objects": len(self.tracker.objects),
            "metrics": self.metrics.get_stats(),
        }

    def get_health(self):
        return {
            "healthy": self.model is not None,
            "model": self.model_path,
            "device": self.device,
            "metrics": self.metrics.get_stats(),
        }
