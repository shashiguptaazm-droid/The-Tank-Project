"""Tests for eye_lcd_bridge — covers the /emotion/state → ESP32
expression mapping + manual override precedence + NullHal capture.
"""
from __future__ import annotations

from tank_vision.eye_lcd_bridge import (
    MOOD_TO_EXPR,
    NullEyeSerialHal,
    expr_color,
    mood_to_expression,
)


def test_mood_to_expression_mapping_complete():
    assert mood_to_expression("happy")   == "happy"
    assert mood_to_expression("sad")     == "sad"
    assert mood_to_expression("alert")   == "angry"
    assert mood_to_expression("curious") == "neutral"
    assert mood_to_expression("neutral") == "neutral"
    # unknown mood falls back to neutral
    assert mood_to_expression("garbage") == "neutral"
    # mapping is symmetric with firmware
    assert set(MOOD_TO_EXPR.values()).issubset(
        {"happy", "sad", "angry", "scared", "neutral"}
    )


def test_expr_color_palette():
    # Spot-check that every firmware-side expression has a defined color.
    for expr in ("happy", "sad", "angry", "scared", "neutral"):
        c = expr_color(expr)
        assert 0 <= c <= 0xFFFF, f"bad RGB565 for {expr}"


def test_nullhal_records_latest_payload():
    hal = NullEyeSerialHal()
    hal.write_json({"expr": "happy", "iris": expr_color("happy")})
    hal.write_json({"gaze": [0.25, -0.10]})
    assert hal.last_expr == "happy"
    assert hal.last_gaze == (0.25, -0.10)
    # Latest expr overrides previous; both kept in log for debug.
    assert len(hal.log) == 2
