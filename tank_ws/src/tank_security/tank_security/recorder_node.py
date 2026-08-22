"""Camera recorder — writes MJPEG/MP4 segments on /security/record_now.

Subscribes
    /camera/image_raw        sensor_msgs/Image   bgr8
    /security/record_now     std_msgs/Bool        trigger a recording
    /security/record_stop    std_msgs/Bool        stop the current one
    /security/event          std_msgs/String     any kind, used as filename hint

Publishes
    /security/recording_path  std_msgs/String    absolute path of file being written

Parameters
    output_dir    str   default "/var/tank/recordings"
    fps           int   default 30
    codec         str   default "MJPG"     (FFourCC)
    trigger_sec   float default 8.0         (default recording length)
"""
from __future__ import annotations

import os
import threading
from typing import Optional

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

QOS = 10


class RecorderNode(Node):
    def __init__(self) -> None:
        super().__init__("recorder_node")
        self._declare_params()
        self._bridge = CvBridge()
        self._lock  = threading.Lock()
        self._writer = None  # type: ignore[assignment]
        self._record_started = 0.0

        self.create_subscription(Image, "/camera/image_raw",
                                  self._on_image, QOS)
        self.create_subscription(Bool,  "/security/record_now",
                                  self._on_start, QOS)
        self.create_subscription(Bool,  "/security/record_stop",
                                  self._on_stop, QOS)
        self._path_pub = self.create_publisher(String,
                                                 "/security/recording_path", QOS)
        self.get_logger().info("recorder_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("output_dir", "/var/tank/recordings")
        self.declare_parameter("fps", 30)
        self.declare_parameter("codec", "MJPG")
        self.declare_parameter("trigger_sec", 8.0)

    def _on_start(self, msg: Bool) -> None:
        if not msg.data or self._writer is not None:
            return
        import time as _t
        out = str(self.get_parameter("output_dir").value)
        os.makedirs(out, exist_ok=True)
        fname = f"rec_{int(_t.time())}.avi"
        path = os.path.join(out, fname)
        # We'll grab the frame size from the first frame; use a placeholder
        # writer and finalise once we've seen one.
        fourcc = cv2.VideoWriter_fourcc(
            *str(self.get_parameter("codec").value)
        )
        self._writer = {
            "path": path,
            "fourcc": fourcc,
            "started": _t.time(),
            "video": None,
        }
        self._record_started = _t.time()
        self.get_logger().info(f"recording start: {path}")

    def _on_stop(self, msg: Bool) -> None:
        if msg.data:
            self._close()

    def _on_image(self, msg: Image) -> None:
        if self._writer is None:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge: {exc}", throttle_duration_sec=2.0)
            return
        if self._writer["video"] is None:
            h, w = frame.shape[:2]
            self._writer["video"] = cv2.VideoWriter(
                self._writer["path"], self._writer["fourcc"],
                float(self.get_parameter("fps").value), (w, h),
            )
        self._writer["video"].write(frame)
        import time as _t
        if (_t.time() - self._record_started) > float(self.get_parameter("trigger_sec").value):
            self._close()
        elif self._writer is not None:
            self._path_pub.publish(String(data=self._writer["path"]))

    def _close(self) -> None:
        with self._lock:
            if self._writer is None:
                return
            v = self._writer["video"]
            if v is not None:
                v.release()
            self.get_logger().info(
                f"recording saved: {self._writer['path']}"
            )
            self._writer = None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
