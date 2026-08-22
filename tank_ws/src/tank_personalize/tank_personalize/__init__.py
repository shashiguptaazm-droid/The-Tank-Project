"""tank_personalize — make The Tank's onboard AI feel human.

This package gives The Tank a configurable persona, durable user
memory, structured preferences, a composed system-prompt builder,
and a complete FastAPI-backed preferences dashboard on port 8084.
"""
from __future__ import annotations

from .persona import Persona
from .preferences import (
    AudioPrefs,
    MotionPrefs,
    PrivacyPrefs,
    PreferenceStore,
    SECTION_CLASSES,
    SECTION_DEFAULTS,
)

# Legacy alias — early code referenced SECTION_KEYS; preserve it.
SECTION_KEYS = SECTION_CLASSES
from .memory import MemoryStore, UserMemory
from .prompts import build_system_prompt, greeting_line
from .dialogue import (
    ContextSignals,
    acknowledge_fact,
    empathy_prefix,
    farewell,
    missing_name_ask,
)

__all__ = [
    "Persona",
    "AudioPrefs",
    "MotionPrefs",
    "PrivacyPrefs",
    "PreferenceStore",
    "SECTION_CLASSES",
    "SECTION_DEFAULTS",
    "SECTION_KEYS",
    "MemoryStore",
    "UserMemory",
    "build_system_prompt",
    "greeting_line",
    "ContextSignals",
    "acknowledge_fact",
    "empathy_prefix",
    "farewell",
    "missing_name_ask",
]

__version__ = "0.1.0"
