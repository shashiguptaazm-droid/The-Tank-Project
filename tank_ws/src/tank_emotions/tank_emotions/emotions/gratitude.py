"""Gratitude — appreciation of benefit received; social-bonding."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "gratitude",
    "label":   "Gratitude",
    "valence":   +0.75,
    "arousal":   +0.10,
    "intensity": +0.50,
    "taxonomy": [{"framework": "emmons", "rank": "self_transcendent"}],
    "decay_s": 18.0,
    "safety":    False,
    "signal_words": ["grateful", "thank you", "appreciate", "thanks",
                     "blessed", "lucky", "this means a lot"],
    "linguistic_markers": ["second-person positive", "recipient marker"],
    "physiology": ["warm hands", "soft gaze", "slower breathing"],
    "triggers": ["unexpected help", "remembered kindness"],
    "companion_response": {
        "stance":     "share",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "thank you for sharing that with me.",
        ],
        "do_not": ["deflect gratitude", "self-deprecate"],
    },
    "transitions_out": ["love", "contentment", "joy", "compassion"],
    "notes": "Expressed gratitude predicts wellbeing; mirror lightly.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
