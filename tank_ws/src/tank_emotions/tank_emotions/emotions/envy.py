"""Envy — 2-person: I want what you have."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "envy",
    "label":   "Envy",
    "valence":   -0.55,
    "arousal":   +0.30,
    "intensity": +0.55,
    "taxonomy": [{"framework": "parrott", "rank": "secondary"}],
    "decay_s": 22.0,
    "safety":    False,
    "signal_words": ["envy", "they have", "wish I had", "not fair",
                     "why them", "I'd love to be"],
    "linguistic_markers": ["downward social comparison"],
    "physiology": ["slight frown", "shoulder hunch"],
    "triggers": ["perceived inequality", "out-group success"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "it's okay to want what you don't have.",
        ],
        "do_not": ["moralise about coveting"],
    },
    "transitions_out": ["anger", "sadness", "compassion"],
    "notes": "Often fuels ambition; do not collapse into shame.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
