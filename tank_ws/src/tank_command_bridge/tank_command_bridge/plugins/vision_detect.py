"""``voice.detect_persons`` + ``voice.detect_faces`` plugins.

Two pragmatic voice commands the user can issue:

* "Hey Tank, who's in the room?" → :class:`VoiceDetectPersonsPlugin`
* "Hey Tank, do you see any faces?" → :class:`VoiceDetectFacesPlugin`

Both are **read**-class (no state mutation, no publishing to ROS).
They run YOLO (person class only) or OpenCV Haar cascades on the
*latest* camera frame and return a normalised JSON response that
the LLM can speak aloud with a TTS-friendly line.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import RobotPlugin
from ._vision_helpers import (
    COCO_NAMES,
    FrameSource,
    VisionBox,
    detect_faces,
    _RUN_YOLO,
)


def _tts_count(label: str, boxes: List[Dict[str, Any]]) -> str:
    n = len(boxes)
    if n == 0:
        return f"I don't see any {label}s in the room right now."
    if n == 1:
        return f"I see one {label}."
    return f"I see {n} {label}s."


class VoiceDetectPersonsPlugin(RobotPlugin):
    """YOLO-based person detection on the latest camera frame."""

    NAME = "voice.detect_persons"
    DESCRIPTION = (
        "Run Ultralytics YOLO on the latest camera frame, filter to "
        "the COCO ``person`` class only, and return bounding boxes "
        "with confidence. Returns a TTS-friendly summary plus the raw "
        "box geometry so the LLM can answer follow-ups like \"the one "
        "on the right side\"."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "frame_path":  {"type": "string",
                              "description":
                                  "Optional filesystem path to a JPEG/PNG "
                                  "frame. If omitted, falls back to "
                                  "``frame_b64`` then to the bridge frame "
                                  "snapshot.", "default": ""},
            "frame_b64":   {"type": "string",
                              "description":
                                  "Optional base64-encoded JPEG/PNG frame.",
                              "default": ""},
            "conf":        {"type": "number",
                              "description":
                                  "Confidence threshold (0-1). Default 0.40.",
                              "minimum": 0.05, "maximum": 0.95, "default": 0.40},
            "max_px":      {"type": "integer",
                              "description":
                                  "Longest-edge cap for the snapshot when "
                                  "the bridge has to fetch a frame.",
                              "minimum": 160, "maximum": 1920, "default": 640},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "count":  {"type": "integer"},
            "boxes":  {"type": "array", "items": {"type": "object"}},
            "source": {"type": "string",
                        "description":
                            "\"yolo\" or \"degraded_yolo_unavailable\" "
                            "so the LLM can say \"I couldn't see — YOLO "
                            "isn't loaded\"."},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "vision", "ai"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        source = FrameSource(
            ctx=ctx,
            frame_path=(params.get("frame_path") or "").strip() or None,
            frame_b64=(params.get("frame_b64") or "").strip() or None,
        )
        bytes_or_path = source.frame_path
        if bytes_or_path is None:
            bytes_or_path = source.load(max_px=int(params.get("max_px", 640)))
        if bytes_or_path is None:
            return {"_ok": False, "count": 0, "boxes": [],
                    "source": "no_frame",
                    "tts_text":
                        "I don't have a fresh camera frame right now."}
        conf = float(params.get("conf", 0.40))
        try:
            boxes_v = _RUN_YOLO(bytes_or_path, classes=[0], conf=conf)
        except Exception as exc:
            return {"_ok": False, "count": 0, "boxes": [],
                    "source": "degraded_yolo_unavailable",
                    "_hint": str(exc)[:200],
                    "tts_text":
                        f"I can't run person detection right now — {exc}."}
        # Branch on whether the mocked runner returned pixel-space boxes
        # (test stubs) vs YOLO objects (production).
        boxes: List[Dict[str, Any]] = []
        for b in boxes_v:
            if isinstance(b, VisionBox):
                boxes.append(b.to_dict())
            elif isinstance(b, dict):
                boxes.append({k: v for k, v in b.items()
                              if k in {"label", "conf", "x1", "y1",
                                       "x2", "y2", "track_id"}})
        return {"_ok": True, "count": len(boxes), "boxes": boxes,
                "source": "yolo",
                "tts_text": _tts_count("person", boxes)}


class VoiceDetectFacesPlugin(RobotPlugin):
    """OpenCV Haar cascade face detection."""

    NAME = "voice.detect_faces"
    DESCRIPTION = (
        "Run the OpenCV Haar frontal-face cascade on the latest "
        "camera frame and return detected face rectangles plus a "
        "count. Lighter than YOLO and CPU-only; useful when YOLO "
        "isn't loaded."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "frame_path":  {"type": "string", "default": ""},
            "frame_b64":   {"type": "string", "default": ""},
            "min_size":    {"type": "integer",
                              "description":
                                  "Minimum face rectangle size in pixels.",
                              "minimum": 20, "maximum": 600, "default": 60},
            "max_px":      {"type": "integer", "default": 640,
                              "minimum": 160, "maximum": 1920},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "count":  {"type": "integer"},
            "boxes":  {"type": "array", "items": {"type": "object"}},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "vision", "faces"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        source = FrameSource(
            ctx=ctx,
            frame_path=(params.get("frame_path") or "").strip() or None,
            frame_b64=(params.get("frame_b64") or "").strip() or None,
        )
        bytes_or_path = source.frame_path
        if bytes_or_path is None:
            bytes_or_path = source.load(max_px=int(params.get("max_px", 640)))
        if bytes_or_path is None:
            return {"_ok": False, "count": 0, "boxes": [],
                    "tts_text": "I don't have a fresh frame to scan for faces."}
        try:
            boxes = detect_faces(bytes_or_path,
                                 min_size=int(params.get("min_size", 60)))
        except Exception as exc:
            return {"_ok": False, "count": 0, "boxes": [],
                    "_hint": str(exc)[:200],
                    "tts_text":
                        f"Face detection failed — {exc}."}
        return {"_ok": True, "count": len(boxes), "boxes": boxes,
                "tts_text": _tts_count("face", boxes)}
