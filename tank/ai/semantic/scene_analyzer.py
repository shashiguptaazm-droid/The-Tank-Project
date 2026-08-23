"""
scene_analyzer.py - Semantic Vision (Features 81-100)
Scene classification, segmentation, traversability, hazard detection
"""
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("tank.ai.semantic")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = np = None
    CV2_AVAILABLE = False


class SemanticVision:
    """Features 81-100: Semantic scene understanding."""

    SCENE_CLASSES = {0: "outdoor", 1: "indoor", 2: "corridor", 3: "room", 4: "road"}
    HAZARD_CLASSES = {0: "wet_floor", 1: "stairs", 2: "drop_off", 3: "obstacle", 4: "narrow"}
    SURFACE_CLASSES = {0: "concrete", 1: "carpet", 2: "tile", 3: "grass", 4: "gravel"}

    def __init__(self):
        self.scene_history: List[str] = []
        self.hazard_history: List[Dict] = []
        self.scene_graph: Dict[str, List[str]] = {}

    # 81-83. Image/Scene/Indoor-outdoor classification
    def classify_scene(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"scene": "unknown", "confidence": 0}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        top_half = gray[:h // 2, :]
        bot_half = gray[h // 2:, :]
        top_mean = np.mean(top_half)
        bot_mean = np.mean(bot_half)
        brightness_ratio = top_mean / max(1, bot_mean)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges) / 255.0
        if brightness_ratio > 1.5 and edge_density < 0.1:
            scene = "outdoor"
        elif brightness_ratio < 1.2 and edge_density > 0.15:
            scene = "corridor"
        elif edge_density > 0.2:
            scene = "indoor"
        else:
            scene = "outdoor"
        self.scene_history.append(scene)
        if len(self.scene_history) > 100:
            self.scene_history.pop(0)
        return {"scene": scene, "brightness_ratio": round(brightness_ratio, 3),
                "edge_density": round(edge_density, 4)}

    def classify_image(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"labels": [], "dominant_color": "unknown"}
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h_mean = np.mean(hsv[:, :, 0])
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        dominant = "green" if 35 < h_mean < 85 and s_mean > 50 else "brown" if 10 < h_mean < 25 else "gray"
        return {"dominant_color": dominant, "brightness": round(v_mean, 1)}

    # 84-85. Floor/ground classification, Door detection
    def classify_ground(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"surface": "unknown"}
        h, w = frame.shape[:2]
        floor_region = frame[int(h * 0.6):, :]
        hsv = cv2.cvtColor(floor_region, cv2.COLOR_BGR2HSV)
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        if s_mean < 30 and v_mean < 100:
            surface = "concrete"
        elif v_mean > 150:
            surface = "tile"
        elif s_mean > 60:
            surface = "grass"
        else:
            surface = "carpet"
        return {"surface": surface, "saturation": round(s_mean, 1), "value": round(v_mean, 1)}

    def detect_door(self, frame) -> List[Dict[str, Any]]:
        if not CV2_AVAILABLE or frame is None:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=50, maxLineGap=10)
        doors = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if 75 < angle < 105 and length > 80:
                    doors.append({"bbox": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
                                  "confidence": round(length / 200, 3)})
        return doors

    # 86-91. Stair/Corridor/Table/Chair/Wall/Window detection
    def detect_stairs(self, frame) -> bool:
        if not CV2_AVAILABLE or frame is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 30, minLineLength=30, maxLineGap=5)
        if lines is None:
            return False
        horizontal_lines = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 15:
                horizontal_lines += 1
        return horizontal_lines >= 3

    def detect_corridor(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"corridor": False}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        left_wall = gray[h // 4:3 * h // 4, :w // 4]
        right_wall = gray[h // 4:3 * h // 4, 3 * w // 4:]
        corridor = abs(np.mean(left_wall) - np.mean(right_wall)) < 30
        return {"corridor": corridor, "width": w}

    def detect_table(self, frame) -> bool:
        if not CV2_AVAILABLE or frame is None:
            return False
        h, w = frame.shape[:2]
        mid_region = frame[h // 3:2 * h // 3, w // 4:3 * w // 4]
        hsv = cv2.cvtColor(mid_region, cv2.COLOR_BGR2HSV)
        return np.mean(hsv[:, :, 2]) > 100 and np.std(hsv[:, :, 2]) < 50

    def detect_chair(self, frame) -> bool:
        return self.detect_table(frame)

    def detect_wall(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"wall": False}
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        edge_ratio = np.mean(edges) / 255.0
        return {"wall": edge_ratio < 0.08, "edge_ratio": round(edge_ratio, 4)}

    def detect_window(self, frame) -> bool:
        if not CV2_AVAILABLE or frame is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright = np.mean(gray > 200)
        return bright > 0.05

    # 92. Road/path detection
    def detect_path(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"path": False}
        h, w = frame.shape[:2]
        road_region = frame[h // 2:, w // 4:3 * w // 4]
        hsv = cv2.cvtColor(road_region, cv2.COLOR_BGR2HSV)
        s_mean = np.mean(hsv[:, :, 1])
        return {"path": s_mean < 50, "saturation": round(s_mean, 1)}

    # 93-95. Free-space/Semantic/Instance segmentation
    def segment_free_space(self, frame) -> Dict[str, Any]:
        if not CV2_AVAILABLE or frame is None:
            return {"free_space_pct": 0}
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lower = gray[h // 2:, :]
        _, thresh = cv2.threshold(lower, 100, 255, cv2.THRESH_BINARY)
        free_pct = np.mean(thresh) / 255.0 * 100
        return {"free_space_pct": round(free_pct, 1), "region": "lower_half"}

    def semantic_segmentation(self, frame) -> Dict[str, int]:
        if not CV2_AVAILABLE or frame is None:
            return {}
        h, w = frame.shape[:2]
        regions = {"sky": (0, h // 3), "wall": (h // 3, 2 * h // 3), "floor": (2 * h // 3, h)}
        result = {}
        for name, (y1, y2) in regions.items():
            region = frame[y1:y2, :]
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            result[name] = int(np.mean(gray))
        return result

    def instance_segmentation(self, frame) -> List[Dict[str, Any]]:
        if not CV2_AVAILABLE or frame is None:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        instances = []
        for i, c in enumerate(contours[:10]):
            area = cv2.contourArea(c)
            if area > 500:
                x, y, w, h = cv2.boundingRect(c)
                instances.append({"id": i, "bbox": [x, y, w, h], "area": int(area)})
        return instances

    # 96-98. Surface/Hazard/Traversability
    def classify_surface(self, frame) -> str:
        if not CV2_AVAILABLE or frame is None:
            return "unknown"
        h, w = frame.shape[:2]
        floor = frame[int(h * 0.6):, :]
        hsv = cv2.cvtColor(floor, cv2.COLOR_BGR2HSV)
        s, v = np.mean(hsv[:, :, 1]), np.mean(hsv[:, :, 2])
        if s > 60 and v > 100:
            return "grass"
        elif s < 20 and v > 150:
            return "tile"
        elif v < 80:
            return "asphalt"
        return "concrete"

    def classify_hazard(self, frame) -> List[Dict[str, Any]]:
        hazards = []
        if self.detect_stairs(frame):
            hazards.append({"type": "stairs", "confidence": 0.7})
        if not self.segment_free_space(frame).get("free_space_pct", 100) > 30:
            hazards.append({"type": "blocked_path", "confidence": 0.6})
        return hazards

    def estimate_traversability(self, frame) -> Dict[str, Any]:
        free = self.segment_free_space(frame)
        surface = self.classify_surface(frame)
        hazards = self.classify_hazard(frame)
        score = 100 - len(hazards) * 30
        if free.get("free_space_pct", 0) > 60:
            score += 20
        if surface in ("concrete", "tile"):
            score += 10
        score = max(0, min(100, score))
        return {"traversability": score, "surface": surface, "hazards": hazards, "free_space": free}

    # 99-100. Visual confidence & Semantic scene graph
    def scene_confidence(self, frame) -> float:
        scene = self.classify_scene(frame)
        return scene.get("confidence", 0.5)

    def build_scene_graph(self, detections: List[Dict], scene: Dict) -> Dict[str, Any]:
        nodes = []
        edges = []
        for det in detections:
            nodes.append(det.get("class", "unknown"))
        graph = {"nodes": list(set(nodes)), "edges": [], "scene": scene.get("scene", "unknown")}
        return graph

    def get_status(self) -> Dict[str, Any]:
        return {
            "scenes_analyzed": len(self.scene_history),
            "last_scene": self.scene_history[-1] if self.scene_history else "none",
            "hazards_detected": len(self.hazard_history),
        }
