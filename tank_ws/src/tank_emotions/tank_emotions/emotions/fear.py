"""Fear — anticipation of threat; alarm response."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "fear",
    "label":   "Fear",
    "valence":   -0.65,
    "arousal":   +0.75,
    "intensity": +0.65,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 18.0,
    "safety":    True,    # may need escalation if intense
    "signal_words": ["afraid", "scared", "worried", "anxious", "panic",
                     "terrified", "frightened", "spooked",
                     "dreading", "scary"],
    "linguistic_markers": ["negative intensifier", "ellipsis"],
    "physiology": ["rapid breathing", "cold hands", "tight jaw",
                   "tunnel vision"],
    "triggers": ["threat", "uncertainty", "loss of control",
                "novel loud noise"],
    "companion_response": {
        "stance":     "ground",
        "tone":        "grounding",
        "lengthen":    True,
        "mirror_level":"moderate",
        "phrases": [
            "take your time — there's no rush.",
            "breathe with me — in for four, out for four.",
        ],
        "do_not": ["tease", "push", "minimise"],
    },
    "transitions_out": ["relief", "anticipation", "anger", "sadness"],
    "notes": "If safety module raises 'panic' or 'crisis'; escalate.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][1]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
