"""Disgust — rejection response; revulsion at something core-violating."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "disgust",
    "label":   "Disgust",
    "valence":   -0.70,
    "arousal":   +0.20,
    "intensity": +0.55,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 14.0,
    "safety":    False,
    "signal_words": ["gross", "disgusting", "yuck", "ew", "revolting",
                     "sick of", "nasty", "repulsive", "vile"],
    "linguistic_markers": ["negative superlatives", "vomit imagery"],
    "physiology": ["wrinkled nose", "tongue protrusion",
                  "back-away motion"],
    "triggers": ["rotten food", "violation of moral norm",
                "offensive taste / smell", "injustice"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "dry",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "yeah — that's revolting.",
        ],
        "do_not": ["joke about it", "force more detail"],
    },
    "transitions_out": ["anger", "contempt", "relief"],
    "notes": "frequent precursor to anger when paired with moral code.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
