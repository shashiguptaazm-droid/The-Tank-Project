"""tank_emotions.signals.face — Action Unit (Ekman FACS) heuristics.

Maps a small set of face Action Units (AU) from the FACS standard to a
per-emotion score.  Inputs are expected in the range ``[0, 1]`` (the
intensity of each AU), e.g. ``{"AU12": 0.8, "AU4": 0.5}``.

This module is *defensive*: if no AU is given we return all zeros so
the runtime can degrade to no-op until the vision stack is up.
"""
from __future__ import annotations

from typing import Dict


# Each AU pattern pulls from the FACS coding manual at a high level.
_PATTERNS: Dict[str, Dict[str, float]] = {
    "joy":          {"AU6": 0.6,  "AU12": 0.6},
    "surprise":     {"AU1": 0.5,  "AU2": 0.5,  "AU5B": 0.5, "AU26": 0.4},
    "sadness":      {"AU1": 0.4,  "AU4": 0.6,  "AU15": 0.5},
    "anger":        {"AU4": 0.6,  "AU5": 0.5,  "AU7": 0.5,  "AU23": 0.4, "AU24": 0.4},
    "fear":         {"AU1": 0.4,  "AU2": 0.4,  "AU4": 0.5,  "AU5": 0.5, "AU20": 0.5, "AU26": 0.4},
    "disgust":      {"AU9": 0.6,  "AU10": 0.5, "AU17": 0.5},
    "contempt":     {"AU12R": 0.5, "AU14R": 0.5},
    "embarrassment":{"AU6": 0.3,  "AU12": 0.3, "AU24": 0.5, "AU54": 0.5, "AU64": 0.4},
    "pride":        {"AU53": 0.6, "AU12": 0.4, "AU6": 0.3},
    "shame":        {"AU54": 0.5, "AU64": 0.4, "AU4": 0.4, "AU24": 0.4},
    "guilt":        {"AU4": 0.4,  "AU54": 0.5, "AU64": 0.3},
    "awe":          {"AU1": 0.5,  "AU2": 0.5,  "AU5B": 0.5, "AU26": 0.4},
    "contentment":  {"AU12": 0.4, "AU24": 0.3},
    "anticipation": {"AU5": 0.4,  "AU9": 0.3,  "AU45": 0.4},
    "trust":        {"AU1": 0.3,  "AU6": 0.3,  "AU45": 0.4},
}


def score_face(au_map: Dict[str, float]) -> Dict[str, float]:
    """Return per-emotion face scores given a ``{AU_name: 0..1}`` map."""
    out: Dict[str, float] = {}
    if not au_map:
        return out
    for emo, weights in _PATTERNS.items():
        s = 0.0
        weight_total = sum(weights.values()) or 1.0
        for au, w in weights.items():
            v = au_map.get(au)
            if v is None:
                continue
            s += min(max(v, 0.0), 1.0) * w
        if s:
            out[emo] = min(1.0, s / weight_total)
    return out
