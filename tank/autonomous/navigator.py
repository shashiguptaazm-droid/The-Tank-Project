"""
navigator.py - Autonomous Navigation for Tank
SLAM-free navigation using LiDAR + camera + AprilTags + IMU.
Includes obstacle avoidance, path planning, and waypoint following.
"""
import time
import math
import logging
import threading
import json
import heapq
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("tank.navigation")

# Navigation modes
MODE_IDLE = "idle"
MODE_MANUAL = "manual"
MODE_AUTONOMOUS = "autonomous"
MODE_GOAL = "go_to_goal"
MODE_PATROL = "patrol"
MODE_RETURN_HOME = "return_home"
MODE_DOCKING = "docking"
MODE_EMERGENCY = "emergency_stop"


class OccupancyGrid:
    """Simple 2D occupancy grid for obstacle mapping"""

    def __init__(self, width=100, height=100, resolution=0.1):
        self.width = width
        self.height = height
        self.resolution = resolution  # meters per cell
        self.grid = [[0.0 for _ in range(width)] for _ in range(height)]
        self.robot_pos = {"x": 50, "y": 50, "theta": 0.0}

    def world_to_grid(self, wx, wy):
        gx = int((wx - self.robot_pos["x"]) / self.resolution + self.width / 2)
        gy = int((wy - self.robot_pos["y"]) / self.resolution + self.height / 2)
        return max(0, min(gx, self.width - 1)), max(0, min(gy, self.height - 1))

    def grid_to_world(self, gx, gy):
        wx = (gx - self.width / 2) * self.resolution + self.robot_pos["x"]
        wy = (gy - self.height / 2) * self.resolution + self.robot_pos["y"]
        return wx, wy

    def update_from_lidar(self, ranges, angles):
        """Update grid with LiDAR scan data"""
        for r, a in zip(ranges, angles):
            if r <= 0 or r > 10:
                continue
            abs_angle = a + self.robot_pos["theta"]
            wx = self.robot_pos["x"] + r * math.cos(abs_angle)
            wy = self.robot_pos["y"] + r * math.sin(abs_angle)
            gx, gy = self.world_to_grid(wx, wy)
            if 0 <= gx < self.width and 0 <= gy < self.height:
                self.grid[gy][gx] = min(1.0, self.grid[gy][gx] + 0.3)

            # Mark cells along the ray as free
            steps = int(r / self.resolution)
            for s in range(0, steps, 2):
                sx = self.robot_pos["x"] + s * self.resolution * math.cos(abs_angle)
                sy = self.robot_pos["y"] + s * self.resolution * math.sin(abs_angle)
                sgx, sgy = self.world_to_grid(sx, sy)
                if 0 <= sgx < self.width and 0 <= sgy < self.height:
                    self.grid[sgy][sgx] = max(0.0, self.grid[sgy][sgx] - 0.1)

    def is_free(self, gx, gy):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return self.grid[gy][gx] < 0.5
        return False

    def inflate_obstacles(self, radius=3):
        """Inflate obstacles for safe path planning"""
        inflated = [[self.grid[y][x] for x in range(self.width)] for y in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] > 0.5:
                    for dy in range(-radius, radius + 1):
                        for dx in range(-radius, radius + 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                dist = math.sqrt(dx * dx + dy * dy)
                                weight = max(0, 1.0 - dist / radius)
                                inflated[ny][nx] = max(inflated[ny][nx], weight)
        return inflated


class PathPlanner:
    """A* path planner on occupancy grid"""

    def __init__(self, grid):
        self.grid = grid

    def plan(self, start_gx, start_gy, goal_gx, goal_gy, inflated=None):
        """A* path planning"""
        if not self.grid.is_free(goal_gx, goal_gy):
            # Find nearest free cell to goal
            for r in range(1, 10):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if self.grid.is_free(goal_gx + dx, goal_gy + dy):
                            goal_gx, goal_gy = goal_gx + dx, goal_gy + dy
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

        grid = inflated if inflated else self.grid.grid
        open_set = [(0, start_gx, start_gy)]
        came_from = {}
        g_score = {(start_gx, start_gy): 0}
        closed = set()

        while open_set:
            _, cx, cy = heapq.heappop(open_set)

            if (cx, cy) == (goal_gx, goal_gy):
                path = []
                current = (goal_gx, goal_gy)
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append((start_gx, start_gy))
                path.reverse()
                return path

            if (cx, cy) in closed:
                continue
            closed.add((cx, cy))

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in closed:
                    continue
                if not (0 <= nx < self.grid.width and 0 <= ny < self.grid.height):
                    continue
                if grid[ny][nx] > 0.6:
                    continue

                move_cost = math.sqrt(dx * dx + dy * dy)
                tentative = g_score[(cx, cy)] + move_cost
                if tentative < g_score.get((nx, ny), float('inf')):
                    g_score[(nx, ny)] = tentative
                    heuristic = math.sqrt((nx - goal_gx)**2 + (ny - goal_gy)**2)
                    heapq.heappush(open_set, (tentative + heuristic, nx, ny))
                    came_from[(nx, ny)] = (cx, cy)

        return []  # No path found


class ObstacleAvoidance:
    """Real-time obstacle avoidance using vector field histogram"""

    def __init__(self):
        self.safety_distance = 0.3  # meters
        self.max_speed = 100
        self.avoidance_gain = 2.0

    def compute_velocity(self, ranges, angles, goal_angle=None, goal_distance=1.0):
        """Compute safe velocity using VFH-like approach"""
        if not ranges:
            return 0, 0

        # Find clear sectors
        sector_size = 10  # degrees
        sectors = {}
        for deg in range(0, 360, sector_size):
            count = 0
            min_dist = float('inf')
            for r, a in zip(ranges, angles):
                a_deg = math.degrees(a) % 360
                if abs(a_deg - deg) < sector_size or abs(a_deg - deg + 360) < sector_size:
                    count += 1
                    min_dist = min(min_dist, r)
            sectors[deg] = {"count": count, "min_dist": min_dist}

        # Find best sector (clear + towards goal)
        best_sector = 0
        best_score = -float('inf')

        for deg, info in sectors.items():
            if info["min_dist"] < self.safety_distance:
                continue

            clearance_score = info["min_dist"] * 10

            if goal_angle is not None:
                goal_diff = abs(math.degrees(goal_angle) - deg)
                goal_diff = min(goal_diff, 360 - goal_diff)
                goal_score = -goal_diff * 0.5
            else:
                goal_score = 0

            score = clearance_score + goal_score
            if score > best_score:
                best_score = score
                best_sector = deg

        # Convert to motor commands
        best_rad = math.radians(best_sector)
        turn = math.sin(best_rad) * self.max_speed
        forward = math.cos(best_rad) * self.max_speed

        # Reduce speed near obstacles
        min_clearance = min(r for r in ranges if r > 0) if ranges else 1.0
        if min_clearance < self.safety_distance * 2:
            speed_factor = min_clearance / (self.safety_distance * 2)
            forward *= speed_factor
            turn *= speed_factor

        left = int(max(-self.max_speed, min(self.max_speed, forward + turn)))
        right = int(max(-self.max_speed, min(self.max_speed, forward - turn)))

        return left, right

    def is_emergency_stop(self, ranges):
        """Check if any obstacle is dangerously close"""
        if not ranges:
            return False
        return min(r for r in ranges if r > 0) < 0.15 if ranges else False


class AutonomousNavigator:
    """Full autonomous navigation system"""

    def __init__(self, serial_bridge=None, apriltag_detector=None):
        self.serial_bridge = serial_bridge
        self.detector = apriltag_detector

        self.mode = MODE_IDLE
        self.grid = OccupancyGrid()
        self.planner = PathPlanner(self.grid)
        self.avoidance = ObstacleAvoidance()

        self.current_path = []
        self.path_index = 0
        self.goal = None
        self.waypoints = []
        self.waypoint_index = 0
        self.position = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self.velocity = {"linear": 0.0, "angular": 0.0}

        self.lidar_data = {"ranges": [], "angles": []}
        self.imu_data = {"roll": 0, "pitch": 0, "yaw": 0}

        self._nav_thread = None
        self._running = False
        self._callbacks = []
        self._log = []

    def on_event(self, callback):
        self._callbacks.append(callback)

    def _emit(self, event_type, data=""):
        event = {"type": event_type, "data": data, "time": datetime.now().isoformat()}
        self._log.append(event)
        if len(self._log) > 500:
            self._log = self._log[-500:]
        for cb in self._callbacks:
            cb(event)

    # === MODE CONTROL ===

    def start_autonomous(self):
        """Start autonomous exploration"""
        self.mode = MODE_AUTONOMOUS
        self._running = True
        self._nav_thread = threading.Thread(target=self._autonomous_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_start", "Autonomous mode activated")
        return True

    def go_to_goal(self, x, y):
        """Navigate to a specific goal position"""
        self.goal = {"x": x, "y": y}
        self.mode = MODE_GOAL
        self._running = True

        # Plan path
        start_gx, start_gy = self.grid.world_to_grid(self.position["x"], self.position["y"])
        goal_gx, goal_gy = self.grid.world_to_grid(x, y)
        inflated = self.grid.inflate_obstacles(3)
        self.current_path = self.planner.plan(start_gx, start_gy, goal_gx, goal_gy, inflated)
        self.path_index = 0

        if not self.current_path:
            self._emit("nav_error", f"No path found to ({x}, {y})")
            return False

        self._emit("nav_goal", f"Path planned: {len(self.current_path)} steps to ({x:.1f}, {y:.1f})")
        self._nav_thread = threading.Thread(target=self._goal_loop, daemon=True)
        self._nav_thread.start()
        return True

    def start_patrol(self, waypoints):
        """Patrol through a list of waypoints"""
        self.waypoints = waypoints
        self.waypoint_index = 0
        self.mode = MODE_PATROL
        self._running = True
        self._nav_thread = threading.Thread(target=self._patrol_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_patrol", f"Patrolling {len(waypoints)} waypoints")
        return True

    def return_home(self):
        """Return to home base (NAV_HOME tag = ID 3)"""
        self.mode = MODE_RETURN_HOME
        self._running = True

        # Find home tag
        if self.detector:
            tags = self.detector.get_nav_tags()
            home_tags = [t for t in tags if t["id"] == 3]
            if home_tags and "pose" in home_tags[0]:
                home_pos = home_tags[0]["pose"]
                return self.go_to_goal(home_pos["x"], home_pos["y"])

        self._emit("nav_home", "Returning to home (no tag found, using last known)")
        self._nav_thread = threading.Thread(target=self._return_loop, daemon=True)
        self._nav_thread.start()
        return True

    def emergency_stop(self):
        """Emergency stop all movement"""
        self._running = False
        self.mode = MODE_EMERGENCY
        self._send_motors(0, 0)
        self._emit("nav_emergency", "EMERGENCY STOP")
        return True

    def set_manual(self, left, right):
        """Manual motor control"""
        self.mode = MODE_MANUAL
        self._running = False
        self._send_motors(left, right)

    # === NAVIGATION LOOPS ===

    def _autonomous_loop(self):
        """Continuous autonomous exploration"""
        while self._running and self.mode == MODE_AUTONOMOUS:
            ranges = self.lidar_data.get("ranges", [])
            angles = self.lidar_data.get("angles", [])

            if ranges:
                # Emergency stop check
                if self.avoidance.is_emergency_stop(ranges):
                    self._send_motors(0, 0)
                    self._emit("nav_avoid", "Emergency stop - obstacle too close")
                    time.sleep(0.5)
                    continue

                # Look for navigation tags
                if self.detector:
                    nav_tags = self.detector.get_nav_tags()
                    if nav_tags:
                        tag = nav_tags[0]
                        if "pose" in tag:
                            self._emit("nav_landmark", f"Tag {tag['name']} at {tag['pose']['distance_m']:.2f}m")

                # Compute avoidance velocity
                goal_angle = None
                if self.goal:
                    dx = self.goal["x"] - self.position["x"]
                    dy = self.goal["y"] - self.position["y"]
                    goal_angle = math.atan2(dy, dx) - self.position["theta"]
                    goal_distance = math.sqrt(dx * dx + dy * dy)

                left, right = self.avoidance.compute_velocity(
                    ranges, angles, goal_angle
                )
                self._send_motors(left, right)
            else:
                # No LiDAR data, do a slow rotation to scan
                self._send_motors(15, -15)

            time.sleep(0.1)

    def _goal_loop(self):
        """Follow planned path to goal"""
        while self._running and self.mode == MODE_GOAL:
            if self.path_index >= len(self.current_path):
                self._send_motors(0, 0)
                self._emit("nav_arrived", f"Reached goal ({self.goal['x']:.1f}, {self.goal['y']:.1f})")
                self.mode = MODE_IDLE
                break

            # Get current and next waypoint on path
            target_gx, target_gy = self.current_path[self.path_index]
            tx, ty = self.grid.grid_to_world(target_gx, target_gy)

            dx = tx - self.position["x"]
            dy = ty - self.position["y"]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < 0.15:
                self.path_index += 1
                continue

            target_angle = math.atan2(dy, dx)
            angle_error = target_angle - self.position["theta"]
            while angle_error > math.pi:
                angle_error -= 2 * math.pi
            while angle_error < -math.pi:
                angle_error += 2 * math.pi

            # Avoidance override
            ranges = self.lidar_data.get("ranges", [])
            if ranges and self.avoidance.is_emergency_stop(ranges):
                self._send_motors(0, 0)
                time.sleep(0.3)
                continue

            # PID-like control
            speed = min(60, max(20, int(distance * 100)))
            turn = int(angle_error * 50)
            left = max(-80, min(80, speed + turn))
            right = max(-80, min(80, speed - turn))
            self._send_motors(left, right)

            time.sleep(0.1)

    def _patrol_loop(self):
        """Patrol through waypoints"""
        while self._running and self.mode == MODE_PATROL:
            if not self.waypoints:
                break

            wp = self.waypoints[self.waypoint_index % len(self.waypoints)]
            self._emit("nav_patrol", f"Heading to waypoint {self.waypoint_index}: ({wp['x']:.1f}, {wp['y']:.1f})")

            self.go_to_goal(wp["x"], wp["y"])

            # Wait for arrival
            while self._running and self.mode == MODE_GOAL:
                time.sleep(0.5)

            if self._running:
                self._emit("nav_patrol", f"Waypoint {self.waypoint_index} reached")
                self.waypoint_index += 1
                time.sleep(2)  # Pause at waypoint

    def _return_loop(self):
        """Return to last known home position"""
        home_tag_id = 3
        timeout = time.time() + 60

        while self._running and time.time() < timeout:
            if self.detector:
                tags = self.detector.get_nav_tags()
                home_tags = [t for t in tags if t["id"] == home_tag_id]
                if home_tags:
                    tag = home_tags[0]
                    cx = tag["center"]["x"]
                    error = cx - 320
                    if abs(error) < 50 and tag.get("pose", {}).get("distance_m", 10) < 0.5:
                        self._send_motors(0, 0)
                        self._emit("nav_home", "Arrived at home base")
                        self.mode = MODE_IDLE
                        return

                    turn = int(error * 0.15)
                    self._send_motors(30 + turn, 30 - turn)
                else:
                    # Search for home tag
                    self._send_motors(15, -15)
            time.sleep(0.2)

        self._send_motors(0, 0)
        self._emit("nav_home", "Return home timeout")
        self.mode = MODE_IDLE

    # === SENSOR UPDATES ===

    def update_lidar(self, ranges, angles):
        """Update with new LiDAR data"""
        self.lidar_data = {"ranges": ranges, "angles": angles}
        self.grid.update_from_lidar(ranges, angles)

    def update_imu(self, yaw, roll=0, pitch=0):
        """Update position from IMU"""
        self.imu_data = {"yaw": yaw, "roll": roll, "pitch": pitch}
        self.position["theta"] = math.radians(yaw)

    def update_position(self, x, y, theta=None):
        """Update robot position (from SLAM or odometry)"""
        self.position["x"] = x
        self.position["y"] = y
        if theta is not None:
            self.position["theta"] = theta

    def update_encoders(self, left_ticks, right_ticks):
        """Update position from encoder odometry"""
        # Simple differential drive odometry
        wheel_circumference = 0.21  # meters (JGB37-520)
        ticks_per_rev = 390
        wheel_base = 0.30  # meters

        dl = (left_ticks / ticks_per_rev) * wheel_circumference
        dr = (right_ticks / ticks_per_rev) * wheel_circumference

        d = (dl + dr) / 2
        dtheta = (dr - dl) / wheel_base

        self.position["x"] += d * math.cos(self.position["theta"] + dtheta / 2)
        self.position["y"] += d * math.sin(self.position["theta"] + dtheta / 2)
        self.position["theta"] += dtheta

    def _send_motors(self, left, right):
        """Send motor commands"""
        if self.serial_bridge:
            try:
                self.serial_bridge.send_command(f"MOTOR {int(left)} {int(right)}")
            except:
                pass

    def stop(self):
        self._running = False
        self._send_motors(0, 0)
        self.mode = MODE_IDLE

    def get_status(self):
        """Full navigation status"""
        return {
            "mode": self.mode,
            "position": {
                "x": round(self.position["x"], 2),
                "y": round(self.position["y"], 2),
                "theta_deg": round(math.degrees(self.position["theta"]), 1),
            },
            "goal": self.goal,
            "path_length": len(self.current_path),
            "path_progress": f"{self.path_index}/{len(self.current_path)}" if self.current_path else "none",
            "waypoints_total": len(self.waypoints),
            "waypoints_done": self.waypoint_index,
            "lidar_points": len(self.lidar_data.get("ranges", [])),
            "obstacles_in_grid": sum(
                1 for y in range(self.grid.height)
                for x in range(self.grid.width)
                if self.grid.grid[y][x] > 0.5
            ),
            "running": self._running,
            "recent_events": self._log[-5:],
        }

    def get_grid_map(self):
        """Get occupancy grid as JSON for visualization"""
        return {
            "width": self.grid.width,
            "height": self.grid.height,
            "resolution": self.grid.resolution,
            "robot": self.grid.robot_pos,
            "grid": [
                [round(self.grid.grid[y][x], 2) for x in range(self.grid.width)]
                for y in range(self.grid.height)
            ],
        }


# === Standalone test ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    nav = AutonomousNavigator()
    nav.on_event(lambda e: print(f"[{e['type']}] {e['data']}"))

    print(json.dumps(nav.get_status(), indent=2))
    print("Grid obstacle count:", nav.get_status()["obstacles_in_grid"])
