"""Lightweight dialogue patterns that give The Tank a human voice.

These are short, *per-turn* snippets layered on top of the persona
+ memory: prefix empathy, postfix acknowledgements, and farewell
lines. They are deliberately *thin* \u2014 the real coherence comes from
the LLM \u2014 but they ensure even a single-line reply still reads as
human.

The patterns pick their tone from :class:`Persona`:

    * ``warm``         — friendly, soft
    * ``professional`` — measured, helpful
    * ``playful``      — light, casual
    * ``dry``          — concise, no fluff
    * ``quirky``       — small personality flourishes

The :class:`ContextSignals` dataclass describes the *outer* state
the snippet is dropped into: was there an error? has the user been
silent for a while? is the battery low?
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .memory import UserMemory
from .persona import Persona


# --------------------------------------------------------------------------- #
# Context
# --------------------------------------------------------------------------- #

@dataclass
class ContextSignals:
    """Per-turn context that the dialogue patterns key off.

    All fields optional with sane defaults so a caller in a hurry can
    drop a single flag in and still get a sensible prefix.
    """

    has_error: bool = False
    is_short_input: bool = False       # user spoke < 5 words
    seconds_since_user_input: float = 0.0
    battery_low: bool = False
    just_woke: bool = False            # wake word fired minutes ago
    just_estop: bool = False           # safety latch just engaged
    user_input: str = ""               # raw user utterance


VALID_FAREWELL_REASONS = ("idle", "sleep", "estop", "shutdown", "patrol")


# --------------------------------------------------------------------------- #
# Empathy prefix
# --------------------------------------------------------------------------- #

def empathy_prefix(ctx: Optional[ContextSignals],
                   persona: Optional[Persona]) -> str:
    """One-line prefix that warms up a long answer.

    Returns an empty string in the "dry" tone so the LLM doesn't
    accidentally double-up with its own warmth.
    """
    p = persona or Persona.defaults()
    if getattr(p, "tone", None) == "dry":
        return ""
    ctx = ctx or ContextSignals()

    if ctx.just_estop:
        return "Safety first — "
    if ctx.has_error:
        return "Oof — "
    if ctx.battery_low:
        return "Heads-up, battery's low — "
    if p.tone == "playful":
        if ctx.seconds_since_user_input > 12:
            return "Alright, "
        return "Sure — "
    if p.tone == "professional":
        return "Certainly. "
    if p.tone == "warm":
        if ctx.is_short_input:
            return "Of course — "
        if ctx.just_woke:
            return "Welcome back. "
        return "Sure thing — "
    if p.tone == "quirky":
        return "On it. "
    return ""


# --------------------------------------------------------------------------- #
# Farewell line
# --------------------------------------------------------------------------- #

def farewell(persona: Optional[Persona],
             reason: str = "idle") -> str:
    """Short closing line for shutdown / estop / sleep / hand-off.

    Returns a non-empty string regardless of reason so the TTS engine
    always has something to say instead of a bare silence.
    """
    p = persona or Persona.defaults()
    if reason not in VALID_FAREWELL_REASONS:
        reason = "idle"

    base: str
    if p.signature_phrases:
        # The *last* phrase is conventionally the goodbye phrase.
        base = p.signature_phrases[-1]
    else:
        base = "Going quiet for now."

    if reason == "estop":
        return f"{base} Safety first."
    if reason == "shutdown":
        return f"{base} Shutting down."
    if reason == "sleep":
        return f"{base} Sleep tight."
    if reason == "patrol":
        return f"{base} Going on patrol."
    return f"{base} Call if you need me."


# --------------------------------------------------------------------------- #
# Fact acknowledgement
# --------------------------------------------------------------------------- #

def acknowledge_fact(persona: Optional[Persona],
                     fact: str = "") -> str:
    """Sentence the AI uses right after MemoryStore.add_fact.

    We include a clipped copy of the stored fact so the user can
    verify what the AI just remembered.
    """
    p = persona or Persona.defaults()
    clipped = (fact or "").strip()[:120]

    if p.tone == "playful":
        prefix = "Got it — I've tucked that away."
    elif p.tone == "dry":
        prefix = "Noted."
    elif p.tone == "professional":
        prefix = "Acknowledged. I'll keep that in mind."
    elif p.tone == "quirky":
        prefix = "Filed."
    elif p.tone == "warm":
        prefix = "Thanks for sharing — I'll remember that."
    else:
        prefix = "OK, got it."

    if not clipped:
        return prefix
    return f"{prefix} (\u201C{clipped}\u201D)"


# --------------------------------------------------------------------------- #
# Missing-name ask
# --------------------------------------------------------------------------- #

def missing_name_ask(persona: Optional[Persona]) -> str:
    """One-line ask when we don't yet have a remembered name.

    Used by the dashboard and the assistant fallback path to surface
    a single gentle invitation, not a multi-message interrogation.
    """
    p = persona or Persona.defaults()
    if p.tone == "playful":
        return "By the way \u2014 what should I call you?"
    if p.tone == "professional":
        return "May I know what to call you, for future reference?"
    if p.tone == "dry":
        return "Name?"
    if p.tone == "quirky":
        return "And you are\u2026 the human, of course \u2014 but what name should I use for you?"
    return "What would you like me to call you?"


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

def compose_acknowledgements(persona: Optional[Persona],
                              memory: Optional[UserMemory]) -> List[str]:
    """Collect a *small set* of one-liners the LLM can weave in.

    Useful for the dashboard "What might Tank say?" preview. Always
    returns at least one item.
    """
    p = persona or Persona.defaults()
    m = memory or UserMemory()
    lines: List[str] = []
    if m.remembered_name:
        lines.append(f"Address you as '{m.remembered_name}'.")
    if m.custom_facts:
        lines.append(f"Reference up to {len(m.custom_facts)} remembered facts.")
    if m.last_seen_ts:
        lines.append("Track when we last talked.")
    if p.response_style == "concise":
        lines.append("Keep replies to a single sentence unless asked.")
    if p.tone == "warm":
        lines.append("Open with a small moment of warmth when natural.")
    if not lines:
        lines.append("Speak plainly, in the active tone.")
    return lines
