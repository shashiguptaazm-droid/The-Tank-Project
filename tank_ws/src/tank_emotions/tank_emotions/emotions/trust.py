"""Trust — confidence in someone / something reliable."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "trust",
    "label":   "Trust",
    "valence":   +0.55,
    "arousal":   +0.10,
    "intensity": +0.50,
    "taxonomy": [{"framework": "plutchik", "rank": "primary"}],
    "decay_s": 25.0,
    "safety":    False,
    "signal_words": ["trust", "rely", "confide", "believe in",
                     "faith", "count on", "depend"],
    "linguistic_markers": ["first-person plural", "low intensifier"],
    "physiology": ["open posture", "slow blink rate", "steady voice"],
    "triggers": ["predictable outcome", "kept promise", "familiar helper"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "quiet",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "I'm with you on this — take it slowly.",
        ],
        "do_not": ["demand confession", "over-promise"],
    },
    "transitions_out": ["joy", "love", "anticipation"],
    "notes": "Trust often needs time — companion should not fast-forward.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
