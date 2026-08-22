"""Tank Shell Dashboard — 3-zone real-time command center.

Zone Layout:
  ┌──────────────────────────────────────────────┐
  │  Zone A: Overview (camera + AI avatar + status)│
  ├──────────────────────┬───────────────────────┤
  │  Zone B: Map/Nav     │  Zone C: Quick Actions │
  │  (robot position,    │  (estop, dock, patrol, │
  │   waypoints, SLAM)   │   diagnostics, power)  │
  └──────────────────────┴───────────────────────┘
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget, QProgressBar,
)

from tank_os.core.ai_manager import AIManager
from tank_os.core.diagnostics_manager import DiagnosticsManager
from tank_os.core.emotion_manager import EmotionManager
from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.hardware_manager import HardwareManager
from tank_os.core.memory_manager import MemoryManager
from tank_os.core.navigation_manager import NavigationManager
from tank_os.core.notification_manager import NotificationManager
from tank_os.core.power_manager import PowerManager
from tank_os.core.robot_manager import RobotManager
from tank_os.core.security_manager import SecurityManager
from tank_os.core.settings_manager import SettingsManager
from tank_os.core.storage_manager import StorageManager
from tank_os.core.vision_manager import VisionManager
from tank_os.widgets.ai_avatar import AIAvatar
from tank_os.widgets.camera_widget import CameraWidget
from tank_os.widgets.map_widget import MapWidget
from tank_os.widgets.status_widget import StatusWidget
from tank_os.widgets.battery_widget import BatteryWidget
from tank_os.widgets.clock_widget import ClockWidget

logger = logging.getLogger("tank_os.shell.dashboard")


class _QuickAction(QPushButton):
    """A dashboard quick-action button with icon, label, and status dot."""

    def __init__(self, icon: str, label: str, color: str = "#00BFFF",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText(f"{icon}\n{label}")
        r, g, b = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba({r},{g},{b},0.08);
                border: 2px solid rgba({r},{g},{b},0.15);
                border-radius: 10px; padding: 10px 8px;
                font-size: 10px; color: {color};
                text-align: center;
            }}
            QPushButton:hover {{
                background: rgba({r},{g},{b},0.18);
                border-color: rgba({r},{g},{b},0.4);
            }}
            QPushButton:pressed {{
                background: rgba({r},{g},{b},0.28);
            }}
        """)
        self.setMinimumHeight(60)


