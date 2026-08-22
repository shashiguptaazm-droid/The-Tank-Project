"""Motion detection — frame differencing triggered by /security/enable.

Subscribes
    /camera/image_raw  sensor_msgs/Image   bgr8
    /security/enable   std_msgs/Bool       default True

Publishes
    /security/events/motion        std_msgs/String   "{timestamp} motion"

Parameters
    diff_threshold   int   default 25        (per-pixel delta)
    min_contour_area int   default 1500      (ignore tiny diffs)
    cooldown_sec     float default 5.0
"""
from __future__ import annotations

import threading
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

QOS = 10


class MotionNode(Node):
    def __init__(self) -> None:
        super().__init__("motion_node")
        self._declare_params()
        self._bridge = CvBridge()
        self._lock = threading.Lock()
        self._enabled = bool(self.get_parameter("enable").value)
        self._last_pub = 0.0
        self._last_frame = None  # type: ignore[assignment]
        self.create_subscription(Image, "/camera/image_raw", self._on_image, QOS)
        self.create_subscription(Bool,  "/security/enable",  self._on_enable, QOS)
        self._pub = self.create_publisher(String, "/security/events/motion", QOS)
        self.get_logger().info("motion_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("enable", True)
        self.declare_parameter("diff_threshold", 25)
        self.declare_parameter("min_contour_area", 1500)
        self.declare_parameter("cooldown_sec", 5.0)

    def _on_enable(self, msg: Bool) -> None:
        with self._lock:
            self._enabled = msg.data

    def _on_image(self, msg: Image) -> None:
        if not self._enabled:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge: {exc}", throttle_duration_sec=2.0)
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        with self._lock:
            if self._last_frame is None:
                self._last_frame = gray
                return
            delta = cv2.absdiff(self._last_frame, gray)
            self._last_frame = gray
            # cooldown
            now = time.monotonic()
            if (now - self._last_pub) < float(self.get_parameter("cooldown_sec").value):
                return
            thresh = cv2.threshold(
                delta, int(self.get_parameter("diff_threshold").value),
                255, cv2.THRESH_BINARY,
            )[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
        min_area = int(self.get_parameter("min_contour_area").value)
        for c in contours:
            if cv2.contourArea(c) < min_area:
                continue
            self._last_pub = now
            self._pub.publish(String(
                data=f"motion at t={now:.3f} area={int(cv2.contourArea(c))}"
            ))
            break


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
