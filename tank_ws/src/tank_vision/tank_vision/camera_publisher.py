"""AI vision camera publisher for The Tank Project.

Captures frames from any OpenCV-compatible camera (USB webcam, Pi Camera
Module 2/3 via libcamera, or V4L2 device). This node is deliberately thin:
it just produces `sensor_msgs/Image` and `sensor_msgs/CameraInfo`; the
actual detection / depth model lives in a downstream node
(``tank_perception`` later in phase 5).

Publishes (configurable, default 30 Hz):
  * /camera/image_raw   (sensor_msgs/Image, ``bgr8``)
  * /camera/camera_info (sensor_msgs/CameraInfo, height / width populated,
                         intrinsics left zeroed — fill from a YAML in
                         phase 2 once we calibrate the lens)
"""
from __future__ import annotations

from typing import Optional

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import CameraInfo, Image

DEFAULT_DEVICE = 0
DEFAULT_WIDTH  = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS    = 30
QOS = 10


class CameraHalInterface:
    """Returns a single BGR frame per call."""
    def read(self): ...
    def close(self) -> None: ...


class OpenCvCameraHal:
    """OpenCV VideoCapture-based HAL."""

    def __init__(self, device: int = DEFAULT_DEVICE,
                 width: int = DEFAULT_WIDTH,
                 height: int = DEFAULT_HEIGHT,
                 fps: int = DEFAULT_FPS) -> None:
        import cv2
        self._cap = cv2.VideoCapture(device)
        if width  > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        if height > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps    > 0:
            self._cap.set(cv2.CAP_PROP_FPS,          fps)
        if not self._cap.isOpened():
            raise RuntimeError(f"could not open video device {device}")

    def read(self):
        import cv2
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("camera frame not ready")
        return frame

    def close(self) -> None:
        try:
            self._cap.release()
        except Exception:
            pass


class CameraPublisherNode(Node):
    def __init__(self, hal: Optional[CameraHalInterface] = None) -> None:
        super().__init__("camera_publisher")
        self.declare_parameter("device",   DEFAULT_DEVICE)
        self.declare_parameter("width",    DEFAULT_WIDTH)
        self.declare_parameter("height",   DEFAULT_HEIGHT)
        self.declare_parameter("fps",      DEFAULT_FPS)
        self.declare_parameter("frame_id", "camera_optical_frame")

        hal_provided = hal is not None
        self._hal = hal or OpenCvCameraHal(
            device=int(self.get_parameter("device").value),
            width=int(self.get_parameter("width").value),
            height=int(self.get_parameter("height").value),
            fps=int(self.get_parameter("fps").value),
        )
        if not hal_provided:
            self.get_logger().info(
                f"Using OpenCvCameraHal device={self.get_parameter('device').value}"
            )

        self._img_pub  = self.create_publisher(Image,      "camera/image_raw",   QOS)
        self._info_pub = self.create_publisher(CameraInfo, "camera/camera_info", QOS)

        fps = max(1.0, float(self.get_parameter("fps").value))
        self._timer = self.create_timer(1.0 / fps, self._tick)
        self.get_logger().info("camera_publisher initialised")

    def _tick(self) -> None:
        try:
            frame = self._hal.read()
        except Exception as exc:
            self.get_logger().warn(
                f"camera read failed: {exc}", throttle_duration_sec=2.0
            )
            return

        height, width = frame.shape[:2]
        stamp = self.get_clock().now().to_msg()
        frame_id = str(self.get_parameter("frame_id").value)

        img = Image()
        img.header.stamp    = stamp
        img.header.frame_id = frame_id
        img.height       = height
        img.width        = width
        img.encoding     = "bgr8"
        img.is_bigendian = False
        img.step         = width * 3
        img.data         = frame.tobytes()
        self._img_pub.publish(img)

        info = CameraInfo()
        info.header = img.header
        info.height = height
        info.width  = width
        self._info_pub.publish(info)

    def destroy_node(self) -> None:
        try:
            self._hal.close()
        finally:
            super().destroy_node()


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = CameraPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
