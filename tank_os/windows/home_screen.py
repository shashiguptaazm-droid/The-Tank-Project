"""HomeScreen — the main dashboard with camera, AI avatar, map, and status."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget,
)

from tank_os.widgets.ai_avatar import AIAvatar
from tank_os.widgets.camera_widget import CameraWidget
from tank_os.widgets.map_widget import MapWidget
from tank_os.widgets.status_widget import StatusWidget

logger = logging.getLogger("tank_os.windows.home")


class HomeScreen(QWidget):
    """The main dashboard screen — command center with camera, avatar, map, health."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("homeScreen")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Top: Welcome + status summary
        self._welcome = QLabel("🤖 TankOS — Command Center")
        self._welcome.setStyleSheet("""
            font-size: 18px; font-weight: bold;
            padding: 4px 0px; color: #FFFFFF;
        """)
        main_layout.addWidget(self._welcome)

        # Middle: Camera + Avatar + Map grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # Camera feed
        camera_frame = self._make_panel("📷 Camera Feed")
        self._camera = CameraWidget(show_detections=True)
        self._camera.setMinimumSize(320, 220)
        camera_frame.layout().addWidget(self._camera)
        grid.addWidget(camera_frame, 0, 0)

        # AI Avatar
        avatar_frame = self._make_panel("🤗 AI Companion")
        self._avatar = AIAvatar(size=140)
        avatar_frame.layout().addWidget(self._avatar, 0, Qt.AlignCenter)
        grid.addWidget(avatar_frame, 0, 1)

        # Navigation Map
        map_frame = self._make_panel("🗺 Live Map")
        self._map = MapWidget()
        self._map.setMinimumSize(300, 180)
        map_frame.layout().addWidget(self._map)
        grid.addWidget(map_frame, 1, 0)

        # Status
        status_frame = self._make_panel("📊 System Health")
        self._status = StatusWidget()
        status_frame.layout().addWidget(self._status)
        grid.addWidget(status_frame, 1, 1)

        main_layout.addLayout(grid, 1)

        # Quick action buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)
        for text, icon in [
            ("Start Camera", "📷"), ("Run Diagnostics", "🔍"),
            ("Navigate Home", "🏠"), ("Emergency Stop", "⛔"),
        ]:
            btn = self._make_action_btn(icon, text)
            actions.addWidget(btn)
        actions.addStretch()
        main_layout.addLayout(actions)

    def _make_panel(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("homePanel")
        frame.setStyleSheet("""
            #homePanel {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 4px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; color: #888; font-weight: bold;")
        layout.addWidget(title_lbl)
        return frame

    def _make_action_btn(self, icon: str, text: str) -> QLabel:
        label = QLabel(f"{icon} {text}")
        label.setCursor(Qt.PointingHandCursor)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            background: rgba(0,191,255,0.15);
            border: 1px solid rgba(0,191,255,0.3);
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: bold;
        """)
        label.mousePressEvent = lambda e, t=text: self._on_action(t)
        return label

    def _on_action(self, text: str) -> None:
        logger.info("Action: %s", text)
        if "Camera" in text:
            self._camera.start()
        elif "Stop" in text:
            self._camera.stop()

    def on_enter(self) -> None:
        """Called when this screen becomes active."""
        pass

    def on_leave(self) -> None:
        """Called when navigating away from this screen."""
        pass
