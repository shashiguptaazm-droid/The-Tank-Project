"""Compassion — other-focused concern with action tendency to help."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "compassion",
    "label":   "Compassion",
    "valence":   +0.55,
    "arousal":   +0.05,
    "intensity": +0.55,
    "taxonomy": [{"framework": "goetz",   "rank": "other_focused"}],
    "decay_s": 22.0,
    "safety":    False,
    "signal_words": ["compassion", "feel for", "sorry for",
                     "this must be hard", "I care about",
                     "let's help", "suffering"],
    "linguistic_markers": ["second-person concern", "softening adverb"],
    "physiology": ["soft brow", "warm hands", "slowed pace"],
    "triggers": ["witnessed suffering of identified other"],
    "companion_response": {
        "stance":     "hold-space",
        "tone":        "empathic",
        "lengthen":    True,
        "mirror_level":"deep",
        "phrases": [
            "I see you, and I'm holding space.",
        ],
        "do_not": ["diagnose the other", "fix instead of be with"],
    },
    "transitions_out": ["love", "awe", "gratitude", "sadness"],
    "notes": "Distinguish from pity (downward focus) — keep side-by-side.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
