"""tank_emotions.core — shared schema + decay + transition helpers.

Every emotion module returns a descriptor dict that we lift into a
typed ``Emotion`` dataclass so the rest of the system (companion,
display, persistence) can rely on a uniform shape:

* ``valence``  -  -1.0 (negative)  .. +1.0 (positive)
* ``arousal``  -  -1.0 (calm)      .. +1.0 (energetic)
* ``intensity``-  -1.0 (mild)      .. +1.0 (overwhelming)
* ``decay_s``  -  half-life in seconds (used by ``decay.py``)
* ``safety``   -  True if companion SHOULD escalate (medical, distress)
* ``taxonomy`` -  list of (framework, rank) pairs
* ``signal_words``       -  text cues (joined with ',' lower)
* ``companion_response`` -  mapping of behaviour fields
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List, Optional


SAFETY_FLAG_LABEL = {
    False: "none",
    True:  "may_need_escalation",
}


@dataclass
class Emotion:
    """Typed schema for a single emotion descriptor."""

    name:     str
    label:    str
    valence:  float
    arousal:  float
    intensity: float = 0.5
    decay_s:  float = 12.0
    safety:   bool = False
    taxonomy: List[Dict[str, str]] = field(default_factory=list)
    signal_words: List[str] = field(default_factory=list)
    linguistic_markers: List[str] = field(default_factory=list)
    physiology: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    companion_response: Dict[str, object] = field(default_factory=dict)
    transitions_out: List[str] = field(default_factory=list)
    notes:   str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    """Clamp ``x`` to ``[lo, hi]``."""
    return max(lo, min(hi, x))


def is_negative(valence: float) -> bool:
    """Categorise the valence axis."""
    return valence < -0.2


def is_positive(valence: float) -> bool:
    return valence > 0.2


def is_high_arousal(arousal: float) -> bool:
    return arousal > 0.3


def rough_category(e: Emotion) -> str:
    """Coarse quadrant label: q1..q4 + neutral."""
    v, a = e.valence, e.arousal
    if abs(v) < 0.2 and abs(a) < 0.3:
        return "neutral"
    if v > 0 and a > 0:
        return "positive_high_arousal"
    if v > 0 and a <= 0:
        return "positive_low_arousal"
    if v < 0 and a > 0:
        return "negative_high_arousal"
    return "negative_low_arousal"


def safe_default_desc() -> Emotion:
    """A canonical neutral / fallback descriptor."""
    return Emotion(
        name="neutral", label="Neutral",
        valence=0.0, arousal=0.0, intensity=0.5,
        taxonomy=[{"framework": "core", "rank": "default"}],
        notes=("Fallback descriptor used when the runtime cannot "
               "resolve a higher-precision emotion."),
    )
