"""Anger — block / fight response; goal-frustration."""
from __future__ import annotations

DESCRIPTOR = {
    "name":    "anger",
    "label":   "Anger",
    "valence":   -0.70,
    "arousal":   +0.80,
    "intensity": +0.75,
    "taxonomy": [
        {"framework": "plutchik", "rank": "primary"},
        {"framework": "ekman",    "rank": "basic"},
    ],
    "decay_s": 22.0,
    "safety":    True,
    "signal_words": ["angry", "furious", "rage", "pissed", "livid",
                     "mad", "hate", "fed up", "irritated",
                     "outraged", "boiling"],
    "linguistic_markers": ["exclamation", "profanity", "ranking words"],
    "physiology": ["clenched jaw", "raised voice", "flushed face"],
    "triggers": ["blocked goal", "injustice", "violation of boundary"],
    "companion_response": {
        "stance":     "mirror",
        "tone":        "grounding",
        "lengthen":    False,
        "mirror_level":"moderate",
        "phrases": [
            "that sounds infuriating — what's the goal?",
        ],
        "do_not": ["match the anger", "moralise", "instantly apologise"],
    },
    "transitions_out": ["disgust", "contempt", "relief",
                        "sadness", "shame"],
    "notes": "Voice should stay slow, low volume — model de-escalation.",
}


def describe() -> dict:
    return dict(DESCRIPTOR)


def companion_phrase() -> str:
    return DESCRIPTOR["companion_response"]["phrases"][0]


def is_signal_in_text(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in DESCRIPTOR["signal_words"])
