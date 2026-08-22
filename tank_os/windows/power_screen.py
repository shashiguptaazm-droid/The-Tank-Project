"""PowerScreen — battery monitoring, performance modes, sleep/shutdown/reboot."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from tank_os.core.power_manager import PowerManager
from tank_os.core.event_bus import Event, EventBus
from tank_os.core.notification_manager import NotificationManager

logger = logging.getLogger("tank_os.windows.power")

PERF_MODES = ["powersave", "balanced", "performance"]
PERF_ICONS = {"powersave": "🌱", "balanced": "⚖️", "performance": "🚀"}
PERF_DESC = {
    "powersave": "CPU throttled, GPU disabled, max battery life",
    "balanced": "Adaptive clock speeds, standard brightness",
    "performance": "Max CPU/GPU clocks, full brightness",
}


class _MetricCard(QFrame):
    """A single metric display card (e.g., battery %, temp, cycles)."""

    def __init__(self, title: str, value: str, subtitle: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("powerMetricCard")
        self.setStyleSheet("""
            #powerMetricCard {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; color: #888; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFF;")
        self._value_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value_lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet("font-size: 10px; color: #666;")
            sub.setAlignment(Qt.AlignCenter)
            layout.addWidget(sub)


class PowerScreen(QWidget):
    """Power management screen with battery health, performance, and system controls."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._power = PowerManager()
        self._bus = EventBus()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔋 Power & Battery")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ── Battery gauge section ──
        gauge_frame = QFrame()
        gauge_frame.setObjectName("powerGauge")
        gauge_frame.setStyleSheet("""
            #powerGauge {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)
        gauge_layout = QVBoxLayout(gauge_frame)
        gauge_layout.setContentsMargins(20, 16, 20, 16)
        gauge_layout.setSpacing(8)

        gauge_header = QHBoxLayout()
        gauge_title = QLabel("Battery Level")
        gauge_title.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        gauge_header.addWidget(gauge_title)
        gauge_header.addStretch()

        self._charge_badge = QLabel("⚡ Charging")
        self._charge_badge.setStyleSheet("""
            background: rgba(0,230,118,0.12);
            color: #00E676; border: 1px solid rgba(0,230,118,0.25);
            border-radius: 10px; padding: 3px 10px;
            font-size: 10px; font-weight: bold;
        """)
        self._charge_badge.setVisible(False)
        gauge_header.addWidget(self._charge_badge)
        gauge_layout.addLayout(gauge_header)

        self._battery_bar = QProgressBar()
        self._battery_bar.setRange(0, 100)
        self._battery_bar.setValue(self._power.battery_percent)
        self._battery_bar.setTextVisible(True)
        self._battery_bar.setFormat(f"{self._power.battery_percent}%")
        self._battery_bar.setFixedHeight(32)
        self._battery_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.06);
                border: none; border-radius: 16px;
                text-align: center; font-size: 14px;
                font-weight: bold; color: #FFF;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00C853, stop:1 #00E676);
                border-radius: 16px;
            }
        """)
        gauge_layout.addWidget(self._battery_bar)

        # Range indicators
        range_layout = QHBoxLayout()
        self._est_range = QLabel("Est. runtime: ~8h")
        self._est_range.setStyleSheet("font-size: 10px; color: #777;")
        range_layout.addWidget(self._est_range)
        range_layout.addStretch()
        self._voltage_lbl = QLabel(f"Voltage: {self._power.voltage:.1f}V")
        self._voltage_lbl.setStyleSheet("font-size: 10px; color: #777;")
        range_layout.addWidget(self._voltage_lbl)
        gauge_layout.addLayout(range_layout)

        layout.addWidget(gauge_frame)

        # ── Metric cards ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self._temp_card = _MetricCard("🌡 Temperature", f"{self._power.battery_temp_c:.0f}°C", "Nominal range")
        cards_layout.addWidget(self._temp_card)

        self._cycles_card = _MetricCard("🔄 Cycles", str(self._power.charge_cycles), "Lifetime")
        cards_layout.addWidget(self._cycles_card)

        self._current_card = _MetricCard("⚡ Current", f"{self._power.current_ma:.0f}mA", "Draw rate")
        cards_layout.addWidget(self._current_card)

        layout.addLayout(cards_layout)

        # ── Performance modes ──
        perf_frame = QFrame()
        perf_frame.setObjectName("powerPerf")
        perf_frame.setStyleSheet("""
            #powerPerf {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)
        perf_layout = QVBoxLayout(perf_frame)
        perf_layout.setContentsMargins(20, 14, 20, 14)
        perf_layout.setSpacing(8)

        perf_title = QLabel("⚡ Performance Mode")
        perf_title.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        perf_layout.addWidget(perf_title)

        perf_btns = QHBoxLayout()
        perf_btns.setSpacing(8)
        self._perf_btns: list[QPushButton] = []
        for mode in PERF_MODES:
            btn = QPushButton(f"{PERF_ICONS[mode]} {mode.title()}")
            btn.setCheckable(True)
            btn.setChecked(mode == self._power.performance_mode)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 10px; padding: 8px 16px;
                    font-size: 12px; color: #CCC;
                }
                QPushButton:hover {
                    background: rgba(0,191,255,0.15);
                    border-color: rgba(0,191,255,0.3);
                }
                QPushButton:checked {
                    background: rgba(0,191,255,0.2);
                    border-color: rgba(0,191,255,0.5);
                    color: #FFF;
                }
            """)
            btn.clicked.connect(lambda checked, m=mode: self._set_performance(m))
            perf_btns.addWidget(btn)
            self._perf_btns.append(btn)
        perf_layout.addLayout(perf_btns)

        self._perf_desc = QLabel(PERF_DESC.get(self._power.performance_mode, ""))
        self._perf_desc.setStyleSheet("font-size: 10px; color: #666; padding-top: 2px;")
        perf_layout.addWidget(self._perf_desc)

        layout.addWidget(perf_frame)

        # ── System power controls ──
        sys_frame = QFrame()
        sys_frame.setObjectName("powerSys")
        sys_frame.setStyleSheet("""
            #powerSys {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)
        sys_layout = QVBoxLayout(sys_frame)
        sys_layout.setContentsMargins(20, 14, 20, 14)
        sys_layout.setSpacing(8)

        sys_title = QLabel("⚙️ System Power")
        sys_title.setStyleSheet("font-size: 13px; color: #AAA; font-weight: bold;")
        sys_layout.addWidget(sys_title)

        sys_btns = QHBoxLayout()
        sys_btns.setSpacing(10)

        sleep_btn = self._make_sys_btn("😴 Sleep", 255, 167, 38, self._power.sleep)
        reboot_btn = self._make_sys_btn("🔄 Reboot", 66, 165, 245, self._power.reboot)
        shutdown_btn = self._make_sys_btn("⏻ Shutdown", 239, 83, 80, self._power.shutdown)

        sys_btns.addWidget(sleep_btn)
        sys_btns.addWidget(reboot_btn)
        sys_btns.addWidget(shutdown_btn)
        sys_layout.addLayout(sys_btns)

        layout.addWidget(sys_frame)

        layout.addStretch()

        # ── Auto-refresh timer ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)  # refresh every 5s

        self._bus.on("battery_changed", self._on_battery_event)
        self._bus.on("charging_state_changed", self._on_charging_event)
        self._bus.on("performance_changed", self._on_perf_change)

    def _make_sys_btn(self, text: str, color_r: int, color_g: int, color_b: int, callback) -> QPushButton:
        btn = QPushButton(text)
        hex_color = f"#{color_r:02x}{color_g:02x}{color_b:02x}".upper()
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({color_r},{color_g},{color_b},0.15);
                border: 1px solid {hex_color}44;
                border-radius: 10px; padding: 10px 20px;
                font-size: 12px; font-weight: bold; color: {hex_color};
            }}
            QPushButton:hover {{
                background: rgba({color_r},{color_g},{color_b},0.25);
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _set_performance(self, mode: str) -> None:
        self._power.set_performance(mode)
        self._perf_desc.setText(PERF_DESC.get(mode, ""))
        NotificationManager().info("Performance", f"Switched to {mode.title()} mode")
        # Update button states
        current = self._power.performance_mode
        for btn in self._perf_btns:
            btn.setChecked(btn.text().startswith(PERF_ICONS.get(current, "")))

    def _refresh(self) -> None:
        pct = self._power.battery_percent
        self._battery_bar.setValue(pct)
        self._battery_bar.setFormat(f"{pct}%")
        self._battery_bar.setStyleSheet(self._battery_style(pct))
        self._temp_card._value_lbl.setText(f"{self._power.battery_temp_c:.0f}°C")
        self._cycles_card._value_lbl.setText(str(self._power.charge_cycles))
        self._current_card._value_lbl.setText(f"{self._power.current_ma:.0f}mA")
        self._voltage_lbl.setText(f"Voltage: {self._power.voltage:.1f}V")
        self._charge_badge.setVisible(self._power.is_charging)
        # Update performance button state
        current = self._power.performance_mode
        for btn in self._perf_btns:
            for mode in PERF_MODES:
                if btn.text().startswith(PERF_ICONS[mode]):
                    btn.setChecked(mode == current)

    def _battery_style(self, pct: int) -> str:
        if pct <= 10:
            color1, color2 = "#D32F2F", "#F44336"
        elif pct <= 20:
            color1, color2 = "#FF8F00", "#FFA000"
        else:
            color1, color2 = "#00C853", "#00E676"
        return f"""
            QProgressBar {{
                background: rgba(255,255,255,0.06);
                border: none; border-radius: 16px;
                text-align: center; font-size: 14px;
                font-weight: bold; color: #FFF;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color1}, stop:1 {color2});
                border-radius: 16px;
            }}
        """

    def _on_battery_event(self, event: Event) -> None:
        self._refresh()

    def _on_charging_event(self, event: Event) -> None:
        self._refresh()

    def _on_perf_change(self, event: Event) -> None:
        self._refresh()

    def on_show(self) -> None:
        self._timer.start(5000)
        self._refresh()

    def on_hide(self) -> None:
        self._timer.stop()
