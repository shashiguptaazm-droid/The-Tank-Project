"""Tank — Unified AI Engine.

Application code calls AIEngine — it doesn't care if inference
happens locally, on VPS, or through an API.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.ai")


class AIEngine:
    def __init__(self, vps_client: Optional["VPSClient"] = None, local_model: str = "yolov8n.pt") -> None:
        self._vps = vps_client
        self._local_model = local_model
        self._online = True
        self._latencies: list = []

    def detect(self, image: Any = None, frame_data: bytes = b"") -> Dict[str, Any]:
        """Run object detection. Returns structured JSON."""
        start = time.time()
        try:
            if self._vps and self._vps.is_healthy():
                result = self._vps.detect(frame_data)
            else:
                result = self._local_detect(image)
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            result = {"objects": [], "error": str(e)}
        elapsed = time.time() - start
        self._latencies.append(elapsed)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        return result

    def classify(self, image: Any = None, label: str = "") -> Dict[str, Any]:
        """Classify an object. Returns structured JSON."""
        try:
            if self._vps and self._vps.is_healthy():
                return self._vps.classify(label)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
        return {"label": label, "confidence": 0.5, "source": "local"}

    def reason(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI reasoning about current situation. Returns structured JSON."""
        try:
            if self._vps and self._vps.is_healthy():
                return self._vps.reason(context)
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
        return {"situation": "unknown", "recommended_action": "idle", "confidence": 0.3}

    def analyze(self, fusion_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fused sensor data. Returns structured recommendation."""
        situation = "idle"
        action = "idle"
        priority = "normal"
        conf = fusion_result.get("confidence", 0.0)
        entity = fusion_result.get("entity", "unknown")
        dist = fusion_result.get("distance_m", 999.0)

        if entity == "person":
            if dist < 1.0:
                situation = "person_close"
                action = "track"
                priority = "high"
            else:
                situation = "person_detected"
                action = "approach"
                priority = "normal"
        elif entity == "obstacle":
            situation = "obstacle_detected"
            action = "retreat"
            priority = "high"

        return {
            "object": entity,
            "confidence": conf,
            "distance_m": dist,
            "situation": situation,
            "recommended_action": action,
            "priority": priority,
        }

    @property
    def avg_latency(self) -> float:
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0.0

    def _local_detect(self, image: Any) -> Dict[str, Any]:
        try:
            from ultralytics import YOLO
            model = YOLO(self._local_model)
            results = model(image, conf=0.5) if image is not None else []
            objects = []
            for r in results:
                for box in r.boxes:
                    objects.append({
                        "object": r.names[int(box.cls)],
                        "confidence": float(box.conf),
                        "bbox": box.xyxy.tolist(),
                    })
            return {"objects": objects, "source": "local_yolo"}
        except Exception as e:
            logger.warning(f"Local YOLO failed: {e}")
            return {"objects": [], "source": "unavailable"}
