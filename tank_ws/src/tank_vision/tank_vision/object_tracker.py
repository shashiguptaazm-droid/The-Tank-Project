"""Visual object tracker — runs a lightweight YOLOv8n model on the AI
camera feed and drives the pan-tilt head to keep the chosen class centred
in the frame.

Subscribes:
    /camera/image_raw          sensor_msgs/Image       bgr8
    /tracker/target_class      std_msgs/String         default "person"
    /tracker/tracking_enabled  std_msgs/Bool           default True

Publishes:
    /tracked_target            geometry_msgs/PointStamped
                              (gaze in NDC x,y in [-1, 1] + frame_id timestamp)
    /tracked_target/visible    std_msgs/Bool
    /pan_tilt_cmd              sensor_msgs/JointState  feeds pan_tilt_controller
    /tracked_target/bbox       geometry_msgs/PolygonStamped
                              four (x,y) image-space points defining the bbox

Parameters:
    yolo_model        str      default "yolov8n.pt"
    conf_threshold    float    default 0.35
    pan_kp            float    default 0.6  (rad per NDC unit)
    tilt_kp           float    default 0.6
    pan_limits        [floats] default [-1.5708, 1.5708]
    tilt_limits       [floats] default [-0.7854, 0.7854]
    frame_id          str      default "camera_optical_frame"
"""
from __future__ import annotations

import math
import threading
from typing import List, Optional, Tuple

import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Point32, PointStamped, PolygonStamped
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import Bool, String
from std_msgs.msg import Header
from vision_msgs.msg import Detection2D


DEFAULT_MODEL = "yolov8n.pt"
QOS = 10


class YoloHalInterface:
    """Lazy wrapper around ultralytics so missing deps don't break py_compile."""
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        from ultralytics import YOLO
        self._model = YOLO(model_name)

    def predict(self, frame, conf: float = 0.35):
        # returns ultralytics results object (single image)
        return self._model.predict(source=frame, conf=conf, verbose=False)[0]

    def close(self) -> None: pass


class NullYoloHal:
    """Returns deterministic synthetic detections for tests / dry-runs."""
    def __init__(self) -> None:
        self.calls: int = 0

    def predict(self, frame, conf: float = 0.35):
        # Mark sure it'll never crash a downstream order:
        self.calls += 1
        class _BoxList(list):
            def __init__(self, payload): super().__init__(payload)
        return _BoxList([])
    def close(self) -> None: pass


