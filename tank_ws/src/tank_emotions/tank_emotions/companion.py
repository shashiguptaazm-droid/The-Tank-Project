"""tank_emotions.companion — how the AI should respond per emotion.

Each emotion descriptor declares ``companion_response``::

    {
        "stance":     "mirror" | "ground" | "hold-space" | "share"
                    | "redirect-joy" | "escalate" | "neutral",
        "tone":        "warm" | "dry" | "playful" | "quiet"
                     | "professional" | "grounding" | "empathic",
        "lengthen":    bool,  # speak longer to make space
        "mirror_level": "light"|"moderate"|"deep",
        "phrases": ["..."],
        "do_not": ["..."],
    }

This module exposes ``plan()`` returning a typed ``CompanionPlan``.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import List, Optional

from .core import Emotion


DEFAULT_STANCES = {
    # Map stances -> default tone if the descriptor doesn't override.
    "mirror":       "empathic",
    "ground":       "grounding",
    "hold-space":   "quiet",
    "share":        "warm",
    "redirect-joy": "playful",
    "escalate":     "warm",
    "neutral":      "professional",
}


@dataclass
class CompanionPlan:
    emotion:    str
    stance:     str
    tone:       str
    lengthen:   bool
    mirror_level: str
    phrases:    List[str]
    do_not:     List[str]
    safety:     bool

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def plan(emo: Emotion) -> CompanionPlan:
    cr = emo.companion_response or {}
    stance = cr.get("stance") or (
        "escalate" if emo.safety
        else ("share" if emo.valence > 0.4 else "hold-space")
    )
    tone = cr.get("tone") or DEFAULT_STANCES.get(stance, "warm")
    return CompanionPlan(
        emotion=emo.name,
        stance=stance,
        tone=tone,
        lengthen=bool(cr.get("lengthen", False)),
        mirror_level=cr.get("mirror_level", "moderate"),
        phrases=list(cr.get("phrases", [])),
        do_not=list(cr.get("do_not", [])),
        safety=emo.safety,
    )


def instruction_text(plan: CompanionPlan) -> str:
    """Render a compact plan as a single line for logs / dashboards."""
    base = f"[{plan.emotion}] stance={plan.stance} tone={plan.tone}"
    if plan.lengthen:
        base += " lengthen=YES"
    if plan.safety:
        base += " SAFETY"
    return base
