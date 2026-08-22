"""Hope — future-oriented positive; agency + pathway."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "hope",
    "label":   "Hope",
    "valence":   +0.55,
    "arousal":   +0.30,
    "intensity": +0.50,
    "taxonomy": [{"framework": "snyder", "rank": "cognitive_positive"}],
    "decay_s": 22.0,
    "safety":    False,
    "signal_words": ["hopefully", "wish", "maybe tomorrow", "can be",
                     "possible", "optimistic", "I can do this"],
    "linguistic_markers": ["future tense", "modal verb"],
    "physiology": ["lifted chest", "longer breath cycles"],
    "triggers": ["evidence of progress", "trusted helper"],
    "companion_response": {
        "stance":     "share",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "I'm hopeful too — what would next look like?",
        ],
        "do_not": ["over-promise", "replace with certainty"],
    },
    "transitions_out": ["anticipation", "joy", "trust", "gratitude"],
    "notes": "Offer small next steps; preserve agency.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
