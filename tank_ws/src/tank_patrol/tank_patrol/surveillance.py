"""Pure-Python surveillance event classifier + alert severity rules.

This module is ROS-free so the same logic can be exercised by both
``surveillance_node.py`` (online) and ``surveillance_review.py`` (CLI).

Severity rule
-------------
Replace 2σ-from-waypoints with a simple distance threshold — far less
prone to false-positive alert fatigue.

* ``patrol_phase == "paused"`` AND ``label == "person"``             => **critical**
* ``patrol_phase == "patrolling"`` AND ``label == "person"``
    * ``distance > ON_PATH_M`` (3.0 m, could be 999.0 sentinel for
      "unknown active edge")                                       => **warning**
    * ``distance ≤ ON_PATH_M`` (could be family member)             => **info**
* ``bucket == "person"`` AND other phases                            => **warning**
* ``bucket == "noise"``                                              => **info**
* anything else                                                      => **info**

The sentinel value is a *finite* large number (999.0 m) so the JSON
serialisation step downstream stays RFC-7159 compliant. Never use
``float('inf')`` — strict JSON parsers (and MQTT/SSE consumers) reject
the literal ``Infinity`` token.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


# Public types -------------------------------------------------------------
class AlertSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


@dataclass
class MotionObservation:
    ts: float
    source: str
    bbox: Tuple[float, float, float, float]  # xyxy normalized 0..1
    confidence: float
    label: str                              # raw upstream label

    def to_dict(self) -> Dict:
        return {
            "ts":         self.ts,
            "source":     self.source,
            "bbox":       list(self.bbox),
            "confidence": self.confidence,
            "label":      self.label,
        }


@dataclass
class PatrolAlert:
    ts: float
    severity: AlertSeverity
    label: str
    observation: MotionObservation
    patrol_phase: str
    distance_from_active_edge_m: float
    note: str = ""

    def to_dict(self) -> Dict:
        d = {
            "ts":                             self.ts,
            "severity":                       self.severity.value,
            "label":                          self.label,
            "patrol_phase":                   self.patrol_phase,
            "distance_from_active_edge_m":    self.distance_from_active_edge_m,
            "observation":                    self.observation.to_dict(),
        }
        if self.note:
            d["note"] = self.note
        return d


# Tunables ----------------------------------------------------------------
PERSON_MIN_CONF        = 0.4
ANIMAL_MIN_CONF        = 0.3   # animals are harder to classify; allow lower
VEHICLE_MIN_CONF       = 0.4
NOISE_AREA_CUTOFF      = 0.0005
LOW_AREA_CUTOFF        = 0.005
LOW_CONF_DEFAULT       = 0.4
ON_PATH_M              = 3.0
# Sentinel for "active-edge distance unknown" — must be FINITE so JSON
# serialisation is RFC-7159 valid. Used by surveillance_node when
# /plan/current_edge is not yet wired; results in conservative WARNING
# for any person during patrolling.
OFF_PATH_SENTINEL_M    = 999.0


# Classifier ---------------------------------------------------------------
def classify(obs: MotionObservation) -> str:
    """Bucket a raw MotionObservation into:
    `person | animal | vehicle | unknown | noise`."""
    lbl = (obs.label or "").strip().lower()
    conf = float(obs.confidence)
    if not lbl or lbl in ("noise", "shadow", "", "null", "none"):
        return "noise"
    if obs.bbox[2] <= obs.bbox[0] or obs.bbox[3] <= obs.bbox[1]:
        return "unknown"
    area = max(0.0, (obs.bbox[2] - obs.bbox[0]) * (obs.bbox[3] - obs.bbox[1]))

    if conf <= 0.0 or area <= 0.0:
        return "noise"
    if area < NOISE_AREA_CUTOFF:
        return "noise" if lbl in ("motion", "blob") else "unknown"

    if lbl in ("person", "pedestrian", "human", "face"):
        return "person" if conf >= PERSON_MIN_CONF else "unknown"
    if lbl in ("cat", "dog", "animal", "raccoon", "deer",
               "fox", "rabbit", "bird"):
        return "animal" if conf >= ANIMAL_MIN_CONF else "noise"
    if lbl in ("car", "vehicle", "truck", "van", "bus",
               "bike", "bicycle", "motorbike"):
        return "vehicle" if conf >= VEHICLE_MIN_CONF else "unknown"
    if lbl in ("motion", "blob"):
        return "noise" if (area < LOW_AREA_CUTOFF or conf < LOW_CONF_DEFAULT) \
            else "unknown"
    return "unknown"


# Severity rule ------------------------------------------------------------
def severity(obs: MotionObservation,
             *,
             patrol_phase: str,
             distance_from_active_edge_m: float) -> AlertSeverity:
    """Distance is expected to be a FINITE float — pass OFF_PATH_SENTINEL_M
    (= 999.0) when no active-edge data is available yet. Never pass
    float('inf'); the JSON serialisation downstream will reject it."""
    bucket = classify(obs)
    if bucket == "noise":
        return AlertSeverity.INFO

    if patrol_phase == "paused" and bucket == "person":
        return AlertSeverity.CRITICAL

    if patrol_phase == "patrolling" and bucket == "person":
        if distance_from_active_edge_m > ON_PATH_M:
            return AlertSeverity.WARNING
        return AlertSeverity.INFO

    if bucket == "person":
        return AlertSeverity.WARNING

    return AlertSeverity.INFO


# Event log ---------------------------------------------------------------
class AlertJournal:
    """Append-only JSONL file at /var/lib/tank/surveillance/<date>.jsonl."""

    DIR = "/var/lib/tank/surveillance"

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._base_dir = base_dir or self.DIR
        self._lock_path: Optional[str] = None
        self._fh = None

    def _path_for(self, ts: float) -> str:
        from datetime import datetime, timezone
        day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        return os.path.join(self._base_dir, f"{day}.jsonl")

    def append(self, alert: PatrolAlert) -> str:
        path = self._path_for(alert.ts)
        os.makedirs(self._base_dir, exist_ok=True)
        if self._fh is None or self._lock_path != path:
            if self._fh is not None:
                self._fh.close()
            self._fh = open(path, "a", encoding="utf-8")
            self._lock_path = path
        try:
            self._fh.write(json.dumps(alert.to_dict(),
                                      ensure_ascii=False,
                                      allow_nan=False) + "\n")
            self._fh.flush()
            return path
        except Exception:
            return ""

    def read_day(self, day: str) -> List[Dict]:
        path = os.path.join(self._base_dir, f"{day}.jsonl")
        if not os.path.exists(path):
            return []
        out: List[Dict] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            finally:
                self._fh = None
                self._lock_path = None


def to_observation(payload: Dict) -> Optional[MotionObservation]:
    """Parse a /security/events/motion JSON message into a MotionObservation."""
    try:
        bbox = tuple(float(v) for v in payload.get("bbox", (0, 0, 0, 0)))
    except Exception:
        bbox = (0.0, 0.0, 0.0, 0.0)
    try:
        ts = float(payload.get("ts", time.time()))
    except Exception:
        ts = time.time()
    try:
        conf = float(payload.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    return MotionObservation(
        ts=ts,
        source=str(payload.get("source", "motion_node")),
        bbox=bbox,
        confidence=conf,
        label=str(payload.get("label", "")),
    )
