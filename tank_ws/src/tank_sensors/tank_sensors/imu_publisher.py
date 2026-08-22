"""IMU publisher for The Tank Project.

Uses a BNO055 9-DOF IMU on I²C bus 1 (default address 0x28). The BNO055
fuses accel / gyro / magnetometer on-chip so we get a quaternion orientation
out of the box. If you swap to a different IMU, change the implementation
behind ``ImuHalInterface`` — the node stays the same.

Publishes (50 Hz by default):
  * /imu/data    (sensor_msgs/Imu)             - fused orientation + rates
  * /imu/mag     (sensor_msgs/MagneticField)
  * /imu/calib   (std_msgs/Int8MultiArray)     - (sys,gyr,acc,mag) calib status
"""
from __future__ import annotations

import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Int8MultiArray

QOS = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT)
DEFAULT_RATE_HZ = 50.0
DEFAULT_I2C_ADDRESS = 0x28


class ImuHalInterface:
    """Abstract IMU driver. SI units; quaternion returned as (w, x, y, z)."""
    def read(self) -> dict: ...
    def close(self) -> None: ...


class Bno055ImuHal:
    """BNO055 backed by the Adafruit CircuitPython driver."""

    def __init__(self, address: int = DEFAULT_I2C_ADDRESS) -> None:
        from adafruit_bno055 import BNO055
        import board  # type: ignore[import-not-found]
        import busio
        self._i2c = busio.I2C(board.SCL, board.SDA)
        # BNO055 needs a soft reset + NDOF mode after power-up; the Adafruit
        # driver leaves the chip in NDOF by default.
        self._bno = BNO055(self._i2c, address=address)

    def read(self) -> dict:
        bno = self._bno
        return {
            "quat": tuple(bno.quaternion or (1.0, 0.0, 0.0, 0.0)),
            "gyro": tuple(bno.gyro or (0.0, 0.0, 0.0)),
            "accel": tuple(bno.acceleration or (0.0, 0.0, 0.0)),
            "mag": tuple(bno.magnetic or (0.0, 0.0, 0.0)),
            "calib": tuple(bno.calibration_status or (0, 0, 0, 0)),
        }

    def close(self) -> None:
        try:
            self._i2c.deinit()
        except Exception:
            pass


class ImuPublisherNode(Node):
    def __init__(self, hal: Optional[ImuHalInterface] = None,
                 rate_hz: float = DEFAULT_RATE_HZ) -> None:
        super().__init__("imu_publisher")
        self.declare_parameter("i2c_address", DEFAULT_I2C_ADDRESS)
        self.declare_parameter("rate_hz", rate_hz)
        self.declare_parameter("frame_id", "imu_link")

        hal_provided = hal is not None
        self._hal = hal or Bno055ImuHal(
            address=int(self.get_parameter("i2c_address").value)
        )
        if not hal_provided:
            addr = int(self.get_parameter("i2c_address").value)
            self.get_logger().info(f"Using Bno055ImuHal at I²C address 0x{addr:02x}.")

        self._period    = 1.0 / max(1.0, float(self.get_parameter("rate_hz").value))
        self._imu_pub   = self.create_publisher(Imu,             "imu/data",  QOS)
        self._mag_pub   = self.create_publisher(MagneticField,   "imu/mag",   QOS)
        self._calib_pub = self.create_publisher(Int8MultiArray,  "imu/calib", QOS)
        self._timer     = self.create_timer(self._period, self._tick)
        self.get_logger().info("imu_publisher initialised")

    def _tick(self) -> None:
        try:
            data = self._hal.read()
        except Exception as exc:
            self.get_logger().warn(
                f"IMU read failed: {exc}", throttle_duration_sec=2.0
            )
            return
        stamp = self.get_clock().now().to_msg()
        frame = str(self.get_parameter("frame_id").value)

        imu = Imu()
        imu.header.stamp = stamp
        imu.header.frame_id = frame
        w, x, y, z = data["quat"]
        imu.orientation.w = float(w)
        imu.orientation.x = float(x)
        imu.orientation.y = float(y)
        imu.orientation.z = float(z)
        gx, gy, gz = data["gyro"]
        imu.angular_velocity.x = float(gx)
        imu.angular_velocity.y = float(gy)
        imu.angular_velocity.z = float(gz)
        ax, ay, az = data["accel"]
        imu.linear_acceleration.x = float(ax)
        imu.linear_acceleration.y = float(ay)
        imu.linear_acceleration.z = float(az)
        self._imu_pub.publish(imu)

        mag = MagneticField()
        mag.header.stamp = stamp
        mag.header.frame_id = frame
        mx, my, mz = data["mag"]
        mag.magnetic_field.x = float(mx)
        mag.magnetic_field.y = float(my)
        mag.magnetic_field.z = float(mz)
        self._mag_pub.publish(mag)

        calib = Int8MultiArray()
        calib.data = list(data["calib"])
        self._calib_pub.publish(calib)


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = ImuPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
