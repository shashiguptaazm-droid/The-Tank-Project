"""
TankOS Theme Engine — dark/light/custom themes with accent colours, fonts, wallpapers.

Themes are JSON-defined in ``tank_os/themes/`` and loaded at startup.
The engine provides a :class:`Theme` dataclass, dynamic switching, and
CSS generation for PySide6 widgets.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.theme")

THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"


@dataclass
class Theme:
    """A complete theme definition."""
    name: str
    label: str = ""
    dark: bool = True
    accent_color: str = "#00BFFF"
    background_primary: str = "#1A1A2E"
    background_secondary: str = "#16213E"
    background_tertiary: str = "#0F3460"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0B0B0"
    text_accent: str = "#00BFFF"
    border_color: str = "#2A2A4A"
    success_color: str = "#00E676"
    warning_color: str = "#FFC107"
    error_color: str = "#FF5252"
    info_color: str = "#448AFF"
    surface_color: str = "#222244"
    overlay_color: str = "#00000080"
    font_family: str = "sans-serif"
    font_size_base: int = 14
    corner_radius: int = 8
    blur_radius: int = 10
    shadow_opacity: float = 0.3
    wallpaper: str = ""
    icon_set: str = "default"
    custom_css: str = ""

    # Animation presets
    transition_duration_ms: int = 200
    animation_curve: str = "ease-out"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "dark": self.dark,
            "accent_color": self.accent_color,
            "background_primary": self.background_primary,
            "background_secondary": self.background_secondary,
            "background_tertiary": self.background_tertiary,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "text_accent": self.text_accent,
            "border_color": self.border_color,
            "success_color": self.success_color,
            "warning_color": self.warning_color,
            "error_color": self.error_color,
            "info_color": self.info_color,
            "surface_color": self.surface_color,
            "overlay_color": self.overlay_color,
            "font_family": self.font_family,
            "font_size_base": self.font_size_base,
            "corner_radius": self.corner_radius,
            "blur_radius": self.blur_radius,
            "shadow_opacity": self.shadow_opacity,
            "wallpaper": self.wallpaper,
            "icon_set": self.icon_set,
            "custom_css": self.custom_css,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Theme":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def css(self, selector: str = "") -> str:
        """Generate a CSS string for a given widget selector."""
        bg = self.background_primary
        fg = self.text_primary
        accent = self.accent_color
        return f"""
{selector} {{
    background-color: {bg};
    color: {fg};
    font-family: {self.font_family};
    font-size: {self.font_size_base}px;
}}
{selector} QPushButton {{
    background-color: {accent};
    color: {fg};
    border-radius: {self.corner_radius}px;
    padding: 8px 16px;
}}
{selector} QLabel {{
    color: {fg};
}}
"""


class ThemeEngine:
    """Singleton that manages theme loading, switching, and CSS generation."""

    _instance: Optional["ThemeEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ThemeEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._themes: Dict[str, Theme] = {}
                cls._instance._current: Optional[Theme] = None
                cls._instance._bus = EventBus()
            return cls._instance

    def initialize(self) -> None:
        """Load built-in themes from ``themes/`` directory."""
        self._register_builtin()
        self._load_from_disk()
        self._current = self._themes.get("dark", list(self._themes.values())[0])
        self._bus.emit(Event("theme_initialized", {
            "theme": self._current.name,
            "count": len(self._themes),
        }, source="theme_engine"))

    def _register_builtin(self) -> None:
        """Register the two built-in themes."""
        self._themes["dark"] = Theme(
            name="dark", label="Dark Mode", dark=True,
            background_primary="#0D0D1A",
            background_secondary="#1A1A2E",
            background_tertiary="#16213E",
            text_primary="#EAEAEA",
            text_secondary="#9E9E9E",
            text_accent="#00BFFF",
            border_color="#2A2A4A",
            surface_color="#1E1E3A",
            accent_color="#00BFFF",
        )
        self._themes["light"] = Theme(
            name="light", label="Light Mode", dark=False,
            background_primary="#F5F5FA",
            background_secondary="#FFFFFF",
            background_tertiary="#E8E8F0",
            text_primary="#1A1A2E",
            text_secondary="#666680",
            text_accent="#0066CC",
            border_color="#D0D0E0",
            surface_color="#FFFFFF",
            accent_color="#0066CC",
        )

    def _load_from_disk(self) -> None:
        """Load user-installed themes from JSON files."""
        if not THEMES_DIR.exists():
            return
        for f in sorted(THEMES_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                theme = Theme.from_dict(data)
                self._themes[theme.name] = theme
                logger.info("Loaded theme: %s", theme.name)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to load theme %s: %s", f.name, exc)

    def set_theme(self, name: str) -> bool:
        """Switch to a theme by name. Emits ``theme_changed``."""
        theme = self._themes.get(name)
        if theme is None:
            logger.warning("Theme %r not found", name)
            return False
        self._current = theme
        self._bus.emit(Event("theme_changed", {
            "name": name,
            "theme": theme.to_dict(),
        }, source="theme_engine"))
        logger.info("Switched to theme: %s", name)
        return True

    @property
    def current(self) -> Theme:
        if self._current is None:
            self.initialize()
        return self._current or self._themes["dark"]

    def get(self, name: str) -> Optional[Theme]:
        return self._themes.get(name)

    def list(self) -> List[Theme]:
        return list(self._themes.values())

    def names(self) -> List[str]:
        return sorted(self._themes.keys())

    def apply_to(self, widget: Any) -> None:
        """Apply the current theme to a Qt widget via setStyleSheet."""
        theme = self.current
        try:
            stylesheet = f"""
QWidget {{
    background-color: {theme.background_primary};
    color: {theme.text_primary};
    font-family: {theme.font_family};
    font-size: {theme.font_size_base}px;
}}
QPushButton {{
    background-color: {theme.accent_color};
    color: {theme.text_primary};
    border: none;
    border-radius: {theme.corner_radius}px;
    padding: 8px 16px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {self._lighten(theme.accent_color, 0.2)};
}}
QPushButton:pressed {{
    background-color: {self._darken(theme.accent_color, 0.2)};
}}
QLabel {{
    color: {theme.text_primary};
}}
QLineEdit {{
    background-color: {theme.background_secondary};
    color: {theme.text_primary};
    border: 1px solid {theme.border_color};
    border-radius: {theme.corner_radius}px;
    padding: 6px;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {theme.background_tertiary};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {theme.accent_color};
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}
QScrollBar:vertical {{
    background: {theme.background_secondary};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {theme.accent_color};
    border-radius: 4px;
    min-height: 30px;
}}
"""
            widget.setStyleSheet(stylesheet)
        except Exception as exc:
            logger.warning("Could not apply theme: %s", exc)

    @staticmethod
    def _lighten(hex_color: str, factor: float) -> str:
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        try:
            hex_color = hex_color.lstrip("#")
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = max(0, int(r - r * factor))
            g = max(0, int(g - g * factor))
            b = max(0, int(b - b * factor))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color
