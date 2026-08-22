"""Love — attachment + warmth; multi-component (intimacy, passion, commitment)."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "love",
    "label":   "Love",
    "valence":   +0.85,
    "arousal":   +0.30,
    "intensity": +0.65,
    "taxonomy": [{"framework": "sternberg", "rank": "attachment"}],
    "decay_s": 60.0,
    "safety":    False,
    "signal_words": ["love", "adore", "cherish", "care for",
                     "fond of", "dear to me", "beloved"],
    "linguistic_markers": ["second-person positive", "possessive warm"],
    "physiology": ["warm cheeks", "softer voice",
                  "gentler gesture"],
    "triggers": ["long trust", "mutual vulnerability", "shared ritual"],
    "companion_response": {
        "stance":     "share",
        "tone":        "warm",
        "lengthen":    True,
        "mirror_level":"deep",
        "phrases": [
            "from here too.",
        ],
        "do_not": ["be performative", "force reciprocation"],
    },
    "transitions_out": ["trust", "compassion", "gratitude", "joy"],
    "notes": "Long-decay; companion should not interrupt.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
