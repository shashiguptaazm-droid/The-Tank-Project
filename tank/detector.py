"""
apriltag_detector.py - AprilTag Detection for Tank
Detects AprilTags from USB camera for docking, navigation landmarks, and pose estimation.
Uses OpenCV ArUco AprilTag detector (no extra deps needed on Jetson).
"""
import cv2
import cv2.aruco as aruco
import numpy as np
import time
import logging
import json
import math
import urllib.request
import struct

logger = logging.getLogger("tank.apriltag")

# Tag definitions for the Tank project
TAG_MAP = {
    0: {"name": "DOCK_ENTER", "desc": "Charging dock approach marker"},
    1: {"name": "DOCK_ALIGN", "desc": "Charging dock alignment marker"},
    2: {"name": "DOCK_LOCK", "desc": "Charging dock lock-in marker"},
    3: {"name": "NAV_HOME", "desc": "Home base landmark"},
    4: {"name": "NAV_WAYPOINT_A", "desc": "Waypoint A"},
    5: {"name": "NAV_WAYPOINT_B", "desc": "Waypoint B"},
    6: {"name": "NAV_WAYPOINT_C", "desc": "Waypoint C"},
    7: {"name": "ZONE_START", "desc": "Start zone marker"},
    8: {"name": "ZONE_END", "desc": "End zone marker"},
    9: {"name": "OBSTACLE_WARN", "desc": "Obstacle warning marker"},
    10: {"name": "PERSON-zone", "desc": "Person detection zone"},
    11: {"name": "DOCK_RETURN", "desc": "Return to dock marker"},
    12: {"name": "NAV_HAZARD", "desc": "Hazard zone marker"},
    13: {"name": "NAV_CHARGING", "desc": "Charging station zone"},
    14: {"name": "WAYPOINT_D", "desc": "Waypoint D"},
    15: {"name": "WAYPOINT_E", "desc": "Waypoint E"},
}

# Camera calibration for pose estimation (update after calibration)
CAMERA_MATRIX = None
DIST_COEFFS = None

# AprilTag physical size in meters (distance between tag border lines)
TAG_SIZE_METERS = 0.06  # 6cm tags


