"""
fusion.py - Sensor Fusion AI (Features 141-155)
Kalman filter, EKF, multi-sensor fusion, confidence, degradation
"""
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("tank.ai.fusion")


class KalmanFilter:
    """Standard Kalman filter for state estimation."""
    def __init__(self, dim_x=6, dim_z=3):
        self.dim_x = dim_x
        self.dim_z = dim_z
        self.x = np.zeros((dim_x, 1))
        self.P = np.eye(dim_x) * 10
        self.F = np.eye(dim_x)
        self.H = np.zeros((dim_z, dim_x))
        self.H[:dim_z, :dim_z] = np.eye(dim_z)
        self.Q = np.eye(dim_x) * 0.01
        self.R = np.eye(dim_z) * 1.0
        self._I = np.eye(dim_x)

    def predict(self, dt: float = 0.05):
        self.F[:3, 3:6] = np.eye(3) * dt
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z: np.ndarray):
        z = z.reshape(-1, 1)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (self._I - K @ self.H) @ self.P

    def get_state(self) -> np.ndarray:
        return self.x.copy()


class ExtendedKalmanFilter:
    """Extended Kalman filter for nonlinear systems."""
    def __init__(self):
        self.x = np.zeros((6, 1))
        self.P = np.eye(6) * 10
        self.Q = np.eye(6) * 0.01
        self.R = np.eye(3) * 1.0
        self._I = np.eye(6)

    def predict(self, v: float, omega: float, dt: float = 0.05):
        theta = self.x[2, 0]
        if abs(omega) > 0.001:
            self.x[0, 0] += v / omega * (math.sin(theta + omega * dt) - math.sin(theta))
            self.x[1, 0] += v / omega * (-math.cos(theta + omega * dt) + math.cos(theta))
        else:
            self.x[0, 0] += v * math.cos(theta) * dt
            self.x[1, 0] += v * math.sin(theta) * dt
        self.x[2, 0] += omega * dt
        self.P = self.P + self.Q

    def update(self, z: np.ndarray):
        H = np.zeros((3, 6))
        H[:3, :3] = np.eye(3)
        y = z.reshape(-1, 1) - H @ self.x
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (self._I - K @ H) @ self.P


