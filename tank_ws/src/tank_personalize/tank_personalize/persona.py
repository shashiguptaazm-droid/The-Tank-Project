"""Persona dataclass + sane defaults + validator + serializer.

A :class:`Persona` describes *how* The Tank's AI presents itself — its
name, tone, response style, voice settings, emoji usage, optional
signature phrases, and the catalogue key for the Piper TTS voice.

The dashboard lets the user overwrite any subset; the validator only
complains, never crashes.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List


# Bounded lengths — STATUS.md design rule 4: clip every line that
# flows into a prompt. Keeping these as constants makes them easy to
# reference from the FastAPI layer too.
NAME_MAX = 40
BACKSTORY_MAX = 1000
SIGNATURE_MAX = 8
PHRASE_MAX = 80
VOICE_ID_MAX = 64

# Piper voice IDs follow `<lang>_<region>-<name>-<quality>`, e.g.
# ``en_US-lessac-medium``. The catalogue lives in
# ``tank_text.voice_manager.VOICE_LIBRARY``; we only validate the
# *format* here so ``tank_personalize`` doesn't import ``tank_text``.
_VOICE_ID_PATTERN = re.compile(
    r"^[a-z]{2}_[A-Z]{2}-[a-z0-9_\-]+-(low|medium|high)$"
)


@dataclass
class Persona:
    """The Tank's self-presentation, configured by the user."""

    name: str = "Tank"
    tone: str = "warm"            # one of TONE_OPTIONS
    response_style: str = "balanced"  # one of STYLE_OPTIONS
    backstory: str = (
        "A helpful assistant companion built into The Tank, a "
        "tracked Raspberry-Jetson robot that explores rooms, "
        "recognises its owner, and chats in plain English."
    )
    voice_rate: float = 1.0      # Piper rate multiplier; 0.5–2.0
    voice_pitch: float = 1.0     # 0.5–2.0
    voice_volume: float = 1.0    # 0.0–1.0
    voice_id: str = "en_US-lessac-medium"   # Piper catalogue key
    emoji_use: str = "subtle"    # one of EMOJI_OPTIONS
    time_zone: str = "UTC"
    signature_phrases: List[str] = field(default_factory=lambda: [
        "How can I help today?",
        "Standing by.",
        "Ready when you are.",
    ])

    # ---------- enumerations ----------
    TONE_OPTIONS = ("warm", "professional", "playful", "dry", "quirky")
    STYLE_OPTIONS = ("concise", "balanced", "detailed", "chatty")
    EMOJI_OPTIONS = ("off", "subtle", "moderate", "lots")

    # ---------- construction ----------
    @classmethod
    def defaults(cls) -> "Persona":
        return cls()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Persona":
        """Build a Persona from a (possibly partial) dict.

        Unknown keys are silently ignored — the user might be sending
        values from a newer schema that we don't understand yet.
        An empty or None dict returns the full defaults.
        """
        if not d:
            return cls.defaults()
        valid_keys = {f.name for f in fields(cls)}
        kwargs: Dict[str, Any] = {
            k: v for k, v in d.items() if k in valid_keys
        }
        return cls(**kwargs)

    # ---------- serialisation ----------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # ---------- validation ----------
    def validate(self) -> List[str]:
        """Return a list of human-readable warnings (empty if fine)."""
        warnings: List[str] = []
        if self.tone not in self.TONE_OPTIONS:
            warnings.append(f"unknown tone {self.tone!r}; expected one of "
                            f"{self.TONE_OPTIONS}")
        if self.response_style not in self.STYLE_OPTIONS:
            warnings.append(f"unknown response_style "
                            f"{self.response_style!r}; expected one of "
                            f"{self.STYLE_OPTIONS}")
        if self.emoji_use not in self.EMOJI_OPTIONS:
            warnings.append(f"unknown emoji_use {self.emoji_use!r}; "
                            f"expected one of {self.EMOJI_OPTIONS}")
        if not isinstance(self.voice_rate, (int, float)) \
                or not (0.5 <= float(self.voice_rate) <= 2.0):
            warnings.append(f"voice_rate should be a number 0.5–2.0; "
                            f"got {self.voice_rate!r}")
        if not isinstance(self.voice_pitch, (int, float)) \
                or not (0.5 <= float(self.voice_pitch) <= 2.0):
            warnings.append(f"voice_pitch should be a number 0.5–2.0; "
                            f"got {self.voice_pitch!r}")
        if not isinstance(self.voice_volume, (int, float)) \
                or not (0.0 <= float(self.voice_volume) <= 1.0):
            warnings.append(f"voice_volume should be a number 0.0–1.0; "
                            f"got {self.voice_volume!r}")
        if not isinstance(self.voice_id, str) \
                or not _VOICE_ID_PATTERN.match(self.voice_id or ""):
            warnings.append(
                f"voice_id should match Piper's "
                f"<lang>_<region>-<name>-<quality> format "
                f"(e.g. en_US-lessac-medium); got {self.voice_id!r}")
        if not isinstance(self.backstory, str):
            warnings.append("backstory must be a string")
        elif len(self.backstory) > BACKSTORY_MAX:
            warnings.append(
                f"backstory truncated to {BACKSTORY_MAX} chars "
                f"(got {len(self.backstory)})")
        if not isinstance(self.signature_phrases, list):
            warnings.append("signature_phrases must be a list of strings")
        else:
            if len(self.signature_phrases) > SIGNATURE_MAX:
                warnings.append(
                    f"signature_phrases truncated to {SIGNATURE_MAX} "
                    f"entries (got {len(self.signature_phrases)})")
            for p in self.signature_phrases:
                if not isinstance(p, str):
                    warnings.append("signature_phrases must be strings")
                    break
        return warnings

    # ---------- ergonomics ----------
    def sanitised(self) -> "Persona":
        """Return a copy with values clipped to safe ranges/limits."""
        clean = Persona.from_dict(self.to_dict())

        def _safe_float(value: Any, lo: float, hi: float,
                        default: float) -> float:
            """Coerce ``value`` to a bounded float. Garbage in → default."""
            try:
                return max(lo, min(hi, float(value)))
            except (TypeError, ValueError):
                return default

        clean.voice_rate = _safe_float(self.voice_rate, 0.5, 2.0, 1.0)
        clean.voice_pitch = _safe_float(self.voice_pitch, 0.5, 2.0, 1.0)
        # Voice-volume: conservative default (0.7) so a malformed POST
        # can't crank Tank to full blast unnoticed.
        clean.voice_volume = _safe_float(self.voice_volume, 0.0, 1.0, 0.7)
        clean.backstory = (self.backstory or "")[:BACKSTORY_MAX]
        # voice_id: format-validated and clipped. Garbage → default so
        # bad input lands the operator on a known voice, not stub silence.
        if (isinstance(self.voice_id, str)
                and _VOICE_ID_PATTERN.match(self.voice_id or "")):
            clean.voice_id = self.voice_id.strip()[:VOICE_ID_MAX]
        else:
            clean.voice_id = "en_US-lessac-medium"
        cleaned_phrases: List[str] = []
        seen = set()
        for p in (self.signature_phrases or [])[:SIGNATURE_MAX]:
            if not isinstance(p, str):
                continue
            trimmed = p.strip()[:PHRASE_MAX]
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            cleaned_phrases.append(trimmed)
        if not cleaned_phrases:
            cleaned_phrases = Persona.defaults().signature_phrases
        clean.signature_phrases = cleaned_phrases
        clean.name = (self.name or "Tank").strip()[:NAME_MAX] or "Tank"
        clean.time_zone = (self.time_zone or "UTC").strip()[:40] or "UTC"
        return clean
