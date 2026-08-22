"""tank_emotions.dialogue — per-tone empathy prefixes and safe fallbacks.

Composes with :mod:`tank_personalize.dialogue` from the existing
``tank_personalize`` package so the actual LLM prompt keeps a single
source of truth for tone.  We deliberately keep the surface small:

* ``empathy_prefix(plan)``     -  "of course.", "alright.", empty, …
* ``escalation_floor(plan)``   -  "do you want me to flag someone?"
* ``fallback_reply(plan)``     -  short reply when we have no other context

Prefer the centralised helpers over hard-coding phrases in the
emotion modules — the tone dictionary is the single editable surface.
"""
from __future__ import annotations

from typing import Optional

from .companion import CompanionPlan


EMPATHY_PREFIX = {
    "warm":         "of course — ",
    "grounding":    "let's slow down. ",
    "quiet":        "I'm here. ",
    "playful":      "haha — alright, ",
    "dry":          "",
    "professional": "noted. ",
    "empathic":     "yeah — ",
}

ESCALATION_FLOOR = {
    # always include when safety flag is raised
    "ESCALATE_FLOOR": (
        "if this feels bigger than a chat — I can ping a trusted contact. "
        "want me to?"
    ),
}


def empathy_prefix(plan: CompanionPlan) -> str:
    return EMPATHY_PREFIX.get(plan.tone, "")


def safe_floor_for(plan: CompanionPlan) -> Optional[str]:
    if plan.safety:
        return ESCALATION_FLOOR["ESCALATE_FLOOR"]
    return None


def fallback_reply(text: str, plan: CompanionPlan) -> str:
    """Compose a safe short reply when no other context is available."""
    prefix = empathy_prefix(plan)
    short = (text or "").strip() or "I hear you."
    reply = f"{prefix}I hear you — {short}" if prefix else f"I hear you — {short}"
    floor = safe_floor_for(plan)
    if floor:
        reply = reply.rstrip(". ") + ". " + floor
    return reply