class SensorFusion:
    """Features 141-155: Multi-sensor fusion, Kalman, confidence, degradation."""

    def __init__(self):
        self.kf = KalmanFilter()
        self.ekf = ExtendedKalmanFilter()
        self.sensor_states: Dict[str, Dict] = {
            "camera": {"healthy": True, "confidence": 1.0, "last_update": 0},
            "lidar": {"healthy": True, "confidence": 1.0, "last_update": 0},
            "imu": {"healthy": True, "confidence": 1.0, "last_update": 0},
            "odometry": {"healthy": True, "confidence": 1.0, "last_update": 0},
        }
        self.fused_pose = (0.0, 0.0, 0.0)
        self.confidence = 1.0
        self.degraded_mode = False
        self._disagreement_threshold = 2.0
        self.fusion_log: List[Dict] = []

    # 141-144. Camera+LiDAR, LiDAR+odo, IMU+odo, Camera+IMU fusion
    def fuse_camera_lidar(self, camera_pose, lidar_pose) -> Tuple[float, float, float]:
        wc = self.sensor_states["camera"]["confidence"]
        wl = self.sensor_states["lidar"]["confidence"]
        total = wc + wl
        if total == 0:
            return (0, 0, 0)
        x = (camera_pose[0] * wc + lidar_pose[0] * wl) / total
        y = (camera_pose[1] * wc + lidar_pose[1] * wl) / total
        t = (camera_pose[2] * wc + lidar_pose[2] * wl) / total
        return (x, y, t)

    def fuse_lidar_odometry(self, lidar_pose, odo_pose) -> Tuple[float, float, float]:
        wl = self.sensor_states["lidar"]["confidence"]
        wo = self.sensor_states["odometry"]["confidence"]
        total = wl + wo
        if total == 0:
            return (0, 0, 0)
        return tuple((lidar_pose[i] * wl + odo_pose[i] * wo) / total for i in range(3))

    def fuse_imu_odometry(self, imu_heading, odo_pose, imu_weight: float = 0.3) -> Tuple[float, float, float]:
        wo = self.sensor_states["odometry"]["confidence"]
        wi = self.sensor_states["imu"]["confidence"]
        w1 = wo * (1 - imu_weight)
        w2 = wi * imu_weight
        total = w1 + w2
        if total == 0:
            return odo_pose
        return (odo_pose[0], odo_pose[1], (odo_pose[2] * w1 + imu_heading * w2) / total)

    def fuse_camera_imu(self, camera_pose, imu_rotation) -> Tuple[float, float, float]:
        wc = self.sensor_states["camera"]["confidence"]
        wi = self.sensor_states["imu"]["confidence"]
        total = wc + wi
        if total == 0:
            return (0, 0, 0)
        return (camera_pose[0], camera_pose[1],
                (camera_pose[2] * wc + imu_rotation * wi) / total)

    # 145. Timestamp alignment
    def align_timestamps(self, sensor_data: Dict[str, float]) -> Dict[str, float]:
        base_time = max(sensor_data.values()) if sensor_data else time.time()
        aligned = {}
        for sensor, ts in sensor_data.items():
            dt = base_time - ts
            aligned[sensor] = dt
        return aligned

    # 146-148. Confidence weighting, disagreement, failure detection
    def update_sensor_confidence(self, sensor: str, confidence: float):
        if sensor in self.sensor_states:
            self.sensor_states[sensor]["confidence"] = confidence
            self.sensor_states[sensor]["last_update"] = time.time()

    def detect_disagreement(self, readings: Dict[str, float]) -> Dict[str, Any]:
        if len(readings) < 2:
            return {"disagreement": False}
        values = list(readings.values())
        mean = np.mean(values)
        std = np.std(values)
        disagree = std > self._disagreement_threshold
        return {"disagreement": disagree, "std": round(std, 3), "values": readings}

    def detect_sensor_failure(self, sensor: str, timeout: float = 5.0) -> bool:
        state = self.sensor_states.get(sensor)
        if state and time.time() - state["last_update"] > timeout:
            state["healthy"] = False
            state["confidence"] = 0.0
            logger.warning(f"Sensor {sensor} failure detected (timeout)")
            return True
        return False

    # 149-150. Degradation & recovery
    def enter_degraded_mode(self, failed_sensors: List[str]):
        self.degraded_mode = True
        for s in failed_sensors:
            if s in self.sensor_states:
                self.sensor_states[s]["healthy"] = False
                self.sensor_states[s]["confidence"] = 0.0
        self.confidence = sum(s["confidence"] for s in self.sensor_states.values()) / len(self.sensor_states)
        logger.warning(f"Degraded mode: {failed_sensors} failed, confidence={self.confidence:.2f}")

    def recover_sensor(self, sensor: str):
        if sensor in self.sensor_states:
            self.sensor_states[sensor]["healthy"] = True
            self.sensor_states[sensor]["confidence"] = 1.0
            self.sensor_states[sensor]["last_update"] = time.time()
            active = sum(1 for s in self.sensor_states.values() if s["healthy"])
            if active >= len(self.sensor_states) * 0.75:
                self.degraded_mode = False
                logger.info(f"Sensor {sensor} recovered, full mode restored")

    # 151-154. Bayesian fusion, KF, EKF, confidence score
    def fuse_all(self, camera_pos, lidar_pos, imu_h, odo_pos) -> Dict[str, Any]:
        cam_lidar = self.fuse_camera_lidar(camera_pos, lidar_pos)
        lidar_odo = self.fuse_lidar_odometry(lidar_pos, odo_pos)
        imu_odo = self.fuse_imu_odometry(imu_h, odo_pos)
        final = tuple(np.mean([cam_lidar, lidar_odo, imu_odo], axis=0))
        self.fused_pose = final
        self.confidence = sum(s["confidence"] for s in self.sensor_states.values()) / len(self.sensor_states)
        return {"fused_pose": [round(v, 4) for v in final], "confidence": round(self.confidence, 3),
                "degraded": self.degraded_mode}

    def update_kalman(self, measurement: np.ndarray, dt: float = 0.05):
        self.kf.predict(dt)
        self.kf.update(measurement)
        return self.kf.get_state().flatten().tolist()

    def update_ekf(self, velocity: float, omega: float, measurement: np.ndarray, dt: float = 0.05):
        self.ekf.predict(velocity, omega, dt)
        self.ekf.update(measurement)
        state = self.ekf.x.flatten()
        return {"x": round(state[0], 4), "y": round(state[1], 4), "theta": round(state[2], 4)}

    def get_perception_state(self) -> Dict[str, Any]:
        return {
            "fused_pose": list(self.fused_pose),
            "confidence": round(self.confidence, 3),
            "degraded_mode": self.degraded_mode,
            "sensors": {k: {"healthy": v["healthy"], "confidence": v["confidence"]}
                        for k, v in self.sensor_states.items()},
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "degraded_mode": self.degraded_mode,
            "confidence": round(self.confidence, 3),
            "sensors": {k: v["healthy"] for k, v in self.sensor_states.items()},
        }
