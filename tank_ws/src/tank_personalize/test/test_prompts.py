"""Tests for tank_personalize.prompts."""
from __future__ import annotations

from tank_personalize.memory import UserMemory
from tank_personalize.persona import Persona
from tank_personalize.prompts import (
    MAX_LEN,
    STYLE_GUIDANCE,
    build_system_prompt,
    greeting_line,
)


def test_default_compose_returns_under_cap():
    p = build_system_prompt(Persona.defaults(), UserMemory(),
                             extra_notes="room=kitchen")
    assert len(p) <= MAX_LEN
    assert "PERSONA" in p
    assert "GREETINGS" in p
    assert "HOUSE RULES" in p
    assert "CALLER NOTES" in p


def test_prompt_contains_persona_name_and_tone():
    p = Persona.defaults()
    p.name = "Sparky"
    p.tone = "playful"
    out = build_system_prompt(p, UserMemory())
    assert "Sparky" in out
    assert "playful" in out


def test_prompt_contains_remembered_name():
    m = UserMemory()
    m.remembered_name = "Aisha"
    out = build_system_prompt(Persona.defaults(), m)
    assert "'Aisha'" in out


def test_prompt_contains_recent_facts():
    m = UserMemory()
    m.custom_facts = ["loves dark mode", "tea over coffee"]
    out = build_system_prompt(Persona.defaults(), m)
    assert "dark mode" in out
    assert "tea" in out


def test_prompt_caps_under_max_for_huge_history():
    m = UserMemory()
    m.custom_facts = ["x" * 600 for _ in range(40)]
    p = build_system_prompt(Persona.defaults(), m, max_len=2000)
    assert len(p) <= 2000


def test_extra_notes_is_clipped():
    long = "y" * 5000
    out = build_system_prompt(Persona.defaults(), UserMemory(),
                               extra_notes=long)
    assert len(out) <= MAX_LEN


def test_style_guidance_table_used():
    for style, hint in STYLE_GUIDANCE.items():
        p = Persona.defaults()
        p.response_style = style
        assert hint in build_system_prompt(p, UserMemory())


def test_greeting_uses_name():
    p = Persona.defaults()
    p.name = "TankBot"
    g = greeting_line(p, UserMemory())
    assert g.startswith("TankBot")
    assert "Ready" in g or "Standing by" in g or "How can I help" in g


def test_greeting_with_name_mentions_user():
    p = Persona.defaults()
    m = UserMemory(remembered_name="Aisha")
    g = greeting_line(p, m)
    assert "Aisha" in g
