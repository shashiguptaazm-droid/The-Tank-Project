"""2D SLAM bridge / metadata publisher.

slam_toolbox already publishes ``/map`` (nav_msgs/OccupancyGrid), but
downstream tools (RViz, Nav2, the future cartographer-style debugger)
often want a ``/map_metadata`` topic that just carries the grid info
without the heavy data array.

This node also writes the latest map to disk (and to /tmp) every time
it changes, so the operator can grab a `.pgm` file for inspection.

Subscribes:
    /map             nav_msgs/OccupancyGrid

Publishes:
    /map_metadata    nav_msgs/MapMetaData
    /map/saved       std_msgs/String    ("/tmp/tank_map_<timestamp>.pgm")
"""
from __future__ import annotations

import os
import time
from typing import Optional

import rclpy
from nav_msgs.msg import MapMetaData, OccupancyGrid
from rclpy.node import Node
from std_msgs.msg import String

QOS = 5
DEFAULT_SAVE_DIR = "/tmp"


def occupancy_grid_to_pgm(grid: OccupancyGrid) -> str:
    """Save the occupancy grid to a portable PGM file and return the path."""
    os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)
    fname = f"tank_map_{int(time.time())}.pgm"
    fpath = os.path.join(DEFAULT_SAVE_DIR, fname)
    width = grid.info.width
    height = grid.info.height
    resolution = grid.info.resolution
    header = (
        f"P5\n"
        f"# The Tank Project — 2D SLAM occupancy grid\n"
        f"# resolution: {resolution}\n"
        f"# origin: ({grid.info.origin.position.x:.3f}, "
        f"{grid.info.origin.position.y:.3f}, "
        f"{grid.info.origin.position.z:.3f})\n"
        f"{width} {height}\n255\n"
    )
    with open(fpath, "wb") as fh:
        fh.write(header.encode("ascii"))
        # PGM uses 0 = black (occupied), 255 = white (free).
        # ROS OccupancyGrid uses -1 (unknown) = 205 by convention.
        for raw in grid.data:
            if raw == -1 or raw > 99:
                byte = 205 if raw == -1 else 0
            elif raw == 0:
                byte = 254
            else:
                # Linear remap from [1..100] chance -> [253..1]
                byte = max(1, 254 - raw * 253 // 100)
            fh.write(bytes([byte]))
    return fpath


class Slam2dBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("slam_2d_bridge")
        self.declare_parameter("save_to_disk", True)
        self.declare_parameter("save_dir", DEFAULT_SAVE_DIR)
        self._last_save = 0.0
        self._meta_pub = self.create_publisher(MapMetaData, "map_metadata", QOS)
        self._save_pub = self.create_publisher(String,         "map/saved",   QOS)
        self._sub      = self.create_subscription(OccupancyGrid, "map",
                                                   self._on_map, QOS)
        self.get_logger().info("slam_2d_bridge initialised")

    def _on_map(self, msg: OccupancyGrid) -> None:
        self._meta_pub.publish(msg.info)
        now = time.time()
        if bool(self.get_parameter("save_to_disk").value) and (now - self._last_save) > 5.0:
            try:
                path = occupancy_grid_to_pgm(msg)
                self._last_save = now
                self.get_logger().info(f"saved map to {path}")
                self._save_pub.publish(String(data=path))
            except Exception as exc:
                self.get_logger().warn(f"map save failed: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Slam2dBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
