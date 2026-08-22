"""Relief — post-stress discharge; cessation of threat."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "relief",
    "label":   "Relief",
    "valence":   +0.65,
    "arousal":   -0.45,
    "intensity": +0.55,
    "taxonomy": [{"framework": "parrott", "rank": "secondary"}],
    "decay_s": 14.0,
    "safety":    False,
    "signal_words": ["relief", "phew", "made it", "thank god",
                     "finally", "off my chest", "breathing again"],
    "linguistic_markers": ["completed tense", "exclamation"],
    "physiology": ["deep exhale", "slumped shoulders"],
    "triggers": ["end of danger", "favourable resolution"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "breathe — we made it through the worst of it.",
        ],
        "do_not": ["rush the moment", "introduce new tension"],
    },
    "transitions_out": ["contentment", "joy", "gratitude"],
    "notes": "Bridges the gap between high-arousal fear and rest.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
