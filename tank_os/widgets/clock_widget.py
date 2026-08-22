"""LiveClock — real-time clock widget for the TopBar."""

from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger("tank_os.widgets.clock")


class LiveClock(QWidget):
    """Displays current time (HH:MM:SS) and date, updating every second."""

    def __init__(self, parent: Optional[QWidget] = None,
                 show_seconds: bool = True,
                 font_size: int = 14,
                 date_format: str = "ddd MMM d") -> None:
        super().__init__(parent)
        self._show_seconds = show_seconds
        self._date_format = date_format
        self._font_size = font_size
        self._setup_ui()
        self._start_timer()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(0)

        self._time_label = QLabel()
        self._time_label.setAlignment(Qt.AlignCenter)
        self._time_label.setStyleSheet(
            f"font-size: {self._font_size}px; font-weight: bold;"
        )
        layout.addWidget(self._time_label)

        self._date_label = QLabel()
        self._date_label.setAlignment(Qt.AlignCenter)
        self._date_label.setStyleSheet(
            "font-size: 10px; opacity: 0.7;"
        )
        layout.addWidget(self._date_label)

        self._update_time()

    def _start_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)

    def _update_time(self) -> None:
        now = time.localtime()
        fmt = "%H:%M:%S" if self._show_seconds else "%H:%M"
        self._time_label.setText(time.strftime(fmt, now))
        self._date_label.setText(time.strftime(self._date_format, now))

    def set_font_size(self, size: int) -> None:
        self._font_size = size
        self._time_label.setStyleSheet(
            f"font-size: {size}px; font-weight: bold;"
        )


ClockWidget = LiveClock  # alias for backward compatibility
