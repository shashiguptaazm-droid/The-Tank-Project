"""ROS 2 node owning the autonomous patrolling state machine.

State topology
--------------
   paused ── resume ──► patrolling ─┐
                                  │
                                  ├─→ returning → docking → charging
                                  │                              │
                                  ▼                              │
                                idle ◄──────────── estop_release ┘
                                  ▲
                estop_press ──► emergency_stop (always wins)

* ``/estop`` True => emergency_stop ALWAYS wins (safety first).
* ``/battery/state.percentage < 0.20`` => returning (auto-dock).
* All waypoints done                    => returning.
* ``/patrol/cmd`` JSON:
    ``{"action":"start","mode":"waypoint","waypoints_file":"/path.json"}``  start
    ``{"action":"pause"}``                                                   pause
    ``{"action":"resume"}``                                                  resume
    ``{"action":"stop"}``                                                    stop

Controller
----------
v1 publishes :class:`geometry_msgs.msg.Twist` on /cmd_vel (the type
:mod:`tank_motion.motor_controller` subscribes to). Linear speed is
blended via ``cos(yaw_err)`` so the robot always makes *some* forward
progress even while rotating — this avoids the rotate-stop-rotate
oscillation that happens when the scan-based collision guard fires.
Nav2 integration is queued in follow-ups.
"""
from __future__ import annotations

import json
import math
import threading
import time
from typing import Optional

import rclpy
from rclpy.callback_groups import (
    MutuallyExclusiveCallbackGroup,
    ReentrantCallbackGroup,
)
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState, LaserScan
from std_msgs.msg import Bool, String

from .patrol_modes import (
    MovementGoal,
    PatrolMode,
    Pose2D,
    RandomWalkPatrol,
    WaypointPatrol,
    load_waypoints_json,
)


QOS = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)


class Phase:
    IDLE           = "idle"
    READY          = "ready"
    PATROLLING     = "patrolling"
    RETURNING      = "returning"
    DOCKING        = "docking"
    CHARGING       = "charging"
    PAUSED         = "paused"
    EMERGENCY_STOP = "emergency_stop"


DEFAULT_REPO = "/root/the tank project"
DEFAULT_WAYPOINTS_FILE = f"{DEFAULT_REPO}/tank_ws/src/tank_patrol/config/waypoints_demo.json"
DEFAULT_RANDOM_BOUNDS = (-5.0, -5.0, 5.0, 5.0)
DEFAULT_BATTERY_RETURN_THRESHOLD = 0.20
DEFAULT_BATTERY_CRITICAL_THRESHOLD = 0.10
DEFAULT_COLLISION_MIN_RANGE_M = 0.45


