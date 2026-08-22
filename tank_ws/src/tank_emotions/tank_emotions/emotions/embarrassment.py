"""Embarrassment — short-lived self-conscious reaction to a social faux pas."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "embarrassment",
    "label":   "Embarrassment",
    "valence":   -0.20,
    "arousal":   +0.55,
    "intensity": +0.40,
    "taxonomy": [{"framework": "izard", "rank": "self_conscious"}],
    "decay_s": 6.0,
    "safety":    False,
    "signal_words": ["embarrassed", "foot-in-mouth", "red in the face",
                     "awkward", "oops", "cringe", "mortified"],
    "linguistic_markers": ["short exclamation", "self-correction"],
    "physiology": ["blushing", "gaze aversion", "smile + grimace"],
    "triggers": ["social faux pas", "unintended attention"],
    "companion_response": {
        "stance":     "redirect-joy",
        "tone":        "playful",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "we all have those moments.",
        ],
        "do_not": ["prolong the spotlight", "shame the user"],
    },
    "transitions_out": ["joy", "amusement", "shame"],
    "notes": "Usually fades fast; light humour is the correct mirror.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
