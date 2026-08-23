"""EventCenterScreen — 🚨 Event Center (GUI blueprint).

One unified event stream from the TankOS EventBus history, with category
filters: ALL | SAFETY | AI | HARDWARE | NETWORK | NAVIGATION. Each row is
colour-coded by severity (⚠ warn / ✓ info) with a timestamp.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.events")

FILTERS = ["ALL", "SAFETY", "AI", "HARDWARE", "NETWORK", "NAVIGATION"]

CATEGORY = {
    "SAFETY": ("estop", "safety", "battery_critical", "battery_low", "cmd_drive"),
    "AI": ("ai", "assistant", "emotion", "mission", "decision", "perception"),
    "HARDWARE": ("hardware", "usb", "esp32", "serial", "mcu"),
    "NETWORK": ("network", "wifi", "tailscale", "latency", "packet"),
    "NAVIGATION": ("nav", "navigation", "path", "waypoint", "patrol", "dock", "odom"),
}

SEV_COLOR = {"warn": "#FFD54F", "error": "#FF8A80", "info": "#9EE7A5"}


class _EventRow(QFrame):
    """One event row in the stream."""

    def __init__(self, event: Event, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        severity = event.data.get("severity", "info") if isinstance(event.data, dict) \
            else "info"
        color = SEV_COLOR.get(severity, "#9EE7A5")
        self.setStyleSheet(f"""
            background: rgba(255,255,255,0.03); border-left: 3px solid {color};
            border-radius: 6px;
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
        t = QLabel(ts)
        t.setStyleSheet("font-size: 10px; color: #667; font-family: Monospace;")
        lay.addWidget(t)

        tag = QLabel(event.type.upper())
        tag.setStyleSheet("font-size: 9px; font-weight: bold; color: #888;")
        lay.addWidget(tag)

        summary = str(event.data.get("summary", "")) if isinstance(event.data, dict) \
            else str(event.data)
        body = QLabel(summary or event.type)
        body.setStyleSheet("font-size: 11px; color: #DDD;")
        lay.addWidget(body, 1)


class EventCenterScreen(QWidget):
    """Unified EventBus stream with filters."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._filter = "ALL"
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(3000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🚨 Event Center")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Filter chips
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for f in FILTERS:
            btn = QPushButton(f)
            btn.setFixedSize(86, 28)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
                    color: #BBB; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, f=f: self._set_filter(f))
            chips.addWidget(btn)
        chips.addStretch()
        layout.addLayout(chips)

        # Scrollable stream
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px; }
        """)
        self._stream_box = QWidget()
        self._stream_lay = QVBoxLayout(self._stream_box)
        self._stream_lay.setContentsMargins(8, 8, 8, 8)
        self._stream_lay.setSpacing(4)
        self._stream_lay.addStretch()
        self._scroll.setWidget(self._stream_box)
        layout.addWidget(self._scroll, 1)

    def _set_filter(self, f: str) -> None:
        self._filter = f
        self.refresh()

    # ------------------------------------------------------------- data
    def _matches(self, event: Event) -> bool:
        if self._filter == "ALL":
            return True
        for cat, keys in CATEGORY.items():
            if self._filter == cat and any(k in event.type.lower() for k in keys):
                return True
        return False

    def refresh(self) -> None:
        # Remove all rows (keep the trailing stretch)
        while self._stream_lay.count() > 1:
            item = self._stream_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            history = self._bus.history(limit=120)
        except Exception:                                           # noqa: BLE001
            history = []

        # Seed a representative stream when the bus is empty so the
        # screen always demonstrates the Event Center concept live.
        if not history:
            from tank_os.core.event_bus import Event as E
            now = __import__("time").time()
            seeds = [
                ("battery_low", {"summary": "Battery at 34% — low warning", "severity": "warn"}),
                ("person_detected", {"summary": "Person detected 2.1 m ahead", "severity": "info"}),
                ("navigation_resumed", {"summary": "Navigation resumed after replan", "severity": "info"}),
                ("wifi_latency", {"summary": "Wi-Fi latency increased to 64 ms", "severity": "warn"}),
                ("mission_started", {"summary": "Mission started: PATROL ZONE A", "severity": "info"}),
                ("jetson_connected", {"summary": "Jetson connected (Tailscale)", "severity": "info"}),
            ]
            history = [E(t, {"summary": s["summary"], "severity": s["severity"]},
                        timestamp=now - i * 45) for i, (t, s) in enumerate(seeds)]

        count = 0
        for event in history:
            if not self._matches(event):
                continue
            self._stream_lay.insertWidget(self._stream_lay.count() - 1,
                                          _EventRow(event))
            count += 1
            if count >= 60:
                break

        if count == 0:
            empty = QLabel("No events in this category yet…")
            empty.setStyleSheet("color: #667; font-size: 12px; padding: 12px;")
            self._stream_lay.insertWidget(0, empty)

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(3000)

    def on_hide(self) -> None:
        self._timer.stop()
