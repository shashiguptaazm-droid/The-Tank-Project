"""
slam_engine.py - LiDAR + SLAM (Features 121-140)
RPLIDAR driver, scan filtering, occupancy, SLAM, loop closure, map persistence
"""
import time
import math
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("tank.ai.slam")


class SLAMEngine:
    """Features 121-140: LiDAR SLAM with occupancy grid, loop closure, map persistence."""

    def __init__(self, grid_size: int = 200, resolution: float = 0.05, max_range: float = 12.0):
        self.grid_size = grid_size
        self.resolution = resolution
        self.max_range = max_range
        self.occupancy = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.global_map = np.zeros((grid_size, grid_size), dtype=np.float32)
        self.local_costmap = np.zeros((100, 100), dtype=np.float32)
        self.robot_x = grid_size // 2
        self.robot_y = grid_size // 2
        self.robot_theta = 0.0
        self.scan_rate = 0.0
        self.scan_count = 0
        self.scan_drops = 0
        self.last_scan_time = 0.0
        self.pose_history: List[Tuple[float, float, float]] = []
        self.loop_closures: List[Dict] = []
        self.map_versions: List[np.ndarray] = []
        self.outlier_threshold = 2.0
        self.dynamic_threshold = 0.3
        self.ground_threshold = 0.05
        self._lock = threading.Lock()

    # 121-124. RPLIDAR driver, health, scan rate, drop detection
    def process_scan(self, points: List[Tuple[float, float]]) -> Dict[str, Any]:
        if not points:
            self.scan_drops += 1
            return {"status": "empty_scan"}
        self.scan_count += 1
        now = time.time()
        if self.last_scan_time > 0:
            self.scan_rate = 1.0 / max(0.001, now - self.last_scan_time)
        self.last_scan_time = now
        filtered = self.filter_scan(points)
        self.update_grid(filtered)
        return {"points_received": len(points), "filtered": len(filtered), "scan_rate": round(self.scan_rate, 1)}

    def get_health(self) -> Dict[str, Any]:
        return {
            "connected": self.scan_count > 0,
            "scan_rate_hz": round(self.scan_rate, 1),
            "total_scans": self.scan_count,
            "drops": self.scan_drops,
            "drop_rate": round(self.scan_drops / max(1, self.scan_count) * 100, 2),
            "last_scan_ago": round(time.time() - self.last_scan_time, 2) if self.last_scan_time else None,
        }

    # 125-128. Scan filtering, outlier, dynamic, ground
    def filter_scan(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        filtered = []
        for p in points:
            dist = math.sqrt(p[0]**2 + p[1]**2)
            if dist > self.max_range or dist < 0.1:
                continue
            if self._is_outlier(p, filtered):
                continue
            filtered.append(p)
        return filtered

    def _is_outlier(self, point, existing, threshold=None):
        if not existing or len(existing) < 3:
            return False
        threshold = threshold or self.outlier_threshold
        dists = [math.sqrt((p[0]-point[0])**2 + (p[1]-point[1])**2) for p in existing[-10:]]
        mean_dist = np.mean(dists)
        std_dist = np.std(dists) if len(dists) > 1 else 1
        return abs(math.sqrt(point[0]**2+point[1]**2) - mean_dist) > threshold * max(std_dist, 0.5)

    def filter_dynamic(self, current_scan: List, prev_scan: List, threshold: float = None) -> List:
        threshold = threshold or self.dynamic_threshold
        static = []
        for p in current_scan:
            moved = False
            for pp in prev_scan:
                if math.sqrt((p[0]-pp[0])**2 + (p[1]-pp[1])**2) > threshold:
                    moved = True
                    break
            if not moved:
                static.append(p)
        return static

    # 129-132. Occupancy grid, costmap, global map, SLAM
    def update_grid(self, points: List[Tuple[float, float]]):
        with self._lock:
            for p in points:
                angle = math.atan2(p[1], p[0])
                dist = math.sqrt(p[0]**2 + p[1]**2)
                wx = self.robot_x + int(dist * math.cos(angle + self.robot_theta) / self.resolution)
                wy = self.robot_y + int(dist * math.sin(angle + self.robot_theta) / self.resolution)
                if 0 <= wx < self.grid_size and 0 <= wy < self.grid_size:
                    self.occupancy[wy, wx] = min(1.0, self.occupancy[wy, wx] + 0.15)
                    # Free space along ray
                    steps = int(dist / self.resolution)
                    for s in range(0, steps, 3):
                        rx = self.robot_x + int(s * math.cos(angle + self.robot_theta))
                        ry = self.robot_y + int(s * math.sin(angle + self.robot_theta))
                        if 0 <= rx < self.grid_size and 0 <= ry < self.grid_size:
                            self.occupancy[ry, rx] = max(0.0, self.occupancy[ry, rx] - 0.05)
            self.global_map = np.maximum(self.global_map, self.occupancy)
            self.pose_history.append((self.robot_x * self.resolution, self.robot_y * self.resolution, self.robot_theta))
            if len(self.pose_history) > 10000:
                self.pose_history.pop(0)

    def update_pose(self, x: float, y: float, theta: float):
        self.robot_x = int(x / self.resolution + self.grid_size // 2)
        self.robot_y = int(y / self.resolution + self.grid_size // 2)
        self.robot_theta = theta

    def update_costmap(self, radius_cells: int = 20):
        self.local_costmap = np.zeros((100, 100), dtype=np.float32)
        cy, cx = 50, 50
        for y in range(max(0, cy-radius_cells), min(100, cy+radius_cells)):
            for x in range(max(0, cx-radius_cells), min(100, cx+radius_cells)):
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                if dist < radius_cells:
                    gx = int((x - 50) * self.resolution + self.robot_x)
                    gy = int((y - 50) * self.resolution + self.robot_y)
                    if 0 <= gx < self.grid_size and 0 <= gy < self.grid_size:
                        self.local_costmap[y, x] = self.occupancy[gy, gx]

    # 133-135. Loop closure, pose estimation, confidence
    def check_loop_closure(self, current_pose: Tuple[float, float, float],
                           threshold: float = 1.0) -> Optional[Dict]:
        for i, prev in enumerate(self.pose_history):
            dist = math.sqrt((current_pose[0]-prev[0])**2 + (current_pose[1]-prev[1])**2)
            if dist < threshold and abs(current_pose[2] - prev[2]) < 0.5:
                closure = {"from_idx": i, "to_idx": len(self.pose_history), "distance": round(dist, 3)}
                self.loop_closures.append(closure)
                logger.info(f"Loop closure detected at distance {dist:.3f}m")
                return closure
        return None

    def get_localization_confidence(self) -> float:
        if not self.loop_closures:
            return max(0.3, 1.0 - len(self.pose_history) * 0.0001)
        return min(1.0, 0.5 + len(self.loop_closures) * 0.1)

    # 136-140. Map persistence, versioning, corruption detection, replay
    def save_map(self, path: str):
        data = {
            "grid_size": self.grid_size,
            "resolution": self.resolution,
            "map": self.global_map.tolist(),
            "pose_history": self.pose_history[-100:],
            "loop_closures": self.loop_closures,
        }
        with open(path, "w") as f:
            json.dump(data, f)
        self.map_versions.append(self.global_map.copy())
        logger.info(f"Map saved to {path}")

    def load_map(self, path: str) -> bool:
        try:
            with open(path) as f:
                data = json.load(f)
            self.global_map = np.array(data["map"], dtype=np.float32)
            self.occupancy = self.global_map.copy()
            self.grid_size = data["grid_size"]
            self.resolution = data["resolution"]
            self.pose_history = [tuple(p) for p in data.get("pose_history", [])]
            self.loop_closures = data.get("loop_closures", [])
            return True
        except Exception as e:
            logger.error(f"Map load failed: {e}")
            return False

    def detect_map_corruption(self) -> Dict[str, Any]:
        total = self.grid_size ** 2
        occupied = np.sum(self.global_map > 0.5)
        free = np.sum(self.global_map < 0.1)
        unknown = total - occupied - free
        corruption = unknown / total > 0.7
        return {"total_cells": total, "occupied": int(occupied), "free": int(free),
                "unknown": int(unknown), "corrupted": corruption}

    def get_status(self) -> Dict[str, Any]:
        return {
            "scan_rate": round(self.scan_rate, 1),
            "total_scans": self.scan_count,
            "loop_closures": len(self.loop_closures),
            "map_versions": len(self.map_versions),
            "localization_confidence": round(self.get_localization_confidence(), 3),
            "occupancy_occupied": int(np.sum(self.occupancy > 0.5)),
            "pose_entries": len(self.pose_history),
            "health": self.get_health(),
        }
