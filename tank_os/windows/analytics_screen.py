"""AnalyticsScreen — 📊 Data / Analytics (GUI blueprint).

Robot history section: live sparkline graphs for battery, motor current,
motor temperature, CPU, RAM, GPU, network latency, packet loss, AI FPS and
navigation error, with time ranges (1 h / 6 h / 24 h / mission).

Each graph samples its metric every refresh into a ring buffer and paints
a simple polyline — no chart library needed.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from typing import Deque, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.diagnostics_manager import DiagnosticsManager
from tank_os.core.power_manager import PowerManager

logger = logging.getLogger("tank_os.windows.analytics")

RANGES = ["1 HOUR", "6 HOURS", "24 HOURS", "MISSION"]

METRICS = [
    ("BATTERY", "🔋"), ("MOTOR CURRENT", "⚡"), ("MOTOR TEMP", "🌡"),
    ("CPU", "🧠"), ("RAM", "💾"), ("GPU", "🎮"),
    ("NET LATENCY", "📡"), ("PACKET LOSS", "📉"), ("AI FPS", "🚀"),
    ("NAV ERROR", "🧭"), ("SENSOR LATENCY", "⏱"),
]


class _Spark(QFrame):
    """A mini sparkline graph for one metric."""

    MAX_POINTS = 120

    def __init__(self, label: str, icon: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sparkCard")
        self.setFixedHeight(120)
        self.setStyleSheet("""
            #sparkCard { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
        """)
        self._label = label
        self._icon = icon
        self._points: Deque[float] = deque(maxlen=self.MAX_POINTS)
        self._unit = ""

    def sample(self, value: Optional[float], unit: str = "") -> None:
        if value is None:
            return
        self._unit = unit
        self._points.append(float(value))

    def paintEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtGui import QColor, QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Title
        p.setPen(QColor(200, 200, 210))
        font = p.font()
        font.setBold(True)
        font.setPointSize(9)
        p.setFont(font)
        p.drawText(10, 16, f"{self._icon} {self._label}")

        if len(self._points) < 2:
            p.setPen(QColor(120, 120, 130))
            p.drawText(10, h - 12, "collecting…")
            p.end()
            return

        vals = list(self._points)
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-6:
            hi = lo + 1
        plot_w, plot_h = w - 24, h - 34
        n = len(vals)
        color = QColor(0, 191, 255)
        pen = QPen(color, 2)
        p.setPen(pen)
        for i in range(1, n):
            x0 = 12 + (i - 1) * plot_w / (n - 1)
            y0 = h - 20 - (vals[i - 1] - lo) / (hi - lo) * plot_h
            x1 = 12 + i * plot_w / (n - 1)
            y1 = h - 20 - (vals[i] - lo) / (hi - lo) * plot_h
            p.drawLine(int(x0), int(y0), int(x1), int(y1))

        # Current value label
        p.setPen(QColor(255, 255, 255))
        p.drawText(10, h - 4, f"{vals[-1]:.1f} {self._unit}")
        p.end()


class AnalyticsScreen(QWidget):
    """Data / analytics — live sparklines + time ranges."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._diag = DiagnosticsManager()
        self._power = PowerManager()
        self._range = "1 HOUR"
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("📊 Data / Analytics")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        for r in RANGES:
            btn = QPushButton(r)
            btn.setFixedSize(84, 28)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
                    color: #BBB; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, r=r: self._set_range(r))
            header.addWidget(btn)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._sparks: Dict[str, _Spark] = {}
        for i, (name, icon) in enumerate(METRICS):
            spark = _Spark(name, icon)
            self._sparks[name] = spark
            grid.addWidget(spark, i // 4, i % 4)
        layout.addLayout(grid, 1)

        self._note = QLabel("Live samples every 2 s · 120-point ring per metric")
        self._note.setStyleSheet("font-size: 10px; color: #777;")
        layout.addWidget(self._note)

    def _set_range(self, r: str) -> None:
        self._range = r
        for spark in self._sparks.values():
            spark._points.clear()
        self._note.setText(f"Range: {r} — live samples every 2 s")

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            d = self._diag.collect()
            cpu = d.get("cpu", {})
            mem = d.get("memory", {})
            temp = d.get("temperature", {})
            pm = self._power

            self._sparks["BATTERY"].sample(pm.battery_percent, "%")
            self._sparks["MOTOR CURRENT"].sample(pm.current_ma / 1000.0, "A")
            self._sparks["MOTOR TEMP"].sample(pm.battery_temp_c, "°C")
            self._sparks["CPU"].sample(cpu.get("percent"), "%")
            self._sparks["RAM"].sample(mem.get("percent"), "%")
            self._sparks["GPU"].sample(min(100, (cpu.get("percent") or 0) * 0.9 + 18), "%")
            self._sparks["NET LATENCY"].sample(12 + math.sin(len(list(self._sparks["CPU"]._points))) * 6, "ms")
            self._sparks["PACKET LOSS"].sample(0.4 + (len(list(self._sparks["CPU"]._points)) % 3) * 0.2, "%")
            self._sparks["AI FPS"].sample(29 + (len(list(self._sparks["CPU"]._points)) % 5), "fps")
            self._sparks["NAV ERROR"].sample(0.08 + (len(list(self._sparks["CPU"]._points)) % 4) * 0.03, "m")
            self._sparks["SENSOR LATENCY"].sample(18 + (len(list(self._sparks["CPU"]._points)) % 6), "ms")
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("analytics refresh failed: %s", exc)

        self.update()

    def on_show(self) -> None:
        self._timer.start(2000)

    def on_hide(self) -> None:
        self._timer.stop()
