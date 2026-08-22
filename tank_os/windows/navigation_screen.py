"""NavigationScreen — SLAM map, waypoints, robot position, controls."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.navigation_manager import NavigationManager
from tank_os.widgets.map_widget import MapWidget

logger = logging.getLogger("tank_os.windows.navigation")


class NavigationScreen(QWidget):
    """Navigation screen with map, waypoints, and robot control."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._nav = NavigationManager()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left: Map
        left = QVBoxLayout()
        left.setSpacing(8)

        header = QLabel("🗺 Navigation & SLAM")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        left.addWidget(header)

        self._map = MapWidget()
        self._map.setMinimumSize(500, 340)
        left.addWidget(self._map, 1)
        layout.addLayout(left, 3)

        # Right: Controls
        right = QFrame()
        right.setObjectName("navPanel")
        right.setStyleSheet("""
            #navPanel {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(8)

        right_layout.addWidget(QLabel("📍 Waypoints"))
        right_layout.addWidget(QLabel("Click to navigate:", styleSheet="font-size: 11px; color: #888;"))

        self._wp_list = QListWidget()
        self._wp_list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px; color: white;
                font-size: 11px;
            }
            QListWidget::item:hover { background: rgba(0,191,255,0.15); }
            QListWidget::item:selected { background: rgba(0,191,255,0.3); }
        """)
        self._wp_list.itemDoubleClicked.connect(self._on_waypoint_click)
        right_layout.addWidget(self._wp_list, 1)

        # Add waypoint
        add_layout = QHBoxLayout()
        self._wp_input = QLineEdit()
        self._wp_input.setPlaceholderText("Waypoint name...")
        self._wp_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px; padding: 4px 8px;
                font-size: 11px; color: white;
            }
        """)
        add_layout.addWidget(self._wp_input)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #00BFFF; border: none;
                border-radius: 14px; font-size: 16px;
                font-weight: bold; color: white;
            }
        """)
        add_btn.clicked.connect(self._add_waypoint)
        add_layout.addWidget(add_btn)
        right_layout.addLayout(add_layout)

        # Robot control
        right_layout.addWidget(QLabel("🤖 Robot Control"))
        drive_layout = QHBoxLayout()
        for text, icon in [("◀", "left"), ("▲", "fwd"), ("▼", "back"), ("▶", "right"), ("⏹", "stop")]:
            btn = QPushButton(text)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 8px; font-size: 16px; color: white;
                }
                QPushButton:hover { background: rgba(0,191,255,0.3); }
                QPushButton:pressed { background: rgba(0,191,255,0.5); }
            """)
            btn.clicked.connect(lambda _, d=icon: self._drive(d))
            drive_layout.addWidget(btn)
        right_layout.addLayout(drive_layout)
        right_layout.addStretch()

        layout.addWidget(right, 1)

        self._refresh_waypoints()

    def _refresh_waypoints(self) -> None:
        self._wp_list.clear()
        for wp in self._nav.waypoints:
            item = QListWidgetItem(f"📍 {wp.name} ({wp.x:.1f}, {wp.y:.1f})")
            item.setData(Qt.UserRole, wp.name)
            self._wp_list.addItem(item)

    def _on_waypoint_click(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.UserRole)
        self._nav.navigate_waypoint(name)
        logger.info("Navigating to waypoint: %s", name)

    def _add_waypoint(self) -> None:
        name = self._wp_input.text().strip()
        if not name:
            return
        # Add at current position
        pose = self._nav.pose
        self._nav.add_waypoint(name, pose.x + 1, pose.y + 1)
        self._wp_input.clear()
        self._refresh_waypoints()

    def _drive(self, direction: str) -> None:
        from tank_os.core.robot_manager import RobotManager
        robot = RobotManager()
        vels = {"fwd": (0.3, 0), "back": (-0.3, 0),
                "left": (0, 0.5), "right": (0, -0.5), "stop": (0, 0)}
        vx, wz = vels.get(direction, (0, 0))
        robot.drive(vx, wz, duration_s=2.0)
