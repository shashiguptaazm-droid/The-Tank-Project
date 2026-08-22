"""Pan-tilt servo controller for the head unit.

Two hobby servos driven by a PCA9685 16-channel 12-bit PWM board over I²C
(default address 0x40). Subscribes to ``/pan_tilt_cmd`` as
``sensor_msgs/JointState`` with joint names ``"pan"`` and ``"tilt"`` and
publishes the current pose on ``/pan_tilt_state``.

Angles are specified in radians, clamped per the configured joint limits,
and mapped internally to the servo's standard 1000..2000 µs pulse range.
"""
from __future__ import annotations

import math
from typing import Optional

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState

DEFAULT_PCA9685_ADDR = 0x40
QOS = 10


class ServoDriver:
    """Abstract 2-axis servo head."""
    def set_angle(self, channel: int, radians: float) -> None: ...
    def close(self) -> None: ...


class Pca9685ServoDriver:
    """PCA9685-backed implementation.

    Uses Adafruit's CircuitPython driver + adafruit_motor.servo. The
    board.SCL/SDA terms are correct on a stock Pi — they map to I²C bus 1.
    """
    def __init__(self, i2c_address: int = DEFAULT_PCA9685_ADDR,
                 pwm_frequency: int = 50,
                 pan_channel: int = 0, tilt_channel: int = 1,
                 min_pulse_us: int = 1000, max_pulse_us: int = 2000) -> None:
        from adafruit_pca9685 import PCA9685
        from adafruit_motor import servo
        import board  # type: ignore[import-not-found]
        import busio
        self._i2c = busio.I2C(board.SCL, board.SDA)
        self._pca = PCA9685(self._i2c, address=i2c_address)
        self._pca.frequency = pwm_frequency
        self._pan_servo  = servo.Servo(
            self._pca.channels[pan_channel],
            min_pulse=min_pulse_us,
            max_pulse=max_pulse_us,
        )
        self._tilt_servo = servo.Servo(
            self._pca.channels[tilt_channel],
            min_pulse=min_pulse_us,
            max_pulse=max_pulse_us,
        )
        self._pan_channel  = pan_channel
        self._tilt_channel = tilt_channel

    def set_angle(self, channel: int, radians: float) -> None:
        deg = max(0.0, min(180.0, math.degrees(radians)))
        if channel == self._pan_channel:
            self._pan_servo.angle = deg
        elif channel == self._tilt_channel:
            self._tilt_servo.angle = deg

    def close(self) -> None:
        try:
            self._pca.deinit()
        except Exception:
            pass


class PanTiltControllerNode(Node):
    def __init__(self, driver: Optional[ServoDriver] = None) -> None:
        super().__init__("pan_tilt_controller")
        self.declare_parameter("i2c_address",  DEFAULT_PCA9685_ADDR)
        self.declare_parameter("pwm_frequency", 50)
        self.declare_parameter("pan_channel",   0)
        self.declare_parameter("tilt_channel",  1)
        self.declare_parameter("pan_min",      -1.5708)
        self.declare_parameter("pan_max",       1.5708)
        self.declare_parameter("tilt_min",     -0.7854)
        self.declare_parameter("tilt_max",      0.7854)

        hal_provided = driver is not None
        self._driver = driver or Pca9685ServoDriver(
            i2c_address=int(self.get_parameter("i2c_address").value),
            pwm_frequency=int(self.get_parameter("pwm_frequency").value),
            pan_channel=int(self.get_parameter("pan_channel").value),
            tilt_channel=int(self.get_parameter("tilt_channel").value),
        )
        if not hal_provided:
            self.get_logger().info("Using Pca9685ServoDriver on I²C bus 1.")

        self._pan  = 0.0
        self._tilt = 0.0
        self._sub  = self.create_subscription(JointState, "pan_tilt_cmd",
                                              self._on_cmd, QOS)
        self._pub  = self.create_publisher(JointState, "pan_tilt_state", QOS)
        self.get_logger().info("pan_tilt_controller initialised")

    def _on_cmd(self, msg: JointState) -> None:
        params = {n: float(p) for n, p in zip(msg.name, msg.position)}
        if "pan" in params:
            self._pan = self._clamp(
                params["pan"],
                float(self.get_parameter("pan_min").value),
                float(self.get_parameter("pan_max").value),
            )
        if "tilt" in params:
            self._tilt = self._clamp(
                params["tilt"],
                float(self.get_parameter("tilt_min").value),
                float(self.get_parameter("tilt_max").value),
            )
        try:
            self._driver.set_angle(int(self.get_parameter("pan_channel").value),  self._pan)
            self._driver.set_angle(int(self.get_parameter("tilt_channel").value), self._tilt)
        except Exception as exc:
            self.get_logger().error(f"servo write failed: {exc}")
        self._publish_state()

    def _publish_state(self) -> None:
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = ["pan", "tilt"]
        js.position = [self._pan, self._tilt]
        self._pub.publish(js)

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = PanTiltControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
