"""DiagnosticsScreen — system health, performance monitoring, logs."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.diagnostics_manager import DiagnosticsManager

logger = logging.getLogger("tank_os.windows.diagnostics")


class _MetricBar(QWidget):
    """A single metric display with label, value bar, and percentage."""

    def __init__(self, name: str, icon: str, color: str = "#00BFFF",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = color
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(24)
        icon_lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon_lbl)

        self._name = QLabel(name)
        self._name.setFixedWidth(60)
        self._name.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        layout.addWidget(self._name)

        self._bar = QProgressBar()
        self._bar.setFixedHeight(10)
        self._bar.setTextVisible(False)
        self._bar.setRange(0, 100)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.08);
                border: none; border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self._bar, 1)

        self._value = QLabel("--")
        self._value.setFixedWidth(50)
        self._value.setAlignment(Qt.AlignRight)
        self._value.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: bold;")
        layout.addWidget(self._value)

    def set_value(self, pct: float, text: str = "") -> None:
        self._bar.setValue(min(100, max(0, int(pct))))
        self._value.setText(text or f"{pct:.0f}%")


class DiagnosticsScreen(QWidget):
    """Comprehensive system diagnostics dashboard."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._diagnostics = DiagnosticsManager()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("🔍 System Diagnostics")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Metrics grid
        self._metrics: Dict[str, _MetricBar] = {}
        metrics_config = [
            ("CPU", "🖥", "#FF6B35"),
            ("RAM", "🧠", "#00BFFF"),
            ("Disk", "💾", "#00E676"),
            ("Temp", "🌡", "#FF5252"),
        ]
        for name, icon, color in metrics_config:
            bar = _MetricBar(name, icon, color)
            layout.addWidget(bar)
            self._metrics[name.lower()] = bar

        # Network info
        net_frame = QFrame()
        net_frame.setStyleSheet("""
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px; padding: 8px;
        """)
        net_layout = QHBoxLayout(net_frame)
        net_layout.addWidget(QLabel("📡", styleSheet="font-size: 14px;"))
        self._net_label = QLabel("Network: --")
        self._net_label.setStyleSheet("font-size: 11px; color: #AAA;")
        net_layout.addWidget(self._net_label)

        self._ros_label = QLabel("ROS: --")
        self._ros_label.setStyleSheet("font-size: 11px; color: #AAA;")
        net_layout.addWidget(self._ros_label)

        self._uptime_label = QLabel("Uptime: --")
        self._uptime_label.setStyleSheet("font-size: 11px; color: #AAA;")
        net_layout.addWidget(self._uptime_label)
        net_layout.addStretch()
        layout.addWidget(net_frame)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(10)

        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,191,255,0.2);
                border: 1px solid rgba(0,191,255,0.3);
                border-radius: 8px; padding: 8px 16px;
                font-size: 12px; color: #00BFFF; font-weight: bold;
            }
            QPushButton:hover { background: rgba(0,191,255,0.3); }
        """)
        refresh_btn.clicked.connect(self._refresh)
        actions.addWidget(refresh_btn)

        diagnose_btn = QPushButton("🔬 Run Full Diagnostics")
        diagnose_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; padding: 8px 16px;
                font-size: 12px; color: white;
            }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        diagnose_btn.clicked.connect(self._run_full)
        actions.addWidget(diagnose_btn)

        actions.addStretch()
        layout.addLayout(actions)

        # Full report area
        report_frame = QFrame()
        report_frame.setObjectName("diagReport")
        report_frame.setStyleSheet("""
            #diagReport {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 8px;
            }
        """)
        report_layout = QVBoxLayout(report_frame)
        report_layout.addWidget(QLabel("📋 Report", styleSheet="font-size: 11px; color: #888;"))
        self._report_label = QLabel("Run diagnostics to see report.")
        self._report_label.setStyleSheet("font-size: 10px; color: #666; font-family: monospace;")
        self._report_label.setWordWrap(True)
        report_layout.addWidget(self._report_label)
        report_layout.addStretch()
        layout.addWidget(report_frame, 1)

        # Auto-refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)
        self._refresh()

    def _refresh(self) -> None:
        try:
            data = self._diagnostics.collect()
            cpu = data.get("cpu", {})
            mem = data.get("memory", {})
            disk = data.get("disk", {})
            temp = data.get("temperature", {})

            if "percent" in cpu:
                self._metrics["cpu"].set_value(cpu.get("percent", 0))
            if "percent" in mem:
                self._metrics["ram"].set_value(mem.get("percent", 0))
            if "percent" in disk:
                self._metrics["disk"].set_value(disk.get("percent", 0))

            temp_c = temp.get("cpu_c")
            if temp_c:
                self._metrics["temp"].set_value(
                    min(100, max(0, (temp_c / 85.0) * 100)),
                    f"{temp_c:.1f}°C",
                )

            net = data.get("network", {})
            ips = net.get("ips", [])
            self._net_label.setText(f"📡 IP: {ips[0] if ips else 'offline'}")

            ros = data.get("ros", {})
            nodes = ros.get("node_count", 0)
            self._ros_label.setText(f"🔄 ROS: {nodes} nodes")

            uptime = data.get("uptime", 0.0)
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            mins = int((uptime % 3600) // 60)
            self._uptime_label.setText(
                f"⏱ {'{}d {}h {}m'.format(days, hours, mins) if days else '{}h {}m'.format(hours, mins)}"
            )
        except Exception as exc:
            logger.debug("Refresh error: %s", exc)

    def _run_full(self) -> None:
        data = self._diagnostics.collect()
        report = []
        for key, value in data.items():
            if key == "timestamp":
                continue
            report.append(f"{key.upper()}: {value}")
        self._report_label.setText("\n".join(report[:30]))
