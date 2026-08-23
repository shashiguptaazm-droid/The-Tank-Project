"""
servo_intel.py - Servo Intelligence System
Features 71-80: Calibration, motion profiles, collision protection, poses
"""
import time
import math
import threading
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("tank.unoq.servo")


class ServoChannel:
    def __init__(self, channel: int, name: str, min_angle: int = 0, max_angle: int = 180):
        self.channel = channel
        self.name = name
        self.current_angle = 90
        self.target_angle = 90
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.calibrated_min = 0
        self.calibrated_max = 180
        self.calibrated_center = 90
        self.speed_limit = 90
        self.accel_limit = 120
        self.timeout_ms = 5000
        self.last_command_time = 0.0
        self.enabled = True


class ServoIntelligence:
    """PCA9685 servo management with calibration, motion, collision protection."""

    def __init__(self, num_channels: int = 16):
        self.num_channels = num_channels
        self.servos = {}
        self.poses = {}
        self.collision_pairs = []
        self._lock = threading.Lock()
        self.on_move: Optional[callable] = None

    def add_servo(self, channel: int, name: str, **kwargs):
        self.servos[channel] = ServoChannel(channel, name, **kwargs)

    def move(self, channel: int, angle: int, speed: int = 90) -> bool:
        with self._lock:
            if channel not in self.servos:
                return False
            servo = self.servos[channel]
            if not servo.enabled:
                return False
            angle = max(servo.min_angle, min(servo.max_angle, angle))
            angle = max(servo.calibrated_min, min(servo.calibrated_max, angle))
            if self._check_collision(channel, angle):
                logger.warning(f"Collision detected: channel {channel} -> {angle}°")
                return False
            servo.target_angle = angle
            servo.last_command_time = time.time()
            if self.on_move:
                self.on_move({"channel": channel, "angle": angle, "speed": speed})
            return True

    def _check_collision(self, channel: int, angle: int) -> bool:
        for pair in self.collision_pairs:
            if channel in pair:
                other_ch = pair[0] if pair[1] == channel else pair[1]
                if other_ch in self.servos:
                    other = self.servos[other_ch]
                    if channel < other_ch and angle > 150 and other.current_angle > 150:
                        return True
                    if channel > other_ch and angle < 30 and other.current_angle < 30:
                        return True
        return False

    def smooth_move(self, channel: int, target: int, duration_s: float = 1.0):
        if channel not in self.servos:
            return
        servo = self.servos[channel]
        start = servo.current_angle
        steps = int(duration_s * 20)
        for i in range(1, steps + 1):
            t = i / steps
            ease = 0.5 * (1 - math.cos(math.pi * t))
            angle = int(start + (target - start) * ease)
            self.move(channel, angle)
            time.sleep(duration_s / steps)

    def save_pose(self, name: str):
        self.poses[name] = {ch: s.current_angle for ch, s in self.servos.items()}
        logger.info(f"Pose saved: {name}")

    def load_pose(self, name: str, duration: float = 1.0):
        if name not in self.poses:
            return False
        pose = self.poses[name]
        threads = []
        for ch, angle in pose.items():
            t = threading.Thread(target=self.smooth_move, args=(ch, angle, duration))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return True

    def disable_all(self):
        for s in self.servos.values():
            s.enabled = False

    def enable_all(self):
        for s in self.servos.values():
            s.enabled = True

    def check_timeouts(self, timeout_ms: int = 5000):
        now = time.time()
        for ch, servo in self.servos.items():
            if servo.last_command_time > 0:
                if (now - servo.last_command_time) * 1000 > timeout_ms:
                    servo.enabled = False
                    logger.warning(f"Servo {ch} disabled: timeout")

    def add_collision_pair(self, ch1: int, ch2: int):
        self.collision_pairs.append((ch1, ch2))

    def get_status(self) -> Dict[str, Any]:
        return {
            "servos": {
                ch: {"name": s.name, "angle": s.current_angle, "target": s.target_angle, "enabled": s.enabled}
                for ch, s in self.servos.items()
            },
            "poses": list(self.poses.keys()),
            "collision_pairs": len(self.collision_pairs),
        }
