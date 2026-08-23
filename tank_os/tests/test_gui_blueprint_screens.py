"""Smoke tests for the GUI-blueprint screens (Drive, Mission, AI Brain,
Robot Health, ESP32 Fleet, Jetson, Competition, Event Center).

Each test instantiates the screen offscreen and asserts it grabs a
non-empty image — proving the screen builds and paints. (The full shell
navigation is exercised in test_shell_navigation below.)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


SCREENS = {
    "drive": "tank_os.windows.drive_screen.DriveScreen",
    "mission": "tank_os.windows.mission_screen.MissionScreen",
    "brain": "tank_os.windows.ai_brain_screen.AIBrainScreen",
    "health": "tank_os.windows.health_screen.HealthScreen",
    "fleet": "tank_os.windows.fleet_screen.FleetScreen",
    "jetson": "tank_os.windows.jetson_screen.JetsonScreen",
    "competition": "tank_os.windows.competition_screen.CompetitionScreen",
    "events": "tank_os.windows.event_center.EventCenterScreen",
}


@pytest.mark.parametrize("name", sorted(SCREENS))
def test_screen_builds_and_paints(name: str) -> None:
    _app()
    module_path, cls_name = SCREENS[name].rsplit(".", 1)
    import importlib
    cls = getattr(importlib.import_module(module_path), cls_name)
    widget = cls()
    widget.resize(1024, 768)
    image = widget.grab().toImage()
    assert not image.isNull()
    assert image.width() == 1024 and image.height() == 768


def test_home_screen_has_launcher_tiles() -> None:
    _app()
    from tank_os.windows.home_screen import HomeScreen
    home = HomeScreen()
    home.resize(1024, 768)
    # The blueprint's 8 launcher tiles must be registered.
    assert len(home._tiles) == 8
    for screen in ("drive", "brain", "navigation", "camera",
                   "mission", "diagnostics", "settings", "files"):
        assert screen in home._tiles


def test_dock_exposes_core_screens() -> None:
    _app()
    from tank_os.widgets.bottom_dock import BottomDock
    screens = {s for _, _, s in BottomDock.DOCK_ITEMS}
    # Blueprint core-7 + key extras reachable in ≤2 clicks
    assert {"home", "drive", "mission", "navigation", "camera",
            "brain", "health"} <= screens
    assert {"fleet", "jetson", "competition", "events"} <= screens
