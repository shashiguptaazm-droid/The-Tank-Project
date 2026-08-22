"""Face drawing for the 1.3\" OLED.

Each helper renders a face for a discrete mood using Pillow primitives.
The output is always an L-mode (binary) image sized ``(width, height)``.
The default 128 × 64 is the native SH1106 resolution.

Moods drawn:
    "happy"   — arc smile + curve-up eyebrows
    "sad"     — frown + droopy eyebrows
    "angry"   — sharp scowl + tight brows (alert / distressed)
    "scared"  — wide eyes + small O mouth
    "neutral" — straight mouth + dot-eyes (eyelid hint)

``/emotion/state`` from emotion_node uses ``{happy, sad, alert,
curious, neutral}``; tank_display translates via :data:`MOOD_TO_FACE`
the same way ``eye_lcd_bridge`` translates for the ESP32.
"""
from __future__ import annotations

import math
from typing import Tuple

from PIL import Image, ImageDraw


DEFAULT_W, DEFAULT_H = 128, 64

# /emotion/state mood → faces mood key. Mirrors eye_lcd_bridge mapping
# but adapted for what the OLED can show.
MOOD_TO_FACE = {
    "happy":   "happy",
    "sad":     "sad",
    "alert":   "angry",
    "curious": "neutral",
    "neutral": "neutral",
}


def face_for_mood(mood: str) -> str:
    return MOOD_TO_FACE.get(mood, "neutral")


def _blank(size: Tuple[int, int]) -> Image.Image:
    return Image.new("1", size, 0)


def _eye(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 4) -> None:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=1)


def _mouth(d: ImageDraw.ImageDraw, cx: int, cy: int,
           curve: float = 0.0, width: int = 22,
           points: int = 60) -> None:
    """Draw a mouth centred at (cx, cy). ``curve > 0`` = smile (rises to
    the right at top); ``curve < 0`` = sad (droops)."""
    pts = []
    for i in range(points + 1):
        t = -1.0 + 2.0 * (i / points)
        x = cx + (width // 2) * t
        y = int(cy + curve * (1.0 - t * t) * 6)
        pts.append((x, y))
    d.line(pts, fill=1, width=2)


def _eyebrows(d: ImageDraw.ImageDraw, cx: int, cy: int,
              slope: float = 0.0, width: int = 16) -> None:
    """Centre eyebrow at (cx, cy). ``slope > 0`` = angry outer-up;
    ``slope < 0`` = sad outer-down."""
    dy = int(slope * 4)
    d.line([
        (cx - width // 2, cy + dy),
        (cx + width // 2, cy - dy),
    ], fill=1, width=2)


def _outline(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 28) -> None:
    """Light circle guide around the face — sells the "panel" look."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1, width=1)


def draw_happy(size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)) -> Image.Image:
    img = _blank(size); d = ImageDraw.Draw(img)
    cx, cy = size[0] // 2, size[1] // 2
    _outline(d, cx, cy)
    # eyes
    _eye(d, cx - 18, cy - 8)
    _eye(d, cx + 18, cy - 8)
    # brows curve up (happy)
    _eyebrows(d, cx - 18, cy - 18, slope=-0.4)
    _eyebrows(d, cx + 18, cy - 18, slope= 0.4)
    # smile (curve > 0)
    _mouth(d, cx, cy + 14, curve=1.2, width=28)
    return img


def draw_sad(size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)) -> Image.Image:
    img = _blank(size); d = ImageDraw.Draw(img)
    cx, cy = size[0] // 2, size[1] // 2
    _outline(d, cx, cy)
    _eye(d, cx - 18, cy - 6)
    _eye(d, cx + 18, cy - 6)
    _eyebrows(d, cx - 18, cy - 18, slope= 0.4)
    _eyebrows(d, cx + 18, cy - 18, slope=-0.4)
    _mouth(d, cx, cy + 14, curve=-1.0, width=24)
    return img


def draw_angry(size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)) -> Image.Image:
    img = _blank(size); d = ImageDraw.Draw(img)
    cx, cy = size[0] // 2, size[1] // 2
    _outline(d, cx, cy)
    _eye(d, cx - 18, cy - 8, r=5)
    _eye(d, cx + 18, cy - 8, r=5)
    # brows slope inward-down (angry)
    _eyebrows(d, cx - 18, cy - 18, slope= 1.0)
    _eyebrows(d, cx + 18, cy - 18, slope=-1.0)
    _mouth(d, cx, cy + 14, curve=-0.6, width=22)
    return img


def draw_scared(size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)) -> Image.Image:
    img = _blank(size); d = ImageDraw.Draw(img)
    cx, cy = size[0] // 2, size[1] // 2
    _outline(d, cx, cy)
    _eye(d, cx - 18, cy - 8, r=7)   # wider eyes
    _eye(d, cx + 18, cy - 8, r=7)
    _eyebrows(d, cx - 18, cy - 22, slope=-0.6)  # raised
    _eyebrows(d, cx + 18, cy - 22, slope= 0.6)
    # small O mouth
    d.ellipse((cx - 6, cy + 10, cx + 6, cy + 22), outline=1, width=2)
    return img


def draw_neutral(size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)) -> Image.Image:
    img = _blank(size); d = ImageDraw.Draw(img)
    cx, cy = size[0] // 2, size[1] // 2
    _outline(d, cx, cy)
    _eye(d, cx - 18, cy - 6)
    _eye(d, cx + 18, cy - 6)
    _eyebrows(d, cx - 18, cy - 18, slope=0.0)
    _eyebrows(d, cx + 18, cy - 18, slope=0.0)
    _mouth(d, cx, cy + 14, curve=0.0, width=22)
    return img


DRAWERS = {
    "happy":   draw_happy,
    "sad":     draw_sad,
    "angry":   draw_angry,
    "scared":  draw_scared,
    "neutral": draw_neutral,
}


def render_face(mood: str, size: Tuple[int, int] = (DEFAULT_W, DEFAULT_H)
                ) -> Image.Image:
    """Render the right face for an ``/emotion/state`` mood.

    Unknown moods fall back to neutral."""
    face = face_for_mood(mood)
    drawer = DRAWERS.get(face, draw_neutral)
    return drawer(size)
