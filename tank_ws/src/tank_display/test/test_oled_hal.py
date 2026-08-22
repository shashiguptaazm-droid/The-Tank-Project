"""Tests for tank_display NullOledHal — copy-on-write, frame log, getdata-friendly."""
from __future__ import annotations

from PIL import Image

from tank_display.faces import render_face
from tank_display.oled_hal import NullOledHal


def test_nullhal_records_every_frame():
    hal = NullOledHal(width=128, height=64)
    img = render_face("happy", size=(128, 64))
    hal.display(img, mood="happy")
    assert len(hal.frames) == 1
    assert hal.last_frame["mood"] == "happy"
    assert hal.last_frame["image"].size == (128, 64)
    # mutate original; snapshot must NOT change (we copy on display)
    img.paste(0, (0, 0, 128, 64))  # blank out
    # Use numpy-free count (getdata() is deprecated in Pillow 10).
    pixel_count = sum(1 for px in hal.last_frame["image"].getdata() if px)
    assert pixel_count > 0, "snapshot should still have lit pixels"


def test_nullhal_sequence_keeps_all_frames():
    hal = NullOledHal()
    for mood in ("happy", "sad", "neutral", "angry", "neutral"):
        hal.display(render_face(mood), mood=mood)
    assert [f["mood"] for f in hal.frames] == \
        ["happy", "sad", "neutral", "angry", "neutral"]
    # Last frame is the latest mood.
    assert hal.last_frame["mood"] == "neutral"


def test_nullhal_frames_bounded_for_long_runs():
    """NullHal.frames must be a deque(maxlen=64) so long-running live
    nodes don't OOM. Push 80 frames; only the last 64 should remain."""
    hal = NullOledHal()
    for i in range(80):
        hal.display(render_face("neutral"), mood=f"mood_{i}")
    assert len(hal.frames) == 64
    # Oldest remaining frame should be the 16th (we dropped 0..15).
    assert hal.frames[0]["mood"] == "mood_16"
    assert hal.frames[-1]["mood"] == "mood_79"
