"""BatteryWidget — battery percentage indicator for the TopBar."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget

from tank_os.core.power_manager import PowerManager

logger = logging.getLogger("tank_os.widgets.battery")


class BatteryWidget(QWidget):
    """Draws a battery icon with percentage fill and charging indicator."""

    def __init__(self, parent: Optional[QWidget] = None,
                 width: int = 48, height: int = 24) -> None:
        super().__init__(parent)
        self._width = width
        self._height = height
        self.setFixedSize(width, height)
        self._power = PowerManager()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(5000)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pct = self._power.battery_percent
        charging = self._power.is_charging

        w, h = self._width, self._height
        body = (0, int(h * 0.2), int(w * 0.85), int(h * 0.6))
        tip = (int(w * 0.85), int(h * 0.35), int(w * 0.12), int(h * 0.3))

        # Determine color
        if charging:
            color = QColor("#00E676")  # green
        elif pct <= 20:
            color = QColor("#FF5252")  # red
        elif pct <= 50:
            color = QColor("#FFC107")  # yellow
        else:
            color = QColor("#00E676")  # green

        # Body outline
        painter.setPen(QPen(QColor("#AAAAAA"), 1.5))
        painter.setBrush(QBrush(QColor("#222222")))
        painter.drawRoundedRect(*body, 3, 3)

        # Tip
        painter.setPen(QPen(QColor("#AAAAAA"), 1.5))
        painter.setBrush(QBrush(QColor("#AAAAAA")))
        painter.drawRect(*tip)

        # Fill
        fill_w = max(2, int(body[2] * pct / 100) - 4)
        fill = (body[0] + 2, body[1] + 2, fill_w, body[3] - 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(*fill, 2, 2)

        # Charging bolt
        if charging:
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setFont(QFont("sans-serif", 10, QFont.Bold))
            bolt_x = body[0] + int(body[2] / 2) - 4
            bolt_y = body[1] + int(body[3] / 2) + 4
            painter.drawText(bolt_x, bolt_y, "⚡")

        # Percentage text
        painter.setPen(QPen(QColor("#FFFFFF")))
        painter.setFont(QFont("sans-serif", 8))
        txt_x = body[0] + int(body[2] / 2) - 10
        txt_y = body[1] + int(body[3] / 2) + 3
        painter.drawText(txt_x, txt_y, f"{pct}%")

        painter.end()
