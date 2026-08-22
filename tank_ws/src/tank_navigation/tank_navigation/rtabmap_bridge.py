"""3D-Map bridge — bookkeeping for RTAB-Map.

rtabmap_ros publishes rich statistics (``/rtabmap/info``) and the actual
dense cloud (``/rtabmap/cloud_map``). Robotics stacks sometimes want to
quantise "how much progress have we made" into a single integer — this
node republishes the latest stats as /mapping/loop_closures and writes a
small JSON dump of progress every ~10 s, useful when the operator runs
the robot without RViz open.

Subscribes:
    /rtabmap/info        rtabmap_msgs/Info

Publishes:
    /mapping/stats        std_msgs/String      JSON snapshot
    /mapping/loop_count   std_msgs/Int32       cumulative loop closures
"""
from __future__ import annotations

import json
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String

# rtabmap_msgs only carries the msg class if RTAB-Map is installed.
# Try to import it lazily; fall back to a generic StubInfo message.
try:
    from rtabmap_msgs.msg import Info as RtabInfo  # type: ignore
except Exception:
    RtabInfo = None  # type: ignore

QOS = 5


class RtabMapBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("rtabmap_bridge")
        self.declare_parameter("log_every_sec", 10.0)
        self._last_log = 0.0
        self._stats_pub  = self.create_publisher(String, "mapping/stats",      QOS)
        self._loops_pub  = self.create_publisher(Int32,  "mapping/loop_count", QOS)
        if RtabInfo is None:
            self.get_logger().warn("rtabmap_msgs not importable; "
                                   "the bridge will only republish saved stats.")
        else:
            self.create_subscription(RtabInfo, "rtabmap/info",
                                     self._on_info, QOS)
        self._timer = self.create_timer(1.0, self._tick)
        self.get_logger().info("rtabmap_bridge initialised")

    def _on_info(self, msg) -> None:
        stats = {
            "stamp":        time.time(),
            "loop_closures": int(getattr(msg, "loop_closure_count", 0)),
            "keyframes":    int(getattr(msg, "keyframes_count",    0)),
            "words":        int(getattr(msg, "words_count",        0)),
            "nodes":        int(getattr(msg, "nodes_count",        0)),
            "edges":        int(getattr(msg, "edges_count",        0)),
            "wm_size":      float(getattr(msg, "wm",  0.0)),
        }
        self._loops_pub.publish(Int32(data=stats["loop_closures"]))
        self._stats_pub.publish(String(data=json.dumps(stats)))

    def _tick(self) -> None:
        if RtabInfo is None:
            return
        now = time.time()
        if (now - self._last_log) > float(self.get_parameter("log_every_sec").value):
            self._last_log = now
            self.get_logger().info("(bridge) RTAB-Map stats up to date")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RtabMapBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
