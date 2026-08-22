"""Tests for tank_personalize.persona."""
from __future__ import annotations

import pytest

from tank_personalize.persona import Persona


def test_defaults_roundtrip():
    p = Persona.defaults()
    d = p.to_dict()
    assert isinstance(d["name"], str) and d["name"]
    assert d["tone"] in Persona.TONE_OPTIONS
    assert d["response_style"] in Persona.STYLE_OPTIONS
    assert d["emoji_use"] in Persona.EMOJI_OPTIONS
    assert isinstance(d["signature_phrases"], list)
    assert d["signature_phrases"], "default phrases must not be empty"
    rebuilt = Persona.from_dict(d)
    assert rebuilt.to_dict() == d


def test_from_dict_tolerates_unknown_keys():
    payload = {"name": "Sparky", "future_field": ["x", "y"],
               "another": 42, "tone": "quirky"}
    p = Persona.from_dict(payload)
    assert p.name == "Sparky"
    assert p.tone == "quirky"
    # Unknown fields should NOT appear on the dataclass.
    assert not hasattr(p, "future_field") or getattr(p, "future_field", None) is None


def test_from_dict_empty_returns_defaults():
    p = Persona.from_dict(None)
    assert p.name == "Tank"
    p2 = Persona.from_dict({})
    assert p2.tone == "warm"


def test_validate_rejects_bad_values():
    p = Persona()
    p.tone = "snarky"
    p.response_style = "terse"
    p.voice_rate = 3.0
    p.voice_pitch = 0.0
    msgs = p.validate()
    # Expect at least 4 warnings.
    joined = " ".join(msgs).lower()
    assert "tone" in joined
    assert "response_style" in joined or "style" in joined
    assert "voice_rate" in joined
    assert "voice_pitch" in joined


def test_sanitised_clamps():
    p = Persona()
    p.voice_rate = 99.0
    p.voice_volume = -0.5
    p.voice_pitch = "high"  # type: ignore[assignment]
    p.signature_phrases = ["x" * 1000, "", 42, "good line"]  # type: ignore[list-item]
    s = p.sanitised()
    assert 0.5 <= s.voice_rate <= 2.0
    assert 0.0 <= s.voice_volume <= 1.0
    # signature_phrases cleaned to <=8 strings, each <=80 chars.
    assert 1 <= len(s.signature_phrases) <= 8
    assert all(isinstance(x, str) and x.strip() for x in s.signature_phrases)
    for phrase in s.signature_phrases:
        assert len(phrase) <= 80


def test_sanitised_truncates_backstory():
    p = Persona()
    p.backstory = "x" * 5000
    s = p.sanitised()
    assert len(s.backstory) <= 1000


def test_sanitised_strips_name():
    p = Persona()
    p.name = "   "  # whitespace-only
    s = p.sanitised()
    assert s.name == "Tank"


def test_validate_clean_returns_empty_list():
    p = Persona.defaults()
    assert p.validate() == []
