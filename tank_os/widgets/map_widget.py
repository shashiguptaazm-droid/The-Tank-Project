"""MapWidget — navigation map display with robot position and waypoints."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from tank_os.core.navigation_manager import NavigationManager

logger = logging.getLogger("tank_os.widgets.map")


class MapWidget(QWidget):
    """Displays a top-down map with robot position, waypoints, and obstacles."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._nav = NavigationManager()
        self.setMinimumSize(240, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel("🗺 Navigation Map")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("font-size: 11px; color: #888; padding: 4px;")
        layout.addWidget(self._title)

        self._map_area = _MapCanvas()
        self._map_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._map_area)

        self._status = QLabel("No map loaded")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("font-size: 10px; color: #666; padding: 2px;")
        layout.addWidget(self._status)

        # Refresh timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._map_area.update)
        self._timer.start(1000)

    @property
    def map_canvas(self) -> _MapCanvas:
        return self._map_area


class _MapCanvas(QWidget):
    """Internal canvas that paints the map."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._nav = NavigationManager()
        self.setMinimumSize(200, 160)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        margin = 20
        map_w = w - margin * 2
        map_h = h - margin * 2

        # Background
        painter.fillRect(event.rect(), QColor("#1A1A2E"))

        # Grid
        painter.setPen(QPen(QColor("#2A2A4A"), 0.5))
        grid_size = 20
        for x in range(0, w, grid_size):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, grid_size):
            painter.drawLine(0, y, w, y)

        # Map border
        painter.setPen(QPen(QColor("#3A3A5A"), 1))
        painter.drawRect(margin, margin, map_w, map_h)

        # Waypoints
        waypoints = self._nav.waypoints
        for wp in waypoints:
            wx = int(margin + (wp.x + 5.0) / 10.0 * map_w)
            wy = int(margin + (5.0 - wp.y) / 10.0 * map_h)
            wx = max(margin, min(w + margin, wx))
            wy = max(margin, min(h + margin, wy))

            painter.setPen(QPen(QColor("#00BFFF"), 2))
            painter.setBrush(QBrush(QColor("#00BFFF80")))
            painter.drawEllipse(wx - 4, wy - 4, 8, 8)

            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("sans-serif", 7))
            painter.drawText(wx + 8, wy + 4, wp.name)

        # Robot position
        pose = self._nav.pose
        rx = int(margin + (pose.x + 5.0) / 10.0 * map_w)
        ry = int(margin + (5.0 - pose.y) / 10.0 * map_h)
        rx = max(margin + 10, min(w - margin - 10, rx))
        ry = max(margin + 10, min(h - margin - 10, ry))

        # Robot glow
        glow = QRadialGradient(rx, ry, 20)
        glow.setColorAt(0, QColor(0, 191, 255, 120))
        glow.setColorAt(1, QColor(0, 191, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rx - 20, ry - 20, 40, 40)

        # Robot body
        painter.setBrush(QBrush(QColor("#00BFFF")))
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawEllipse(rx - 6, ry - 6, 12, 12)

        # Direction indicator
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(rx, ry,
                         int(rx + 12 * (pose.yaw if pose.yaw else 0)),
                         int(ry - 12 * (abs(pose.yaw) if pose.yaw else 1)))

        # Position text
        painter.setPen(QPen(QColor("#AAAAAA")))
        painter.setFont(QFont("sans-serif", 8))
        painter.drawText(rx + 14, ry + 4,
                         f"({pose.x:.1f}, {pose.y:.1f})")

        # SLAM indicator
        if self._nav.is_slam_active:
            painter.setPen(QPen(QColor("#00E676")))
            painter.setFont(QFont("sans-serif", 8))
            painter.drawText(8, h - 8, "🔵 SLAM active")

        painter.end()
