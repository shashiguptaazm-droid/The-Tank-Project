"""
nav_manager.py — Navigation Manager
Waypoint navigation, path planning, obstacle avoidance, timeout, e-stop,
exploration, return-home, mission manager, cognitive integration.
"""
import time
import math
import json
import logging
import threading
from datetime import datetime
from collections import deque

logger = logging.getLogger("tank.nav.manager")

MODE_IDLE = "idle"
MODE_MANUAL = "manual"
MODE_WAYPOINT = "waypoint"
MODE_EXPLORATION = "exploration"
MODE_RETURN_HOME = "return_home"
MODE_PATROL = "patrol"
MODE_EMERGENCY = "emergency_stop"


class Mission:
    def __init__(self, name="unnamed"):
        self.name = name
        self.waypoints = []
        self.current_index = 0
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.results = []

    def add_waypoint(self, x, y, action=None, timeout=30):
        self.waypoints.append({"x": x, "y": y, "action": action, "timeout": timeout})

    def start(self):
        self.status = "running"
        self.start_time = time.time()
        self.current_index = 0

    def complete(self, success=True):
        self.status = "completed" if success else "failed"
        self.end_time = time.time()

    def get_progress(self):
        if not self.waypoints:
            return 0
        return self.current_index / len(self.waypoints)

    def get_elapsed(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "waypoints": len(self.waypoints),
            "current": self.current_index,
            "progress": f"{self.get_progress():.0%}",
            "elapsed_s": round(self.get_elapsed()),
        }