class _MetricTile(QFrame):
    """A compact system metric tile (CPU, RAM, temp, battery, etc.)."""

    def __init__(self, icon: str, label: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricTile")
        self.setStyleSheet("""
            #metricTile {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        ic = QLabel(icon)
        ic.setStyleSheet("font-size: 14px;")
        top.addWidget(ic)
        top.addStretch()

        self._value = QLabel("--")
        self._value.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")
        top.addWidget(self._value)
        layout.addLayout(top)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 8px; color: #777; font-weight: bold;")
        layout.addWidget(lbl)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class Dashboard(QWidget):
    """3-zone command center — the heart of the Tank Shell."""

    # Refresh intervals (ms)
    _REFRESH_METRICS = 3000   # CPU, RAM, temp
    _REFRESH_POWER = 10000    # battery
    _REFRESH_STATUS = 5000    # system status

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._bus = EventBus()
        self._diagnostics = DiagnosticsManager()
        self._power = PowerManager()
        self._emotion = EmotionManager()
        self._settings = SettingsManager()
        self._hardware = HardwareManager()
        self._storage = StorageManager()

        self.setObjectName("dashboard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # ── Top status bar ──
        status_bar = QHBoxLayout()
        status_bar.setSpacing(8)

        self._clock = ClockWidget()
        status_bar.addWidget(self._clock)

        self._system_badge = QLabel("● NOMINAL")
        self._system_badge.setStyleSheet("""
            background: rgba(0,230,118,0.12);
            color: #00E676; border: 1px solid rgba(0,230,118,0.25);
            border-radius: 10px; padding: 3px 10px;
            font-size: 10px; font-weight: bold;
        """)
        status_bar.addWidget(self._system_badge)

        status_bar.addStretch()

        title = QLabel("🤖 TankOS Command Center")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFF;")
        status_bar.addWidget(title)

        status_bar.addStretch()

        self._battery_w = BatteryWidget()
        status_bar.addWidget(self._battery_w)

        layout.addLayout(status_bar)

        # ── Main grid (3 zones) ──
        grid = QGridLayout()
        grid.setSpacing(8)

        # Zone A: Camera feed + AI companion (takes 2 columns, 2 rows)
        zone_a = QFrame()
        zone_a.setObjectName("zoneA")
        zone_a.setStyleSheet("""
            #zoneA {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)
        za_layout = QGridLayout(zone_a)
        za_layout.setContentsMargins(10, 8, 10, 8)
        za_layout.setSpacing(8)

        # Camera
        cam_panel = self._make_mini_panel("📷 Camera Feed")
        self._camera = CameraWidget(show_detections=True)
        self._camera.setMinimumSize(260, 180)
        cam_panel.layout().addWidget(self._camera)
        za_layout.addWidget(cam_panel, 0, 0, 2, 1)

        # AI Avatar
        avatar_panel = self._make_mini_panel("🤗 AI Companion")
        self._avatar = AIAvatar(size=100)
        avatar_panel.layout().addWidget(self._avatar, 0, Qt.AlignCenter)
        za_layout.addWidget(avatar_panel, 0, 1)

        # Emotion state
        emotion_panel = self._make_mini_panel("💭 Emotion")
        self._emotion_lbl = QLabel("neutral")
        self._emotion_lbl.setStyleSheet("font-size: 14px; color: #CCC; font-weight: bold;")
        self._emotion_lbl.setAlignment(Qt.AlignCenter)
        emotion_panel.layout().addWidget(self._emotion_lbl)
        za_layout.addWidget(emotion_panel, 1, 1)

        grid.addWidget(zone_a, 0, 0, 2, 2)

        # Zone B: Map & Navigation
        zone_b = QFrame()
        zone_b.setObjectName("zoneB")
        zone_b.setStyleSheet("""
            #zoneB {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)
        zb_layout = QVBoxLayout(zone_b)
        zb_layout.setContentsMargins(10, 8, 10, 8)
        zb_layout.setSpacing(6)

        map_header = QHBoxLayout()
        map_title = QLabel("🗺 Live Map & Navigation")
        map_title.setStyleSheet("font-size: 11px; color: #888; font-weight: bold;")
        map_header.addWidget(map_title)
        map_header.addStretch()
        self._pose_lbl = QLabel("x: --  y: --  θ: --")
        self._pose_lbl.setStyleSheet("font-size: 9px; color: #555;")
        map_header.addWidget(self._pose_lbl)
        zb_layout.addLayout(map_header)

        self._map = MapWidget()
        self._map.setMinimumSize(200, 140)
        zb_layout.addWidget(self._map, 1)

        # Nav controls
        nav_btns = QHBoxLayout()
        nav_btns.setSpacing(4)
        for icon, label, cb in [
            ("⏹", "Stop", self._on_stop),
            ("🏠", "Home", self._on_home),
            ("⏯", "Resume", self._on_resume),
            ("🔄", "Scan", self._on_nav_scan),
        ]:
            btn = QPushButton(f"{icon} {label}")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 6px; padding: 4px 8px;
                    font-size: 9px; color: #CCC;
                }
                QPushButton:hover { background: rgba(0,191,255,0.15); }
            """)
            btn.clicked.connect(cb)
            nav_btns.addWidget(btn)
        zb_layout.addLayout(nav_btns)

        grid.addWidget(zone_b, 0, 2)

        # Zone C: Quick Actions + System Health
        zone_c = QFrame()
        zone_c.setObjectName("zoneC")
        zone_c.setStyleSheet("""
            #zoneC {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
            }
        """)
        zc_layout = QVBoxLayout(zone_c)
        zc_layout.setContentsMargins(10, 8, 10, 8)
        zc_layout.setSpacing(6)

        # Quick actions grid
        qa_title = QLabel("⚡ Quick Actions")
        qa_title.setStyleSheet("font-size: 11px; color: #888; font-weight: bold;")
        zc_layout.addWidget(qa_title)

        qa_grid = QGridLayout()
        qa_grid.setSpacing(4)

        actions = [
            ("⛔", "E-STOP", "#EF5350", 0, 0, self._on_estop),
            ("📷", "Camera", "#00BFFF", 0, 1, self._on_start_camera),
            ("🔍", "Diagnose", "#FFA726", 0, 2, self._on_diagnose),
            ("🔒", "Lock", "#AB47BC", 1, 0, self._on_lock),
            ("🎙", "Listen", "#42A5F5", 1, 1, self._on_listen),
            ("🗑", "Clear", "#78909C", 1, 2, self._on_clear_notifs),
        ]

        for icon, label, color, row, col, cb in actions:
            btn = _QuickAction(icon, label, color)
            btn.clicked.connect(cb)
            qa_grid.addWidget(btn, row, col)
        zc_layout.addLayout(qa_grid)

        # System health metrics
        health_title = QLabel("📊 System Health")
        health_title.setStyleSheet("font-size: 11px; color: #888; font-weight: bold; padding-top: 4px;")
        zc_layout.addWidget(health_title)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(4)

        self._metric_cpu = _MetricTile("🖥", "CPU")
        self._metric_ram = _MetricTile("🧠", "RAM")
        self._metric_temp = _MetricTile("🌡", "Temp")
        self._metric_disk = _MetricTile("💾", "Disk")
        self._metric_ros = _MetricTile("🔄", "ROS")
        self._metric_uptime = _MetricTile("⏱", "Uptime")

        metrics_grid.addWidget(self._metric_cpu, 0, 0)
        metrics_grid.addWidget(self._metric_ram, 0, 1)
        metrics_grid.addWidget(self._metric_temp, 0, 2)
        metrics_grid.addWidget(self._metric_disk, 1, 0)
        metrics_grid.addWidget(self._metric_ros, 1, 1)
        metrics_grid.addWidget(self._metric_uptime, 1, 2)
        zc_layout.addLayout(metrics_grid)

        grid.addWidget(zone_c, 1, 2)

        layout.addLayout(grid, 1)

        # ── Bottom status bar ──
        bot_bar = QHBoxLayout()
        bot_bar.setSpacing(12)

        self._hardware_count = QLabel("HW: --")
        self._hardware_count.setStyleSheet("font-size: 9px; color: #666;")
        bot_bar.addWidget(self._hardware_count)

        self._notif_count = QLabel("Notifs: 0")
        self._notif_count.setStyleSheet("font-size: 9px; color: #666;")
        bot_bar.addWidget(self._notif_count)

        self._mem_count = QLabel("Mem: 0 entries")
        self._mem_count.setStyleSheet("font-size: 9px; color: #666;")
        bot_bar.addWidget(self._mem_count)

        bot_bar.addStretch()

        self._storage_info = QLabel("Disk: --")
        self._storage_info.setStyleSheet("font-size: 9px; color: #666;")
        bot_bar.addWidget(self._storage_info)

        layout.addLayout(bot_bar)

        # ── Event subscriptions ──
        self._bus.on("emotion_changed", self._on_emotion)
        self._bus.on("battery_changed", self._on_battery)
        self._bus.on("battery_critical", self._on_battery_critical)
        self._bus.on("estop_triggered", self._on_estop_event)
        self._bus.on("notification", self._on_notification_event)
        self._bus.on("hardware_connected", self._on_hw_event)
        self._bus.on("hardware_disconnected", self._on_hw_event)
        self._bus.on("pose_updated", self._on_pose_update)

        # ── Refresh timers ──
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._refresh_metrics)
        self._metrics_timer.start(self._REFRESH_METRICS)

        self._power_timer = QTimer(self)
        self._power_timer.timeout.connect(self._refresh_power)
        self._power_timer.start(self._REFRESH_POWER)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(self._REFRESH_STATUS)

        # Initial refresh
        self._refresh_metrics()
        self._refresh_power()
        self._refresh_status()

    # ── Helpers ──

    @staticmethod
    def _make_mini_panel(title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("dashMiniPanel")
        frame.setStyleSheet("""
            #dashMiniPanel {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 9px; color: #666; font-weight: bold;")
        layout.addWidget(lbl)
        return frame

    # ── Metric refresh ──

    def _refresh_metrics(self) -> None:
        try:
            summary = self._diagnostics.summary()
            self._metric_cpu.set_value(f"{summary.get('cpu', '--')}%")
            self._metric_ram.set_value(f"{summary.get('mem', '--')}%")
            self._metric_temp.set_value(f"{summary.get('temp', '--')}°C")

            # Disk from StorageManager
            try:
                usage = self._storage.usage_summary()
                self._metric_disk.set_value(f"{usage.get('percent', '--')}%")
                self._storage_info.setText(
                    f"Disk: {usage.get('used_gb','--')}/{usage.get('total_gb','--')} GB")
            except Exception:
                self._metric_disk.set_value("--")

            # ROS nodes
            self._metric_ros.set_value(f"{summary.get('ros_nodes', 0)}")

            # Uptime
            try:
                import subprocess
                r = subprocess.run(["uptime", "-p"], capture_output=True,
                                   text=True, timeout=2)
                uptime_str = r.stdout.strip().replace("up ", "")
                self._metric_uptime.set_value(uptime_str[:12])
            except Exception:
                self._metric_uptime.set_value("--")

        except Exception:
            pass

    def _refresh_power(self) -> None:
        pct = self._power.battery_percent
        charging = self._power.is_charging

        # Update system badge color based on battery
        if pct <= 15:
            self._system_badge.setText(f"● {pct}% BATTERY")
            self._system_badge.setStyleSheet("""
                background: rgba(244,67,54,0.15);
                color: #F44336; border: 1px solid rgba(244,67,54,0.3);
                border-radius: 10px; padding: 3px 10px;
                font-size: 10px; font-weight: bold;
            """)

    def _refresh_status(self) -> None:
        # Hardware count
        try:
            hw = self._hardware.detect_all()
            self._hardware_count.setText(f"HW: {len(hw)} devices")
        except Exception:
            pass

        # Memory entries
        try:
            stats = MemoryManager().get_stats()
            self._mem_count.setText(f"Mem: {stats.get('total_entities',0)} entries")
        except Exception:
            pass

    # ── Quick action handlers ──

    def _on_start_camera(self) -> None:
        self._camera.start()
        NotificationManager().info("Camera", "Camera started")

    def _on_estop(self) -> None:
        SecurityManager().estop()
        NotificationManager().warning("E-STOP", "Emergency stop activated!", speech=True)

    def _on_diagnose(self) -> None:
        summary = self._diagnostics.summary()
        NotificationManager().info(
            "Diagnostics",
            f"CPU: {summary.get('cpu')}%, Mem: {summary.get('mem')}%, Temp: {summary.get('temp')}°C"
        )

    def _on_lock(self) -> None:
        from tank_os.core.security_manager import SecurityManager
        SecurityManager().lock()
        NotificationManager().info("Security", "System locked")

    def _on_listen(self) -> None:
        from tank_os.core.voice_manager import VoiceManager
        VoiceManager().start_listening()
        NotificationManager().info("Voice", "Listening...")

    def _on_clear_notifs(self) -> None:
        NotificationManager().dismiss_all()

    def _on_stop(self) -> None:
        RobotManager().stop()
        NotificationManager().info("Robot", "Stopped")

    def _on_home(self) -> None:
        RobotManager().dock()
        NotificationManager().info("Robot", "Returning to dock")

    def _on_resume(self) -> None:
        RobotManager().resume()
        NotificationManager().info("Robot", "Resumed")

    def _on_nav_scan(self) -> None:
        NavigationManager().scan_environment()
        NotificationManager().info("Navigation", "Scanning environment")

    # ── Event handlers ──

    def _on_emotion(self, event: Event) -> None:
        name = event.data.get("name", "neutral")
        self._emotion_lbl.setText(name)

    def _on_battery(self, event: Event) -> None:
        pass  # BatteryWidget handles its own display

    def _on_battery_critical(self, event: Event) -> None:
        pct = event.data.get("percent", "?")
        self._system_badge.setText(f"● {pct}% CRITICAL")
        self._system_badge.setStyleSheet("""
            background: rgba(244,67,54,0.2);
            color: #F44336; border: 1px solid rgba(244,67,54,0.4);
            border-radius: 10px; padding: 3px 10px;
            font-size: 10px; font-weight: bold;
        """)

    def _on_estop_event(self, event: Event) -> None:
        latched = event.data.get("latched", True)
        if latched:
            self._system_badge.setText("● E-STOP")
            self._system_badge.setStyleSheet("""
                background: rgba(244,67,54,0.2);
                color: #F44336; border: 1px solid rgba(244,67,54,0.4);
                border-radius: 10px; padding: 3px 10px;
                font-size: 10px; font-weight: bold;
            """)

    def _on_notification_event(self, event: Event) -> None:
        pass  # NotificationsOverlay handles its own updates

    def _on_hw_event(self, event: Event) -> None:
        self._refresh_status()

    def _on_pose_update(self, event: Event) -> None:
        x = event.data.get("x", 0)
        y = event.data.get("y", 0)
        theta = event.data.get("theta", 0)
        self._pose_lbl.setText(f"x: {x:.1f}  y: {y:.1f}  θ: {theta:.1f}°")

    # ── Lifecycle ──

    def on_show(self) -> None:
        """Called when dashboard becomes visible."""
        self._metrics_timer.start(self._REFRESH_METRICS)
        self._power_timer.start(self._REFRESH_POWER)
        self._status_timer.start(self._REFRESH_STATUS)
        self._refresh_metrics()

    def on_hide(self) -> None:
        """Called when dashboard is hidden."""
        self._metrics_timer.stop()
        self._power_timer.stop()
        self._status_timer.stop()
