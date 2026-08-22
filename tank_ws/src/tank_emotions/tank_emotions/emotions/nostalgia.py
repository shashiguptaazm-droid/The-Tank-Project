"""Nostalgia — bittersweet autobiographical memory; longing + warmth."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "nostalgia",
    "label":   "Nostalgia",
    "valence":   +0.30,
    "arousal":   -0.10,
    "intensity": +0.45,
    "taxonomy": [{"framework": "sedikides", "rank": "self_derived"}],
    "decay_s": 35.0,
    "safety":    False,
    "signal_words": ["nostalgia", "remember when", "back then", "those days",
                     "I miss those", "used to", "good old days"],
    "linguistic_markers": ["past tense", "first-person plural"],
    "physiology": ["soft gaze", "slower voice"],
    "triggers": ["sensory cue", "anniversary", "music"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "warm",
        "lengthen":    True,
        "mirror_level":"moderate",
        "phrases": [
            "memory is a kind of home.",
        ],
        "do_not": ["correct the memory", "rush back to now"],
    },
    "transitions_out": ["contentment", "love", "melancholy", "gratitude"],
    "notes": "Mixed-emotion: high valence + slight sadness; protect the tone.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
