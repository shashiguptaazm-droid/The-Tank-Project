"""StatusWidget — system status cards for CPU, RAM, disk, network, uptime."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar,
    QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.diagnostics_manager import DiagnosticsManager

logger = logging.getLogger("tank_os.widgets.status")


class _StatusCard(QFrame):
    """A single status card with icon, label, value, and progress bar."""

    def __init__(self, icon: str, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setStyleSheet("""
            #statusCard {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 6px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        header = QHBoxLayout()
        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet("font-size: 16px;")
        header.addWidget(self._icon_label)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        header.addWidget(self._title_label)
        header.addStretch()
        layout.addLayout(header)

        self._value_label = QLabel("--")
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self._value_label)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.1);
                border: none; border-radius: 3px;
            }
            QProgressBar::chunk {
                background: #00BFFF;
                border-radius: 3px;
            }
        """)
        self._progress.hide()
        layout.addWidget(self._progress)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_progress(self, pct: int, color: str = "#00BFFF") -> None:
        self._progress.setValue(min(100, max(0, pct)))
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.1);
                border: none; border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """)
        self._progress.show()


class StatusWidget(QWidget):
    """Grid of system status cards (CPU, RAM, Disk, Net, Uptime, ROS)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._diagnostics = DiagnosticsManager()

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._cards: Dict[str, _StatusCard] = {}

        card_configs = [
            ("🖥", "CPU", 0, 0),
            ("🧠", "RAM", 0, 1),
            ("💾", "Disk", 1, 0),
            ("🌡", "Temp", 1, 1),
            ("📡", "Network", 2, 0),
            ("🔄", "ROS", 2, 1),
        ]

        for icon, title, row, col in card_configs:
            card = _StatusCard(icon, title)
            layout.addWidget(card, row, col)
            self._cards[title.lower()] = card

        # Uptime label
        self._uptime_label = QLabel("Uptime: --")
        self._uptime_label.setAlignment(Qt.AlignCenter)
        self._uptime_label.setStyleSheet("font-size: 10px; color: #666; padding: 4px;")
        layout.addWidget(self._uptime_label, 3, 0, 1, 2)

        self._update_all()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_all)
        self._timer.start(5000)

    def _update_all(self) -> None:
        try:
            stats = self._diagnostics.collect()
            self._update_card("cpu", stats.get("cpu", {}), "%")
            self._update_card("ram", stats.get("memory", {}), "%")
            self._update_card("disk", stats.get("disk", {}), "%")
            self._update_card("temp", stats.get("temperature", {}), "°C")
            self._update_network(stats.get("network", {}))
            self._update_ros(stats.get("ros", {}))
            self._update_uptime(stats.get("uptime", 0.0))
        except Exception as exc:
            logger.debug("Status update error: %s", exc)

    def _update_card(self, name: str, data: Dict[str, Any], suffix: str) -> None:
        card = self._cards.get(name)
        if not card:
            return
        pct = data.get("percent")
        if pct is not None:
            card.set_value(f"{pct}{suffix}")
            color = "#00E676" if pct < 70 else "#FFC107" if pct < 90 else "#FF5252"
            card.set_progress(int(pct), color)
        elif "cpu_c" in data:
            val = data["cpu_c"]
            card.set_value(f"{val:.1f}°C" if isinstance(val, float) else f"{val}{suffix}")
        elif "load_1m" in data:
            card.set_value(f"load {data['load_1m']}")
        else:
            card.set_value("N/A")

    def _update_network(self, data: Dict[str, Any]) -> None:
        card = self._cards.get("network")
        if not card:
            return
        ips = data.get("ips", [])
        card.set_value(ips[0] if ips else "offline")

    def _update_ros(self, data: Dict[str, Any]) -> None:
        card = self._cards.get("ros")
        if not card:
            return
        n = data.get("node_count", 0)
        card.set_value(f"{n} node{'s' if n != 1 else ''}" if n else "N/A")

    def _update_uptime(self, uptime_s: float) -> None:
        days = int(uptime_s // 86400)
        hours = int((uptime_s % 86400) // 3600)
        mins = int((uptime_s % 3600) // 60)
        if days > 0:
            self._uptime_label.setText(f"⏱ Uptime: {days}d {hours}h {mins}m")
        else:
            self._uptime_label.setText(f"⏱ Uptime: {hours}h {mins}m")
