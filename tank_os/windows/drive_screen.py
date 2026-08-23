"""DriveScreen — 🕹️ Drive mode (GUI blueprint).

Shows a virtual joystick, physical-controller status, left/right track
speed, velocity, heading, odometry, motor current/temperature, an E-stop
button and the five drive modes (MANUAL / ASSISTED / AUTONOMOUS /
PRECISION / EMERGENCY).

Real control commands are emitted on the EventBus (``cmd_drive``) so the
robot layer decides what actually happens — the GUI never touches PWM.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus
from tank_os.core.power_manager import PowerManager
from tank_os.widgets.status_widget import StatusWidget

logger = logging.getLogger("tank_os.windows.drive")

MODES = ["MANUAL", "ASSISTED", "AUTONOMOUS", "PRECISION", "EMERGENCY"]
MAX_SPEED = 0.5  # m/s hard limit (matches robot_manager clamping)


class _Joystick(QWidget):
    """A simple virtual joystick — click / drag to set direction+power.

    Emits ``changed(x, y)`` where x ∈ [-1,1] (turn) and y ∈ [-1,1] (throttle).
    """

    changed = Signal(float, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self._pos = (0.0, 0.0)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtGui import QColor, QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(20, 22, 40))
        p.setPen(QPen(QColor(60, 70, 100), 2))
        p.drawEllipse(2, 2, self.width() - 4, self.height() - 4)
        p.setPen(QPen(QColor(40, 50, 80), 1))
        cx, cy = self.width() / 2, self.height() / 2
        p.drawLine(int(cx), 4, int(cx), self.height() - 4)
        p.drawLine(4, int(cy), self.width() - 4, int(cy))
        # Stick
        sx = cx + self._pos[0] * (cx - 22)
        sy = cy - self._pos[1] * (cy - 22)
        p.setBrush(QColor(0, 191, 255))
        p.setPen(QPen(QColor(120, 230, 255), 1))
        p.drawEllipse(int(sx) - 18, int(sy) - 18, 36, 36)
        p.end()

    def _update_pos(self, x: float, y: float) -> None:
        # Dead zone ~10%
        mag = math.hypot(x, y)
        if mag < 0.1:
            x = y = 0.0
        self._pos = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
        self.update()
        self.changed.emit(*self._pos)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._handle(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._handle(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._update_pos(0.0, 0.0)

    def _handle(self, event) -> None:
        cx, cy = self.width() / 2, self.height() / 2
        x = (event.position().x() - cx) / (cx - 22)
        y = -(event.position().y() - cy) / (cy - 22)
        self._update_pos(x, y)


class DriveScreen(QWidget):
    """Drive mode — joystick + telemetry + E-stop + drive modes."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._power = PowerManager()
        self._mode = "MANUAL"
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    # --------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🕹️ Drive")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFF;")
        header.addWidget(title)
        header.addStretch()
        self._mode_lbl = QLabel("MANUAL")
        self._mode_lbl.setStyleSheet("""
            background: rgba(0,191,255,0.15); border: 1px solid rgba(0,191,255,0.4);
            border-radius: 10px; padding: 6px 14px; font-size: 13px; font-weight: bold;
            color: #80D8FF;
        """)
        header.addWidget(self._mode_lbl)
        layout.addLayout(header)

        mid = QHBoxLayout()
        mid.setSpacing(14)

        # Left: joystick + mode buttons
        left = QVBoxLayout()
        left.setSpacing(8)
        self._joystick = _Joystick()
        self._joystick.changed.connect(self._on_joy)
        left.addWidget(self._joystick, 0, Qt.AlignCenter)

        modes_row = QHBoxLayout()
        modes_row.setSpacing(6)
        for m in MODES:
            btn = QPushButton(m)
            btn.setFixedSize(96, 34)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
                    color: #CCC; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,191,255,0.2); color: #FFF; }
            """)
            btn.clicked.connect(lambda _=False, m=m: self._set_mode(m))
            modes_row.addWidget(btn)
        left.addLayout(modes_row)
        mid.addLayout(left)

        # Right: telemetry grid
        right = QGridLayout()
        right.setSpacing(8)
        self._tl = {}
        for i, (key, label) in enumerate([
            ("track", "Track L / R"), ("velocity", "Velocity"),
            ("heading", "Heading"), ("odom", "Odometry"),
            ("current", "Motor current"), ("temp", "Motor temp"),
            ("controller", "Controller"), ("max", "Max speed"),
        ]):
            card = self._card(label)
            right.addWidget(card, i // 2, i % 2)
        mid.addLayout(right, 1)
        layout.addLayout(mid, 1)

        # Bottom: E-stop + status
        bottom = QHBoxLayout()
        self._estop = QPushButton("⛔ E-STOP")
        self._estop.setFixedSize(120, 44)
        self._estop.setStyleSheet("""
            QPushButton { background: #D32F2F; color: #FFF; font-size: 14px;
                font-weight: bold; border: none; border-radius: 10px; }
            QPushButton:hover { background: #E53935; }
        """)
        self._estop.clicked.connect(self._on_estop)
        bottom.addWidget(self._estop)
        bottom.addStretch()
        self._status = StatusWidget()
        bottom.addWidget(self._status, 1)
        layout.addLayout(bottom)

    def _card(self, label: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("driveCard")
        frame.setStyleSheet("""
            #driveCard { background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; }
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 9px; color: #888; font-weight: bold;")
        lay.addWidget(lbl)
        val = QLabel("—")
        val.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")
        lay.addWidget(val)
        self._tl[label] = val
        return frame

    # ------------------------------------------------------------- data
    def _on_joy(self, x: float, y: float) -> None:
        # tank-tread: throttle = y, turn = x -> left/right track speeds
        throttle = y * MAX_SPEED
        turn = x * MAX_SPEED
        left = max(-MAX_SPEED, min(MAX_SPEED, throttle + turn))
        right = max(-MAX_SPEED, min(MAX_SPEED, throttle - turn))
        self._tl["Track L / R"].setText(f"{left:+.2f} / {right:+.2f} m/s")
        self._tl["Velocity"].setText(f"{abs(y) * MAX_SPEED:.2f} m/s")
        self._tl["Heading"].setText(f"{x * 90:.0f}°")
        self._bus.emit(Event("cmd_drive", {
            "left": round(left, 3), "right": round(right, 3),
            "mode": self._mode, "source": "drive_screen",
        }, source="drive_screen"))

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._mode_lbl.setText(mode)
        self._bus.emit(Event("drive_mode", {"mode": mode}, source="drive_screen"))

    def _on_estop(self) -> None:
        self._bus.emit(Event("estop_triggered", {"latched": True, "reason": "drive-screen"},
                             source="drive_screen"))
        self._tl["Velocity"].setText("0.00 m/s")
        self._tl["Track L / R"].setText("0.00 / 0.00 m/s")
        self._joystick._update_pos(0.0, 0.0)

    def _tick(self) -> None:
        try:
            self._tl["Max speed"].setText(f"{MAX_SPEED:.1f} m/s")
            self._tl["Controller"].setText("virtual joystick")
            pm = self._power
            self._tl["Motor current"].setText(f"{pm.current_ma / 1000:.2f} A")
            self._tl["Motor temp"].setText(f"{pm.battery_temp_c} °C")
            self._tl["Odometry"].setText(
                f"{pm.voltage:.1f} V · {pm.battery_percent}%")
        except Exception:  # noqa: BLE001
            pass

    def on_show(self) -> None:
        self._timer.start(1000)

    def on_hide(self) -> None:
        self._timer.stop()
