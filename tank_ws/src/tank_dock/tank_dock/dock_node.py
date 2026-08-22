"""Auto-dock — AprilTag detection + IR beacon homing.

Subscribes
    /camera/image_raw    sensor_msgs/Image       bgr8
    /dock/enable         std_msgs/Bool           default True

Publishes
    /dock/pose           geometry_msgs/PoseStamped   tag in camera frame
    /dock/charge_cmd     std_msgs/Bool               relay the contactor
    /dock/state          std_msgs/String             "searching" | "docked" | "lost"

Parameters
    tag_size             float default 0.10     m
    tag_id               int   default 42       (applies to dock marker)
    offset_distance      float default 0.40     (m ahead of tag for final stop)
    timeout_sec          float default 30.0     (search -> lost)
"""
from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose, PoseStamped
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

QOS = 10


class AprilTagDetect:
    def __init__(self, tag_id: int, tag_size: float) -> None:
        try:
            self._detector = cv2.aruco.ArucoDetector(
                cv2.aruco.Dictionary_get(cv2.aruco.DICT_APRILTAG_36h11),
                cv2.aruco.DetectorParameters_create(),
            )
        except AttributeError:
            # Newer OpenCV API
            self._dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
            self._params = cv2.aruco.DetectorParameters()
            self._detector = cv2.aruco.ArucoDetector(self._dict, self._params)
        self._expected_id = tag_id
        # Approximate camera intrinsic (Pi Cam v3 nominal) — calibrate in prod.
        self._K = np.array([
            [800.0,   0.0, 640.0],
            [  0.0, 800.0, 360.0],
            [  0.0,   0.0,   1.0],
        ])
        self._D = np.zeros(5)

    def detect(self, frame) -> Optional[Pose]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._detector.detectMarkers(gray)
        if ids is None:
            return None
        for i, marker_id in enumerate(ids.flatten().tolist()):
            if marker_id != self._expected_id:
                continue
            # Pose estimation (OpenCV >=4.7)
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners[i:i+1], self._tag_size, self._K, self._D,
            )
            tvec = tvecs[0][0]
            pose = Pose()
            pose.position.x = float(tvec[0])
            pose.position.y = float(tvec[1])
            pose.position.z = float(tvec[2])
            return pose
        return None


class DockNode(Node):
    def __init__(self) -> None:
        super().__init__("dock_node")
        self._declare_params()
        self._bridge = CvBridge()
        self._tag_id  = int(self.get_parameter("tag_id").value)
        self._tag_sz  = float(self.get_parameter("tag_size").value)
        self._det = AprilTagDetect(self._tag_id, self._tag_sz)
        self._enabled = bool(self.get_parameter("enable").value)
        self._last_seen = 0.0
        self._creation_ts = time.monotonic()
        self._state = "searching"

        self.create_subscription(Image, "/camera/image_raw",
                                  self._on_image, QOS)
        self.create_subscription(Bool,  "/dock/enable",
                                  self._on_enable, QOS)
        self._pose_pub = self.create_publisher(PoseStamped, "/dock/pose", QOS)
        self._cmd_pub  = self.create_publisher(Bool, "/dock/charge_cmd", QOS)
        self._state_pub = self.create_publisher(String, "/dock/state", QOS)

        self._timer = self.create_timer(0.5, self._tick)
        self.get_logger().info("dock_node initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("enable", True)
        self.declare_parameter("tag_size", 0.10)
        self.declare_parameter("tag_id", 42)
        self.declare_parameter("offset_distance", 0.40)
        self.declare_parameter("timeout_sec", 30.0)

    def _on_enable(self, msg: Bool) -> None:
        self._enabled = msg.data
        if not msg.data:
            self._state = "searching"
        else:
            self._creation_ts = time.monotonic()
        self._state_pub.publish(String(data=self._state))

    def _on_image(self, msg: Image) -> None:
        if not self._enabled:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge: {exc}", throttle_duration_sec=2.0)
            return
        pose = self._det.detect(frame)
        if pose is None:
            return
        self._last_seen = time.monotonic()
        ps = PoseStamped()
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.header.frame_id = "camera_optical_frame"
        ps.pose = pose
        self._pose_pub.publish(ps)
        if pose.position.z < 0.30 and (
            self._state != "docked"
        ):
            self._state = "docked"
            self._cmd_pub.publish(Bool(data=True))
            self._state_pub.publish(String(data=self._state))

    def _tick(self) -> None:
        if not self._enabled:
            return
        if self._state == "searching":
            elapsed = time.monotonic() - self._creation_ts
            if (elapsed > float(self.get_parameter("timeout_sec").value)) \
                    and (time.monotonic() - self._last_seen) > 5.0:
                self._state = "lost"
                self._state_pub.publish(String(data=self._state))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DockNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
