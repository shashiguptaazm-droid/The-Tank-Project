"""Tests for tank_personalize.dialogue."""
from __future__ import annotations

from tank_personalize.dialogue import (
    ContextSignals,
    VALID_FAREWELL_REASONS,
    acknowledge_fact,
    compose_acknowledgements,
    empathy_prefix,
    farewell,
    missing_name_ask,
)
from tank_personalize.memory import UserMemory
from tank_personalize.persona import Persona


def _persona(tone: str) -> Persona:
    p = Persona.defaults()
    p.tone = tone
    return p


def _ctx(**kw) -> ContextSignals:
    return ContextSignals(**kw)


def test_dry_returns_empty_prefix():
    assert empathy_prefix(_ctx(has_error=True), _persona("dry")) == ""


def test_warm_short_input_of_course():
    out = empathy_prefix(_ctx(is_short_input=True), _persona("warm"))
    assert "Of course" in out


def test_playful_long_pause_starts_with_alright():
    out = empathy_prefix(_ctx(seconds_since_user_input=15),
                          _persona("playful"))
    assert out.lower().startswith("alright")


def test_error_triggers_oof():
    out = empathy_prefix(_ctx(has_error=True), _persona("warm"))
    assert "Oof" in out


def test_estop_safety_first():
    out = empathy_prefix(_ctx(just_estop=True), _persona("professional"))
    assert "Safety" in out


def test_farewell_default_uses_signature():
    p = Persona.defaults()
    p.signature_phrases = ["Hello.", "Bye!"]
    out = farewell(p)
    assert "Bye!" in out
    assert "Call if you need me" in out


def test_farewell_estop():
    out = farewell(Persona.defaults(), reason="estop")
    assert "Safety first" in out


def test_farewell_invalid_reason_falls_back_to_idle():
    out = farewell(Persona.defaults(), reason="bogus")
    assert "Call if you need me" in out


def test_farewell_all_reasons_nonempty():
    for r in VALID_FAREWELL_REASONS:
        out = farewell(Persona.defaults(), reason=r)
        assert out and isinstance(out, str)


def test_acknowledge_fact_variants():
    p_play = _persona("playful")
    p_dry = _persona("dry")
    p_pro = _persona("professional")
    p_quirk = _persona("quirky")
    p_warm = _persona("warm")
    fact = "pancakes for breakfast"
    assert "tucked" in acknowledge_fact(p_play, fact)
    assert "Noted" in acknowledge_fact(p_dry, fact)
    assert "Acknowledged" in acknowledge_fact(p_pro, fact)
    assert "Filed" in acknowledge_fact(p_quirk, fact)
    assert "Thanks" in acknowledge_fact(p_warm, fact) or \
           "remember" in acknowledge_fact(p_warm, fact).lower()


def test_acknowledge_fact_handles_missing_fact():
    out = acknowledge_fact(_persona("warm"), "")
    # Empty fact must not produce "(...)"
    assert "(" not in out


def test_missing_name_ask_present_per_tone():
    for tone in Persona.TONE_OPTIONS:
        out = missing_name_ask(_persona(tone))
        assert out and isinstance(out, str)


def test_compose_acknowledgements_with_memory():
    p = Persona.defaults()
    p.response_style = "concise"
    m = UserMemory(remembered_name="Aisha",
                    custom_facts=["x", "y"],
                    last_seen_ts=123.4)
    lines = compose_acknowledgements(p, m)
    assert isinstance(lines, list) and lines
    assert any("Aisha" in s for s in lines)


def test_compose_acknowledgements_empty_memory_still_returns_something():
    lines = compose_acknowledgements(Persona.defaults(), UserMemory())
    assert lines
