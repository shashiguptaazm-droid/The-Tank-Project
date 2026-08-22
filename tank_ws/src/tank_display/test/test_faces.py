"""Tests for tank_display/faces — every supported mood renders a valid
1-bit bitmap + the mapping stays consistent with eye_lcd_bridge."""
from __future__ import annotations

from PIL import Image

from tank_display.faces import (
    DRAWERS,
    MOOD_TO_FACE,
    face_for_mood,
    render_face,
)


def test_render_every_supported_mood():
    for mood in ("happy", "sad", "alert", "curious", "neutral"):
        img = render_face(mood)
        assert isinstance(img, Image.Image)
        assert img.mode == "1"
        assert img.size == (128, 64)


def test_face_mapping_consistent_with_bridge():
    """tank_display.MOOD_TO_FACE must produce only moods that
    DRAWERS recognises (otherwise render_face() would fall through to
    neutral silently)."""
    for src, face_mood in MOOD_TO_FACE.items():
        assert face_mood in DRAWERS, (
            f"mood {src!r} maps to {face_mood!r} but DRAWERS has no entry"
        )
    # And the bridge's values map into the same key set.
    assert set(MOOD_TO_FACE.values()) <= set(DRAWERS.keys())


def test_render_custom_size():
    img = render_face("happy", size=(64, 32))
    assert img.size == (64, 32)
    assert img.mode == "1"


def test_unknown_mood_falls_back_to_neutral():
    """face_for_mood('garbage') must return 'neutral' so render_face
    picks the neutral drawer (no exception)."""
    assert face_for_mood("garbage") == "neutral"
    img = render_face("garbage")
    # Should not crash; same shape as default.
    assert img.size == (128, 64)
