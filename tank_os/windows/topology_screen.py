"""TopologyScreen — 🧩 Hardware Topology (GUI blueprint).

THE TANK hardware tree: JETSON (CAM/LIDAR/AI) + UNO Q (MCU→MOTOR,
SERVO, IMU, ESP32). Clicking a node shows its live diagnostic page below.

State is derived from the live RobotDoctor + ESP32FleetManager + USB scan.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from tank_os.core.robot_doctor import RobotDoctor

logger = logging.getLogger("tank_os.windows.topology")


class _Node(QFrame):
    """A clickable topology node."""

    def __init__(self, label: str, status: str, detail: str = "",
                 on_click=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._detail = detail
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        color = {"ok": "#4CAF50", "warn": "#FFC107", "fault": "#E53935"}.get(
            status, "#888")
        bg = {"ok": "rgba(76,175,80,0.12)", "warn": "rgba(255,193,7,0.12)",
              "fault": "rgba(211,47,47,0.14)"}.get(status, "rgba(255,255,255,0.04)")
        self.setStyleSheet(f"""
            background: {bg}; border: 1px solid {color}; border-radius: 10px;
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #FFF;"
                          " background: transparent;")
        lay.addWidget(lbl)
        if detail:
            d = QLabel(detail)
            d.setAlignment(Qt.AlignCenter)
            d.setStyleSheet("font-size: 9px; color: #9AA; background: transparent;")
            lay.addWidget(d)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._on_click:
            self._on_click(self._detail or self)


class TopologyScreen(QWidget):
    """Hardware topology tree with click-to-diagnose."""

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
        title = QLabel("🧩 Hardware Topology")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._hint = QLabel("click a node → diagnostics")
        self._hint.setStyleSheet("font-size: 10px; color: #777;")
        header.addWidget(self._hint)
        layout.addLayout(header)

        # Root
        self._root = self._node("THE TANK", "ok", "autonomous robot")
        self._root.setMinimumHeight(44)
        layout.addWidget(self._root)

        # Jetson / UNO Q branches
        branches = QHBoxLayout()
        branches.setSpacing(14)

        jetson_box = self._branch("JETSON — Orin Nano")
        self._jetson = self._node("🟧 JETSON", "ok", "")
        jetson_box.addWidget(self._jetson)
        jetson_kids = QGridLayout()
        jetson_kids.setSpacing(8)
        self._cam = self._node("📷 CAM", "ok", "")
        self._lidar = self._node("📡 LIDAR", "ok", "")
        self._ai = self._node("🧠 AI", "ok", "")
        for i, n in enumerate((self._cam, self._lidar, self._ai)):
            jetson_kids.addWidget(n, 0, i)
        jetson_box.addLayout(jetson_kids)
        branches.addLayout(jetson_box, 1)

        unoq_box = self._branch("UNO Q — STM32")
        self._unoq = self._node("🔷 UNO Q", "ok", "")
        unoq_box.addWidget(self._unoq)
        unoq_kids = QGridLayout()
        unoq_kids.setSpacing(8)
        self._mcu = self._node("🔌 MCU", "ok", "")
        self._servo = self._node("🦾 SERVO", "ok", "")
        self._imu = self._node("🧭 IMU", "ok", "")
        for i, n in enumerate((self._mcu, self._servo, self._imu)):
            unoq_kids.addWidget(n, 0, i)
        unoq_box.addLayout(unoq_kids)
        branches.addLayout(unoq_box, 1)
        layout.addLayout(branches)

        # ESP32 row
        esp_label = QLabel("ESP32 FLEET")
        esp_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        layout.addWidget(esp_label)
        esp_row = QHBoxLayout()
        esp_row.setSpacing(8)
        self._esp32: Dict[str, _Node] = {}
        for name in ("CAMERA", "DUAL-EYES", "AI-CAM"):
            n = self._node(name, "warn", "")
            self._esp32[name] = n
            esp_row.addWidget(n)
        layout.addLayout(esp_row)

        # Detail panel
        self._detail = QLabel("Click a node to see its live diagnostics…")
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet("""
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #B8E6FF;
        """)
        layout.addWidget(self._detail, 1)

    def _branch(self, title: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(8)
        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        box.addWidget(t)
        return box

    def _node(self, label: str, status: str, detail: str) -> _Node:
        return _Node(label, status, detail, on_click=self._show_detail)

    # ------------------------------------------------------------- data
    def refresh(self) -> None:
        try:
            diag = self._doctor.diagnose()
            state = {r.name: r for r in diag.subsystems}
        except Exception:                                           # noqa: BLE001
            state = {}

        def _set(node: _Node, sub: str) -> None:
            r = state.get(sub)
            status = r.status if r else "warn"
            node.setStyleSheet({
                "ok": "background: rgba(76,175,80,0.12); border: 1px solid #4CAF50;"
                      " border-radius: 10px;",
                "warn": "background: rgba(255,193,7,0.12); border: 1px solid #FFC107;"
                        " border-radius: 10px;",
                "fault": "background: rgba(211,47,47,0.14); border: 1px solid #E53935;"
                         " border-radius: 10px;",
            }.get(status, "background: rgba(255,255,255,0.04); border-radius: 10px;"))

        _set(self._jetson, "jetson")
        _set(self._cam, "jetson")
        _set(self._lidar, "network")
        _set(self._ai, "cpu_ram")
        _set(self._unoq, "services")
        _set(self._mcu, "mcu")
        _set(self._servo, "servos")
        _set(self._imu, "imu")
        for name, node in self._esp32.items():
            _set(node, "esp32")

        # ESP32 fleet detail
        try:
            from tank_os.core.esp32_fleet import ESP32FleetManager
            fleet = ESP32FleetManager()
            fleet.discover()
            for board in fleet.list():
                node = self._esp32.get(board.name.split(" ")[0].upper())
                if node:
                    ok = board.status == "online"
                    node.setStyleSheet(
                        "background: rgba(76,175,80,0.12); border: 1px solid #4CAF50;"
                        " border-radius: 10px;" if ok else
                        "background: rgba(211,47,47,0.14); border: 1px solid #E53935;"
                        " border-radius: 10px;")
        except Exception:                                           # noqa: BLE001
            pass

    def _show_detail(self, source) -> None:
        detail = source if isinstance(source, str) else ""
        if detail:
            self._detail.setText(f"🔍 {detail}")
        else:
            self._detail.setText("🔍 Tap a component row for subsystem status —"
                                 " see the Robot Health screen for full diagnostics.")

    def on_show(self) -> None:
        self.refresh()
        self._timer.start(5000)

    def on_hide(self) -> None:
        self._timer.stop()
