"""Skid-steer motor controller for The Tank Project.

Subscribes:
  * /cmd_vel   (geometry_msgs/Twist)
  * /estop     (std_msgs/Bool, latched — wins over /cmd_vel)

Publishes (50 Hz):
  * /odom          (nav_msgs/Odometry)
  * /motor_status  (std_msgs/Float32MultiArray)
                   [v_left, v_right, linear, angular, cmd_age_sec]
  * /joint_states  (sensor_msgs/JointState, ``track_left_joint`` +
                   ``track_right_joint``)

Hardware: motor driver H-bridge on GPIO (DIR + PWM per motor) via
``gpiozero``, which works on the Pi 5 (the legacy ``RPi.GPIO`` does not).

A 0.5 s watchdog on ``/cmd_vel`` halts the motors if no Twist arrives.
Recovery is automatic; the latched ``/estop`` from ``safety_watchdog``
always wins.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float32MultiArray

from .truck_kinematics import (
    ChassisGeometry,
    compute_motor_command,
    track_speeds_to_twist,
)

CMD_TIMEOUT_SEC = 0.5
DEFAULT_RATE_HZ = 50.0
QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


@dataclass
class MotorHalInterface:
    """Thread-safe hardware abstraction for a dual-channel H-bridge driver."""
    def set_motors(self, duty_left: float, duty_right: float) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class GpioZeroMotorHAL:
    """gpiozero-backed HAL — works on Pi 5 via ``libgpio``."""
    def __init__(self, dir_left: int, pwm_left: int,
                 dir_right: int, pwm_right: int,
                 pwm_frequency: int = 1000) -> None:
        from gpiozero import PWMOutputDevice, OutputDevice  # lazy import
        self._dir_left   = OutputDevice(dir_left)
        self._pwm_left   = PWMOutputDevice(pwm_left,  frequency=pwm_frequency)
        self._dir_right  = OutputDevice(dir_right)
        self._pwm_right  = PWMOutputDevice(pwm_right, frequency=pwm_frequency)
        self._lock = threading.Lock()

    def set_motors(self, duty_left: float, duty_right: float) -> None:
        with self._lock:
            self._dir_left.value  = bool(duty_left  >= 0)
            self._dir_right.value = bool(duty_right >= 0)
            self._pwm_left.value  = abs(duty_left)
            self._pwm_right.value = abs(duty_right)

    def stop(self) -> None:
        with self._lock:
            self._pwm_left.value  = 0.0
            self._pwm_right.value = 0.0

    def close(self) -> None:
        with self._lock:
            try: self._pwm_left.value  = 0.0
            except Exception: pass
            try: self._pwm_right.value = 0.0
            except Exception: pass
            self._pwm_left.close()
            self._pwm_right.close()
            self._dir_left.close()
            self._dir_right.close()


class NullMotorHAL:
    """HAL that swallows commands; used in unit tests and ``dry_run`` mode."""
    def __init__(self) -> None:
        self.last_duty: Tuple[float, float] = (0.0, 0.0)

    def set_motors(self, duty_left: float, duty_right: float) -> None:
        self.last_duty = (duty_left, duty_right)

    def stop(self) -> None:
        self.last_duty = (0.0, 0.0)

    def close(self) -> None:
        pass


class MotorControllerNode(Node):
    def __init__(self, hal: Optional[MotorHalInterface] = None) -> None:
        super().__init__("motor_controller")
        self._declare_params()
        self._geo     = self._build_geometry()
        self._max_rpm = float(self.get_parameter("max_rpm").value)
        hal_provided = hal is not None
        self._hal = hal or GpioZeroMotorHAL(
            dir_left=int(self.get_parameter("dir_left_pin").value),
            pwm_left=int(self.get_parameter("pwm_left_pin").value),
            dir_right=int(self.get_parameter("dir_right_pin").value),
            pwm_right=int(self.get_parameter("pwm_right_pin").value),
            pwm_frequency=int(self.get_parameter("pwm_frequency").value),
        )
        if not hal_provided:
            self.get_logger().info("Using GpioZeroMotorHAL on the Pi 5 GPIO header.")

        self._lock           = threading.Lock()
        self._last_twist     = (0.0, 0.0)
        self._last_cmd_time  = 0.0
        self._estop_latched  = False
        self._v_left, self._v_right = 0.0, 0.0

        self._cmd_sub    = self.create_subscription(Twist, "cmd_vel", self._on_cmd_vel, QOS)
        self._estop_sub  = self.create_subscription(Bool,  "estop",   self._on_estop,   QOS)
        self._odom_pub   = self.create_publisher(Odometry,           "odom",          QOS)
        self._status_pub = self.create_publisher(Float32MultiArray,  "motor_status",  QOS)
        self._js_pub     = self.create_publisher(JointState,         "joint_states",  QOS)
        self._timer      = self.create_timer(1.0 / DEFAULT_RATE_HZ, self._tick)
        self.get_logger().info("motor_controller initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("track_width", 0.30)
        self.declare_parameter("wheel_radius", 0.05)
        self.declare_parameter("max_linear_velocity", 0.8)
        self.declare_parameter("max_angular_velocity", 1.5)
        self.declare_parameter("max_rpm", 220.0)
        self.declare_parameter("dir_left_pin",  17)
        self.declare_parameter("pwm_left_pin",  18)
        self.declare_parameter("dir_right_pin", 27)
        self.declare_parameter("pwm_right_pin", 22)
        self.declare_parameter("pwm_frequency", 1000)

    def _build_geometry(self) -> ChassisGeometry:
        return ChassisGeometry(
            track_width=float(self.get_parameter("track_width").value),
            wheel_radius=float(self.get_parameter("wheel_radius").value),
            max_linear_velocity=float(self.get_parameter("max_linear_velocity").value),
            max_angular_velocity=float(self.get_parameter("max_angular_velocity").value),
        )

    def _on_cmd_vel(self, msg: Twist) -> None:
        with self._lock:
            self._last_cmd_time = time.monotonic()
            self._last_twist = (msg.linear.x, msg.angular.z)
        if not self._estop_latched:
            self._apply(msg.linear.x, msg.angular.z)

    def _on_estop(self, msg: Bool) -> None:
        with self._lock:
            self._estop_latched = msg.data
            if msg.data:
                self._hal.stop()
                self.get_logger().warn("E-stop LATCHED — motors halted")
            else:
                self.get_logger().info("E-stop released")
                if self._last_cmd_time and (time.monotonic() - self._last_cmd_time) < CMD_TIMEOUT_SEC:
                    self._apply(*self._last_twist)

    def _apply(self, linear: float, angular: float) -> None:
        duty_left, duty_right, v_left, v_right = compute_motor_command(
            linear, angular, self._geo, self._max_rpm
        )
        with self._lock:
            self._hal.set_motors(duty_left, duty_right)
            self._v_left  = v_left
            self._v_right = v_right

    def _tick(self) -> None:
        now = time.monotonic()
        with self._lock:
            cmd_age        = (now - self._last_cmd_time) if self._last_cmd_time else math.inf
            estop          = self._estop_latched
            v_left, v_right = self._v_left, self._v_right
        if estop or cmd_age > CMD_TIMEOUT_SEC:
            self._hal.stop()
            if estop:
                return
            return
        linear, angular = track_speeds_to_twist(v_left, v_right, self._geo)
        stamp = self.get_clock().now().to_msg()
        odom = Odometry()
        odom.header.stamp    = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id  = "base_link"
        odom.twist.twist.linear.x  = linear
        odom.twist.twist.angular.z = angular
        self._odom_pub.publish(odom)
        status = Float32MultiArray()
        status.data = [v_left, v_right, linear, angular, float(cmd_age)]
        self._status_pub.publish(status)
        js = JointState()
        js.header.stamp = stamp
        js.name = ["track_left_joint", "track_right_joint"]
        js.velocity = [v_left / self._geo.wheel_radius,
                       v_right / self._geo.wheel_radius]
        self._js_pub.publish(js)

    def destroy_node(self) -> None:
        try:
            self._hal.close()
        finally:
            super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = MotorControllerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
