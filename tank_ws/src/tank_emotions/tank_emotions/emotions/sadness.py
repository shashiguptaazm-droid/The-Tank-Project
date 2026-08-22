"""Sadness — the loss response; quiet, slowed, weighted."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "sadness",
    "label":   "Sadness",
    "valence":   -0.65,
    "arousal":   -0.40,
    "intensity": +0.55,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 30.0,
    "safety":    True,
    "signal_words": ["sad", "down", "blue", "heartbroken", "lonely",
                     "miss", "crying", "tearful", "grief",
                     "devastated", "lost", "empty"],
    "linguistic_markers": ["low energy adverbs", "negation",
                            "first-person present"],
    "physiology": ["tears", "slumped posture", "low voice", "sighs"],
    "triggers": ["loss", "rejection", "loneliness",
                "reminder of past"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "empathic",
        "lengthen":    True,
        "mirror_level":"deep",
        "phrases": [
            "I'm sorry — that's heavy.",
            "you don't have to make it okay right now.",
        ],
        "do_not": ["cheer up", "compare to worse", "advice without asking"],
    },
    "transitions_out": ["relief", "hope", "acceptance",
                        "anger", "melancholy"],
    "notes": "Tonal mirror should be deep but never patronising.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
