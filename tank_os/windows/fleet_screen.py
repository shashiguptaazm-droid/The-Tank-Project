"""FleetScreen — 🟢 ESP32 Fleet (GUI blueprint).

All ESP32 nodes with identity, online status, path, heartbeat count,
firmware and telemetry — rendered from the live ESP32FleetManager (the
same engine as ``tank unoq esp32``). Auto-refreshes; a summary strip shows
online/offline totals.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.esp32_fleet import ESP32FleetManager

logger = logging.getLogger("tank_os.windows.fleet")


class _BoardCard(QFrame):
    """One ESP32 board card."""

    def __init__(self, board, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        online = board.status == "online"
        accent = "#4CAF50" if online else "#FF8A80"
        bg = "rgba(76,175,80,0.10)" if online else "rgba(211,47,47,0.10)"
        self.setObjectName("fleetCard")
        self.setStyleSheet(f"""
            #fleetCard {{
                background: {bg}; border: 1px solid {accent};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(3)

        top = QHBoxLayout()
        icon = QLabel("🟢" if online else "🔴")
        icon.setStyleSheet("font-size: 14px;")
        top.addWidget(icon)
        name = QLabel(board.name)
        name.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFF;")
        top.addWidget(name)
        top.addStretch()
        status = QLabel("ONLINE" if online else "OFFLINE")
        status.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {accent};")
        top.addWidget(status)
        lay.addLayout(top)

        rows = [
            ("Host", board.host or "—"),
            ("Serial", board.serial or "—"),
            ("Path", board.path or "—"),
            ("Heartbeats", str(board.heartbeat_count)),
            ("Firmware", board.firmware or "—"),
        ]
        for key, val in rows:
            row = QHBoxLayout()
            k = QLabel(key)
            k.setStyleSheet("font-size: 9px; color: #888;")
            row.addWidget(k)
            row.addStretch()
            v = QLabel(val)
            v.setStyleSheet("font-size: 10px; color: #CCC;")
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(v)
            lay.addLayout(row)

        if board.telemetry:
            tele = ", ".join(f"{k}={v}" for k, v in list(board.telemetry.items())[:4])
            t = QLabel(tele)
            t.setWordWrap(True)
            t.setStyleSheet("font-size: 9px; color: #7FA;")
            lay.addWidget(t)


class FleetScreen(QWidget):
    """ESP32 fleet dashboard."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._fleet = ESP32FleetManager()
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(5000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🟢 ESP32 Fleet")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._summary = QLabel("—")
        self._summary.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 12px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._summary)
        btn = QPushButton("🔄 Rescan")
        btn.setStyleSheet("""
            QPushButton { background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.4); border-radius: 8px;
                padding: 7px 14px; color: #80D8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.28); }
        """)
        btn.clicked.connect(self.refresh)
        header.addWidget(btn)
        layout.addLayout(header)

        self._grid = QGridLayout()
        self._grid.setSpacing(10)
        layout.addLayout(self._grid, 1)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            self._fleet.discover()
            boards = self._fleet.list()
            summary = self._fleet.summary()
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("fleet refresh failed: %s", exc)
            return

        self._summary.setText(
            f"{summary['online']}/{summary['total']} online"
            + (f"  ·  ⚠ {summary['offline']} offline" if summary["offline"] else ""))

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not boards:
            empty = QLabel("No ESP32 boards discovered yet — waiting for USB/serial scan…")
            empty.setStyleSheet("color: #777; font-size: 13px;")
            self._grid.addWidget(empty, 0, 0)
            return

        for i, board in enumerate(boards):
            self._grid.addWidget(_BoardCard(board), i // 2, i % 2)
        self._grid.setRowStretch(len(boards) // 2 + 1, 1)

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(5000)

    def on_hide(self) -> None:
        self._timer.stop()
