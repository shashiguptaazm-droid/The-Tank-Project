"""LiDAR publisher for The Tank Project.

Defaults to an RPLidar A1/A2/A3 over USB serial. We implement the RPLidar
bridge in pure Python so we don't depend on `ros-<dist>-rplidar`. If you'd
rather use upstream `rplidar_ros`, just disable this node in
`sensors.launch.py`.

Publishes one full 360° revolution per ``sensor_msgs/LaserScan`` message
on ``/scan``.
"""
from __future__ import annotations

import math
import threading
from typing import Optional

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import LaserScan

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_FRAME = "lidar_link"
QOS = 10


class LidarHalInterface:
    """Yields one complete scan per iteration. Each scan is a sequence of
    ``(quality, angle_deg, distance_mm)`` tuples — the contract used by
    RPLidar's ``iter_scans()`` generator.
    """
    def iter_scans(self): ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class RplidarHal:
    """Wraps the Slamtec RPLidar pure-Python driver."""

    def __init__(self, port: str = DEFAULT_PORT, baudrate: int = 115_200,
                 timeout: float = 1.0) -> None:
        from rplidar import RPLidar
        self._lidar = RPLidar(port, baudrate=baudrate, timeout=timeout)

    def iter_scans(self):
        for scan in self._lidar.iter_scans():
            yield scan

    def stop(self) -> None:
        try:
            self._lidar.stop()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._lidar.disconnect()
        except Exception:
            pass


class LidarPublisherNode(Node):
    def __init__(self, hal: Optional[LidarHalInterface] = None) -> None:
        super().__init__("lidar_publisher")
        self.declare_parameter("port",     DEFAULT_PORT)
        self.declare_parameter("frame_id", DEFAULT_FRAME)
        self.declare_parameter("baudrate", 115_200)

        hal_provided = hal is not None
        self._hal = hal or RplidarHal(
            port=str(self.get_parameter("port").value),
            baudrate=int(self.get_parameter("baudrate").value),
        )
        if not hal_provided:
            self.get_logger().info(
                f"Using RplidarHal on {self.get_parameter('port').value}"
            )

        self._pub        = self.create_publisher(LaserScan, "scan", QOS)
        self._stop_event = threading.Event()
        self._thread     = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.get_logger().info("lidar_publisher initialised")

    def _loop(self) -> None:
        try:
            for scan in self._hal.iter_scans():
                if self._stop_event.is_set():
                    break
                try:
                    self._publish(scan)
                except Exception as exc:
                    self.get_logger().warn(
                        f"scan publish failed: {exc}", throttle_duration_sec=1.0
                    )
        except Exception as exc:
            self.get_logger().error(f"LiDAR scan loop exited: {exc}")
        self.get_logger().warn("LiDAR scan loop exited")

    def _publish(self, scan) -> None:
        if not scan:
            return
        angles     = [math.radians(row[1]) for row in scan]
        ranges_mm  = [row[2] for row in scan]
        ranges     = [d / 1000.0 for d in ranges_mm]
        msg = LaserScan()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = str(self.get_parameter("frame_id").value)
        if angles:
            msg.angle_min      = min(angles)
            msg.angle_max      = max(angles)
            msg.angle_increment = (msg.angle_max - msg.angle_min) / max(1, len(angles) - 1)
        msg.time_increment = 0.0
        msg.scan_time      = 0.0
        msg.range_min      = 0.15
        msg.range_max      = 12.0
        msg.ranges         = ranges
        self._pub.publish(msg)

    def destroy_node(self) -> None:
        self._stop_event.set()
        try:
            self._hal.stop()
        finally:
            try:
                self._hal.close()
            finally:
                super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = LidarPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
