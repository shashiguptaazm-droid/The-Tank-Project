"""Shared AI-vision helpers for the voice.detect_* plugins.

Design rules
~~~~~~~~~~~~
* **Heavy deps are lazy.** :mod:`cv2` and :mod:`ultralytics` (YOLO)
  are imported inside the function bodies only — never at module
  load time.  This way the package imports cleanly in CI benches
  that lack these libs.
* **Mockable proxy.** :func:`_RUN_YOLO` is the public seam tests
  patch.  Default calls :func:`_real_yolo` which actually loads
  YOLO.  Replace :data:`_RUN_YOLO` with a list-of-dicts stub to
  test the plugins hermetically.
* **Schema discipline.** YOLO output is normalised into a small
  dict list: ``{"label": str, "conf": float, "x1": int, ...}``
  so :class:`RobotPlugin` callers don't need to know YOLO's
  internal datatypes.

The plugin layer is at ``tank_command_bridge/plugins/vision_detect.py``
and ``tank_command_bridge/plugins/vision_security.py``; this file is
just the wrapper layer they call into.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class VisionBox:
    label: str
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int
    track_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {"label": self.label, "conf": round(self.conf, 3),
               "x1": self.x1, "y1": self.y1,
               "x2": self.x2, "y2": self.y2}
        if self.track_id is not None:
            out["track_id"] = self.track_id
        return out


# COCO class id → label for the curated subset we care about.
COCO_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus",
    7: "truck", 15: "cat", 16: "dog", 56: "chair", 57: "couch",
    60: "dining table", 62: "tv",
}


def _label_for(class_id: int) -> str:
    return COCO_NAMES.get(int(class_id), "object")


# ---------------------------------------------------------------------------
# Mockable proxy
# ---------------------------------------------------------------------------
_RUN_YOLO: Callable[..., List[VisionBox]] = lambda *_a, **_k: []


def set_yolo_runner(fn: Callable[..., List[VisionBox]]) -> None:
    """Tests replace the runner at module load time."""
    global _RUN_YOLO
    _RUN_YOLO = fn


def reset_yolo_runner() -> None:
    """Drop back to the real (heavy) runner."""
    global _RUN_YOLO
    _RUN_YOLO = lambda *_a, **_k: _real_yolo(*_a, **_k)


def _real_yolo(image_target: Union[str, bytes, "Any"],
               classes: Optional[List[int]] = None,
               conf: float = 0.40,
               model_path: str = "yolov8n.pt") -> List[VisionBox]:
    """Heavy path: actually load YOLO and run inference.

    ``image_target`` may be a filesystem path (``str``), raw JPEG
    bytes (``bytes``), or an already-decoded :mod:`cv2` image (we
    duck-type-check via a ``shape`` attribute).
    """
    try:
        from ultralytics import YOLO  # noqa: WPS433 (lazy import)
    except ImportError as exc:
        raise VisionUnavailable(f"ultralytics not installed: {exc}")
    try:
        import numpy as _np   # noqa: WPS433
        import cv2           # noqa: WPS433
    except ImportError as exc:
        raise VisionUnavailable(f"opencv-python not installed: {exc}")

    model = YOLO(model_path)

    if isinstance(image_target, str):
        results = model(image_target, conf=conf,
                        classes=classes or list(COCO_NAMES.keys()),
                        verbose=False)
    elif isinstance(image_target, bytes):
        arr = _np.frombuffer(image_target, dtype=_np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        results = model(img, conf=conf,
                        classes=classes or list(COCO_NAMES.keys()),
                        verbose=False)
    else:
        results = model(image_target, conf=conf,
                        classes=classes or list(COCO_NAMES.keys()),
                        verbose=False)

    out: List[VisionBox] = []
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            cls_id = int(box.cls[0])
            score = float(box.conf[0])
            tr_id = (int(box.id[0])
                     if box.id is not None and len(box.id) > 0 else None)
            out.append(VisionBox(
                label=_label_for(cls_id), conf=score,
                x1=x1, y1=y1, x2=x2, y2=y2, track_id=tr_id,
            ))
    return out


# Initialise the runner to the heavy path by default.
reset_yolo_runner()


# ---------------------------------------------------------------------------
# Face / head detection — OpenCV Haar cascade (ships with OpenCV)
# ---------------------------------------------------------------------------
def detect_faces(image_target: Union[str, bytes, "Any"],
                 min_size: int = 60) -> List[Dict[str, Any]]:
    """Best-effort face detection with OpenCV Haar cascades.

    Returns ``[{"conf": float, "x1": int, "y1": int, "x2": int, "y2": int}, ...]``.

    Returns an empty list if OpenCV isn't installed OR if the
    cascade XML isn't in the OpenCV data folder.
    """
    try:
        import numpy as _np   # noqa: WPS433
        import cv2           # noqa: WPS433
    except ImportError:
        return []

    if isinstance(image_target, str):
        img = cv2.imread(image_target)
        if img is None:
            return []
    elif isinstance(image_target, bytes):
        arr = _np.frombuffer(image_target, dtype=_np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return []
    else:
        img = image_target

    cascade_path = (getattr(cv2.data, "haarcascades", "")
                    + "haarcascade_frontalface_default.xml")
    if not cascade_path or not isinstance(cascade_path, str):
        return []
    try:
        cascade = cv2.CascadeClassifier(cascade_path)
    except Exception:
        return []
    if cascade.empty():
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    rects = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_size, min_size),
    )
    return [
        {"conf": 1.0, "x1": int(x), "y1": int(y),
         "x2": int(x + w), "y2": int(y + h)}
        for (x, y, w, h) in rects
    ]


# ---------------------------------------------------------------------------
# Frame-source abstraction
# ---------------------------------------------------------------------------
class FrameSource:
    """Pluggable camera-frame source. Plug-points:

    1. ``ctx.snapshot_camera_jpeg(max_px=...)`` — the existing
       bridge publishers expose this; returns a dict with ``data_url``.
    2. ``frame_path`` / ``frame_b64`` parameters from the LLM.
    3. A poke stub for tests.
    """

    def __init__(self, ctx: Any = None,
                 frame_path: Optional[str] = None,
                 frame_b64: Optional[str] = None) -> None:
        self.ctx = ctx
        self.frame_path = frame_path
        self.frame_b64 = frame_b64

    def load(self, max_px: int = 640) -> Optional[bytes]:
        """Return JPEG bytes or None if nothing is available."""
        if self.frame_b64:
            try:
                return base64.b64decode(self.frame_b64)
            except Exception:
                return None
        if self.frame_path:
            try:
                with open(self.frame_path, "rb") as fh:
                    return fh.read()
            except OSError:
                return None
        if self.ctx is not None and hasattr(self.ctx, "snapshot_camera_jpeg"):
            snap = self.ctx.snapshot_camera_jpeg(max_px=max_px) or {}
            url = snap.get("data_url", "") or ""
            if url.startswith("data:image/jpeg;base64,"):
                try:
                    return base64.b64decode(url.split(",", 1)[1])
                except Exception:
                    return None
        return None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class VisionUnavailable(RuntimeError):
    """Raised when the heavy vision backend isn't loadable."""