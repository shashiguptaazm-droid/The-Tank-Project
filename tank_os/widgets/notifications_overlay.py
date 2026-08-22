"""NotificationsOverlay — floating notification popup overlay."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus
from tank_os.core.notification_manager import Notification, NotificationManager, Priority

logger = logging.getLogger("tank_os.widgets.notifications")


class _NotificationCard(QFrame):
    """A single notification display card."""

    def __init__(self, notif: Notification, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.notif = notif
        self._opacity = 1.0
        self.setObjectName("notifCard")
        self.setStyleSheet(self._make_style(notif))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        icon = notif.icon or self._icon_for_priority(notif.priority)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(notif.title)
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        title.setWordWrap(True)
        text_layout.addWidget(title)

        if notif.message:
            msg = QLabel(notif.message)
            msg.setStyleSheet("font-size: 11px; color: #BBBBBB;")
            msg.setWordWrap(True)
            text_layout.addWidget(msg)

        layout.addLayout(text_layout, 1)

        # Dismiss button
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #888;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { color: #FF5252; }
        """)
        dismiss_btn.clicked.connect(self._dismiss)
        layout.addWidget(dismiss_btn)

    def _icon_for_priority(self, priority: Priority) -> str:
        if priority >= Priority.CRITICAL:
            return "🔴"
        elif priority >= Priority.HIGH:
            return "🟡"
        elif priority >= Priority.NORMAL:
            return "🔵"
        return "⚪"

    def _make_style(self, notif: Notification) -> str:
        priority_colors = {
            Priority.CRITICAL: "rgba(255,82,82,0.2)",
            Priority.HIGH: "rgba(255,193,7,0.2)",
            Priority.NORMAL: "rgba(68,138,255,0.15)",
            Priority.LOW: "rgba(255,255,255,0.05)",
        }
        bg = priority_colors.get(notif.priority, "rgba(255,255,255,0.05)")
        border = notif.priority >= Priority.HIGH
        border_style = "border: 1px solid rgba(255,82,82,0.3);" if border else \
                       "border: 1px solid rgba(255,255,255,0.1);"
        return f"""
            #notifCard {{
                background: {bg};
                {border_style}
                border-radius: 8px;
                margin: 2px 0px;
            }}
        """

    def _dismiss(self) -> None:
        NotificationManager().dismiss(self.notif.id)
        self.parent().layout().removeWidget(self)
        self.deleteLater()

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, val: float) -> None:
        self._opacity = val
        self.setStyleSheet(self._make_style(self.notif) +
                           f"#notifCard {{ opacity: {val}; }}")

    opacity = Property(float, get_opacity, set_opacity)


class NotificationsOverlay(QFrame):
    """Floating notification panel that slides down from the top."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._notifications = NotificationManager()
        self._visible = False
        self._max_visible = 5

        self.setObjectName("notifOverlay")
        self.setFixedWidth(380)
        self.setMinimumHeight(60)
        self.setMaximumHeight(400)
        self.hide()

        self.setStyleSheet("""
            #notifOverlay {
                background: rgba(20, 20, 40, 0.95);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔔 Notifications")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #FF5252;
                font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Scrollable notification list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent; border: none;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.05); width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2); border-radius: 2px;
            }
        """)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

        self._bus.on("notification", self._on_notification)

    def toggle(self) -> None:
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self._refresh()
            self.show()
            self._visible = True
            self.raise_()

    def _on_notification(self, event: Event) -> None:
        if self._visible:
            self._refresh()

    def _refresh(self) -> None:
        # Clear old cards
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        active = self._notifications.active(self._max_visible)
        for n in active:
            card = _NotificationCard(n)
            self._list_layout.insertWidget(0, card)

    def _clear_all(self) -> None:
        self._notifications.dismiss_all()
        self._refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._refresh()
