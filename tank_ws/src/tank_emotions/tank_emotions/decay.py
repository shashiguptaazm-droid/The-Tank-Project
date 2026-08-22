"""tank_emotions.decay — half-life interpolation back to neutral.

Models every emotion as a transient impulse whose valence and arousal
decay toward ``0`` at a configurable half-life (``e.decay_s``).

Useful for the display / audio runtime to decide when to "calm down".
The model is intentionally simple — the system does NOT need a full
HMM here; a single ``after`` timestamp + the descriptor is enough.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional

from .core import Emotion


@dataclass
class DecayedEmotion:
    name:  str
    label: str
    valence:       float
    arousal:       float
    residual:      float  # 0..1, fraction of original intensity left
    elapsed_s:     float
    half_life_s:   float
    safety:        bool


def decay_to(emo: Emotion, elapsed_s: float) -> DecayedEmotion:
    """Return the emotion's valence / arousal after ``elapsed_s`` seconds.

    Half-life formula:  residual = 0.5 ** (elapsed / half_life)
    """
    half = max(emo.decay_s, 0.001)
    residual = 0.5 ** (elapsed_s / half)
    return DecayedEmotion(
        name=emo.name,
        label=emo.label,
        valence=emo.valence * residual,
        arousal=emo.arousal * residual,
        residual=residual,
        elapsed_s=elapsed_s,
        half_life_s=half,
        safety=emo.safety,
    )


def fresh(emo: Emotion) -> DecayedEmotion:
    """Return the emotion at the moment of observation (residual = 1.0)."""
    return decay_to(emo, 0.0)


def should_relax(emo: Emotion, elapsed_s: float,
                 threshold: float = 0.20) -> bool:
    """Return True if the emotion has decayed below ``threshold``."""
    return decay_to(emo, elapsed_s).residual < threshold


def age_seconds(t0_ts: float) -> float:
    return max(0.0, time.time() - t0_ts)
