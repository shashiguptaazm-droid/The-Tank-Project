"""PatrolScreen — patrol route management and monitoring."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from tank_os.core.robot_manager import RobotManager

logger = logging.getLogger("tank_os.windows.patrol")


class PatrolScreen(QWidget):
    """Patrol route management, timing, and monitoring."""

    MODES = [
        ("🔁 Random", "random", "Explore randomly between waypoints"),
        ("🔄 Loop", "loop", "Cycle through all waypoints in order"),
        ("📍 Station", "station", "Stay at one waypoint observing"),
        ("🎯 Mission", "mission", "Execute a pre-set patrol mission"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._robot = RobotManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header
        header = QLabel("🚁 Patrol & Autonomous Missions")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Status bar
        self._status_bar = QFrame()
        self._status_bar.setObjectName("patrolStatus")
        self._status_bar.setFixedHeight(60)
        self._status_bar.setStyleSheet("""
            #patrolStatus {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 8px;
            }
        """)
        status_layout = QHBoxLayout(self._status_bar)
        self._status_icon = QLabel("⏸")
        self._status_icon.setStyleSheet("font-size: 24px;")
        status_layout.addWidget(self._status_icon)

        self._status_text = QLabel("Patrol Inactive")
        self._status_text.setStyleSheet("font-size: 14px; font-weight: bold; color: #888;")
        status_layout.addWidget(self._status_text)
        status_layout.addStretch()

        self._patrol_count = QLabel("0 routes")
        self._patrol_count.setStyleSheet("font-size: 12px; color: #666;")
        status_layout.addWidget(self._patrol_count)
        layout.addWidget(self._status_bar)

        # Patrol mode cards
        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(12)
        for icon, mode, desc in self.MODES:
            card = self._make_mode_card(icon, mode, desc)
            modes_layout.addWidget(card)
        layout.addLayout(modes_layout)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self._start_btn = QPushButton("▶ Start Patrol")
        self._start_btn.setStyleSheet("""
            QPushButton {
                background: #00E676; border: none;
                border-radius: 8px; padding: 10px 24px;
                font-size: 14px; font-weight: bold; color: #000;
            }
            QPushButton:hover { background: #00F090; }
        """)
        self._start_btn.clicked.connect(lambda: self._start_patrol("random"))
        controls.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⏹ Stop Patrol")
        self._stop_btn.setStyleSheet("""
            QPushButton {
                background: #FF5252; border: none;
                border-radius: 8px; padding: 10px 24px;
                font-size: 14px; font-weight: bold; color: white;
            }
            QPushButton:hover { background: #FF7070; }
        """)
        self._stop_btn.clicked.connect(self._stop_patrol)
        controls.addWidget(self._stop_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Log
        log_frame = QFrame()
        log_frame.setObjectName("patrolLog")
        log_frame.setStyleSheet("""
            #patrolLog {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 8px;
            }
        """)
        log_layout = QVBoxLayout(log_frame)
        log_layout.addWidget(QLabel("📋 Patrol Log"))
        self._log_label = QLabel("No patrol activity yet.")
        self._log_label.setStyleSheet("font-size: 11px; color: #888; padding: 8px;")
        self._log_label.setWordWrap(True)
        log_layout.addWidget(self._log_label)
        log_layout.addStretch()
        layout.addWidget(log_frame, 1)

    def _make_mode_card(self, icon: str, mode: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("patrolCard")
        card.setStyleSheet("""
            #patrolCard {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        card_layout.addWidget(QLabel(icon, styleSheet="font-size: 24px;"))
        name = QLabel(mode.upper())
        name.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        card_layout.addWidget(name)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 10px; color: #888;")
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)

        btn = QPushButton("▶ Select")
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,191,255,0.2);
                border: 1px solid rgba(0,191,255,0.3);
                border-radius: 6px; padding: 4px 12px;
                font-size: 10px; color: #00BFFF;
            }
            QPushButton:hover { background: rgba(0,191,255,0.3); }
        """)
        btn.clicked.connect(lambda: self._start_patrol(mode))
        card_layout.addWidget(btn)
        card_layout.addStretch()
        return card

    def _start_patrol(self, mode: str) -> None:
        self._robot.patrol(mode)
        self._status_icon.setText("▶")
        self._status_text.setText(f"Patrolling ({mode})")
        self._status_text.setStyleSheet("font-size: 14px; font-weight: bold; color: #00E676;")
        self._log(f"Patrol started — mode: {mode}")

    def _stop_patrol(self) -> None:
        self._robot.stop_patrol()
        self._status_icon.setText("⏸")
        self._status_text.setText("Patrol Stopped")
        self._status_text.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF5252;")
        self._log("Patrol stopped")

    def _log(self, message: str) -> None:
        import time
        ts = time.strftime("%H:%M:%S")
        current = self._log_label.text()
        lines = [f"[{ts}] {message}"] + current.split("\n")[:19]
        self._log_label.setText("\n".join(lines))
