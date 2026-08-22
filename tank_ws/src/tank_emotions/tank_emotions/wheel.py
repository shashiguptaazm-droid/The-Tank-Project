"""tank_emotions.wheel — Plutchik wheel geometry + ASCII renderer.

Each emotion has a unit-vector pole on the wheel:

    joy            = ( 0.50,  0.87)
    trust          = ( 0.87,  0.50)
    fear           = ( 0.87, -0.50)
    surprise       = ( 0.50, -0.87)
    sadness        = (-0.50, -0.87)
    disgust        = (-0.87, -0.50)
    anger          = (-0.87,  0.50)
    anticipation  = (-0.50,  0.87)

``render_ascii()`` draws an N x N grid with intensity rings centred on
the wheel and the eight plutchik poles labelled.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple


Poles: Dict[str, Tuple[float, float]] = {
    "joy":           ( 0.50,  0.87),
    "trust":         ( 0.87,  0.50),
    "fear":          ( 0.87, -0.50),
    "surprise":      ( 0.50, -0.87),
    "sadness":       (-0.50, -0.87),
    "disgust":       (-0.87, -0.50),
    "anger":         (-0.87,  0.50),
    "anticipation":  (-0.50,  0.87),
}


def project(x: float, y: float, w: int, h: int) -> Tuple[int, int]:
    gx = int(round((x + 1.0) / 2.0 * (w - 1)))
    gy = int(round((1.0 - (y + 1.0) / 2.0) * (h - 1)))
    return gx, gy


def render_ascii(size: int = 18,
                 intensities: Dict[str, float] = None) -> List[str]:
    """Render a Plutchik-wheel ASCII grid.

    ``intensities`` is optional ``{name: 0..1}`` for each pole — dots
    are drawn with ``*`` if intensity >= 0.66 and ``o`` otherwise.
    """
    intensities = intensities or {}
    w = h = size
    grid = [[" "] * w for _ in range(h)]
    rings = [0.33, 0.66, 1.00]
    for r in rings:
        pts = []
        for i in range(0, 360, 12):
            rad = math.radians(i)
            x = math.cos(rad) * r
            y = math.sin(rad) * r
            pts.append(project(x, y, w, h))
        for gx, gy in pts:
            if 0 <= gx < w and 0 <= gy < h:
                grid[gy][gx] = "." if r < 1.0 else "-"
    for name, (x, y) in Poles.items():
        gx, gy = project(x, y, w, h)
        if 0 <= gx < w and 0 <= gy < h:
            intensity = intensities.get(name, 0.0)
            grid[gy][gx] = "*" if intensity >= 0.66 else "o"
            if len(name) <= 8 and 0 <= gx - len(name) // 2 < w - len(name):
                for i, ch in enumerate(name):
                    grid[gy][gx - len(name) // 2 + i] = ch
    return ["".join(row) for row in grid]


def grid_to_string(grid: List[str]) -> str:
    header = "+" + "-" * len(grid[0]) + "+"
    return header + "\n" + "\n".join("|" + row + "|" for row in grid) + "\n" + header
