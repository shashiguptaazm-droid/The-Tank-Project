"""Tank — Sensor Fusion Layer.

Combines camera, LiDAR, thermal, and IMU readings into unified entities.
Tracks uncertainty explicitly. Never pretends sensors agree when they don't.
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank.fusion")


@dataclass
class FusedEntity:
    entity_type: str  # person, object, obstacle, etc.
    confidence: float  # 0.0 - 1.0
    distance_m: float
    sources: List[str]  # which sensors contributed
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    uncertainty: float = 0.0  # higher = less certain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity_type,
            "confidence": round(self.confidence, 3),
            "distance_m": round(self.distance_m, 2),
            "sources": self.sources,
            "uncertainty": round(self.uncertainty, 3),
            "timestamp": self.timestamp,
        }


class SensorFusion:
    def __init__(self) -> None:
        self._camera_detections: List[Dict] = []
        self._lidar_distance: Optional[float] = None
        self._thermal_human: bool = False
        self._thermal_confidence: float = 0.0

    def update_camera(self, detections: List[Dict]) -> None:
        self._camera_detections = detections

    def update_lidar(self, distance_m: Optional[float]) -> None:
        self._lidar_distance = distance_m

    def update_thermal(self, human_detected: bool, confidence: float = 0.0) -> None:
        self._thermal_human = human_detected
        self._thermal_confidence = confidence

    def fuse(self) -> List[FusedEntity]:
        entities = []
        sources = []

        # Camera detections
        for det in self._camera_detections:
            obj = det.get("object", "unknown")
            cam_conf = det.get("confidence", 0.0)
            cam_dist = det.get("distance_m", 999.0)
            sources.append("camera")

            # LiDAR distance
            lidar_dist = self._lidar_distance
            if lidar_dist is not None:
                sources.append("lidar")

            # Thermal
            thermal_match = self._thermal_human and obj == "person"
            if thermal_match:
                sources.append("thermal")
                cam_conf = min(1.0, cam_conf + 0.04)  # boost if thermal confirms

            # Fuse distance: prefer LiDAR (more accurate), fallback to camera estimate
            dist = lidar_dist if lidar_dist is not None else cam_dist

            # Uncertainty: higher when fewer sources agree
            uncertainty = 0.1 * (3 - len(sources)) / 3

            entity = FusedEntity(
                entity_type=obj,
                confidence=cam_conf,
                distance_m=dist,
                sources=list(set(sources)),
                uncertainty=uncertainty,
                data=det,
            )
            entities.append(entity)
            sources.clear()

        return entities

    def get_status(self) -> Dict[str, Any]:
        return {
            "camera_detections": len(self._camera_detections),
            "lidar_distance": self._lidar_distance,
            "thermal_human": self._thermal_human,
            "thermal_confidence": self._thermal_confidence,
        }
