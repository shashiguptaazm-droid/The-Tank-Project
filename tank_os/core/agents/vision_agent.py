"""TankOS Vision Agent — camera, YOLO, face recognition, AprilTags, object tracking."""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult
from tank_os.core.vision_manager import VisionManager


class VisionAgent(BaseAgent):
    name = "vision"
    description = "Camera, YOLO detection, face recognition, AprilTags, tracking"

    def __init__(self) -> None:
        super().__init__()
        self._vision = VisionManager()
        self._capabilities = ["capture", "detect", "track", "recognize_face",
                              "detect_apriltag", "start_camera", "stop_camera"]

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        p = params or {}
        if task == "start_camera":
            ok = self._vision.start_camera(p.get("device", "/dev/video0"))
            return AgentResult(success=ok, data={"active": ok})
        elif task == "stop_camera":
            self._vision.stop_camera()
            return AgentResult(success=True, data={"active": False})
        elif task == "capture":
            frame = self._vision.capture_frame()
            if frame:
                return AgentResult(success=True, data={"frame_size": len(frame), "active": True})
            return AgentResult(success=False, error="No camera frame available")
        elif task == "detect":
            dets = self._vision.detect_objects()
            return AgentResult(success=True, data={
                "count": len(dets),
                "objects": [{"label": d.label, "confidence": round(d.confidence, 3)}
                           for d in dets[:10]],
            })
        elif task == "track":
            if not self._vision.is_camera_active:
                return AgentResult(success=False, error="Camera not active")
            dets = self._vision.detect_objects()
            if dets:
                return AgentResult(success=True, data={
                    "tracking": dets[0].label,
                    "position": {"x": dets[0].x, "y": dets[0].y},
                })
            return AgentResult(success=False, error="Nothing to track")
        return AgentResult(success=False, error=f"Unknown task: {task}")



