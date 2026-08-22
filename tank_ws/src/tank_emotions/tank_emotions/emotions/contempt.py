"""Contempt — moral devaluation; 'less than' rather than 'bad'."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "contempt",
    "label":   "Contempt",
    "valence":   -0.45,
    "arousal":   -0.10,
    "intensity": +0.50,
    "taxonomy": [{"framework": "ekman",  "rank": "basic"}],
    "decay_s": 24.0,
    "safety":    False,
    "signal_words": ["contempt", "pathetic", "lesser", "beneath",
                     "scorn", "disdain", "don't respect"],
    "linguistic_markers": ["ranking marker", "negative intensifier"],
    "physiology": ["asymmetric smile (one corner raised)",
                   "slight head-tilt-down"],
    "triggers": ["norm violation by familiar other"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "dry",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "I hear the dismissal — there's a reason.",
        ],
        "do_not": ["match contempt", "reform the user"],
    },
    "transitions_out": ["anger", "disgust", "relief"],
    "notes": "Different from anger — anger over wrongs done, contempt over 'less than'.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
