"""HealthScreen — 🩺 Robot Health (GUI blueprint's strongest competition screen).

One board with every subsystem's health score, rendered from the live
RobotDoctor diagnosis (the same engine as ``tank unoq doctor``). Tap a
component to see its detailed findings; a "Run Diagnosis" button forces a
fresh pass. Colour-coded ✓ / ⚠ / ✗ with the overall score up top.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.robot_doctor import RobotDoctor

logger = logging.getLogger("tank_os.windows.health")

STATUS_ICON = {"ok": "✓", "warn": "⚠", "fault": "✗"}
STATUS_COLOR = {"ok": "#81C784", "warn": "#FFD54F", "fault": "#FF8A80"}
STATUS_BG = {
    "ok": "rgba(76,175,80,0.12)",
    "warn": "rgba(255,193,7,0.12)",
    "fault": "rgba(211,47,47,0.14)",
}

#: Human-friendly display names (blueprint's 11 components).
DISPLAY_NAMES = {
    "jetson": "JETSON", "mcu": "STM32", "cpu_ram": "UNO Q",
    "esp32": "ESP32 FLEET", "motors": "MOTORS", "servos": "SERVOS",
    "imu": "IMU", "network": "NETWORK", "battery": "BATTERY",
    "services": "SERVICES", "camera": "CAMERA", "lidar": "LIDAR",
}


class _HealthTile(QFrame):
    """One subsystem tile: icon + name + score; click for details."""

    def __init__(self, name: str, status: str, score: int,
                 findings: list, on_click, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("healthTile")
        self.setStyleSheet(f"""
            #healthTile {{
                background: {STATUS_BG.get(status, 'rgba(255,255,255,0.04)')};
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
            }}
            #healthTile:hover {{ border: 1px solid rgba(0,191,255,0.5); }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        top = QHBoxLayout()
        icon = QLabel(STATUS_ICON.get(status, "·"))
        icon.setStyleSheet(f"font-size: 16px; color: {STATUS_COLOR.get(status, '#FFF')};")
        top.addWidget(icon)
        name_lbl = QLabel(DISPLAY_NAMES.get(name, name.upper()))
        name_lbl.setStyleSheet("font-size: 10px; color: #BBB; font-weight: bold;")
        top.addWidget(name_lbl)
        top.addStretch()
        lay.addLayout(top)

        score_lbl = QLabel(str(score))
        score_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFF;")
        lay.addWidget(score_lbl)

        if findings:
            note = QLabel(findings[0][:36])
            note.setStyleSheet(f"font-size: 9px; color: {STATUS_COLOR.get(status, '#888')};")
            note.setWordWrap(True)
            lay.addWidget(note)

        self._findings = findings

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._on_click:
            self._on_click(self._findings)


class HealthScreen(QWidget):
    """Robot Health — full board from the live RobotDoctor."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._doctor = RobotDoctor()
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
        title = QLabel("🩺 Robot Health")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._overall = QLabel("—")
        self._overall.setStyleSheet("""
            background: rgba(0,191,255,0.15); border: 1px solid rgba(0,191,255,0.4);
            border-radius: 12px; padding: 8px 18px;
            font-size: 22px; font-weight: bold; color: #80D8FF;
        """)
        header.addWidget(QLabel("OVERALL"))
        header.addWidget(self._overall)
        run = QPushButton("🔄 Run Diagnosis")
        run.setStyleSheet("""
            QPushButton { background: rgba(0,191,255,0.15);
                border: 1px solid rgba(0,191,255,0.4); border-radius: 8px;
                padding: 7px 14px; color: #80D8FF; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: rgba(0,191,255,0.28); }
        """)
        run.clicked.connect(self.refresh)
        header.addWidget(run)
        layout.addLayout(header)

        self._grid = QGridLayout()
        self._grid.setSpacing(8)
        layout.addLayout(self._grid, 1)

        # Detail footer
        self._detail = QLabel("Tap a component for diagnostics…")
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet("""
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 8px 12px; font-size: 11px; color: #9AA;
        """)
        layout.addWidget(self._detail)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            diag = self._doctor.diagnose()
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("health refresh failed: %s", exc)
            return

        self._overall.setText(f"{diag.health_score}/100")
        color = "#80D8FF" if diag.health_score >= 80 else \
            ("#FFD54F" if diag.health_score >= 50 else "#FF8A80")
        self._overall.setStyleSheet(f"""
            background: rgba(0,191,255,0.15); border: 1px solid {color};
            border-radius: 12px; padding: 8px 18px;
            font-size: 22px; font-weight: bold; color: {color};
        """)

        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        reports = diag.subsystems
        cols = 3
        for i, r in enumerate(reports):
            tile = _HealthTile(r.name, r.status, r.score, r.findings,
                               self._show_detail)
            self._grid.addWidget(tile, i // cols, i % cols)
        self._grid.setRowStretch(len(reports) // cols + 1, 1)

    def _show_detail(self, findings: list) -> None:
        if findings:
            self._detail.setText(" 🔍 " + " · ".join(findings[:4]))
        else:
            self._detail.setText(" ✓ All nominal")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(5000)

    def on_hide(self) -> None:
        self._timer.stop()
