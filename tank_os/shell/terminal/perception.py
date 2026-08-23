#!/usr/bin/env python3
"""Auto Perception Pipeline — motion + LiDAR → AI → SMS.

Continuously monitors:
1. Camera for motion (frame differencing)
2. LiDAR for human presence (distance < threshold)

When triggered:
1. Captures camera frame + runs YOLO
2. Reads LiDAR distance
3. Sends both to LLM for interpretation
4. Sends AI summary via SMS to user's phone
"""

from __future__ import annotations

import os
import sys
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# Add project to path
_PROJECT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT))


@dataclass
class PerceptionEvent:
    timestamp: float
    motion_score: float
    lidar_distance: float
    yolo_detections: str
    ai_interpretation: str
    sms_sent: bool
    sms_error: Optional[str] = None


class PerceptionPipeline:
    """Monitors camera + LiDAR, triggers AI + SMS on detection."""

    def __init__(self, *, motion_threshold: float = 0.02,
                 lidar_threshold_mm: int = 2000,
                 cooldown_s: float = 30,
                 phone: str = "+917860245819",
                 remote_camera_url: Optional[str] = None):
        self.motion_threshold = motion_threshold
        self.lidar_threshold_mm = lidar_threshold_mm
        self.cooldown_s = cooldown_s
        self.phone = phone
        self.remote_camera_url = remote_camera_url  # e.g. "http://192.168.31.72:8080/snapshot.jpg"

        self._prev_frame: Optional[np.ndarray] = None
        self._last_trigger = 0.0
        self._running = False
        self._events: list = []
        self._callbacks: list = []

    def on_event(self, callback):
        """Register a callback for perception events."""
        self._callbacks.append(callback)

    def start(self):
        """Start the perception loop in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self._check()
            except Exception as e:
                pass
            time.sleep(0.5)

    def _check(self):
        now = time.time()
        if now - self._last_trigger < self.cooldown_s:
            return

        motion = self._detect_motion()
        lidar_dist = self._read_lidar_distance()

        # Trigger if motion OR close object
        motion_triggered = motion > self.motion_threshold
        lidar_triggered = lidar_dist > 0 and lidar_dist < self.lidar_threshold_mm

        if motion_triggered or lidar_triggered:
            self._last_trigger = now
            event = self._handle_trigger(motion, lidar_dist)
            self._events.append(event)
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception:
                    pass

    def _detect_motion(self) -> float:
        """Detect motion via frame differencing. Returns 0-1 score.

        Tries in order:
        1. Remote camera URL (e.g. UNO Q ESP32 CAM via HTTP)
        2. DFRobot USB camera (agent_chat._capture_frame)
        3. Direct cv2 camera
        """
        try:
            frame_path = self._capture_from_any_source()
            if not frame_path:
                return 0.0

            frame = cv2.imread(frame_path)
            if frame is None:
                return 0.0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self._prev_frame is None:
                self._prev_frame = gray
                return 0.0

            diff = cv2.absdiff(self._prev_frame, gray)
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            score = np.sum(thresh) / (thresh.shape[0] * thresh.shape[1] * 255)
            self._prev_frame = gray
            return float(score)
        except Exception:
            return 0.0

    def _read_lidar_distance(self) -> float:
        """Read nearest object distance from LiDAR in mm. Returns 0 if no data."""
        try:
            from tank_os.shell.terminal.lidar_reader import read_lidar
            scan = read_lidar(timeout_s=1.0)
            if scan and scan.min_distance > 0:
                return float(scan.min_distance)
        except Exception:
            pass
        return 0.0

    def _capture_from_any_source(self) -> Optional[str]:
        """Try all available camera sources. Returns path to saved JPEG."""
        frame_dir = Path("/tmp/perception_frames")
        frame_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(frame_dir / "latest.jpg")

        # 1. Remote camera URL (UNO Q ESP32 CAM, etc.)
        if self.remote_camera_url:
            try:
                import httpx
                resp = httpx.get(self.remote_camera_url, timeout=5)
                if resp.status_code == 200 and len(resp.content) > 500:
                    Path(out_path).write_bytes(resp.content)
                    return out_path
            except Exception:
                pass

        # 2. DFRobot USB camera (Jetson local)
        try:
            from tank_os.shell.terminal.agent_chat import _capture_frame
            frame_path = _capture_frame()
            if frame_path:
                return frame_path
        except Exception:
            pass

        # 3. Direct cv2 webcam
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    cv2.imwrite(out_path, frame)
                    return out_path
        except Exception:
            pass

        return None

    def _handle_trigger(self, motion: float, lidar_dist: float) -> PerceptionEvent:
        """Full pipeline: capture → YOLO → LLM → SMS."""
        event = PerceptionEvent(
            timestamp=time.time(),
            motion_score=motion,
            lidar_distance=lidar_dist,
            yolo_detections="",
            ai_interpretation="",
            sms_sent=False,
        )

        # 1. Capture frame + YOLO (from any available source)
        try:
            from tank_os.shell.terminal.agent_chat import _run_yolo
            frame = self._capture_from_any_source()
            if frame:
                event.yolo_detections = _run_yolo(frame)
        except Exception as e:
            event.yolo_detections = f"Camera error: {e}"

        # 2. LiDAR detail
        lidar_info = ""
        if lidar_dist > 0:
            lidar_info = f"LiDAR: object at {lidar_dist/1000:.2f}m"
        else:
            lidar_info = "LiDAR: no close objects"

        # 3. AI interpretation
        prompt = (
            f"Security event detected at {time.strftime('%H:%M:%S')}\n\n"
            f"Motion level: {motion:.3f} (threshold: {self.motion_threshold})\n"
            f"{lidar_info}\n"
            f"YOLO detections: {event.yolo_detections}\n\n"
            f"Interpret this in 1-2 sentences. What is happening? Is it a person? "
            f"What are they doing? Should the owner be alerted?"
        )

        try:
            from tank_os.shell.terminal.agent_chat import _rotate_chat, _SYSTEM_PROMPT
            msgs = [
                {"role": "system", "content": "You are a security AI. Interpret sensor data concisely in 1-2 sentences. Be specific about what you detect. Reply with plain text only, no JSON."},
                {"role": "user", "content": prompt},
            ]
            event.ai_interpretation = _rotate_chat(msgs)
        except Exception as e:
            event.ai_interpretation = f"AI error: {e}"

        # 4. Send SMS — full LLM interpretation to owner
        sms_text = (
            f"TankOS Alert [{time.strftime('%H:%M:%S')}]\n\n"
            f"AI Interpretation:\n{event.ai_interpretation}\n\n"
            f"Sensor Data:\n"
            f"Motion: {motion:.3f}\n"
            f"LiDAR: {lidar_dist/1000:.2f}m\n"
            f"YOLO: {event.yolo_detections}"
        )

        try:
            from tank_os.shell.terminal.sms_sender import send_sms
            result = send_sms(sms_text, phone=self.phone)
            event.sms_sent = result.get("success", False)
            event.sms_error = result.get("error")
        except Exception as e:
            event.sms_error = str(e)

        return event

    @property
    def events(self):
        return list(self._events)

    @property
    def is_running(self):
        return self._running