class ObjectTrackerNode(Node):
    def __init__(self, hal: Optional[YoloHalInterface] = None) -> None:
        super().__init__("object_tracker")
        self._declare_params()
        hal_provided = hal is not None
        self._hal = hal or YoloHalInterface(
            str(self.get_parameter("yolo_model").value)
        )
        if not hal_provided:
            self.get_logger().info(
                f"YOLO loaded: {self.get_parameter('yolo_model').value}"
            )
        self._bridge = CvBridge()

        self._lock         = threading.Lock()
        self._target_class = str(self.get_parameter("target_class").value)
        self._tracking     = bool(self.get_parameter("tracking_enabled").value)
        self._visible      = False
        self._last_gaze    = (0.0, 0.0)

        self.create_subscription(Image,  "camera/image_raw",       self._on_image, QOS)
        self.create_subscription(String, "tracker/target_class",   self._on_class, QOS)
        self.create_subscription(Bool,   "tracker/tracking_enabled", self._on_en, QOS)

        self._gaze_pub  = self.create_publisher(PointStamped,    "tracked_target",          QOS)
        self._vis_pub   = self.create_publisher(Bool,           "tracked_target/visible",  QOS)
        self._pt_pub    = self.create_publisher(JointState,     "pan_tilt_cmd",             QOS)
        self._box_pub   = self.create_publisher(PolygonStamped, "tracked_target/bbox",      QOS)
        self._det_pub   = self.create_publisher(Detection2D,    "tracker/detection",        QOS)
        self._timer     = self.create_timer(0.05, self._publish_visibility)
        self.get_logger().info("object_tracker initialised")

    def _declare_params(self) -> None:
        self.declare_parameter("yolo_model", DEFAULT_MODEL)
        self.declare_parameter("target_class", "person")
        self.declare_parameter("tracking_enabled", True)
        self.declare_parameter("conf_threshold", 0.35)
        self.declare_parameter("pan_kp", 0.6)
        self.declare_parameter("tilt_kp", 0.6)
        self.declare_parameter("pan_min",  -1.5708)
        self.declare_parameter("pan_max",   1.5708)
        self.declare_parameter("tilt_min", -0.7854)
        self.declare_parameter("tilt_max",  0.7854)
        self.declare_parameter("frame_id", "camera_optical_frame")

    def _on_class(self, msg: String) -> None:
        with self._lock:
            self._target_class = msg.data
        self.get_logger().info(f"tracking class now: {msg.data}")

    def _on_en(self, msg: Bool) -> None:
        with self._lock:
            self._tracking = msg.data

    def _on_image(self, msg: Image) -> None:
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge failed: {exc}", throttle_duration_sec=2.0)
            return
        if not self._tracking:
            return
        self._process_frame(frame, msg.header)

    def _process_frame(self, frame, source_header) -> None:
        try:
            res = self._hal.predict(
                frame, float(self.get_parameter("conf_threshold").value)
            )
        except Exception as exc:
            self.get_logger().warn(f"yolo predict failed: {exc}", throttle_duration_sec=2.0)
            return

        height, width = frame.shape[:2]
        best = self._pick_best_detection(res, width, height)
        visible = best is not None
        with self._lock:
            self._visible = visible
        if not visible:
            return

        (cx_norm, cy_norm, bbox) = best  # cx_norm, cy_norm in [-1, 1]
        stamp = self.get_clock().now().to_msg()
        gaze = PointStamped()
        gaze.header = Header(stamp=stamp, frame_id=str(self.get_parameter("frame_id").value))
        gaze.point.x = float(cx_norm)
        gaze.point.y = float(cy_norm)
        gaze.point.z = 0.0
        self._gaze_pub.publish(gaze)

        # Convert gaze offset to a pan-tilt command (P controller)
        pan  = -float(self.get_parameter("pan_kp").value)  * cx_norm
        tilt =  float(self.get_parameter("tilt_kp").value) * cy_norm
        pan  = self._clamp(pan,  float(self.get_parameter("pan_min").value),
                                float(self.get_parameter("pan_max").value))
        tilt = self._clamp(tilt, float(self.get_parameter("tilt_min").value),
                                float(self.get_parameter("tilt_max").value))
        js = JointState()
        js.header = Header(stamp=stamp)
        js.name = ["pan", "tilt"]
        js.position = [pan, tilt]
        self._pt_pub.publish(js)

        # Publish bounding-box polygon
        poly = PolygonStamped()
        poly.header = gaze.header
        for (px, py) in bbox:
            poly.polygon.points.append(Point32(x=float(px), y=float(py), z=0.0))
        self._box_pub.publish(poly)

        with self._lock:
            self._last_gaze = (cx_norm, cy_norm)

    def _pick_best_detection(self, res, width: int, height: int):
        """Pick the detection closest to the image center for the target class.

        Returns (cx_norm, cy_norm, [(x1,y1)..(x4,y4)]) or None.
        """
        target = self._target_class.lower()
        best = None
        best_score = float("inf")
        try:
            boxes = res.boxes  # ultralytics boxes object
        except AttributeError:
            return None
        names = res.names if hasattr(res, "names") else {}
        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes, "xyxy") else []
        cls = boxes.cls.cpu().numpy().astype(int) if hasattr(boxes, "cls") else []
        for (x1, y1, x2, y2), c in zip(xyxy, cls):
            label = str(names.get(int(c), "")).lower()
            if target not in label:
                continue
            cx = 0.5 * (float(x1) + float(x2))
            cy = 0.5 * (float(y1) + float(y2))
            cx_norm =  2.0 * (cx / width)  - 1.0
            cy_norm = -2.0 * (cy / height) + 1.0
            score = abs(cx_norm) + abs(cy_norm)
            if score < best_score:
                best_score = score
                best = (
                    cx_norm,
                    cy_norm,
                    [(float(x1), float(y1)),
                     (float(x2), float(y1)),
                     (float(x2), float(y2)),
                     (float(x1), float(y2))],
                )
        return best

    def _publish_visibility(self) -> None:
        self._vis_pub.publish(Bool(data=self._visible))

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, v))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ObjectTrackerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._hal.close()
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
