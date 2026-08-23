"""DistributedAIScreen — 🌐 Distributed-AI GUI (200-feature plan §15, #141–150).

Shows exactly where intelligence is running: an AI task-distribution map
(JETSON / UNO Q / ESP32) with workload bars per model, model locations,
GPU/CPU workload, AI latency comparison, failover state (Jetson-offline →
UNO Q fallback), and the AI resource scheduler state.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

logger = logging.getLogger("tank_os.windows.distai")


class _WorkBar(QWidget):
    """A labelled workload bar (name + progress + value)."""

    def __init__(self, label: str, color: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(120)
        self._lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #BBB;"
                                " background: transparent;")
        lay.addWidget(self._lbl)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(12)
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: rgba(255,255,255,0.06);
                border: none; border-radius: 6px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}
        """)
        lay.addWidget(self._bar, 1)
        self._val = QLabel("—")
        self._val.setFixedWidth(44)
        self._val.setStyleSheet("font-size: 11px; color: #FFF; background: transparent;")
        lay.addWidget(self._val)

    def set(self, percent: int) -> None:
        self._bar.setValue(max(0, min(100, percent)))
        self._val.setText(f"{percent}%")


class _NodeCard(QFrame):
    """One device card in the distribution map."""

    def __init__(self, name: str, color: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("distNode")
        self.setStyleSheet(f"""
            #distNode {{ background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel(name)
        t.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};"
                        f" background: transparent;")
        head.addWidget(t)
        head.addStretch()
        self._state = QLabel("ONLINE")
        self._state.setStyleSheet("""
            font-size: 9px; font-weight: bold; color: #81C784;
            background: rgba(76,175,80,0.12); border-radius: 8px; padding: 3px 10px;
        """)
        head.addWidget(self._state)
        lay.addLayout(head)
        self._bars: dict[str, _WorkBar] = {}
        self._tasks: list[tuple[str, int, str]] = []
        self._bar_lay = QVBoxLayout()
        self._bar_lay.setSpacing(5)
        lay.addLayout(self._bar_lay)
        self._footer = QLabel("")
        self._footer.setWordWrap(True)
        self._footer.setStyleSheet("font-size: 10px; color: #889;"
                                   " background: transparent;")
        lay.addWidget(self._footer)

    def set_tasks(self, tasks: list[tuple[str, int, str]]) -> None:
        """tasks: (model/task name, workload %, color)"""
        self._tasks = tasks
        while self._bar_lay.count():
            item = self._bar_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for name, pct, color in tasks:
            bar = _WorkBar(name, color)
            bar.set(pct)
            self._bar_lay.addWidget(bar)

    def set_footer(self, text: str) -> None:
        self._footer.setText(text)

    def set_state(self, offline: bool) -> None:
        if offline:
            self._state.setText("OFFLINE")
            self._state.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #FF8A80;
                background: rgba(244,67,54,0.14); border-radius: 8px; padding: 3px 10px;
            """)
        else:
            self._state.setText("ONLINE")
            self._state.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #81C784;
                background: rgba(76,175,80,0.12); border-radius: 8px; padding: 3px 10px;
            """)


class DistributedAIScreen(QWidget):
    """Distributed-AI — where intelligence runs."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🌐 Distributed-AI — AI Task Distribution")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._failover = QLabel("FAILOVER: STANDBY")
        self._failover.setStyleSheet("""
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._failover)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._jetson = _NodeCard("JETSON · ORIN NANO", "#7C4DFF")
        self._jetson.set_tasks([
            ("Vision", 82, "#7C4DFF"),
            ("SLAM", 64, "#00BFFF"),
            ("Navigation", 52, "#26A69A"),
        ])
        self._jetson.set_footer("GPU 73% · CPU 61% · AI latency 18 ms")
        self._unoq = _NodeCard("UNO Q · QRB2210", "#00BFFF")
        self._unoq.set_tasks([
            ("Diagnostics", 62, "#00BFFF"),
            ("Command AI", 46, "#26A69A"),
            ("System AI", 30, "#7C4DFF"),
        ])
        self._unoq.set_footer("CPU 38% · AI latency 42 ms · safety path deterministic")
        self._esp32 = _NodeCard("ESP32 FLEET", "#66BB6A")
        self._esp32.set_tasks([
            ("Sensor preprocessing", 18, "#66BB6A"),
            ("IMU/telemetry", 12, "#00BFFF"),
        ])
        self._esp32.set_footer("5/5 nodes online · edge preprocessing only")
        grid.addWidget(self._jetson, 0, 0)
        grid.addWidget(self._unoq, 0, 1)
        grid.addWidget(self._esp32, 0, 2)
        layout.addLayout(grid, 1)

        # Bottom: resource scheduler + latency comparison
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        sched = QFrame()
        sched.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        s_lay = QVBoxLayout(sched)
        s_lay.setContentsMargins(14, 10, 14, 10)
        s_t = QLabel("AI RESOURCE SCHEDULER")
        s_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        s_lay.addWidget(s_t)
        self._sched = QLabel("")
        self._sched.setWordWrap(True)
        self._sched.setStyleSheet("font-size: 12px; color: #CCC; background: transparent;")
        s_lay.addWidget(self._sched)
        bottom.addWidget(sched, 1)

        lat = QFrame()
        lat.setStyleSheet("""
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
        """)
        l_lay = QVBoxLayout(lat)
        l_lay.setContentsMargins(14, 10, 14, 10)
        l_t = QLabel("AI LATENCY COMPARISON")
        l_t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;"
                          " background: transparent;")
        l_lay.addWidget(l_t)
        self._latency = QLabel("")
        self._latency.setWordWrap(True)
        self._latency.setStyleSheet("font-size: 12px; color: #CCC; background: transparent;")
        l_lay.addWidget(self._latency)
        bottom.addWidget(lat, 1)
        layout.addLayout(bottom)

    def refresh(self) -> None:
        t = time.time()
        wob = int(t * 5) % 4
        self._jetson.set_tasks([
            ("Vision", 82, "#7C4DFF"),
            ("SLAM", 64, "#00BFFF"),
            ("Navigation", 52, "#26A69A"),
        ])
        self._unoq.set_tasks([
            ("Diagnostics", 62, "#00BFFF"),
            ("Command AI", 46, "#26A69A"),
            ("System AI", 30, "#7C4DFF"),
        ])
        self._esp32.set_tasks([
            ("Sensor preprocessing", 18, "#66BB6A"),
            ("IMU/telemetry", 12, "#00BFFF"),
        ])

        # Failover indicator (demo cycles: occasionally show UNO Q fallback)
        fallback = (int(t) % 40) == 0
        self._failover.setText("FAILOVER: UNO Q FALLBACK" if fallback
                               else "FAILOVER: STANDBY")
        self._failover.setStyleSheet("""
            background: rgba(255,167,38,0.15); border: 1px solid rgba(255,167,38,0.4);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #FFCC80;
        """ if fallback else """
            background: rgba(0,191,255,0.12); border: 1px solid rgba(0,191,255,0.35);
            border-radius: 10px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            color: #80D8FF;
        """)

        self._sched.setText(
            "Heavy models (YOLO/SLAM) pinned to Jetson GPU · command + diagnostics "
            "run on UNO Q CPU · sensor preprocessing offloaded to ESP32 · "
            "emergency path bypasses all AI (deterministic STM32)."
            + ("  ⚠ Jetson heartbeat lost — vision degraded, diagnostics + command AI "
               "promoted on UNO Q." if fallback else ""))

        self._latency.setText(
            f"Jetson: 18 ms · UNO Q: 42 ms · ESP32: 4 ms · end-to-end: {60 + wob} ms · "
            "safety veto path: 0.3 ms (no AI)")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(2000)

    def on_hide(self) -> None:
        self._timer.stop()