class AprilTagDetector:
    """Detect and track AprilTags from camera stream"""

    def __init__(self, camera_url=None, tag_size=TAG_SIZE_METERS):
        self.camera_url = camera_url
        self.tag_size = tag_size
        self.detector = None
        self.camera_matrix = CAMERA_MATRIX
        self.dist_coeffs = DIST_COEFFS
        self.detected_tags = []
        self.tag_history = {}
        self.frame_count = 0
        self._init_detector()

    def _init_detector(self):
        """Initialize the ArUco AprilTag detector"""
        try:
            self.detector = aruco.ArucoDetector(
                aruco.getPredefinedDictionary(aruco.DICT_APRILTAG_36h11),
                aruco.DetectorParameters()
            )
            logger.info("AprilTag detector initialized (DICT_APRILTAG_36h11)")
        except Exception as e:
            logger.error(f"Failed to init detector: {e}")
            # Fallback to older API
            try:
                self.detector = aruco.detectMarkers
                logger.info("Using legacy ArUco API")
            except:
                logger.error("No ArUco detector available")

    def calibrate(self, camera_matrix, dist_coeffs):
        """Set camera calibration for accurate pose estimation"""
        self.camera_matrix = np.array(camera_matrix)
        self.dist_coeffs = np.array(dist_coeffs) if dist_coeffs else None
        logger.info("Camera calibration loaded for pose estimation")

    def detect_from_frame(self, frame):
        """Detect AprilTags in a given frame"""
        if frame is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        corners, ids, rejected = self.detector.detectMarkers(gray)

        self.detected_tags = []
        if ids is not None and len(ids) > 0:
            for i, tag_id in enumerate(ids.flatten()):
                tag_corners = corners[i][0]
                tag_info = {
                    "id": int(tag_id),
                    "name": TAG_MAP.get(tag_id, {}).get("name", f"UNKNOWN_{tag_id}"),
                    "desc": TAG_MAP.get(tag_id, {}).get("desc", "Unknown tag"),
                    "corners": tag_corners.tolist(),
                    "center": self._get_center(tag_corners),
                    "timestamp": time.time(),
                }

                # Estimate pose if camera is calibrated
                if self.camera_matrix is not None:
                    pose = self._estimate_pose(tag_corners)
                    tag_info.update(pose)

                self.detected_tags.append(tag_info)

                # Track tag history
                self._update_history(tag_id, tag_info)

        self.frame_count += 1
        return self.detected_tags

    def detect_from_usb_camera(self, port="/dev/ttyACM0", baud=921600):
        """Capture frame from USB camera and detect tags"""
        import serial
        try:
            s = serial.Serial(port, baud, timeout=5)
            time.sleep(0.3)
            s.read(s.in_waiting)
            s.write(b"SNAP\n")

            header = b""
            deadline = time.time() + 5
            while time.time() < deadline:
                c = s.read(1)
                if c:
                    header += c
                    if c == b"\n":
                        break

            h = header.decode("utf-8", errors="replace").strip()
            if not h.startswith("FRAME:"):
                s.close()
                return []

            parts = h.split(":")
            expected = int(parts[3])

            jpeg = b""
            dl = time.time() + 10
            while len(jpeg) < expected and time.time() < dl:
                chunk = s.read(min(expected - len(jpeg), 16384))
                if chunk:
                    jpeg += chunk
                    dl = time.time() + 2
            s.read(1)
            s.close()

            # Decode JPEG
            buf = np.frombuffer(jpeg, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is not None:
                return self.detect_from_frame(frame)
        except Exception as e:
            logger.error(f"USB camera read failed: {e}")
        return []

    def detect_from_url(self, url=None):
        """Capture frame from HTTP URL and detect tags"""
        target = url or self.camera_url
        if not target:
            return []
        try:
            req = urllib.request.urlopen(target, timeout=3)
            buf = np.frombuffer(req.read(), dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is not None:
                return self.detect_from_frame(frame)
        except Exception as e:
            logger.error(f"URL capture failed: {e}")
        return []

    def _get_center(self, corners):
        """Get center point of tag"""
        x = float(np.mean(corners[:, 0]))
        y = float(np.mean(corners[:, 1]))
        return {"x": round(x, 1), "y": round(y, 1)}

    def _estimate_pose(self, corners):
        """Estimate 3D pose of tag relative to camera"""
        if self.camera_matrix is None:
            return {}

        obj_points = np.array([
            [-self.tag_size/2,  self.tag_size/2, 0],
            [ self.tag_size/2,  self.tag_size/2, 0],
            [ self.tag_size/2, -self.tag_size/2, 0],
            [-self.tag_size/2, -self.tag_size/2, 0],
        ], dtype=np.float32)

        img_points = corners.astype(np.float32)

        success, rvec, tvec = cv2.solvePnP(
            obj_points, img_points, self.camera_matrix, self.dist_coeffs
        )

        if success:
            # Convert rotation vector to euler angles
            rmat, _ = cv2.Rodrigues(rvec)
            sy = math.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
            if sy > 1e-6:
                roll = math.atan2(rmat[2, 1], rmat[2, 2])
                pitch = math.atan2(-rmat[2, 0], sy)
                yaw = math.atan2(rmat[1, 0], rmat[0, 0])
            else:
                roll = math.atan2(-rmat[1, 2], rmat[1, 1])
                pitch = math.atan2(-rmat[2, 0], sy)
                yaw = 0

            distance = float(np.linalg.norm(tvec))
            return {
                "pose": {
                    "x": round(float(tvec[0][0]), 3),
                    "y": round(float(tvec[1][0]), 3),
                    "z": round(float(tvec[2][0]), 3),
                    "distance_m": round(distance, 3),
                    "roll_deg": round(math.degrees(roll), 1),
                    "pitch_deg": round(math.degrees(pitch), 1),
                    "yaw_deg": round(math.degrees(yaw), 1),
                }
            }
        return {}

    def _update_history(self, tag_id, info):
        """Track tag detections over time"""
        if tag_id not in self.tag_history:
            self.tag_history[tag_id] = {
                "first_seen": time.time(),
                "detections": 0,
                "positions": [],
            }
        self.tag_history[tag_id]["detections"] += 1
        self.tag_history[tag_id]["last_seen"] = time.time()
        self.tag_history[tag_id]["positions"].append(info["center"])
        # Keep last 30 positions
        if len(self.tag_history[tag_id]["positions"]) > 30:
            self.tag_history[tag_id]["positions"] = self.tag_history[tag_id]["positions"][-30:]

    def get_dock_tags(self):
        """Get charging dock tags specifically"""
        return [t for t in self.detected_tags if t["id"] in [0, 1, 2, 11, 13]]

    def get_nav_tags(self):
        """Get navigation landmark tags"""
        return [t for t in self.detected_tags if t["id"] in [3, 4, 5, 6, 14, 15]]

    def is_dock_aligned(self):
        """Check if dock alignment tag is centered in frame"""
        dock_align = [t for t in self.detected_tags if t["id"] == 1]
        if dock_align:
            center = dock_align[0]["center"]
            # Tag should be near center of frame (assume VGA 640x480)
            x_err = abs(center["x"] - 320)
            y_err = abs(center["y"] - 240)
            return x_err < 80 and y_err < 80
        return False

    def get_dock_distance(self):
        """Get distance to dock based on tag size"""
        dock_tags = self.get_dock_tags()
        if dock_tags and "pose" in dock_tags[0]:
            return dock_tags[0]["pose"]["distance_m"]
        # Estimate distance from tag pixel size
        if dock_tags:
            corners = np.array(dock_tags[0]["corners"])
            width_px = np.linalg.norm(corners[0] - corners[1])
            if width_px > 1:
                distance = (self.tag_size * 320) / width_px  # rough estimate
                return round(distance, 2)
        return -1

    def draw_tags(self, frame):
        """Draw detected tags on frame"""
        for tag in self.detected_tags:
            corners = np.array(tag["corners"], dtype=np.int32)
            cv2.polylines(frame, [corners], True, (0, 255, 0), 2)

            cx, cy = int(tag["center"]["x"]), int(tag["center"]["y"])
            label = f"ID:{tag['id']} {tag['name']}"
            cv2.putText(frame, label, (cx - 40, cy - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            if "pose" in tag:
                dist = tag["pose"].get("distance_m", 0)
                cv2.putText(frame, f"{dist:.2f}m", (cx - 20, cy + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        return frame

    def get_status(self):
        """Get detector status"""
        return {
            "detector": "AprilTag 36h11",
            "tag_size_m": self.tag_size,
            "frames_processed": self.frame_count,
            "tags_detected": len(self.detected_tags),
            "unique_tags_seen": len(self.tag_history),
            "calibrated": self.camera_matrix is not None,
            "active_tags": [
                {"id": t["id"], "name": t["name"], "center": t["center"]}
                for t in self.detected_tags
            ],
        }


# === Standalone test ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = AprilTagDetector()

    # Test with USB camera
    tags = detector.detect_from_usb_camera()
    print(f"Detected {len(tags)} tags:")
    for t in tags:
        print(f"  ID:{t['id']} {t['name']} center={t['center']}")
        if "pose" in t:
            print(f"    Distance: {t['pose']['distance_m']}m")

    print(f"\nStatus: {json.dumps(detector.get_status(), indent=2)}")
