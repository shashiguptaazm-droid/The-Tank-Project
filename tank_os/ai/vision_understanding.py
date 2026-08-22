"""TankOS Visual Scene Understanding — camera scene description, visual Q&A, object relationships.

Uses the Qwen2-VL-7B GGUF model (or any VLM) via llama.cpp to:
- Describe scenes from camera images
- Answer questions about what the camera sees
- Understand object relationships and spatial layout
- Generate structured scene reports
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.ai.vision_understanding")


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class SceneDescription:
    """Result of analyzing a camera scene."""
    summary: str                     # Brief description (1-2 sentences)
    detailed: str                    # Detailed description
    objects: List[Dict[str, Any]]   # Objects detected: [{"name": "...", "count": N, "positions": [...]}]
    activities: List[str] = field(default_factory=list)  # Observed activities
    risks: List[str] = field(default_factory=list)        # Safety concerns
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    source_camera: str = ""


@dataclass
class VisualQA:
    """Result of a visual question."""
    question: str
    answer: str
    confidence: float = 0.0
    related_objects: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ── Visual Scene Understanding Engine ───────────────────────────────────

class VisionUnderstandingEngine:
    """Understands camera scenes using YOLO + VLM integration.

    Two-layer approach:
    1. YOLO detection (fast, always available) — objects, faces, motion
    2. VLM deep understanding (when model available) — scene description, Q&A

    Usage:
        engine = VisionUnderstandingEngine()
        engine.initialize()

        # Describe a scene
        desc = engine.describe_scene()

        # Ask about what's visible
        answer = engine.visual_qa("Is there a person in the room?")
    """

    _instance: Optional["VisionUnderstandingEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._vision: Optional[VisionManager] = None
                cls._instance._vlm_available = False
                cls._instance._vlm_model_path = ""
                cls._instance._llm_available = False
                cls._instance._scene_history: List[SceneDescription] = []
                cls._instance._qa_history: List[VisualQA] = []
            return cls._instance

    def initialize(self) -> None:
        """Detect available models and set up event listeners."""
        self._vision = self._get_vision_manager()
        self._detect_models()

        self._bus.on("describe_scene_request", self._on_describe_request)
        self._bus.on("visual_qa_request", self._on_qa_request)
        self._bus.on("camera_frame", self._on_camera_frame)

        logger.info("VisionUnderstandingEngine initialized (VLM=%s, LLM=%s)",
                     self._vlm_available, self._llm_available)

    def _detect_models(self) -> None:
        """Detect available vision and language models."""
        # Check for Qwen2-VL GGUF model
        llm_dir = Path("/var/lib/tank_os/models/llm")
        candidates = list(llm_dir.glob("*VL*gguf")) + list(llm_dir.glob("*vision*gguf")) + \
                     list(llm_dir.glob("*vl*gguf"))
        if candidates:
            self._vlm_model_path = str(candidates[0])
            self._vlm_available = True
            logger.info("VLM model found: %s", candidates[0].name)

        # Check for mmproj file (required for VLM)
        mmproj = list(llm_dir.glob("mmproj*"))
        if mmproj:
            self._mmproj_path = str(mmproj[0])

        # Check if llama-cpp-python is available
        try:
            import llama_cpp  # noqa: F401
            self._llm_available = True
        except ImportError:
            self._llm_available = False

    # ── Scene understanding ───────────────────────────────────────────

    def describe_scene(self, image_path: Optional[str] = None) -> SceneDescription:
        """Describe the current camera scene.

        Combines fast YOLO detection with optional VLM deep understanding.
        """
        start = time.time()

        # Layer 1: Get YOLO detections (fast)
        yolo_objects = self._get_yolo_detections(image_path)

        # Layer 2: Build structured description from detections
        object_summary = self._summarize_objects(yolo_objects)

        # Layer 3: Deep VLM understanding (when available)
        vlm_description = ""
        if self._vlm_available and self._llm_available and image_path:
            vlm_description = self._vlm_describe(image_path)

        # Combine results
        if vlm_description:
            detailed = vlm_description
        else:
            detailed = f"Camera view: {object_summary}"

        summary = object_summary[:120] + "..." if len(object_summary) > 120 else object_summary

        desc = SceneDescription(
            summary=summary,
            detailed=detailed,
            objects=yolo_objects,
            risks=self._assess_risks(yolo_objects),
            confidence=0.8 if self._vlm_available else 0.5,
        )

        self._scene_history.append(desc)
        if len(self._scene_history) > 100:
            self._scene_history.pop(0)

        elapsed = (time.time() - start) * 1000
        logger.info("Scene described in %.0fms (%d objects)", elapsed, len(yolo_objects))
        return desc

    def _get_yolo_detections(self, image_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Run YOLO detection and return structured object list."""
        objects: List[Dict[str, Any]] = []
        try:
            if not self._vision:
                return objects

            # Get latest detections from vision manager
            detections = self._vision.get_detections()
            for detection in detections or []:
                name = detection.get("name", "unknown")
                confidence = detection.get("confidence", 0)
                box = detection.get("box", [0, 0, 0, 0])

                # Merge duplicates
                existing = next((o for o in objects if o["name"] == name), None)
                if existing:
                    existing["count"] += 1
                else:
                    objects.append({
                        "name": name,
                        "count": 1,
                        "max_confidence": confidence,
                        "positions": [{"bbox": box}],
                    })
        except Exception as e:
            logger.warning("YOLO detection failed: %s", e)

        return objects

    def _summarize_objects(self, objects: List[Dict[str, Any]]) -> str:
        """Create a human-readable summary from object detections."""
        if not objects:
            return "No objects detected in the scene."

        parts = []
        for obj in sorted(objects, key=lambda o: -o["count"]):
            name = obj["name"].replace("_", " ")
            count = obj["count"]
            if count == 1:
                parts.append(f"a {name}")
            else:
                parts.append(f"{count} {name}s")

        if len(parts) <= 3:
            return f"Scene contains: {', '.join(parts)}."
        return f"Scene contains: {', '.join(parts[:3])} and {len(parts) - 3} other object types."

    def _vlm_describe(self, image_path: str) -> str:
        """Use VLM model for deep scene understanding."""
        try:
            from llama_cpp import Llama
            # VLM mode requires mmproj file
            mmproj = getattr(self, '_mmproj_path', '')
            if not mmproj or not os.path.exists(mmproj):
                return ""

            llm = Llama(
                model_path=self._vlm_model_path,
                mmproj=mmproj,
                n_ctx=4096,
                verbose=False,
            )
            output = llm.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                            {"type": "text", "text": "Describe this image in detail. What objects, people, and activities do you see?"},
                        ],
                    }
                ],
                max_tokens=256,
                temperature=0.1,
            )
            return output.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.warning("VLM description failed: %s", e)
            return ""

    def _assess_risks(self, objects: List[Dict[str, Any]]) -> List[str]:
        """Assess safety risks from detected objects."""
        risks = []
        risk_objects = {
            "person": "Unknown person detected",
            "car": "Vehicle detected in proximity",
            "fire": "Fire or smoke detected — emergency",
            "dog": "Animal detected in area",
            "cat": "Animal detected in area",
        }
        for obj in objects:
            name = obj.get("name", "").lower()
            if name in risk_objects:
                risks.append(risk_objects[name])
        return risks

    # ── Visual Q&A ───────────────────────────────────────────────────

    def visual_qa(self, question: str, image_path: Optional[str] = None) -> VisualQA:
        """Answer a question about the current camera view."""
        start = time.time()

        # Get base scene understanding
        detections = self._get_yolo_detections(image_path)
        objects = [o["name"] for o in detections]

        # Try VLM Q&A
        answer = ""
        confidence = 0.3
        if self._vlm_available and self._llm_available and image_path:
            try:
                answer, confidence = self._vlm_qa(question, image_path)
            except Exception as e:
                logger.warning("VLM Q&A failed: %s", e)

        # Fallback: keyword-based from YOLO detections
        if not answer:
            answer, confidence = self._keyword_qa(question, objects)

        qa = VisualQA(
            question=question,
            answer=answer,
            confidence=confidence,
            related_objects=objects,
        )
        self._qa_history.append(qa)

        elapsed = (time.time() - start) * 1000
        logger.info("Visual QA answered in %.0fms: %s", elapsed, answer[:50])
        return qa

    def _vlm_qa(self, question: str, image_path: str) -> Tuple[str, float]:
        """Use VLM for visual Q&A."""
        from llama_cpp import Llama
        mmproj = getattr(self, '_mmproj_path', '')
        llm = Llama(
            model_path=self._vlm_model_path,
            mmproj=mmproj,
            n_ctx=4096,
            verbose=False,
        )
        output = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                        {"type": "text", "text": question},
                    ],
                }
            ],
            max_tokens=128,
            temperature=0.1,
        )
        answer = output.get("choices", [{}])[0].get("message", {}).get("content", "")
        return answer, 0.7

    def _keyword_qa(self, question: str, objects: List[str]) -> Tuple[str, float]:
        """Simple keyword-based Q&A fallback."""
        q = question.lower()

        # People detection
        if any(word in q for word in ["person", "people", "someone", "anybody", "human"]):
            if "person" in objects:
                return "Yes, I can see a person in the camera view.", 0.8
            return "No, I don't see any people in the current view.", 0.6

        # Animal detection
        if any(word in q for word in ["animal", "pet", "dog", "cat"]):
            animals = [o for o in objects if o in ("dog", "cat", "bird")]
            if animals:
                return f"Yes, I can see {animals[0]} in the view.", 0.7
            return "No animals detected in the current view.", 0.6

        # Object search
        for obj in objects:
            if obj.lower() in q:
                return f"Yes, I can see {obj.replace('_', ' ')} in the view.", 0.8

        # Generic
        if objects:
            return f"I can see {len(objects)} types of objects, including {objects[0]}.", 0.5
        return "I don't see any distinct objects in the current camera view.", 0.4

    # ── Event handlers ────────────────────────────────────────────────

    def _on_describe_request(self, event: Event) -> None:
        """Handle scene description requests from EventBus."""
        image = event.data.get("image_path")
        desc = self.describe_scene(image)
        self._bus.emit(Event("scene_description", {
            "summary": desc.summary,
            "objects": desc.objects,
            "risks": desc.risks,
        }, source="vision_understanding"))

    def _on_qa_request(self, event: Event) -> None:
        """Handle visual QA requests from EventBus."""
        question = event.data.get("question", "")
        image = event.data.get("image_path")
        qa = self.visual_qa(question, image)
        self._bus.emit(Event("visual_qa_result", {
            "question": qa.question,
            "answer": qa.answer,
            "confidence": qa.confidence,
        }, source="vision_understanding"))

    def _on_camera_frame(self, event: Event) -> None:
        """Handle new camera frames — lightweight analysis.
        Frame events are high-frequency — only do lightweight detection.
        """
        pass

    def _get_vision_manager(self):
        """Lazy import VisionManager — degrades gracefully if camera unavailable."""
        try:
            from tank_os.core.vision_manager import VisionManager
            return VisionManager()
        except Exception as e:
            logger.debug("VisionManager unavailable: %s", e)
            return None

    # ── Queries ───────────────────────────────────────────────────────

    def get_recent_scenes(self, limit: int = 5) -> List[SceneDescription]:
        return sorted(self._scene_history, key=lambda s: s.timestamp, reverse=True)[:limit]

    def get_recent_qa(self, limit: int = 10) -> List[VisualQA]:
        return sorted(self._qa_history, key=lambda q: q.timestamp, reverse=True)[:limit]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "vlm_available": self._vlm_available,
            "model": self._vlm_model_path.split("/")[-1] if self._vlm_model_path else "",
            "scenes_analyzed": len(self._scene_history),
            "qa_answered": len(self._qa_history),
        }