class PatrolNode(Node):
    def __init__(self) -> None:
        super().__init__("patrol_node")
        self._declare_params()
        self._lock = threading.Lock()

        # runtime state
        self._phase: str = Phase.IDLE
        self._mode: Optional[PatrolMode] = None      # type: ignore[assignment]
        self._current_target: Optional[MovementGoal] = None
        self._tolerance: float = 0.30
        self._last_cmd_vel_ms: float = time.time()
        self._estop_pressed: bool = False
        self._current_pose: Pose2D = Pose2D.origin()
        self._min_scan_range_m: float = 99.0
        self._battery_pct: float = 1.0

        # publishers
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", QOS)
        self._state_pub = self.create_publisher(String, "/patrol/state", QOS)
        self._alert_pub = self.create_publisher(String, "/patrol/alert", QOS)
        self._event_pub = self.create_publisher(String, "/patrol/event", QOS)

        # Two callback groups so high-rate sensor callbacks (odom+scan)
        # don't starve the safety inputs (estop+cmd) on a MultiThreaded
        # executor. Both groups are still under MutuallyExclusiveCAUTION
        # within themselves.
        cbg = MutuallyExclusiveCallbackGroup()
        self.create_subscription(Odometry,     "/odom",
                                 self._on_odom,    QOS, callback_group=cbg)
        self.create_subscription(LaserScan,    "/scan",
                                 self._on_scan,    QOS, callback_group=cbg)
        self.create_subscription(BatteryState, "/battery/state",
                                 self._on_battery, QOS, callback_group=cbg)
        self.create_subscription(Bool,          "/estop",
                                 self._on_estop,   QOS, callback_group=cbg)
        self.create_subscription(String,        "/patrol/cmd",
                                 self._on_cmd,     QOS, callback_group=cbg)

        self.create_timer(0.1, self._tick)        # 10 Hz

        self.get_logger().info(f"patrol_node initialised phase={self._phase}")

    def _declare_params(self) -> None:
        self.declare_parameter("waypoints_file", DEFAULT_WAYPOINTS_FILE)
        self.declare_parameter("random_bounds_xmin", DEFAULT_RANDOM_BOUNDS[0])
        self.declare_parameter("random_bounds_ymin", DEFAULT_RANDOM_BOUNDS[1])
        self.declare_parameter("random_bounds_xmax", DEFAULT_RANDOM_BOUNDS[2])
        self.declare_parameter("random_bounds_ymax", DEFAULT_RANDOM_BOUNDS[3])
        self.declare_parameter("random_seed", 42)
        self.declare_parameter("battery_return_threshold",
                               DEFAULT_BATTERY_RETURN_THRESHOLD)
        self.declare_parameter("battery_critical_threshold",
                               DEFAULT_BATTERY_CRITICAL_THRESHOLD)
        self.declare_parameter("collision_min_range_m",
                               DEFAULT_COLLISION_MIN_RANGE_M)

    # --------- subscribers ---------
    def _on_odom(self, msg: Odometry) -> None:
        try:
            x = float(msg.pose.pose.position.x)
            y = float(msg.pose.pose.position.y)
            q = msg.pose.pose.orientation
            n = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w)
            if n < 1e-9:
                return
            qx, qy, qz, qw = q.x / n, q.y / n, q.z / n, q.w / n
            siny_cosp = 2.0 * (qw * qz + qx * qy)
            cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
            yaw = math.atan2(siny_cosp, cosy_cosp)
            self._current_pose = Pose2D(x, y, yaw)
        except Exception:
            pass

    def _on_scan(self, msg: LaserScan) -> None:
        mn = 99.0
        for r in msg.ranges:
            if r is None:
                continue
            try:
                rv = float(r)
            except Exception:
                continue
            if math.isnan(rv) or math.isinf(rv):
                continue
            if 0.05 < rv < mn:
                mn = rv
        self._min_scan_range_m = mn

    def _on_battery(self, msg: BatteryState) -> None:
        self._battery_pct = float(msg.percentage)

    def _on_estop(self, msg: Bool) -> None:
        prev = self._estop_pressed
        self._estop_pressed = bool(msg.data)
        if self._estop_pressed and not prev:
            self._emit_alert("critical", "estop_pressed",
                             "operator engaged emergency stop")
            self._transition_to(Phase.EMERGENCY_STOP)
            self._publish_cmd_vel(0.0, 0.0)
        elif not self._estop_pressed and prev:
            self.get_logger().info("estop released; back to idle")
            self._transition_to(Phase.IDLE)

    def _on_cmd(self, msg: String) -> None:
        try:
            req = json.loads(msg.data)
        except Exception as exc:
            self.get_logger().warn(f"/patrol/cmd bad JSON: {exc}")
            return
        action = str(req.get("action", ""))
        if action == "start":
            self._start(str(req.get("mode", "waypoint")), req)
        elif action == "pause":
            self._transition_to(Phase.PAUSED)
        elif action == "resume":
            if self._phase == Phase.PAUSED:
                self._transition_to(Phase.PATROLLING)
        elif action == "stop":
            self._transition_to(Phase.IDLE)
            self._publish_cmd_vel(0.0, 0.0)
        else:
            self.get_logger().warn(f"/patrol/cmd unknown action: {action!r}")

    # --------- state transitions ---------
    def _transition_to(self, phase: str) -> None:
        old = self._phase
        self._phase = phase
        self._state_pub.publish(String(data=json.dumps({
            "phase": phase, "prev": old, "ts": time.time(),
        })))
        self.get_logger().info(f"phase {old} -> {phase}")

    def _start(self, mode: str, req: dict) -> None:
        try:
            if mode == "waypoint":
                wp_file = str(req.get("waypoints_file")
                              or self.get_parameter("waypoints_file").value)
                waypoints = load_waypoints_json(wp_file)
                self._mode = WaypointPatrol(
                    waypoints, loop=bool(req.get("loop", True)))
                self.get_logger().info(
                    f"started waypoint patrol with {len(waypoints)} waypoints")
            elif mode == "random":
                bounds = (
                    float(self.get_parameter("random_bounds_xmin").value),
                    float(self.get_parameter("random_bounds_ymin").value),
                    float(self.get_parameter("random_bounds_xmax").value),
                    float(self.get_parameter("random_bounds_ymax").value),
                )
                seed_raw = self.get_parameter("random_seed").value
                seed = None if str(seed_raw).strip().lower() in ("", "none", "null") \
                    else int(seed_raw)
                self._mode = RandomWalkPatrol(bounds=bounds, seed=seed)
                self.get_logger().info(f"started random walk bounds={bounds}")
            else:
                self.get_logger().warn(f"unknown mode {mode!r}")
                return
            self._current_target = self._mode.reset(self._current_pose)
            self._tolerance = self._current_target.tolerance
            self._transition_to(Phase.PATROLLING)
        except Exception as exc:
            self.get_logger().error(f"start failed: {exc}")
            self._emit_alert("warning", "start_failed", str(exc))

    # --------- control loop (10 Hz) ---------
    def _tick(self) -> None:
        if self._estop_pressed:
            self._publish_cmd_vel(0.0, 0.0)
            return

        crit = float(self.get_parameter("battery_critical_threshold").value)
        if self._battery_pct <= crit:
            self._publish_cmd_vel(0.0, 0.0)
            self._emit_alert("critical", "battery_critical",
                             f"battery at {self._battery_pct:.2f}")
            self._transition_to(Phase.RETURNING)
            return

        if self._phase in (Phase.IDLE, Phase.PAUSED):
            self._publish_cmd_vel(0.0, 0.0)
            return

        min_r = float(self.get_parameter("collision_min_range_m").value)
        if self._min_scan_range_m < min_r and self._mode is not None:
            self._publish_cmd_vel(0.0, 0.0)
            self._emit_alert("warning", "collision_guard",
                             f"min scan range {self._min_scan_range_m:.2f} m")
            return

        ret_thr = float(self.get_parameter("battery_return_threshold").value)
        if self._battery_pct <= ret_thr and self._phase == Phase.PATROLLING:
            self._emit_alert("warning", "battery_low_returning",
                             f"battery at {self._battery_pct:.2f}, returning")
            self._transition_to(Phase.RETURNING)

        if self._phase == Phase.DOCKING:
            self._publish_cmd_vel(0.0, 0.0)
            return
        if self._phase == Phase.CHARGING:
            self._publish_cmd_vel(0.0, 0.0)
            return
        if self._phase == Phase.RETURNING:
            self.get_logger().info("returning → docking (via tank_dock)")
            self._transition_to(Phase.DOCKING)
            return

        if self._phase == Phase.PATROLLING:
            if self._mode is None or self._current_target is None:
                self._transition_to(Phase.IDLE)
                return
            target = self._current_target.target
            distance = self._current_pose.distance_to(target)
            if distance <= self._tolerance:
                nxt = self._mode.next_goal(self._current_pose)
                if nxt is None:
                    self._emit_alert("info", "patrol_complete",
                                     "all waypoints visited")
                    self._transition_to(Phase.RETURNING)
                    return
                self._current_target = nxt
                self._publish_event({
                    "type": "waypoint_reached",
                    "label": nxt.label,
                    "ts": time.time(),
                })
            self._drive_towards(self._current_target)

    def _drive_towards(self, goal: MovementGoal) -> None:
        """P-controller on Twist.

        Linear velocity is gated by ``cos(yaw_err)`` so the robot always
        makes *some* forward progress even while rotating. The previous
        "linear = 0 if |yaw_err| > 0.4" gate caused a rotate-stop
        oscillation against the /scan collision guard near walls.
        """
        target = goal.target
        dx = target.x - self._current_pose.x
        dy = target.y - self._current_pose.y
        distance = math.hypot(dx, dy)
        if distance < 1e-3:
            return
        desired_yaw = math.atan2(dy, dx)
        yaw_err = self._wrap_angle(desired_yaw - self._current_pose.yaw)
        ang_z = max(-0.6, min(0.6, 1.5 * yaw_err))
        # Blend: full speed when aligned (cos ~1), zero when 90° off.
        linear = goal.speed * max(0.0, math.cos(yaw_err))
        # Brake at the very end of a leg.
        if distance < 0.4:
            linear *= max(0.0, distance / 0.4)
        self._publish_cmd_vel(linear, ang_z)

    @staticmethod
    def _wrap_angle(a: float) -> float:
        while a > math.pi:
            a -= 2 * math.pi
        while a < -math.pi:
            a += 2 * math.pi
        return a

    # --------- publishers ---------
    def _publish_cmd_vel(self, linear_x: float, angular_z: float) -> None:
        # geometry_msgs/Twist — exactly what tank_motion expects.
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self._cmd_pub.publish(msg)
        self._last_cmd_vel_ms = time.time()

    def _publish_event(self, evt: dict) -> None:
        self._event_pub.publish(String(data=json.dumps(evt)))

    def _emit_alert(self, severity: str, label: str, note: str) -> None:
        self._alert_pub.publish(String(data=json.dumps({
            "ts":       time.time(),
            "severity": severity,
            "label":    label,
            "note":     note,
        })))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PatrolNode()
    executor = MultiThreadedExecutor()      # ← multi thread so
                                            # callback groups can run concurrently
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    import sys
    main(args=sys.argv)
