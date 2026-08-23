"""
lidar_processor.py — LiDAR Processing Pipeline
Standardized LaserScan, health monitoring, obstacle detection,
occupancy grid, camera-LiDAR fusion, free-space detection, sync.
"""
import time
import math
import json
import logging
import threading
import numpy as np
from datetime import datetime
from collections import deque

logger = logging.getLogger("tank.perception.lidar")


class LidarHealth:
    def __init__(self):
        self.connected = False
        self.scan_count = 0
        self.last_scan_time = 0
        self.avg_rpm = 0
        self.avg_points = 0
        self.consecutive_failures = 0
        self.total_points = 0

    def record_scan(self, num_points, rpm=0):
        self.connected = True
        self.scan_count += 1
        self.last_scan_time = time.time()
        self.avg_rpm = 0.9 * self.avg_rpm + 0.1 * rpm if rpm > 0 else self.avg_rpm
        self.avg_points = 0.9 * self.avg_points + 0.1 * num_points
        self.total_points += num_points
        self.consecutive_failures = 0

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures > 10:
            self.connected = False

    def is_healthy(self):
        return self.connected and self.consecutive_failures < 5

    def to_dict(self):
        return {
            "connected": self.connected,
            "healthy": self.is_healthy(),
            "scan_count": self.scan_count,
            "avg_rpm": round(self.avg_rpm, 1),
            "avg_points": round(self.avg_points),
            "total_points": self.total_points,
            "consecutive_failures": self.consecutive_failures,
        }


class OccupancyGrid:
    def __init__(self, width=200, height=200, resolution=0.1):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.grid = np.full((height, width), 0.5, dtype=np.float32)
        self.robot_x = width // 2
        self.robot_y = height // 2

    def update_from_scan(self, ranges, angles):
        for r, a in zip(ranges, angles):
            if r <= 0 or r > 12:
                continue
            abs_angle = a
            wx = self.robot_x + int(r * math.cos(abs_angle) / self.resolution)
            wy = self.robot_y + int(r * math.sin(abs_angle) / self.resolution)
            if 0 <= wx < self.width and 0 <= wy < self.height:
                self.grid[wy][wx] = min(1.0, self.grid[wy][wx] + 0.3)
            steps = int(r / self.resolution / 2)
            for s in range(steps):
                sx = self.robot_x + int(s * self.resolution * math.cos(abs_angle) / self.resolution)
                sy = self.robot_y + int(s * self.resolution * math.sin(abs_angle) / self.resolution)
                if 0 <= sx < self.width and 0 <= sy < self.height:
                    self.grid[sy][sx] = max(0.0, self.grid[sy][sx] - 0.05)

    def get_obstacles(self, threshold=0.6):
        obstacles = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] > threshold:
                    wx = (x - self.robot_x) * self.resolution
                    wy = (y - self.robot_y) * self.resolution
                    dist = math.sqrt(wx * wx + wy * wy)
                    angle = math.atan2(wy, wx)
                    obstacles.append({"x": round(wx, 2), "y": round(wy, 2), "distance": round(dist, 2), "angle": round(math.degrees(angle), 1)})
        return obstacles

    def get_free_space(self):
        free = []
        for angle_deg in range(0, 360, 10):
            angle = math.radians(angle_deg)
            for dist in np.arange(0.2, 10, self.resolution):
                gx = int(self.robot_x + dist * math.cos(angle) / self.resolution)
                gy = int(self.robot_y + dist * math.sin(angle) / self.resolution)
                if 0 <= gx < self.width and 0 <= gy < self.height:
                    if self.grid[gy][gx] < 0.3:
                        continue
                    free.append({"angle": angle_deg, "max_distance": round(dist, 2)})
                    break
        return free

    def to_json(self):
        return {
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "obstacles": len(self.get_obstacles()),
        }


