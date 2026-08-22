"""Contentment — quiet satisfaction, the 'okay, this is enough' warm low-valence."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "contentment",
    "label":   "Contentment",
    "valence":   +0.65,
    "arousal":   -0.40,
    "intensity": +0.45,
    "taxonomy": [{"framework": "parrott", "rank": "secondary"}],
    "decay_s": 30.0,
    "safety":    False,
    "signal_words": ["content", "satisfied", "okay", "fine", "good",
                     "settled", "enough", "calmly", "easy"],
    "linguistic_markers": ["low intensifier", "simple sentence"],
    "physiology": ["even breathing", "unclenched jaw",
                   "warm hands"],
    "triggers": ["baseline", "small completion", "quiet rest"],
    "companion_response": {
        "stance":     "neutral",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "Quiet wins are the best kind.",
        ],
        "do_not": ["stir", "press for drama"],
    },
    "transitions_out": ["joy", "gratitude", "love", "nostalgia"],
    "notes": "Often follows joy once arousal decays.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
