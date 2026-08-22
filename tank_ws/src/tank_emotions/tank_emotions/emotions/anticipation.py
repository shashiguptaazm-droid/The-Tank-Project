"""Anticipation — interest, excitement, looking-forward."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "anticipation",
    "label":   "Anticipation",
    "valence":   +0.45,
    "arousal":   +0.65,
    "intensity": +0.55,
    "taxonomy": [{"framework": "plutchik", "rank": "primary"}],
    "decay_s": 14.0,
    "safety":    False,
    "signal_words": ["excited", "looking forward", "can't wait",
                     "curious", "eager", "anticipating", "soon"],
    "linguistic_markers": ["future tense", "exclamation"],
    "physiology": ["leaning forward", "wide eyes",
                  "elevated heart-rate"],
    "triggers": ["upcoming event", "novel opportunity", "preparation"],
    "companion_response": {
        "stance":     "share",
        "tone":        "playful",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "I'm curious too — tell me more.",
        ],
        "do_not": ["kill the momentum", "interrupt with caution"],
    },
    "transitions_out": ["joy", "trust", "fear"],
    "notes": "Pair with forward-looking actions; bad timing = anticipation → fear.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
