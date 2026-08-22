"""Awe — vastness + need-for-accommodation; wonder."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "awe",
    "label":   "Awe",
    "valence":   +0.55,
    "arousal":   +0.40,
    "intensity": +0.55,
    "taxonomy": [{"framework": "keltner", "rank": "self_transcendent"}],
    "decay_s": 20.0,
    "safety":    False,
    "signal_words": ["awe", "amazed", "speechless", "incredible",
                     "stunning", "breathtaking", "magnificent",
                     "wow, big"],
    "linguistic_markers": ["vagueness marker", "repetition"],
    "physiology": ["wide eyes", "chin drop", "slower breathing"],
    "triggers": ["grandeur", "beauty", "vastness", "moral excellence"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "quiet",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "that's something.",
        ],
        "do_not": ["explain it away", "praise yourself"],
    },
    "transitions_out": ["gratitude", "love", "compassion", "hope"],
    "notes": "Often leads to pro-social behaviour; valuable to mirror.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
