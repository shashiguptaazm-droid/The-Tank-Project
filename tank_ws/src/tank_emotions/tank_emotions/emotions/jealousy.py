"""Jealousy — fear of losing someone to a third party."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "jealousy",
    "label":   "Jealousy",
    "valence":   -0.55,
    "arousal":   +0.65,
    "intensity": +0.60,
    "taxonomy": [{"framework": "parrott", "rank": "secondary"}],
    "decay_s": 25.0,
    "safety":    False,
    "signal_words": ["jealous", "they have more time",
                     "replaced", "left for", "suspicious of",
                     "third wheel"],
    "linguistic_markers": ["triad framing", "self comparison"],
    "physiology": ["tight chest", "hypervigilance"],
    "triggers": ["perceived competitor attention", "withdrawal"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "grounding",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "that pinch is real — let's name it.",
        ],
        "do_not": ["minimise", "play ranking games"],
    },
    "transitions_out": ["anger", "sadness", "shame"],
    "notes": "Jealousy is the fear-of-loss triad; envy is a 2-person want.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
