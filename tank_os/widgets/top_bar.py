"""TopBar — system status bar at the top of the Tank Shell."""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)

from tank_os.core.diagnostics_manager import DiagnosticsManager
from tank_os.core.emotion_manager import EmotionManager
from tank_os.core.event_bus import Event, EventBus
from tank_os.core.notification_manager import NotificationManager
from tank_os.core.power_manager import PowerManager
from tank_os.widgets.battery_widget import BatteryWidget
from tank_os.widgets.clock_widget import LiveClock

logger = logging.getLogger("tank_os.widgets.top_bar")


class _IndicatorLabel(QLabel):
    """Small label with dot prefix for compact status display."""

    def __init__(self, icon: str = "", tooltip: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self.setToolTip(tooltip)
        self.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.setAlignment(Qt.AlignCenter)
        self.update_value("--")

    def update_value(self, text: str) -> None:
        self.setText(f"{self._icon} {text}" if self._icon else text)


class TopBar(QFrame):
    """Top system status bar with clock, battery, WiFi, CPU, temp, emotion, notifications."""

    notification_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(44)
        self._bus = EventBus()
        self._power = PowerManager()
        self._diagnostics = DiagnosticsManager()
        self._emotion = EmotionManager()
        self._notifications = NotificationManager()

        self._setup_ui()
        self._connect_events()
        self._start_polling()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # --- Clock (left) ---
        self._clock = LiveClock(show_seconds=False, font_size=13)
        self._clock.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._clock)

        # Separator
        layout.addWidget(self._make_sep())

        # --- Emotion indicator ---
        self._emotion_label = QLabel()
        self._emotion_label.setAlignment(Qt.AlignCenter)
        self._emotion_label.setStyleSheet("font-size: 13px; padding: 2px 8px;")
        self._emotion_label.setToolTip("Robot emotion")
        layout.addWidget(self._emotion_label)

        layout.addWidget(self._make_sep())

        # --- CPU usage ---
        self._cpu_label = _IndicatorLabel("🖥", "CPU usage", self)
        layout.addWidget(self._cpu_label)

        # --- Temperature ---
        self._temp_label = _IndicatorLabel("🌡", "CPU temperature", self)
        layout.addWidget(self._temp_label)

        # Spacer
        layout.addStretch(1)

        # --- WiFi indicator ---
        self._wifi_label = _IndicatorLabel("📶", "WiFi status", self)
        layout.addWidget(self._wifi_label)

        # --- Battery ---
        layout.addWidget(BatteryWidget(width=52, height=22))

        # Separator
        layout.addWidget(self._make_sep())

        # --- Notification bell ---
        self._notif_btn = QPushButton("🔔")
        self._notif_btn.setFixedSize(34, 28)
        self._notif_btn.setToolTip("Notifications")
        self._notif_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 14px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        self._notif_btn.clicked.connect(self.notification_clicked.emit)
        layout.addWidget(self._notif_btn)

        self._notif_badge = QLabel("")
        self._notif_badge.setFixedSize(20, 16)
        self._notif_badge.setAlignment(Qt.AlignCenter)
        self._notif_badge.setStyleSheet("""
            background: #FF5252; color: white;
            font-size: 9px; font-weight: bold;
            border-radius: 8px; padding: 0px;
        """)
        self._notif_badge.hide()
        layout.addWidget(self._notif_badge)

        self._update_all()

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.15);")
        sep.setFixedWidth(1)
        return sep

    def _connect_events(self) -> None:
        self._bus.on("emotion_changed", self._on_emotion)
        self._bus.on("battery_changed", lambda _: self._update_battery())
        self._bus.on("notification", self._on_notification)

    def _on_emotion(self, event: Event) -> None:
        name = event.data.get("name", "neutral")
        emoji_map = {
            "happy": "😊", "excited": "🎉", "curious": "🤔",
            "neutral": "😐", "sad": "😢", "angry": "😠",
            "sleepy": "😴", "surprised": "😮", "loving": "😍",
        }
        emoji = emoji_map.get(name, "😐")
        self._emotion_label.setText(f"{emoji} {name.title()}"[:20])

    def _on_notification(self, event: Event) -> None:
        count = self._notifications.count
        if count > 0:
            self._notif_badge.setText(str(min(count, 99)))
            self._notif_badge.show()
        else:
            self._notif_badge.hide()

    def _start_polling(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._update_all)
        self._poll_timer.start(5000)

    def _update_all(self) -> None:
        self._update_diagnostics()
        self._update_battery()
        self._update_wifi()

    def _update_diagnostics(self) -> None:
        try:
            stats = self._diagnostics.summary()
            cpu = stats.get("cpu", "?")
            temp = stats.get("temp", "?")
            self._cpu_label.update_value(f"{cpu}%" if isinstance(cpu, (int, float)) else f"{cpu}")
            if isinstance(temp, (int, float)):
                self._temp_label.update_value(f"{temp:.0f}°C")
        except Exception:
            pass

    def _update_battery(self) -> None:
        self.update()  # trigger battery widget repaint

    def _update_wifi(self) -> None:
        from tank_os.core.network_manager import NetworkManager
        try:
            net = NetworkManager()
            wifi = net._interfaces.get("wifi")
            if wifi and wifi.connected:
                self._wifi_label.update_value(wifi.ssid[:12])
            else:
                self._wifi_label.update_value("off")
        except Exception:
            self._wifi_label.update_value("off")
