"""Surprise — orientation response to the unexpected."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "surprise",
    "label":   "Surprise",
    "valence":   +0.05,
    "arousal":   +0.85,
    "intensity": +0.55,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 6.0,
    "safety":    False,
    "signal_words": ["whoa", "wow", "really?", "no way", "omg",
                     "didn't expect", "surprised", "sudden"],
    "linguistic_markers": ["interrogative", "exclamation"],
    "physiology": ["wide eyes", " eyebrow raise", " interrupted motion"],
    "triggers": ["novel input", "violated expectation", "loud noise"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "playful",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "whoa — okay, that's a turn.",
        ],
        "do_not": ["explain too quickly", "over-talk"],
    },
    "transitions_out": ["joy", "fear", "anticipation", "disgust"],
    "notes": "Short half-life; ideal for clarifying follow-up questions.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