class LidarProcessor:
    def __init__(self, port="/dev/ttyUSB0", baud=115200, simulated=False):
        self.port = port
        self.baud = baud
        self.simulated = simulated
        self.health = LidarHealth()
        self.occupancy = OccupancyGrid()
        self.latest_scan = None
        self._lock = threading.Lock()
        self._running = False
        self._callbacks = []
        self._ranges = np.array([])
        self._angles = np.array([])

        self.lidar = None
        self.obstacle_zones = {"front": [], "left": [], "right": [], "rear": []}

    def start(self):
        self._running = True
        if self.simulated:
            self._start_simulated()
        else:
            self._start_real()

    def _start_real(self):
        try:
            from rplidar import RPLidar
            self.lidar = RPLidar(self.port, baudrate=self.baud)
            self.health.connected = True
            logger.info(f"LiDAR connected on {self.port}")
            thread = threading.Thread(target=self._real_scan_loop, daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"LiDAR connect failed: {e}")
            self._start_simulated()

    def _real_scan_loop(self):
        try:
            for scan in self.lidar.iter_scans():
                if not self._running:
                    break
                ranges = np.array([m[2] / 1000.0 for m in scan])
                angles = np.array([m[1] for m in scan])
                angles_rad = np.radians(angles)

                with self._lock:
                    self._ranges = ranges
                    self._angles = angles_rad
                    self.latest_scan = {
                        "ranges": ranges.tolist(),
                        "angles": angles.tolist(),
                        "angle_min": float(angles.min()),
                        "angle_max": float(angles.max()),
                        "range_min": float(ranges.min()),
                        "range_max": float(ranges.max()),
                        "num_points": len(ranges),
                        "timestamp": time.time(),
                    }

                self.health.record_scan(len(ranges), 600)
                self.occupancy.update_from_scan(ranges, angles_rad)
                self._update_obstacle_zones(ranges, angles_rad)

                for cb in self._callbacks:
                    cb(self.latest_scan)
        except Exception as e:
            logger.error(f"LiDAR scan error: {e}")
            self.health.record_failure()

    def _start_simulated(self):
        logger.info("LiDAR running in simulated mode")
        thread = threading.Thread(target=self._simulated_loop, daemon=True)
        thread.start()

    def _simulated_loop(self):
        angles = np.linspace(0, 2 * math.pi, 360)
        while self._running:
            ranges = np.array([2.0 + 0.5 * math.sin(a * 3) + np.random.uniform(-0.1, 0.1) for a in angles])
            ranges = np.clip(ranges, 0.1, 12.0)

            with self._lock:
                self._ranges = ranges
                self._angles = angles
                self.latest_scan = {
                    "ranges": ranges.tolist(),
                    "angles": (np.degrees(angles)).tolist(),
                    "angle_min": 0,
                    "angle_max": 360,
                    "range_min": float(ranges.min()),
                    "range_max": float(ranges.max()),
                    "num_points": len(ranges),
                    "timestamp": time.time(),
                }

            self.health.record_scan(len(ranges), 600)
            self.occupancy.update_from_scan(ranges, angles)
            self._update_obstacle_zones(ranges, angles)

            for cb in self._callbacks:
                cb(self.latest_scan)
            time.sleep(0.2)

    def _update_obstacle_zones(self, ranges, angles):
        zones = {"front": [], "left": [], "right": [], "rear": []}
        for r, a in zip(ranges, angles):
            a_deg = math.degrees(a) % 360
            if 315 < a_deg or a_deg < 45:
                zones["front"].append(r)
            elif 45 < a_deg < 135:
                zones["left"].append(r)
            elif 135 < a_deg < 225:
                zones["rear"].append(r)
            elif 225 < a_deg < 315:
                zones["right"].append(r)
        self.obstacle_zones = {z: min(vals) if vals else 99.0 for z, vals in zones.items()}

    def stop(self):
        self._running = False
        if self.lidar:
            try:
                self.lidar.stop()
                self.lidar.disconnect()
            except:
                pass

    def on_scan(self, callback):
        self._callbacks.append(callback)

    def get_ranges(self):
        with self._lock:
            return self._ranges.copy() if len(self._ranges) > 0 else np.array([])

    def get_angles(self):
        with self._lock:
            return self._angles.copy() if len(self._angles) > 0 else np.array([])

    def get_obstacle_zones(self):
        return self.obstacle_zones

    def get_nearest_obstacle(self):
        ranges = self.get_ranges()
        if len(ranges) == 0:
            return 99.0
        valid = ranges[ranges > 0.1]
        return float(valid.min()) if len(valid) > 0 else 99.0

    def fuse_with_camera(self, camera_detections, image_width=640):
        fused = []
        ranges = self.get_ranges()
        angles = self.get_angles()
        if len(ranges) == 0:
            return fused

        for det in camera_detections:
            pixel_cx = det.get("cx", image_width / 2)
            pixel_offset = (pixel_cx - image_width / 2) / (image_width / 2)
            angle_rad = pixel_offset * math.radians(60)
            angle_idx = np.argmin(np.abs(angles - angle_rad))
            distance = float(ranges[angle_idx]) if 0 <= angle_idx < len(ranges) else -1
            fused.append({
                **det,
                "lidar_distance": round(distance, 2),
                "fused": distance > 0,
            })
        return fused

    def get_laserscan_msg(self):
        scan = self.latest_scan
        if not scan:
            return None
        return {
            "header": {"frame_id": "laser", "stamp": datetime.now().isoformat()},
            "angle_min": scan["angle_min"],
            "angle_max": scan["angle_max"],
            "angle_increment": math.radians(1),
            "time_increment": 0,
            "scan_time": 0.1,
            "range_min": 0.15,
            "range_max": 12.0,
            "ranges": scan["ranges"],
        }

    def get_health(self):
        return self.health.to_dict()

    def get_status(self):
        return {
            "port": self.port,
            "simulated": self.simulated,
            "health": self.health.to_dict(),
            "nearest_obstacle_m": round(self.get_nearest_obstacle(), 2),
            "zones": {k: round(v, 2) for k, v in self.obstacle_zones.items()},
            "occupancy": self.occupancy.to_json(),
            "scan_points": len(self._ranges),
        }
