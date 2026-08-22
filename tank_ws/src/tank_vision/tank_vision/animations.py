"""JSON frame-list animation format for The Tank Project's eyes + future
HDMI screens.

Designed so the *same* animation JSON can drive:

* the **ESP32-S3 GC9A101 240×240 round LCDs** (via :doc:`eye_lcd_bridge`),
* a **future JS browser canvas** (HTML5 addon, optional wall-display),
* a **stub renderer** used by tests + benches (no hardware).

Wire shape on ``/eye/animation_play`` (JSON dumped to std_msgs/String)::

    {
      "name": "blink",
      "fps": 12,
      "loop": false,
      "description": "Round eye blink (200 ms close + 120 ms open).",
      "frames": [
        {"cmd": "fill",   "args": {"color": "#000000"}},
        {"cmd": "circle", "args": {"x": 120, "y": 120, "r": 90, "color": "#FFFFFF"}},
        {"cmd": "delay",  "args": {"ms": 200}},
        {"cmd": "reset",  "args": {}}
      ]
    }

Frame command vocabulary (deliberately small so both the firmware and a
canvas renderer can keep up):

========  ===================================  ===========================
cmd       args shape                           effect
========  ===================================  ===========================
fill      ``{color}``                          whole-screen fill
circle    ``{x, y, r, color}``                 filled disk
ring      ``{x, y, r, thickness, color}``      hollow annulus
arc       ``{x, y, r, start_deg, end_deg,
            thickness, color}``                 partial ring
text      ``{x, y, size, color, text}``        1-line text
delay     ``{ms}``                             wait; advances nothing
bitmap    ``{x, y, w, h, file}``               draw raw pixel buffer
video     ``{file, fps}``                      play an SD-card mjpeg
            (firmware-only — JS path falls through)
reset     ``{}``                               clear to black
========  ===================================  ===========================

The vocabulary is the *intersection* of what an Arduino-GFX draw loop
and an HTML5 canvas function call can both express without
per-platform fallthroughs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


EYE_W = 240
EYE_H = 240
CENTER_X = 120
CENTER_Y = 120


@dataclass
class FrameCommand:
    cmd: str
    args: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"cmd": self.cmd, "args": dict(self.args)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FrameCommand":
        return cls(
            cmd=str(d.get("cmd", "")).strip().lower(),
            args=dict(d.get("args") or {}),
        )


@dataclass
class Animation:
    name: str
    fps: int = 12
    loop: bool = False
    frames: List[FrameCommand] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":        self.name,
            "fps":         self.fps,
            "loop":        self.loop,
            "frames":      [f.to_dict() for f in self.frames],
            "description": self.description,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Animation":
        return cls(
            name=str(d.get("name", "")),
            fps=int(d.get("fps", 12)),
            loop=bool(d.get("loop", False)),
            frames=[FrameCommand.from_dict(f) for f in d.get("frames", [])],
            description=str(d.get("description", "")),
        )

    @classmethod
    def from_json(cls, s: str) -> "Animation":
        return cls.from_dict(json.loads(s))


# ────────────────────────────────────────────────────────────────────────────
# Built-in library
# ────────────────────────────────────────────────────────────────────────────

_BUILTIN_ANIMATIONS: Dict[str, Animation] = {}


def _register(anim: Animation) -> None:
    _BUILTIN_ANIMATIONS[anim.name] = anim


def list_animations() -> List[str]:
    return sorted(_BUILTIN_ANIMATIONS)


def get_animation(name: str) -> Optional[Animation]:
    return _BUILTIN_ANIMATIONS.get(name)


def get_animation_json(name: str) -> Optional[str]:
    a = _BUILTIN_ANIMATIONS.get(name)
    return a.to_json() if a else None


_register(Animation(
    name="blink",
    fps=12, loop=False, description="Round eye blink (200 ms close + 120 ms open).",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 90, "color": "#FFFFFF"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 18, "color": "#000000"}),
        FrameCommand("delay",  {"ms": 200}),
        FrameCommand("ring",   {"x": 120, "y": 120, "r": 90,
                                 "thickness": 8, "color": "#888888"}),
        FrameCommand("delay",  {"ms": 120}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="wink_left",
    fps=12, loop=False, description="One-eye wink (top closure).",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 90, "color": "#FFFFFF"}),
        FrameCommand("ring",   {"x": 120, "y": 120, "r": 90,
                                 "thickness": 10, "color": "#000000"}),
        FrameCommand("delay",  {"ms": 300}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="smile",
    fps=12, loop=False, description="Smiling face with amber iris.",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 100, "r": 80, "color": "#FFFFFF"}),
        FrameCommand("arc",    {"x": 120, "y": 130, "r": 60,
                                 "start_deg": 30, "end_deg": 150,
                                 "thickness": 8, "color": "#FF8800"}),
        FrameCommand("delay",  {"ms": 1000}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="sad",
    fps=12, loop=False, description="Sad face — downward arc mouth.",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 80, "color": "#2244FF"}),
        FrameCommand("arc",    {"x": 120, "y": 160, "r": 60,
                                 "start_deg": 210, "end_deg": 330,
                                 "thickness": 8, "color": "#FFFFFF"}),
        FrameCommand("delay",  {"ms": 1000}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="look_left",
    fps=24, loop=False, description="Brief leftward gaze.",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 90, "color": "#FFFFFF"}),
        FrameCommand("circle", {"x": 80,  "y": 120, "r": 18, "color": "#000000"}),
        FrameCommand("delay",  {"ms": 400}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="look_right",
    fps=24, loop=False, description="Brief rightward gaze.",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("circle", {"x": 120, "y": 120, "r": 90, "color": "#FFFFFF"}),
        FrameCommand("circle", {"x": 160, "y": 120, "r": 18, "color": "#000000"}),
        FrameCommand("delay",  {"ms": 400}),
        FrameCommand("reset",  {}),
    ],
))

_register(Animation(
    name="video_play_rickroll",
    fps=12, loop=False, description="Title card → SD-card rickroll.mjpeg.",
    frames=[
        FrameCommand("fill",   {"color": "#000000"}),
        FrameCommand("text",   {"x": 30, "y": 80, "size": 4,
                                 "color": "#FF66AA", "text": "NEVER GONNA"}),
        FrameCommand("text",   {"x": 30, "y": 130, "size": 4,
                                 "color": "#FF66AA", "text": "GIVE YOU UP"}),
        FrameCommand("delay",  {"ms": 800}),
        FrameCommand("video",  {"file": "rickroll.mjpeg", "fps": 12}),
    ],
))


__all__ = [
    "FrameCommand", "Animation",
    "EYE_W", "EYE_H", "CENTER_X", "CENTER_Y",
    "list_animations", "get_animation", "get_animation_json",
]