class NavManager:
    def __init__(self, serial_bridge=None, lidar=None, camera=None, yolo=None):
        self.serial = serial_bridge
        self.lidar = lidar
        self.camera = camera
        self.yolo = yolo

        self.mode = MODE_IDLE
        self.position = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self.velocity = {"linear": 0.0, "angular": 0.0}
        self.mission = None
        self.home = {"x": 0.0, "y": 0.0}
        self.emergency_stop_active = False

        self.safety_distance = 0.3
        self.max_speed = 100
        self.nav_timeout = 60
        self._running = False
        self._nav_thread = None
        self._callbacks = []
        self._log = deque(maxlen=200)

    def on_event(self, callback):
        self._callbacks.append(callback)

    def _emit(self, event_type, data=""):
        event = {"type": event_type, "data": data, "time": datetime.now().isoformat()}
        self._log.append(event)
        for cb in self._callbacks:
            cb(event)

    # === MODE CONTROL ===

    def start_waypoint_nav(self, waypoints):
        self.mission = Mission("waypoint_nav")
        for wp in waypoints:
            self.mission.add_waypoint(wp["x"], wp["y"])
        self.mission.start()
        self.mode = MODE_WAYPOINT
        self._running = True
        self._nav_thread = threading.Thread(target=self._waypoint_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_start", f"Waypoint nav: {len(waypoints)} waypoints")
        return True

    def start_exploration(self):
        self.mode = MODE_EXPLORATION
        self._running = True
        self._nav_thread = threading.Thread(target=self._exploration_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_start", "Autonomous exploration started")
        return True

    def start_patrol(self, waypoints):
        self.mission = Mission("patrol")
        for wp in waypoints:
            self.mission.add_waypoint(wp["x"], wp["y"])
        self.mission.start()
        self.mode = MODE_PATROL
        self._running = True
        self._nav_thread = threading.Thread(target=self._patrol_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_start", f"Patrol: {len(waypoints)} waypoints")
        return True

    def return_home(self):
        self.mode = MODE_RETURN_HOME
        self._running = True
        self._nav_thread = threading.Thread(target=self._return_home_loop, daemon=True)
        self._nav_thread.start()
        self._emit("nav_start", "Returning home")
        return True

    def emergency_stop(self):
        self._running = False
        self.emergency_stop_active = True
        self.mode = MODE_EMERGENCY
        self._send_motors(0, 0)
        self._emit("nav_emergency", "EMERGENCY STOP")
        return True

    def resume(self):
        self.emergency_stop_active = False
        self.mode = MODE_IDLE
        self._emit("nav_resume", "Emergency cleared, resuming")
        return True

    # === NAVIGATION LOOPS ===

    def _waypoint_loop(self):
        start_time = time.time()
        while self._running and self.mission:
            if time.time() - start_time > self.nav_timeout:
                self._emit("nav_timeout", "Navigation timeout")
                self._send_motors(0, 0)
                self.mission.complete(False)
                self.mode = MODE_IDLE
                break

            if self.emergency_stop_active:
                time.sleep(0.1)
                continue

            if self.mission.current_index >= len(self.mission.waypoints):
                self._send_motors(0, 0)
                self.mission.complete(True)
                self._emit("nav_complete", f"Mission '{self.mission.name}' completed")
                self.mode = MODE_IDLE
                break

            wp = self.mission.waypoints[self.mission.current_index]
            dx = wp["x"] - self.position["x"]
            dy = wp["y"] - self.position["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 0.2:
                self._emit("nav_waypoint", f"Waypoint {self.mission.current_index} reached")
                if wp.get("action"):
                    self._execute_action(wp["action"])
                self.mission.current_index += 1
                continue

            if self._check_obstacles():
                self._avoid_obstacle()
                continue

            target_angle = math.atan2(dy, dx)
            angle_error = target_angle - self.position["theta"]
            while angle_error > math.pi: angle_error -= 2 * math.pi
            while angle_error < -math.pi: angle_error += 2 * math.pi

            speed = min(60, max(20, int(dist * 80)))
            turn = int(angle_error * 40)
            left = max(-80, min(80, speed + turn))
            right = max(-80, min(80, speed - turn))
            self._send_motors(left, right)
            time.sleep(0.1)

    def _exploration_loop(self):
        while self._running:
            if self.emergency_stop_active:
                time.sleep(0.1)
                continue

            if self._check_obstacles():
                self._avoid_obstacle()
            else:
                self._send_motors(30, 30)

            self._emit("nav_exploration", f"Exploring... pos=({self.position['x']:.1f},{self.position['y']:.1f})")
            time.sleep(0.5)

    def _patrol_loop(self):
        while self._running and self.mission:
            if self.emergency_stop_active:
                time.sleep(0.1)
                continue

            if self.mission.current_index >= len(self.mission.waypoints):
                self.mission.current_index = 0
                self._emit("nav_patrol", "Patrol cycle complete, restarting")

            wp = self.mission.waypoints[self.mission.current_index]
            dx = wp["x"] - self.position["x"]
            dy = wp["y"] - self.position["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 0.3:
                self._emit("nav_patrol", f"Patrol waypoint {self.mission.current_index} reached")
                self.mission.current_index += 1
                time.sleep(2)
                continue

            target_angle = math.atan2(dy, dx)
            angle_error = target_angle - self.position["theta"]
            while angle_error > math.pi: angle_error -= 2 * math.pi
            while angle_error < -math.pi: angle_error += 2 * math.pi

            speed = min(50, max(20, int(dist * 60)))
            turn = int(angle_error * 35)
            self._send_motors(speed + turn, speed - turn)
            time.sleep(0.1)

    def _return_home_loop(self):
        start = time.time()
        while self._running and time.time() - start < self.nav_timeout:
            if self.emergency_stop_active:
                time.sleep(0.1)
                continue

            dx = self.home["x"] - self.position["x"]
            dy = self.home["y"] - self.position["y"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 0.3:
                self._send_motors(0, 0)
                self._emit("nav_home", "Arrived at home")
                self.mode = MODE_IDLE
                return

            target_angle = math.atan2(dy, dx)
            angle_error = target_angle - self.position["theta"]
            while angle_error > math.pi: angle_error -= 2 * math.pi
            while angle_error < -math.pi: angle_error += 2 * math.pi

            speed = min(50, max(20, int(dist * 50)))
            turn = int(angle_error * 30)
            self._send_motors(speed + turn, speed - turn)
            time.sleep(0.1)

        self._send_motors(0, 0)
        self._emit("nav_home", "Return home timeout")
        self.mode = MODE_IDLE

    def _check_obstacles(self):
        if self.lidar:
            nearest = self.lidar.get_nearest_obstacle()
            if nearest < self.safety_distance:
                return True
        return False

    def _avoid_obstacle(self):
        self._send_motors(-20, 20)
        time.sleep(0.5)
        self._send_motors(0, 0)
        time.sleep(0.1)

    def _execute_action(self, action):
        if isinstance(action, dict):
            self._emit("nav_action", json.dumps(action))
        else:
            self._emit("nav_action", str(action))

    def _send_motors(self, left, right):
        if self.serial:
            try:
                self.serial.send_command(f"MOTOR {int(left)} {int(right)}")
            except:
                pass

    def update_position(self, x, y, theta=None):
        self.position["x"] = x
        self.position["y"] = y
        if theta is not None:
            self.position["theta"] = theta

    def update_encoders(self, left_ticks, right_ticks):
        wheel_circumference = 0.21
        ticks_per_rev = 390
        wheel_base = 0.30
        dl = (left_ticks / ticks_per_rev) * wheel_circumference
        dr = (right_ticks / ticks_per_rev) * wheel_circumference
        d = (dl + dr) / 2
        dtheta = (dr - dl) / wheel_base
        self.position["x"] += d * math.cos(self.position["theta"] + dtheta / 2)
        self.position["y"] += d * math.sin(self.position["theta"] + dtheta / 2)
        self.position["theta"] += dtheta

    def stop(self):
        self._running = False
        self._send_motors(0, 0)
        self.mode = MODE_IDLE

    def get_status(self):
        return {
            "mode": self.mode,
            "position": {
                "x": round(self.position["x"], 2),
                "y": round(self.position["y"], 2),
                "theta_deg": round(math.degrees(self.position["theta"]), 1),
            },
            "emergency_stop": self.emergency_stop_active,
            "mission": self.mission.to_dict() if self.mission else None,
            "recent_events": list(self._log)[-5:],
        }
