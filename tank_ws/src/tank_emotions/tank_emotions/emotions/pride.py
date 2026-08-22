"""Pride — self-conscious positive; earned accomplishment."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "pride",
    "label":   "Pride",
    "valence":   +0.70,
    "arousal":   +0.45,
    "intensity": +0.55,
    "taxonomy": [{"framework": "izard", "rank": "self_conscious"}],
    "decay_s": 30.0,
    "safety":    False,
    "signal_words": ["proud", "did it", "made it", "earned", "accomplished",
                     "my work paid off", "nailed it"],
    "linguistic_markers": ["first-person past", "achievement word"],
    "physiology": ["posture expansion", "head-tilt-up",
                  "slight smile"],
    "triggers": ["completion of effort", "public recognition"],
    "companion_response": {
        "stance":     "share",
        "tone":        "warm",
        "lengthen":    False,
        "mirror_level":"light",
        "phrases": [
            "you earned that.",
        ],
        "do_not": ["credit instead to luck", "compare to others"],
    },
    "transitions_out": ["joy", "contentment", "gratitude"],
    "notes": "Chronic pride can become arrogance — companion should hold.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
