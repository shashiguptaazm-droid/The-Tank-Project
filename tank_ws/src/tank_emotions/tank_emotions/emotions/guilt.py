"""Guilt — 'I did something bad'; reparative action tendency."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "guilt",
    "label":   "Guilt",
    "valence":   -0.55,
    "arousal":   +0.10,
    "intensity": +0.55,
    "taxonomy": [{"framework": "izard", "rank": "self_conscious"}],
    "decay_s": 25.0,
    "safety":    False,
    "signal_words": ["guilty", "my fault", "shouldn't have", "sorry I did",
                     "regret", "I owe", "wrong of me"],
    "linguistic_markers": ["first-person past", "obligation marker"],
    "physiology": ["ruminative posture", "fidgeting hands"],
    "triggers": ["violation of own rule", "harm to someone"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "Carrying that is heavy — let's lighten the load.",
        ],
        "do_not": ["absolve without offer", "lecture about ethics"],
    },
    "transitions_out": ["shame", "relief", "compassion", "sadness"],
    "notes": "Often paired with reparative action; gatekeeper of trust.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
