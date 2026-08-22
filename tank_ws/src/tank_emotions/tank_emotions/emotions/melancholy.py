"""Melancholy — quiet, low-energy sadness that feels reflective rather than disabling."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "melancholy",
    "label":   "Melancholy",
    "valence":   -0.25,
    "arousal":   -0.45,
    "intensity": +0.40,
    "taxonomy": [{"framework": "parrott", "rank": "secondary"}],
    "decay_s": 60.0,
    "safety":    False,
    "signal_words": ["melancholy", "bittersweet", "wistful",
                     "pensive", "quiet tonight", "in my feels"],
    "linguistic_markers": ["present-continuous soft"],
    "physiology": ["even breathing", "lower shoulders"],
    "triggers": ["rain", "music", "dawn / dusk"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "quiet",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "bittersweet but valid.",
        ],
        "do_not": ["try to fix", "force cheer"],
    },
    "transitions_out": ["contentment", "nostalgia", "hope"],
    "notes": "Distinct from depression (clinical) — always remember to escalate if dim.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
