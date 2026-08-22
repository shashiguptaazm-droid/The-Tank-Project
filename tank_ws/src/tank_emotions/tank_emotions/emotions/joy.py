"""Joy — pleasure, brightness, the "yes!" feeling.

Taxonomy: Plutchik primary; Ekman basic (happiness is a faded variant).
"""
from __future__ import annotations

DESCRIPTOR = {
    "name":  "joy",
    "label": "Joy",
    "valence":   +0.85,
    "arousal":   +0.55,
    "intensity": +0.70,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 12.0,
    "safety":    False,
    "signal_words": ["joyful", "happy", "glad", "delighted", "thrilled",
                     "ecstatic", ":)", "haha", "yay", "woohoo", "stoked",
                     "elated", "overjoyed"],
    "linguistic_markers": ["exclamation", "laughter", "positive_superlative"],
    "physiology": ["warm chest", "light body", "relaxed muscles",
                   "increased heart-rate variability"],
    "triggers": ["success", "reunion", "celebration", "win",
                "unexpected gift"],
    "companion_response": {
        "stance":     "share",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "love the energy — let's roll with it.",
            "let me ride this wave with you.",
        ],
        "do_not": ["diminish", "challenge", "ignore"],
    },
    "transitions_out": ["contentment", "anticipation", "relief",
                        "gratitude", "love"],
    "notes": "Caution: extreme euphoria can mask real distress.",
}


def describe() -> dict:
    """Return the descriptor dict (copy)."""
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
