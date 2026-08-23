"""TvLauncherScreen — 📺 TV Mode (GUI blueprint).

A 10-foot launcher — deliberately *different* from the robot dashboard.
Opens the UNO Q TV kiosk (cloud-stack :8200) and the TankOS robot screens
from one big-button grid. Supports keyboard / mouse; the physical remote
and gamepad arrive via the ADB remote / future input layer.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.tv")


class _TvTile(QFrame):
    """A big 10-foot launcher tile."""

    def __init__(self, icon: str, label: str, target: str,
                 on_click, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(180, 120)
        self.setStyleSheet("""
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12); border-radius: 16px;
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(6)
        ic = QLabel(icon)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("font-size: 34px; background: transparent;")
        lay.addWidget(ic, 1)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;"
                          " background: transparent;")
        lay.addWidget(lbl)

        self._target = target
        self._on_click = on_click

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._on_click:
            self._on_click(self._target)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet("""
            background: rgba(0,191,255,0.15);
            border: 2px solid rgba(0,191,255,0.6); border-radius: 16px;
        """)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet("""
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.12); border-radius: 16px;
        """)
        super().leaveEvent(event)


class TvLauncherScreen(QWidget):
    """10-foot TV launcher."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._build_ui()

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(18)

        title = QLabel("THE TANK")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 40px; font-weight: bold; color: #FFF; letter-spacing: 8px;
        """)
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(16)
        tiles = [
            ("▶", "ROBOT", "drive"), ("📺", "MEDIA", "tv-media"), ("🎮", "GAMES", "tv-games"),
            ("📷", "CAMERA", "camera"), ("🧠", "AI", "brain"), ("⚙", "SETTINGS", "settings"),
            ("📡", "NETWORK", "network"), ("🔧", "SYSTEM", "diagnostics"),
        ]
        for i, (icon, label, target) in enumerate(tiles):
            tile = _TvTile(icon, label, target, self._on_tile)
            grid.addWidget(tile, i // 4, i % 4)
        layout.addLayout(grid, 1)

        hint = QLabel("remote · gamepad · keyboard · mouse · touchscreen")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 12px; color: #667;")
        layout.addWidget(hint)

    # ------------------------------------------------------------ logic
    def _on_tile(self, target: str) -> None:
        if target.startswith("tv-"):
            # Media / games → open the UNO Q TV kiosk in the browser
            self._launch_kiosk()
            return
        # Robot-mode screens navigate via the shell
        self._bus.emit(Event("navigate", {"screen": target}, source="tv_launcher"))

    def _launch_kiosk(self) -> None:
        try:
            subprocess.Popen(
                ["chromium", "--no-sandbox", "--kiosk",
                 "http://192.168.31.72:8200"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:                                    # noqa: BLE001
            logger.warning("could not launch kiosk: %s", exc)

    def on_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass
