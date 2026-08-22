"""``voice.detect_intruder`` + ``voice.alert_intruder`` plugins.

The user-flavoured security pair. ``detect_intruder`` is *read-class*
(it never mutates state); ``alert_intruder`` is *write-class* and
emits an event into the existing ``tank_security`` JSONL pipeline
**and** persists a small audit log the operator can scrub.

Run/anomaly shape::

  user:  "Hey Tank, is anyone in the room you don't recognise?"
  tank:   "I see 2 persons, both at over 80 % confidence. None "
           of them are tagged as familiar — should I alert?"
  user:  "Yes, alert."
  tank:   "Alerted. Logged at /var/log/tank/intruders.jsonl."

Plug-point discovery
~~~~~~~~~~~~~~~~~~~~
The actual person recogniser (``voice.detect_faces`` + a face
embedding store) is out of scope for this plugin — we only
flag a high-confidence person detect as a potential intruder.
Future build-out swaps ``_known_faces`` for a proper
similarity/embeddings store.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from . import RobotPlugin
from ._vision_helpers import (
    FrameSource,
    VisionBox,
    _RUN_YOLO,
)


# Where alert_intruder appends JSONL events.  Operator can grep
# or pipe to ``tank_security.event_logger`` if they want.
DEFAULT_INTRUDER_LOG = Path("/var/log/tank/intruders.jsonl")


# Stub — replace via the persona memory or face-recognition pack.
def _known_faces() -> List[str]:
    return ["shashi", "sharma-family"]


def _frame_payload(params: Dict[str, Any], ctx: Any):
    source = FrameSource(
        ctx=ctx,
        frame_path=(params.get("frame_path") or "").strip() or None,
        frame_b64=(params.get("frame_b64") or "").strip() or None,
    )
    target = source.frame_path
    if target is None:
        target = source.load(max_px=int(params.get("max_px", 640)))
    return target


class VoiceDetectIntruderPlugin(RobotPlugin):
    """High-confidence person detection → 'intruder? yes/no' verdict."""

    NAME = "voice.detect_intruder"
    DESCRIPTION = (
        "Run YOLO person detection on the latest camera frame at a "
        "high confidence threshold and compare against a known-faces "
        "stub (returns 'unknown' for every name today until face "
        "embeddings land). Returns ``verdict`` (\"intruder\", "
        "\"all_clear\", or \"unclear\"), the detected persons, and "
        "a TTS-friendly line for the LLM to speak."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "frame_path": {"type": "string", "default": ""},
            "frame_b64":  {"type": "string", "default": ""},
            "conf":       {"type": "number",
                            "description":
                                "Confidence threshold (default 0.55).",
                            "minimum": 0.20, "maximum": 0.95, "default": 0.55},
            "max_px":     {"type": "integer", "default": 640,
                            "minimum": 160, "maximum": 1920},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "verdict":       {"type": "string",
                               "enum": ["intruder", "all_clear", "unclear"]},
            "persons_count":  {"type": "integer"},
            "persons":        {"type": "array", "items": {"type": "object"}},
            "known_faces_matched": {"type": "integer",
                                     "description":
                                         "How many of the detected persons "
                                         "match a known-faces label today. "
                                         "Always 0 until face embeddings "
                                         "are wired."},
            "tts_text":       {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "vision", "security"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        target = _frame_payload(params, ctx)
        if target is None:
            return {"_ok": False, "verdict": "unclear", "persons_count": 0,
                    "persons": [], "known_faces_matched": 0,
                    "tts_text":
                        "I don't have a frame right now."}
        try:
            boxes_v = _RUN_YOLO(target, classes=[0],
                                conf=float(params.get("conf", 0.55)))
        except Exception as exc:
            return {"_ok": False, "verdict": "unclear", "persons_count": 0,
                    "persons": [],
                    "_hint": str(exc)[:200],
                    "tts_text":
                        f"Intruder check unavailable — {exc}"}
        boxes: List[Dict[str, Any]] = []
        for b in boxes_v:
            if isinstance(b, VisionBox):
                boxes.append(b.to_dict())
            elif isinstance(b, dict):
                boxes.append({k: v for k, v in b.items()
                              if k in {"label", "conf", "x1", "y1",
                                       "x2", "y2", "track_id"}})
        persons = [b for b in boxes if b.get("label", "") == "person"]

        # In a future face-embeddings build this would compare each
        # bbox crop against `_known_faces()`.  Today the stub returns
        # 0 matches, so the verdict is "unclear" if anyone is seen.
        if not persons:
            verdict = "all_clear"
            tts = "I don't see anyone in the room."
        else:
            verdict = "unclear"   # unknown face(s) — operator must confirm
            tts = (f"I see {len(persons)} "
                   f"{'person' if len(persons) == 1 else 'persons'}; "
                   "I can't identify them yet.")
        return {"_ok": True, "verdict": verdict,
                "persons_count": len(persons),
                "persons": persons,
                "known_faces_matched": 0,
                "tts_text": tts}


class VoiceAlertIntruderPlugin(RobotPlugin):
    """Persist an 'intruder' event and broadcast it on the security bus."""

    NAME = "voice.alert_intruder"
    DESCRIPTION = (
        "Emit a structured intruder event into the local JSONL "
        "audit log, file::``/var/log/tank/intruders.jsonl``, AND "
        "publish on the in-process ``security_event_sink`` callable "
        "passed via ``ctx`` so other components (tank_security.event_logger, "
        "tank_dashboard WS) can react. Write-class because state is "
        "mutated on disk and a side-effect broadcast is fired."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "verdict": {"type": "string",
                        "enum": ["intruder", "suspicious", "all_clear"],
                        "description":
                            "Severity tag carried through to the log.",
                        "default": "intruder"},
            "reason":  {"type": "string",
                        "description":
                            "Free-text reason the operator/voice gave.",
                        "default": ""},
            "persons": {"type": "array",
                        "description":
                            "Optional list of bounding boxes from "
                            "voice.detect_intruder; logged verbatim.",
                        "items": {"type": "object"},
                        "default": []},
            "log_path": {"type": "string",
                          "description": "Override the JSONL log path.",
                          "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "logged_at":  {"type": "string",
                            "description": "Absolute path of the JSONL file."},
            "event_id":   {"type": "string"},
            "broadcast":  {"type": "boolean",
                            "description":
                                "True iff the ctx bus accepted the event."},
            "tts_text":   {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "vision", "security"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        verdict = (params.get("verdict") or "intruder").strip().lower()
        reason = (params.get("reason") or "").strip()[:240]
        persons = list(params.get("persons") or [])
        log_path = Path(params.get("log_path")
                        or os.environ.get("TANK_INTRUDER_LOG")
                        or DEFAULT_INTRUDER_LOG)
        event = {
            "ts": time.time(),
            "verdict": verdict,
            "reason": reason,
            "persons": persons,
        }
        event_id = f"INTR-{int(event['ts']*1000):x}"
        try:
            parent = log_path.parent
            if str(parent) and str(parent) != ".":
                parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"event_id": event_id, **event}) + "\n")
            logged_ok = True
        except OSError as exc:
            return {"_ok": False, "event_id": event_id,
                    "logged_at": str(log_path),
                    "broadcast": False,
                    "_hint": f"log_write_failed:{exc}",
                    "tts_text": "Couldn't log the alert."}

        broadcast = False
        sink = getattr(ctx, "security_event_sink", None) if ctx is not None else None
        if callable(sink):
            try:
                sink({"event_id": event_id, **event})
                broadcast = True
            except Exception:
                broadcast = False
        return {"_ok": True, "logged_at": str(log_path),
                "event_id": event_id,
                "broadcast": broadcast,
                "tts_text":
                    (f"Alerted. event {event_id} "
                     + ("broadcast to dashboard." if broadcast else "logged only."))}
