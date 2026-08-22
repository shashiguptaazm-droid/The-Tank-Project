"""Shame — global self-devaluation; 'I am bad'."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "shame",
    "label":   "Shame",
    "valence":   -0.70,
    "arousal":   -0.30,
    "intensity": +0.65,
    "taxonomy": [{"framework": "izard", "rank": "self_conscious"}],
    "decay_s": 35.0,
    "safety":    True,
    "signal_words": ["ashamed", "worthless", "pathetic", "can't face",
                     "below", "humiliated", "small",
                     "disgrace", "embarrassed of myself"],
    "linguistic_markers": ["identity-marking negative", "first person"],
    "physiology": ["dropped gaze", "rounded shoulders",
                  "reduced vocal volume"],
    "triggers": ["public exposure of failure", "identity rejection"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "empathic",
        "lengthen":    True,
        "mirror_level":"deep",
        "phrases": [
            "that's a heavy load to carry — let's slow down.",
        ],
        "do_not": ["label them as a person", "publicly praise too soon"],
    },
    "transitions_out": ["sadness", "guilt", "relief"],
    "notes": "Distinguish shame (I am bad) from guilt (I did bad).",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
