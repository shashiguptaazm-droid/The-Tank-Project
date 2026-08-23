"""KnowledgeMapScreen — 🧠 Robot Self-Awareness Map (originality idea #1).

Two maps on one screen:
- ENVIRONMENT MAP — what the robot sees.
- ROBOT KNOWLEDGE MAP — how certain it is (per-region confidence), what it
  doesn't know, where it has previously failed.
- ROBOT HEALTH MAP — subsystem health from the live RobotDoctor.

Each region is painted with a confidence colour (green = known, yellow =
uncertain, red = unknown / previously failed). This is the "knowledge
confidence" panel from the plan (North corridor 96% · Room A 88% ·
Behind obstacle 41% · Stair area 22%).
"""

from __future__ import annotations

import logging
import math
import time
from typing import Dict, List, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

logger = logging.getLogger("tank_os.windows.knowledgemap")

#: (name, x0, y0, x1, y1) regions in map units (0..100)
REGIONS: List[dict] = [
    {"name": "North corridor", "x0": 20, "y0": 5, "x1": 80, "y1": 20,
     "base": 0.96, "color": "#4CAF50"},
    {"name": "Room A", "x0": 5, "y0": 25, "x1": 40, "y1": 60,
     "base": 0.88, "color": "#8BC34A"},
    {"name": "Room B", "x0": 60, "y0": 30, "x1": 95, "y1": 55,
     "base": 0.74, "color": "#FFD54F"},
    {"name": "Behind obstacle", "x0": 45, "y0": 62, "x1": 75, "y1": 82,
     "base": 0.41, "color": "#FFA726"},
    {"name": "Stair area", "x0": 15, "y0": 70, "x1": 40, "y1": 95,
     "base": 0.22, "color": "#E53935"},
]


def _conf_color(conf: float) -> QColor:
    """Green (known) → yellow (uncertain) → red (unknown)."""
    if conf >= 0.75:
        return QColor(76, 175, 80, 200)
    if conf >= 0.5:
        return QColor(255, 193, 7, 200)
    return QColor(229, 57, 53, 200)


class _KnowledgeCanvas(QWidget):
    """Custom-painted knowledge-confidence map."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._regions = REGIONS
        self.setMinimumHeight(280)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background grid
        p.fillRect(0, 0, w, h, QColor(13, 13, 26))
        pen = QPen(QColor(255, 255, 255, 14))
        pen.setWidth(1)
        p.setPen(pen)
        for gx in range(0, w, 40):
            p.drawLine(gx, 0, gx, h)
        for gy in range(0, h, 40):
            p.drawLine(0, gy, w, gy)

        t = time.time()
        for r in self._regions:
            # gentle confidence wobble for a live feel
            wob = 0.03 * math.sin(t / 5.0 + r["x0"])
            conf = max(0.0, min(1.0, r["base"] + wob))
            x = r["x0"] / 100.0 * w
            y = r["y0"] / 100.0 * h
            rw = (r["x1"] - r["x0"]) / 100.0 * w
            rh = (r["y1"] - r["y0"]) / 100.0 * h
            p.fillRect(QRectF(x, y, rw, rh), _conf_color(conf))
            p.setPen(QPen(QColor(255, 255, 255, 60)))
            p.drawRect(QRectF(x, y, rw, rh))
            # label
            p.setPen(QColor(255, 255, 255, 230))
            p.setFont(QFont("Sans", 8, QFont.Bold))
            p.drawText(QRectF(x + 4, y + 4, rw - 8, 14),
                       Qt.AlignLeft, r["name"].upper())
            p.setFont(QFont("Monospace", 9, QFont.Bold))
            p.drawText(QRectF(x + 4, y + 20, rw - 8, 16),
                       Qt.AlignLeft, f"{conf * 100:.0f}%")

        # Robot marker
        rx, ry = w * 0.52, h * 0.5
        p.setBrush(QColor(0, 191, 255, 220))
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawEllipse(QRectF(rx - 10, ry - 10, 20, 20))
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Sans", 8, QFont.Bold))
        p.drawText(QRectF(rx - 30, ry + 14, 60, 14), Qt.AlignCenter, "TANK")
        p.end()


class KnowledgeMapScreen(QWidget):
    """Robot Knowledge Map — environment + self-knowledge + health."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🧠 Robot Knowledge Map")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._overall = QLabel("")
        self._overall.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._overall)
        layout.addLayout(header)

        labels = QHBoxLayout()
        env = QLabel("ENVIRONMENT MAP — what the robot sees")
        know = QLabel("KNOWLEDGE CONFIDENCE — how certain it is")
        for lbl in (env, know):
            lbl.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        labels.addWidget(env)
        labels.addStretch()
        labels.addWidget(know)
        layout.addLayout(labels)

        self._canvas = _KnowledgeCanvas()
        layout.addWidget(self._canvas, 1)

        # Legend + health map
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        legend = QFrame()
        legend.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        l_lay = QVBoxLayout(legend)
        l_lay.setContentsMargins(12, 10, 12, 10)
        l_t = QLabel("KNOWLEDGE LEGEND")
        l_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        l_lay.addWidget(l_t)
        self._legend = QLabel("")
        self._legend.setWordWrap(True)
        self._legend.setStyleSheet("font-size: 11px; color: #CCC;"
                                   " background: transparent;")
        l_lay.addWidget(self._legend)
        bottom.addWidget(legend, 1)

        health = QFrame()
        health.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        h_lay = QVBoxLayout(health)
        h_lay.setContentsMargins(12, 10, 12, 10)
        h_t = QLabel("🩺 ROBOT HEALTH MAP (live)")
        h_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        h_lay.addWidget(h_t)
        self._health = QLabel("")
        self._health.setWordWrap(True)
        self._health.setStyleSheet("font-size: 11px; color: #CCC;"
                                   " background: transparent;")
        h_lay.addWidget(self._health)
        bottom.addWidget(health, 1)
        layout.addLayout(bottom)

    def refresh(self) -> None:
        t = time.time()
        lines = []
        total = 0.0
        for r in REGIONS:
            wob = 0.03 * math.sin(t / 5.0 + r["x0"])
            conf = max(0.0, min(1.0, r["base"] + wob))
            total += conf
            icon = "🟢" if conf >= 0.75 else ("🟡" if conf >= 0.5 else "🔴")
            lines.append(f"{icon} {r['name']:<16} {conf * 100:.0f}%")
        self._legend.setText("\n".join(lines))
        avg = total / len(REGIONS) * 100
        self._overall.setText(f"KNOWLEDGE: {avg:.0f}% CERTAIN")

        # Health from live RobotDoctor
        try:
            from tank_os.core.robot_doctor import RobotDoctor
            diag = RobotDoctor().diagnose()
            sub = [f"{s.name.upper()} {s.score}" for s in diag.subsystems[:6]]
            self._health.setText(
                f"OVERALL: {diag.health_score}/100\n" + " · ".join(sub))
        except Exception:                                           # noqa: BLE001
            self._health.setText("RobotDoctor unavailable")

    def on_show(self) -> None:
        self.refresh()
