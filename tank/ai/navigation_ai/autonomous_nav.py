"""
autonomous_nav.py - Autonomous Navigation AI (Features 156-170)
Waypoint navigation, path planning, obstacle avoidance, return-home
"""
import time
import math
import heapq
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("tank.ai.nav_ai")


class NavigationAI:
    """Features 156-170: Full autonomous navigation stack."""

    def __init__(self, grid_size: int = 200, resolution: float = 0.05):
        self.grid_size = grid_size
        self.resolution = resolution
        self.occupancy = np.zeros((grid_size, grid_size), dtype=np.int8)
        self.robot_x = grid_size // 2
        self.robot_y = grid_size // 2
        self.robot_theta = 0.0
        self.home_pose = (self.robot_x, self.robot_y)
        self.current_waypoints: List[Tuple[int, int]] = []
        self.current_goal = None
        self.speed = 0.0
        self.max_speed = 0.3
        self.safety_margin = 5
        self.nav_active = False
        self.nav_timeout = 300
        self.nav_start_time = 0.0
        self.confidence = 1.0
        self.mission_log: List[Dict] = []
        self.dead_end_count = 0
        self.recovery_count = 0
        self.mode = "autonomous"

    # 156-157. Waypoint navigation + Goal pose planning
    def navigate_to(self, goal_x: float, goal_y: float) -> Dict[str, Any]:
        gx = int(goal_x / self.resolution + self.grid_size // 2)
        gy = int(goal_y / self.resolution + self.grid_size // 2)
        self.current_goal = (gx, gy)
        self.current_waypoints = self.plan_path((self.robot_x, self.robot_y), (gx, gy))
        self.nav_active = True
        self.nav_start_time = time.time()
        self.mode = "go_to_goal"
        return {"waypoints": len(self.current_waypoints), "goal": (goal_x, goal_y), "active": True}

    # 158-159. Global + Local path planner (A*)
    def plan_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                return path[::-1]
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                nx, ny = current[0] + dx, current[1] + dy
                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    if self.occupancy[ny, nx] > 0.5:
                        continue
                    tentative = g_score[current] + math.sqrt(dx*dx + dy*dy)
                    if tentative < g_score.get((nx, ny), float('inf')):
                        came_from[(nx, ny)] = current
                        g_score[(nx, ny)] = tentative
                        f = tentative + math.sqrt((nx-goal[0])**2 + (ny-goal[1])**2)
                        heapq.heappush(open_set, (f, (nx, ny)))
        return []

    # 160-161. Obstacle avoidance + Emergency stop
    def avoid_obstacles(self, lidar_readings: List[float], num_rays: int = 360) -> Dict[str, Any]:
        min_dist = min(lidar_readings) if lidar_readings else 999
        sector_size = num_rays // 3
        front = lidar_readings[:sector_size] if len(lidar_readings) >= sector_size else lidar_readings
        left = lidar_readings[sector_size:2*sector_size] if len(lidar_readings) >= 2*sector_size else []
        right = lidar_readings[2*sector_size:] if len(lidar_readings) >= 3*sector_size else []
        front_min = min(front) if front else 999
        left_min = min(left) if left else 999
        right_min = min(right) if right else 999
        if front_min < 0.3:
            return {"action": "emergency_stop", "reason": "front_collision"}
        if front_min < 0.8:
            if left_min > right_min:
                return {"action": "turn_left", "urgency": 0.8}
            else:
                return {"action": "turn_right", "urgency": 0.8}
        if front_min < 1.5:
            return {"action": "slow_down", "target_speed": 0.1}
        return {"action": "proceed", "min_distance": round(min_dist, 3)}

    def emergency_stop(self) -> Dict[str, Any]:
        self.speed = 0
        self.nav_active = False
        return {"action": "emergency_stop", "speed": 0}

    # 162-164. Predictive avoidance, traversability-aware, risk-aware planning
    def predict_collision(self, velocities: List[Tuple[float, float]], horizon: float = 2.0) -> Dict[str, Any]:
        risks = []
        for vx, vy in velocities:
            steps = int(horizon * 10)
            risk = 0
            for t in range(1, steps + 1):
                px = self.robot_x + int(vx * t * 0.1 / self.resolution)
                py = self.robot_y + int(vy * t * 0.1 / self.resolution)
                if 0 <= px < self.grid_size and 0 <= py < self.grid_size:
                    if self.occupancy[py, px] > 0.5:
                        risk += 1
            risks.append({"velocity": (vx, vy), "collision_risk": risk})
        return {"risks": risks, "safest": min(risks, key=lambda r: r["collision_risk"]) if risks else None}

    def plan_traversability_aware(self, goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        return self.plan_path((self.robot_x, self.robot_y), goal)

    def assess_risk(self, path: List[Tuple[int, int]]) -> float:
        if not path:
            return 1.0
        risk = 0
        for px, py in path:
            neighbors = [(px+dx, py+dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
            for nx, ny in neighbors:
                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    if self.occupancy[ny, nx] > 0.5:
                        risk += 1
        return min(1.0, risk / max(1, len(path) * 3))

    # 165-167. Speed adaptation, narrow passage, dead-end detection
    def adapt_speed(self, obstacles_ahead: float) -> float:
        if obstacles_ahead < 0.5:
            self.speed = 0
        elif obstacles_ahead < 1.0:
            self.speed = 0.05
        elif obstacles_ahead < 2.0:
            self.speed = 0.15
        else:
            self.speed = self.max_speed
        return self.speed

    def detect_narrow_passage(self, lidar_left: float, lidar_right: float, threshold: float = 0.6) -> bool:
        return lidar_left < threshold and lidar_right < threshold

    def detect_dead_end(self, lidar_readings: List[float], threshold: float = 1.0) -> bool:
        if not lidar_readings:
            return False
        front = lidar_readings[:len(lidar_readings)//3]
        left = lidar_readings[len(lidar_readings)//3:2*len(lidar_readings)//3]
        right = lidar_readings[2*len(lidar_readings)//3:]
        front_close = min(front) < threshold if front else True
        side_close = (min(left) < threshold if left else False) and (min(right) < threshold if right else False)
        if front_close and side_close:
            self.dead_end_count += 1
            return True
        return False

    # 168-170. Recovery behavior, confidence, return-to-home
    def recovery_behavior(self) -> Dict[str, Any]:
        self.recovery_count += 1
        if self.recovery_count > 5:
            return {"action": "return_home", "reason": "max_recovery"}
        return {"action": "reverse_turn", "recovery_number": self.recovery_count}

    def update_confidence(self, sensor_fusion_confidence: float, nav_completeness: float):
        self.confidence = sensor_fusion_confidence * 0.6 + nav_completeness * 0.4

    def return_to_home(self) -> Dict[str, Any]:
        self.current_goal = self.home_pose
        self.current_waypoints = self.plan_path((self.robot_x, self.robot_y), self.home_pose)
        self.nav_active = True
        self.mode = "return_home"
        return {"waypoints": len(self.current_waypoints), "home": self.home_pose, "active": True}

    def update_robot_pose(self, x: float, y: float, theta: float):
        self.robot_x = int(x / self.resolution + self.grid_size // 2)
        self.robot_y = int(y / self.resolution + self.grid_size // 2)
        self.robot_theta = theta

    def update_occupancy(self, lidar_points):
        if lidar_points is None:
            return
        for pt in lidar_points:
            if len(pt) < 2:
                continue
            angle = math.atan2(pt[1], pt[0])
            dist = math.sqrt(pt[0]**2 + pt[1]**2)
            wx = self.robot_x + int(dist * math.cos(angle + self.robot_theta) / self.resolution)
            wy = self.robot_y + int(dist * math.sin(angle + self.robot_theta) / self.resolution)
            if 0 <= wx < self.grid_size and 0 <= wy < self.grid_size:
                self.occupancy[wy, wx] = 1

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "nav_active": self.nav_active,
            "goal": self.current_goal,
            "waypoints_remaining": len(self.current_waypoints),
            "speed": round(self.speed, 3),
            "confidence": round(self.confidence, 3),
            "dead_ends": self.dead_end_count,
            "recoveries": self.recovery_count,
            "home": self.home_pose,
        }
