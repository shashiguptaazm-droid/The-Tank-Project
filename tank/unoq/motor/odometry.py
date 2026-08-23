"""
odometry.py - Advanced Odometry System
Features 41-50: Velocity estimation, noise filtering, calibration, confidence
"""
import time
import math
import threading
from typing import Dict, Any, Optional


class OdometryFilter:
    """Low-pass filter for encoder noise."""
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.value = 0.0

    def update(self, raw: float) -> float:
        self.value = self.alpha * raw + (1 - self.alpha) * self.value
        return self.value


class AdvancedOdometry:
    """Full odometry with velocity, calibration, confidence scoring."""

    def __init__(self, wheel_radius=0.033, track_width=0.18, encoder_ppr=390):
        self.wheel_radius = wheel_radius
        self.track_width = track_width
        self.encoder_ppr = encoder_ppr
        self.filter_l = OdometryFilter()
        self.filter_r = OdometryFilter()
        self.left_encoder = 0
        self.right_encoder = 0
        self.left_encoder_prev = 0
        self.right_encoder_prev = 0
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.left_velocity = 0.0
        self.right_velocity = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.total_distance = 0.0
        self.dt = 0.05
        self.last_update = time.time()
        self.heading_drift_rate = 0.0
        self.confidence = 1.0
        self.encoder_dropouts_left = 0
        self.encoder_dropouts_right = 0
        self.calibration_samples = []
        self._lock = threading.Lock()

    def update(self, left_enc: int, right_enc: int):
        with self._lock:
            now = time.time()
            dt = now - self.last_update
            if dt <= 0:
                return
            self.last_update = now
            d_left = left_enc - self.left_encoder_prev
            d_right = right_enc - self.right_encoder_prev
            if abs(d_left) == 0 and abs(self.left_encoder - self.left_encoder_prev) == 0:
                self.encoder_dropouts_left += 1
            if abs(d_right) == 0 and abs(self.right_encoder - self.right_encoder_prev) == 0:
                self.encoder_dropouts_right += 1
            self.left_encoder_prev = self.left_encoder
            self.right_encoder_prev = self.right_encoder
            self.left_encoder = left_enc
            self.right_encoder = right_enc
            raw_vl = (d_left / self.encoder_ppr) * 2 * math.pi * self.wheel_radius / dt
            raw_vr = (d_right / self.encoder_ppr) * 2 * math.pi * self.wheel_radius / dt
            self.left_velocity = self.filter_l.update(raw_vl)
            self.right_velocity = self.filter_r.update(raw_vr)
            self.linear_velocity = (self.left_velocity + self.right_velocity) / 2.0
            self.angular_velocity = (self.right_velocity - self.left_velocity) / self.track_width
            self.theta += self.angular_velocity * dt
            self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
            self.x += self.linear_velocity * math.cos(self.theta) * dt
            self.y += self.linear_velocity * math.sin(self.theta) * dt
            self.total_distance += abs(self.linear_velocity) * dt
            self._update_confidence(dt)

    def _update_confidence(self, dt):
        dropout_penalty = (self.encoder_dropouts_left + self.encoder_dropouts_right) * 0.01
        age_penalty = min(0.1, dt * 0.001)
        self.confidence = max(0.0, 1.0 - dropout_penalty - age_penalty)

    def calibrate_distance(self, actual_distance: float, encoder_ticks: int):
        expected = (encoder_ticks / self.encoder_ppr) * 2 * math.pi * self.wheel_radius
        if expected > 0:
            scale = actual_distance / expected
            self.calibration_samples.append(scale)
            if len(self.calibration_samples) >= 5:
                avg_scale = sum(self.calibration_samples) / len(self.calibration_samples)
                self.wheel_radius *= avg_scale
                self.calibration_samples.clear()
                return {"calibrated": True, "new_radius": self.wheel_radius}
        return {"calibrated": False, "samples": len(self.calibration_samples)}

    def calibrate_heading(self, actual_heading: float):
        error = actual_heading - self.theta
        self.heading_drift_rate = error
        self.theta = actual_heading
        return {"heading_corrected": True, "correction": error}

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.total_distance = 0.0
        self.confidence = 1.0
        self.encoder_dropouts_left = 0
        self.encoder_dropouts_right = 0

    def get_pose(self) -> Dict[str, float]:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "theta": round(self.theta, 4)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "pose": self.get_pose(),
            "linear_velocity": round(self.linear_velocity, 3),
            "angular_velocity": round(self.angular_velocity, 3),
            "left_velocity": round(self.left_velocity, 3),
            "right_velocity": round(self.right_velocity, 3),
            "total_distance": round(self.total_distance, 2),
            "confidence": round(self.confidence, 3),
            "encoder_dropouts_l": self.encoder_dropouts_left,
            "encoder_dropouts_r": self.encoder_dropouts_right,
            "heading_drift": self.heading_drift_rate,
            "wheel_radius": self.wheel_radius,
            "track_width": self.track_width,
        }
