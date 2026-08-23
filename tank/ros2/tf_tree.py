"""
tf_tree.py — Definitive TF2 Transform Tree for Tank
Standardized frames: base_link, laser, camera_optical, camera_link,
imu_link, wheels, tracks.
"""
import math
import time
import json
import logging

logger = logging.getLogger("tank.ros2.tf")


TANK_TF_TREE = {
    "base_link": {
        "parent": None,
        "children": ["laser_link", "camera_link", "imu_link", "left_track", "right_track"],
        "description": "Robot base frame — center of tracked chassis",
    },
    "laser_link": {
        "parent": "base_link",
        "translation": [0.0, 0.0, 0.15],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "description": "LDROBOT LD19 LiDAR — mounted top-center",
    },
    "camera_link": {
        "parent": "base_link",
        "translation": [0.15, 0.0, 0.20],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "description": "DFRobot AI Camera — front-mounted",
    },
    "camera_optical_frame": {
        "parent": "camera_link",
        "translation": [0.0, 0.0, 0.0],
        "rotation": [-0.5, 0.5, -0.5, 0.5],
        "description": "Camera optical frame — Z-forward, X-right, Y-down",
    },
    "imu_link": {
        "parent": "base_link",
        "translation": [0.0, 0.0, 0.05],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "description": "BNO055 IMU — center-mounted",
    },
    "left_track": {
        "parent": "base_link",
        "translation": [0.0, 0.12, 0.0],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "description": "Left track contact point",
    },
    "right_track": {
        "parent": "base_link",
        "translation": [0.0, -0.12, 0.0],
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "description": "Right track contact point",
    },
}


class TFTree:
    def __init__(self):
        self.frames = TANK_TF_TREE.copy()
        self.transforms = []
        self._start_time = time.time()

    def get_transform(self, parent, child):
        if child in self.frames and self.frames[child].get("parent") == parent:
            frame = self.frames[child]
            return {
                "parent": parent,
                "child": child,
                "translation": frame.get("translation", [0, 0, 0]),
                "rotation": frame.get("rotation", [0, 0, 0, 1]),
                "stamp": time.time() - self._start_time,
            }
        return None

    def get_all_transforms(self):
        transforms = []
        for frame_name, frame_data in self.frames.items():
            if frame_data.get("parent"):
                t = self.get_transform(frame_data["parent"], frame_name)
                if t:
                    transforms.append(t)
        return transforms

    def get_tree(self):
        tree = {}
        for name, data in self.frames.items():
            tree[name] = {
                "parent": data.get("parent"),
                "children": data.get("children", []),
                "translation": data.get("translation", [0, 0, 0]),
                "description": data.get("description", ""),
            }
        return tree

    def to_json(self):
        return json.dumps(self.get_tree(), indent=2)


def get_tank_tf_tree():
    return TFTree()
