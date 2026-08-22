"""SecurityScreen — surveillance, emergency stop, access control."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from tank_os.core.security_manager import SecurityManager
from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.security")


class SecurityScreen(QWidget):
    """Security & surveillance control panel."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._security = SecurityManager()
        self._bus = EventBus()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header
        header = QLabel("🛡 Security & Safety")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Status cards
        cards = QHBoxLayout()
        cards.setSpacing(12)

        self._surveillance_card = self._make_status_card(
            "📹 Surveillance", "Inactive", "#888",
            self._toggle_surveillance, "Toggle",
        )
        cards.addWidget(self._surveillance_card)

        self._estop_card = self._make_status_card(
            "⛔ Emergency Stop", "Released", "#00E676",
            self._toggle_estop, "Activate",
        )
        cards.addWidget(self._estop_card)

        self._auth_card = self._make_status_card(
            "🔐 Authentication", "Unauthenticated", "#888",
            self._authenticate, "Login",
        )
        cards.addWidget(self._auth_card)

        layout.addLayout(cards)

        # Alert log
        alert_frame = QFrame()
        alert_frame.setObjectName("secLog")
        alert_frame.setStyleSheet("""
            #secLog {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 8px;
            }
        """)
        alert_layout = QVBoxLayout(alert_frame)
        alert_layout.addWidget(QLabel("📋 Security Events"))
        self._log_label = QLabel("No recent security events.")
        self._log_label.setStyleSheet("font-size: 11px; color: #888; padding: 8px;")
        self._log_label.setWordWrap(True)
        alert_layout.addWidget(self._log_label)
        alert_layout.addStretch()
        layout.addWidget(alert_frame, 1)

        # Info
        info = QLabel("🔒 All security events are logged. E-STOP overrides all motion commands.")
        info.setStyleSheet("font-size: 10px; color: #666; padding: 4px;")
        layout.addWidget(info)

        self._bus.on("estop_triggered", self._on_estop)
        self._bus.on("security_auth", self._on_auth)

    def _make_status_card(self, icon: str, title: str, status_color: str,
                          callback, btn_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("secCard")
        card.setStyleSheet("""
            #secCard {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        card_layout.addWidget(QLabel(icon, styleSheet="font-size: 28px;"))

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        card_layout.addWidget(title_lbl)

        self._status_labels: dict = {}
        status = QLabel("● " + self._status_text(title))
        status.setStyleSheet(f"font-size: 12px; color: {status_color};")
        card_layout.addWidget(status)
        self._status_labels[title] = status

        btn = QPushButton(btn_text)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px; padding: 6px 16px;
                font-size: 11px; color: white;
            }
            QPushButton:hover { background: rgba(0,191,255,0.3); }
        """)
        btn.clicked.connect(callback)
        card_layout.addWidget(btn)
        card_layout.addStretch()

        return card

    def _status_text(self, title: str) -> str:
        if "Surveillance" in title:
            return "Active" if self._security.is_surveillance_active else "Inactive"
        if "Emergency" in title:
            return "LATCHED ⚠️" if self._security.is_estop else "Released"
        if "Authentication" in title:
            return "Authenticated" if self._security.is_authenticated else "Unauthenticated"
        return "Unknown"

    def _toggle_surveillance(self) -> None:
        active = self._security.toggle_surveillance()
        lbl = self._status_labels.get("Surveillance")
        if lbl:
            if active:
                lbl.setText("● Active")
                lbl.setStyleSheet("font-size: 12px; color: #00E676;")
            else:
                lbl.setText("● Inactive")
                lbl.setStyleSheet("font-size: 12px; color: #888;")
        self._log("Surveillance " + ("started" if active else "stopped"))

    def _toggle_estop(self) -> None:
        self._security.estop(not self._security.is_estop)
        # Event handler will update UI

    def _on_estop(self, event: Event) -> None:
        latched = event.data.get("latched", True)
        lbl = self._status_labels.get("Emergency Stop")
        if lbl:
            if latched:
                lbl.setText("● LATCHED ⚠️")
                lbl.setStyleSheet("font-size: 12px; color: #FF5252;")
            else:
                lbl.setText("● Released")
                lbl.setStyleSheet("font-size: 12px; color: #00E676;")
        self._log(f"E-STOP {'ACTIVATED' if latched else 'RELEASED'}")

    def _authenticate(self) -> None:
        # Simulate auth with a default token
        result = self._security.authenticate("tank_admin")
        lbl = self._status_labels.get("Authentication")
        if lbl:
            if result:
                lbl.setText("● Authenticated")
                lbl.setStyleSheet("font-size: 12px; color: #00E676;")
            else:
                lbl.setText("● Failed")
                lbl.setStyleSheet("font-size: 12px; color: #FF5252;")
        self._log("Auth " + ("succeeded" if result else "failed"))

    def _on_auth(self, event: Event) -> None:
        success = event.data.get("success", False)
        lbl = self._status_labels.get("Authentication")
        if lbl:
            if success:
                lbl.setText("● Authenticated")
                lbl.setStyleSheet("font-size: 12px; color: #00E676;")
            else:
                lbl.setText("● Failed")
                lbl.setStyleSheet("font-size: 12px; color: #FF5252;")

    def _log(self, message: str) -> None:
        import time
        ts = time.strftime("%H:%M:%S")
        current = self._log_label.text()
        lines = [f"[{ts}] {message}"] + current.split("\n")[:19]
        self._log_label.setText("\n".join(lines))
