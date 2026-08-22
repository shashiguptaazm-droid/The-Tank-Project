"""DeveloperScreen — developer tools, ROS monitor, terminal, debug."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.windows.developer")


class DeveloperScreen(QWidget):
    """Developer tools — ROS topic viewer, logs, event bus inspector."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left: Tool list
        left = QVBoxLayout()
        left.setSpacing(8)

        header = QLabel("🛠 Developer Mode")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        left.addWidget(header)

        tools = [
            ("📡 ROS Topics", self._show_ros),
            ("📋 Event Bus", self._show_events),
            ("📄 System Log", self._show_log),
            ("💻 Terminal", self._show_terminal),
            ("📦 Packages", self._show_packages),
            ("📊 Performance", self._show_perf),
        ]
        for text, callback in tools:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 8px; padding: 10px 16px;
                    font-size: 12px; color: white; text-align: left;
                }
                QPushButton:hover { background: rgba(0,191,255,0.15); }
            """)
            btn.clicked.connect(callback)
            left.addWidget(btn)

        left.addStretch()
        layout.addLayout(left, 1)

        # Right: Output panel
        right = QFrame()
        right.setObjectName("devPanel")
        right.setStyleSheet("""
            #devPanel {
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px; padding: 8px;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(4)

        self._output_title = QLabel("📡 ROS Topics")
        self._output_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        right_layout.addWidget(self._output_title)

        self._output_list = QListWidget()
        self._output_list.setStyleSheet("""
            QListWidget {
                background: rgba(0,0,0,0.4);
                border: none; border-radius: 6px;
                color: #00E676; font-family: monospace;
                font-size: 10px;
            }
        """)
        right_layout.addWidget(self._output_list, 1)
        layout.addWidget(right, 2)

        # Show default
        self._show_ros()

    def _show_ros(self) -> None:
        self._output_title.setText("📡 ROS Topics")
        self._output_list.clear()
        items = [
            "/tank/cmd_vel", "/tank/odom", "/tank/battery",
            "/tank/camera/image", "/tank/detections",
            "/tank/emotion", "/tank/voice/command",
            "/tank/nav/pose", "/tank/nav/waypoints",
        ]
        for item in items:
            self._output_list.addItem(QListWidgetItem(f"  {item}"))

    def _show_events(self) -> None:
        self._output_title.setText("📋 Event Bus History")
        self._output_list.clear()
        events = self._bus.history(limit=20)
        for e in events:
            ts = f"{e.timestamp:.1f}"[-6:]
            self._output_list.addItem(
                QListWidgetItem(f"  [{ts}] {e.type} ({e.priority.name})")
            )
        if not events:
            self._output_list.addItem("  No recent events")

    def _show_log(self) -> None:
        self._output_title.setText("📄 System Log")
        self._output_list.clear()
        import logging
        entries = [
            "[10:00:01] INFO: TankOS Core initialized",
            "[10:00:02] INFO: Event Bus ready (12 subscribers)",
            "[10:00:02] INFO: Plugin Manager loaded (0 plugins)",
            "[10:00:03] INFO: Theme Engine: dark mode active",
            "[10:00:03] INFO: Animation Engine started (60 FPS)",
            "[10:00:04] INFO: Hardware Manager: 6 devices detected",
            "[10:00:04] INFO: Tank Shell ready — accepting commands",
        ]
        for entry in entries:
            self._output_list.addItem(QListWidgetItem(f"  {entry}"))

    def _show_terminal(self) -> None:
        self._output_title.setText("💻 Terminal")
        self._output_list.clear()
        self._output_list.addItem("  $ TankOS Shell v1.0.0")
        self._output_list.addItem("  $ Type `help` for commands")
        self._output_list.addItem("  $ ")

    def _show_packages(self) -> None:
        self._output_title.setText("📦 Package Manager")
        self._output_list.clear()
        self._output_list.addItem("  📦 tankos-core v1.0.0 ✅")
        self._output_list.addItem("  📦 tankos-shell v1.0.0 ✅")
        self._output_list.addItem("  📦 event-bus v1.0.0 ✅")
        self._output_list.addItem("  📦 theme-engine v1.0.0 ✅")
        self._output_list.addItem("  📦 animation-engine v1.0.0 ✅")
        self._output_list.addItem("  📦 ai-agent-framework v1.0.0 ✅")
        self._output_list.addItem("")
        self._output_list.addItem("  🔄 Check for updates...")

    def _show_perf(self) -> None:
        self._output_title.setText("📊 Performance")
        self._output_list.clear()
        self._output_list.addItem("  ⚡ CPU: 12.4%")
        self._output_list.addItem("  🧠 RAM: 342MB / 8GB (4.3%)")
        self._output_list.addItem("  💾 Disk: 2.1GB / 32GB (6.6%)")
        self._output_list.addItem("  🌡 Temp: 48.2°C")
        self._output_list.addItem("  🎮 FPS: 60")
        self._output_list.addItem("  🔄 Event Bus: 142 events/min")
        self._output_list.addItem("")
        self._output_list.addItem("  📈 All systems nominal")
