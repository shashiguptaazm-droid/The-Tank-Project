"""
Tank Shell — Complete Graphical AI Operating Environment.

This is Layer 4 of TankOS. It provides the full-screen graphical
environment that replaces the desktop.

To run::

    TANKOS_QT=1 python3 -m tank_os.shell.main   # Qt GUI (on Pi with PySide6)
    python3 -m tank_os.shell.main                # simulation mode (any machine)
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from typing import Any, Dict, Optional

from tank_os.core.animation_engine import AnimationEngine, Animation, Easing
from tank_os.core.diagnostics_manager import DiagnosticsManager
from tank_os.core.emotion_manager import EmotionManager
from tank_os.core.event_bus import Event, EventBus, Priority
from tank_os.core.notification_manager import NotificationManager
from tank_os.core.settings_manager import SettingsManager
from tank_os.core.theme_engine import ThemeEngine
from tank_os.core.power_manager import PowerManager
from tank_os.core.charging_manager import ChargingManager
from tank_os.core.preload_manager import PreloadManager
from tank_os.core.ai_manager import AIManager
from tank_os.ai.knowledge_graph import KnowledgeGraph
from tank_os.ai.curiosity_engine import CuriosityEngine
from tank_os.ai.continuous_learning import ContinuousLearningEngine
from tank_os.ai.learning_scheduler import LearningScheduler
from tank_os.ai.experience_engine import ExperienceEngine

# ---------------------------------------------------------------------------
# Module-level helpers for Agent Framework integration
# ---------------------------------------------------------------------------

_RISK_ICONS = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def _close_matches(name: str, candidates: list, n: int = 5) -> list:
    """Fuzzy-match `name` against `candidates` using difflib."""
    try:
        from difflib import get_close_matches
        return get_close_matches(name, candidates, n=n, cutoff=0.4)
    except Exception:
        return []


def _get_tool_registry():
    """Return a ToolRegistry (cached on the function) discovering scripts/.

    The cache is a function attribute so it survives across TankShellCmd
    invocations without introducing module-level init order issues.
    """
    if hasattr(_get_tool_registry, "_cache"):
        return _get_tool_registry._cache
    try:
        from tank_os.agent_framework.registry import ToolRegistry
        from pathlib import Path
        scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
        reg = ToolRegistry(scripts_dir=scripts_dir)
        reg.discover()
        _get_tool_registry._cache = reg
        return reg
    except Exception as e:
        print(f"  ⚠ ToolRegistry unavailable: {e}")
        _get_tool_registry._cache = None
        return None


logger = logging.getLogger("tank_os.shell")

# ---------------------------------------------------------------------------
# Qt detection — all Qt imports are lazy so simulation mode works everywhere
# ---------------------------------------------------------------------------

_USE_QT = os.environ.get("TANKOS_QT", "0") == "1"
_HAS_QT = False
Qt = None
QTimer = None
QApplication = None
QMainWindow = None
QWidget = None
QLabel = None
QStackedWidget = None
QVBoxLayout = None
QHBoxLayout = None
QFrame = None
QPushButton = None
QPropertyAnimation = None
QFont = None

# Screen and widget classes — loaded conditionally
_TankShellMainWindow = None
_HomeScreen = None
_ChatScreen = None
_CameraScreen = None
_NavigationScreen = None
_MemoryScreen = None
_SecurityScreen = None
_PatrolScreen = None
_DiagnosticsScreen = None
_SettingsScreen = None
_DeveloperScreen = None
_AIScreen = None
_TopBar = None
_BottomDock = None
_NotificationsOverlay = None
_Dashboard = None
_PowerScreen = None
_UpdatesScreen = None
_FilesScreen = None
_UsbScreen = None
_DriveScreen = None
_MissionScreen = None
_AIBrainScreen = None
_HealthScreen = None
_FleetScreen = None
_JetsonScreen = None
_CompetitionScreen = None
_EventCenterScreen = None
_SensorsScreen = None
_TopologyScreen = None
_TestCenterScreen = None
_PowerDashboardScreen = None
_NetworkScreen = None
_SecurityCenterScreen = None
_AnalyticsScreen = None
_TvLauncherScreen = None
_AiCommandCenterScreen = None
_AiSafetyCenterScreen = None
_JudgeScreen = None
_DistributedAIScreen = None
_HumanControlScreen = None
_ConstitutionScreen = None
_KnowledgeMapScreen = None
_ToolGraphScreen = None
_TankOSSystemScreen = None
_EvolutionLabScreen = None
_AINativeScreen = None


def _try_load_qt() -> None:
    """Attempt to import PySide6 modules. Sets _HAS_QT on success."""
    global _HAS_QT, Qt, QTimer, QApplication, QMainWindow, QWidget
    global QLabel, QStackedWidget, QVBoxLayout, QHBoxLayout, QFrame
    global QPushButton, QPropertyAnimation, QFont
    global _TankShellMainWindow, _HomeScreen, _ChatScreen, _CameraScreen
    global _NavigationScreen, _MemoryScreen, _SecurityScreen, _PatrolScreen
    global _DiagnosticsScreen, _SettingsScreen, _DeveloperScreen, _AIScreen
    global _TopBar, _BottomDock, _NotificationsOverlay, _Dashboard
    global _PowerScreen, _UpdatesScreen, _FilesScreen, _UsbScreen
    global _DriveScreen, _MissionScreen, _AIBrainScreen, _HealthScreen
    global _FleetScreen, _JetsonScreen, _CompetitionScreen, _EventCenterScreen
    global _SensorsScreen, _TopologyScreen, _TestCenterScreen
    global _PowerDashboardScreen, _NetworkScreen, _SecurityCenterScreen
    global _AnalyticsScreen, _TvLauncherScreen
    global _AiCommandCenterScreen, _AiSafetyCenterScreen, _JudgeScreen
    global _DistributedAIScreen, _HumanControlScreen, _ConstitutionScreen
    global _KnowledgeMapScreen, _ToolGraphScreen, _TankOSSystemScreen
    global _EvolutionLabScreen, _AINativeScreen

    if not _USE_QT:
        return

    try:
        import PySide6  # noqa: F401
    except ImportError:
        return

    from PySide6.QtCore import Qt as _qt, QTimer as _qtimer, QPropertyAnimation as _qanim  # type: ignore
    from PySide6.QtGui import QFont as _qfont  # type: ignore
    from PySide6.QtWidgets import (QApplication as _qapp, QMainWindow as _qmain,  # type: ignore
        QWidget as _qwidget, QLabel as _qlabel, QStackedWidget as _qstack,
        QVBoxLayout as _qvbox, QHBoxLayout as _qhbox, QFrame as _qframe,
        QPushButton as _qbtn)

    Qt, QTimer, QPropertyAnimation, QFont = _qt, _qtimer, _qanim, _qfont
    QApplication, QMainWindow, QWidget, QLabel = _qapp, _qmain, _qwidget, _qlabel
    QStackedWidget, QVBoxLayout, QHBoxLayout = _qstack, _qvbox, _qhbox
    QFrame, QPushButton = _qframe, _qbtn
    _HAS_QT = True

    # Import Qt-dependent UI modules (lazy — they import PySide6 internally)
    from tank_os.widgets.top_bar import TopBar as _tb
    from tank_os.widgets.bottom_dock import BottomDock as _bd
    from tank_os.widgets.notifications_overlay import NotificationsOverlay as _no
    from tank_os.shell.dashboard import Dashboard as _db
    from tank_os.windows.home_screen import HomeScreen as _hs
    from tank_os.windows.chat_screen import ChatScreen as _cs
    from tank_os.windows.camera_screen import CameraScreen as _cms
    from tank_os.windows.navigation_screen import NavigationScreen as _ns
    from tank_os.windows.memory_screen import MemoryScreen as _ms
    from tank_os.windows.security_screen import SecurityScreen as _ss
    from tank_os.windows.patrol_screen import PatrolScreen as _ps
    from tank_os.windows.diagnostics_screen import DiagnosticsScreen as _ds
    from tank_os.windows.settings_screen import SettingsScreen as _sts
    from tank_os.windows.developer_screen import DeveloperScreen as _dvs
    from tank_os.windows.ai_screen import AIScreen as _ais
    from tank_os.windows.power_screen import PowerScreen as _pws
    from tank_os.windows.updates_screen import UpdatesScreen as _ups
    from tank_os.windows.files_screen import FilesScreen as _fls
    from tank_os.windows.usb_screen import UsbScreen as _us
    from tank_os.windows.drive_screen import DriveScreen as _drs
    from tank_os.windows.mission_screen import MissionScreen as _msn
    from tank_os.windows.ai_brain_screen import AIBrainScreen as _abs
    from tank_os.windows.health_screen import HealthScreen as _hls
    from tank_os.windows.fleet_screen import FleetScreen as _flt
    from tank_os.windows.jetson_screen import JetsonScreen as _jts
    from tank_os.windows.competition_screen import CompetitionScreen as _cps
    from tank_os.windows.event_center import EventCenterScreen as _ecs
    from tank_os.windows.sensors_screen import SensorsScreen as _sns
    from tank_os.windows.topology_screen import TopologyScreen as _tps
    from tank_os.windows.test_center import TestCenterScreen as _tcs
    from tank_os.windows.power_dashboard import PowerDashboardScreen as _pds
    from tank_os.windows.network_screen import NetworkScreen as _nws
    from tank_os.windows.security_center import SecurityCenterScreen as _scs
    from tank_os.windows.analytics_screen import AnalyticsScreen as _ans
    from tank_os.windows.tv_launcher import TvLauncherScreen as _tvs
    from tank_os.windows.ai_command_center import AICommandCenterScreen as _acc
    from tank_os.windows.ai_safety_center import AISafetyCenterScreen as _asc
    from tank_os.windows.judge_screen import JudgeScreen as _jgs
    from tank_os.windows.distributed_ai_screen import DistributedAIScreen as _das
    from tank_os.windows.human_control_center import HumanControlCenterScreen as _hcc
    from tank_os.windows.constitution_screen import ConstitutionScreen as _cst
    from tank_os.windows.knowledge_map_screen import KnowledgeMapScreen as _kms
    from tank_os.windows.tool_graph_screen import ToolGraphScreen as _tgs
    from tank_os.windows.tankos_system_screen import TankOSSystemScreen as _tss
    from tank_os.windows.evolution_lab import EvolutionLabScreen as _evs
    from tank_os.windows.ai_native_screen import AINativeScreen as _ans

    _TopBar, _BottomDock, _NotificationsOverlay, _Dashboard = _tb, _bd, _no, _db
    _HomeScreen, _ChatScreen, _CameraScreen = _hs, _cs, _cms
    _NavigationScreen, _MemoryScreen, _SecurityScreen = _ns, _ms, _ss
    _PatrolScreen, _DiagnosticsScreen = _ps, _ds
    _SettingsScreen, _DeveloperScreen, _AIScreen = _sts, _dvs, _ais
    _PowerScreen, _UpdatesScreen, _FilesScreen = _pws, _ups, _fls
    _UsbScreen = _us
    _DriveScreen, _MissionScreen = _drs, _msn
    _AIBrainScreen, _HealthScreen = _abs, _hls
    _FleetScreen, _JetsonScreen = _flt, _jts
    _CompetitionScreen, _EventCenterScreen = _cps, _ecs
    _SensorsScreen, _TopologyScreen = _sns, _tps
    _TestCenterScreen, _PowerDashboardScreen = _tcs, _pds
    _NetworkScreen, _SecurityCenterScreen = _nws, _scs
    _AnalyticsScreen, _TvLauncherScreen = _ans, _tvs
    _AiCommandCenterScreen, _AiSafetyCenterScreen = _acc, _asc
    _JudgeScreen, _DistributedAIScreen = _jgs, _das
    _HumanControlScreen, _ConstitutionScreen = _hcc, _cst
    _KnowledgeMapScreen, _ToolGraphScreen = _kms, _tgs
    _TankOSSystemScreen, _EvolutionLabScreen = _tss, _evs
    _AINativeScreen = _ans

    # Build TankShellMainWindow class (depends on Qt symbols)
    _TankShellMainWindow = _build_main_window_class()


def _build_main_window_class():
    """Factory that creates TankShellMainWindow after Qt symbols are loaded."""

    ScreenMap: Dict[str, Any] = {
        "home": _HomeScreen,
        "chat": _ChatScreen,
        "camera": _CameraScreen,
        "navigation": _NavigationScreen,
        "memory": _MemoryScreen,
        "security": _SecurityScreen,
        "patrol": _PatrolScreen,
        "diagnostics": _DiagnosticsScreen,
        "settings": _SettingsScreen,
        "developer": _DeveloperScreen,
        "ai": _AIScreen,
        "power": _PowerScreen,
        "updates": _UpdatesScreen,
        "files": _FilesScreen,
        "usb": _UsbScreen,
        # ── GUI blueprint additions (core-7 + extras) ────────────────
        "drive": _DriveScreen,          # 🕹 Drive
        "mission": _MissionScreen,      # 🎯 Mission Control
        "brain": _AIBrainScreen,        # 🧠 AI Brain
        "health": _HealthScreen,        # 🩺 Robot Health
        "fleet": _FleetScreen,          # 🟢 ESP32 Fleet
        "jetson": _JetsonScreen,        # 🟧 Jetson Dashboard
        "competition": _CompetitionScreen,  # 🏆 Competition Mode
        "events": _EventCenterScreen,   # 🚨 Event Center
        # ── GUI blueprint wave 2 ─────────────────────────────────────
        "sensors": _SensorsScreen,     # 📡 Sensor Fusion
        "topology": _TopologyScreen,   # 🧩 Hardware Topology
        "test-center": _TestCenterScreen,  # 🧪 Testing Center
        "power-dash": _PowerDashboardScreen,  # 🔋 Power Dashboard
        "network": _NetworkScreen,     # 📡 Network
        "security": _SecurityCenterScreen,  # 🔐 Security Center
        "analytics": _AnalyticsScreen,  # 📊 Data / Analytics
        "tv": _TvLauncherScreen,       # 📺 TV launcher (10-foot)
        # ── 200-feature GUI+AI plan ──────────────────────────────────
        "ai-command": _AiCommandCenterScreen,   # 🧠 AI Command Center
        "ai-safety": _AiSafetyCenterScreen,     # 🔥 AI Safety Center
        "judge": _JudgeScreen,                  # 🏆 Judge Mode
        "distributed-ai": _DistributedAIScreen, # 🌐 Distributed-AI
        # ── Human coordination + originality plan ──────────────────────
        "human": _HumanControlScreen,           # 👤 Human Control Center
        "constitution": _ConstitutionScreen,    # 🌟 Robot Constitution + AI Debate
        "knowledge-map": _KnowledgeMapScreen,   # 🧠 Robot Knowledge Map
        "tool-graph": _ToolGraphScreen,         # 🧠 AI Tool Graph
        "system": _TankOSSystemScreen,          # 🤖 TankOS proper (system view)
        "evolution": _EvolutionLabScreen,       # 🧬 Evolution Lab
        "ai-native": _AINativeScreen,           # 🧠 Native AI (capability-based)
    }

    class TankShellMainWindow(QMainWindow):
        """The main full-screen window of TankOS.

        Layout::

            ┌──────────────────────────────────────────┐
            │  TopBar (system status, clock, battery)  │
            ├──────────────────────────────────────────┤
            │  Screen Area (QStackedWidget)            │
            │  - Home / Chat / Camera / Navigation     │
            │  - Memory / Security / Patrol            │
            │  - Diagnostics / Settings / Developer    │
            ├──────────────────────────────────────────┤
            │  BottomDock (screen navigation)          │
            └──────────────────────────────────────────┘
        """

        def __init__(self) -> None:
            super().__init__()
            self._bus = EventBus()
            self._settings = SettingsManager()
            self._theme = ThemeEngine()
            self._animations = AnimationEngine()
            self._diagnostics = DiagnosticsManager()
            self._emotion = EmotionManager()
            self._notifications = NotificationManager()
            self._power = PowerManager()

            self._current_screen = "home"
            self._loaded_screens: Dict[str, QWidget] = {}

            self._setup_window()
            self._setup_ui()
            self._connect_events()
            self._apply_theme()

            QTimer.singleShot(200, self._on_boot_complete)

        def _setup_window(self) -> None:
            self.setWindowTitle("TankOS — Intelligent Robotic Operating System")
            self.setWindowFlags(
                Qt.FramelessWindowHint if self._settings.get("display.fullscreen", True)
                else Qt.Window
            )
            self.setStyleSheet("background-color: #0D0D1A; color: #FFFFFF;")
            self.showFullScreen()
            self.setCursor(Qt.BlankCursor)
            self.setMinimumSize(640, 400)

        def _setup_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QVBoxLayout(central)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # Top Bar
            self._top_bar = _TopBar()
            self._top_bar.notification_clicked.connect(self._toggle_notifications)
            main_layout.addWidget(self._top_bar)

            # Screen Area
            self._stack = QStackedWidget()
            self._stack.setStyleSheet("background: transparent;")
            main_layout.addWidget(self._stack, 1)
            self._load_screen("home")

            # Bottom Dock
            self._dock = _BottomDock()
            self._dock.screen_changed.connect(self._navigate_to)
            main_layout.addWidget(self._dock)

            # i18n — apply the persisted language to the dock at boot
            try:
                from tank_os.core.i18n import I18nManager  # noqa: PLC0415
                lang = self._settings.get("i18n.language", "en") or "en"
                I18nManager().set_language(lang)
                self._dock.apply_language(lang)
            except Exception as exc:  # noqa: BLE001
                logger.warning("i18n boot apply skipped: %s", exc)

            # Notifications overlay (floating)
            self._notif_overlay = _NotificationsOverlay(self)

        def _load_screen(self, name: str) -> QWidget:
            if name in self._loaded_screens:
                return self._loaded_screens[name]
            cls = ScreenMap.get(name)
            if cls is None:
                logger.warning("Unknown screen: %s", name)
                return self._load_screen("home")
            try:
                screen = cls()
                self._loaded_screens[name] = screen
                self._stack.addWidget(screen)
                return screen
            except Exception as exc:
                logger.exception("Failed to load screen %s: %s", name, exc)
                err = QLabel(f"⚠️ Screen '{name}' failed to load")
                err.setAlignment(Qt.AlignCenter)
                err.setStyleSheet("font-size: 14px; color: #FF5252; padding: 40px;")
                self._loaded_screens[name] = err
                self._stack.addWidget(err)
                return err

        def _navigate_to(self, screen: str) -> None:
            if screen == self._current_screen:
                return
            widget = self._load_screen(screen)
            self._stack.setCurrentWidget(widget)
            self._current_screen = screen
            self._dock.set_active(screen)
            self._bus.emit(Event("screen_changed", {"screen": screen},
                                 source="tank_shell"))

        def _connect_events(self) -> None:
            self._bus.on("battery_critical", self._on_battery_critical)
            self._bus.on("theme_changed", self._on_theme_changed)
            self._bus.on("estop_triggered", self._on_estop)
            self._bus.on("hardware_connected", self._on_hardware_event)
            self._bus.on("hardware_disconnected", self._on_hardware_event)
            self._bus.on("navigate", self._on_navigate_request)
            self._bus.on("language_changed", self._on_language_changed)

        def _on_battery_critical(self, event: Event) -> None:
            self._notifications.error(
                "🔋 Battery Critical",
                f"Battery at {event.data.get('percent', '?')}% — please charge!",
                speech=True, persistent=True,
            )

        def _on_theme_changed(self, event: Event) -> None:
            self._apply_theme()

        def _on_estop(self, event: Event) -> None:
            latched = event.data.get("latched", True)
            if latched:
                self._notifications.notify(
                    "⛔ EMERGENCY STOP",
                    "E-STOP latched — all motion halted!",
                    priority=Priority.CRITICAL, speech=True, persistent=True,
                )
            else:
                self._notifications.info("E-STOP", "Emergency stop released.")

        def _on_navigate_request(self, event: Event) -> None:
            screen = event.data.get("screen")
            if screen in ScreenMap:
                self._navigate_to(screen)

        def _on_language_changed(self, event: Event) -> None:
            """Re-translate the dock + current screen (i18n)."""
            code = event.data.get("code", "en")
            try:
                from tank_os.core.i18n import (  # noqa: PLC0415
                    I18nManager, translate_widget_tree,
                )
                I18nManager().set_language(code)
                self._dock.apply_language(code)
                current = self._loaded_screens.get(self._current_screen)
                if current is not None:
                    translate_widget_tree(current)
                self._settings.set("i18n.language", code)
                self._settings.save()
            except Exception as exc:  # noqa: BLE001
                logger.warning("language change apply failed: %s", exc)

        def _on_hardware_event(self, event: Event) -> None:
            name = event.data.get("name", "device")
            if event.type == "hardware_connected":
                self._notifications.info("Hardware", f"✓ {name} connected")
            elif event.type == "hardware_disconnected":
                self._notifications.warning("Hardware", f"✗ {name} disconnected")

        def _apply_theme(self) -> None:
            self._theme.apply_to(self)

        def _toggle_notifications(self) -> None:
            self._notif_overlay.toggle()
            if self._notif_overlay.isVisible():
                parent_rect = self.rect()
                ox = parent_rect.width() - self._notif_overlay.width() - 16
                self._notif_overlay.move(ox, self._top_bar.height() + 8)
                self._notif_overlay.raise_()

        def _on_boot_complete(self) -> None:
            self._bus.emit(Event("shell_ready", {"screen": self._current_screen},
                                 source="tank_shell"))
            logger.info("Tank Shell ready — accepting user interaction")

        def keyPressEvent(self, event) -> None:  # noqa: N802
            key = event.key()
            if key == Qt.Key_Escape:
                self._navigate_to("home")
            elif key == Qt.Key_F11:
                if self.isFullScreen(): self.showNormal()
                else: self.showFullScreen()
            elif key == Qt.Key_N:
                self._toggle_notifications()
            elif key == Qt.Key_Q and event.modifiers() & Qt.ControlModifier:
                self.close()
            super().keyPressEvent(event)

        def closeEvent(self, event) -> None:  # noqa: N802
            self._bus.emit(Event("shell_shutdown", {}, source="tank_shell"))
            logger.info("Tank Shell shutting down")
            super().closeEvent(event)

    return TankShellMainWindow


# =========================================================================
# TankShell — Entry point (works with or without Qt)
# =========================================================================

class TankShell:
    """Tank Shell — the complete graphical OS environment.

    Manages the Qt application lifecycle, screen navigation, dashboard
    layout, window management, and the event-driven UI lifecycle.
    Works in full Qt mode (with PySide6 on Pi) or simulation mode (text).
    """

    def __init__(self) -> None:
        self._bus = EventBus()
        self._settings = SettingsManager()
        self._running = False
        _try_load_qt()
        self._simulation = not (_HAS_QT)
        self._qt_app: Any = None
        self._main_window: Any = None

    def initialize(self) -> None:
        """Initialize shell subsystems, including PreloadManager."""
        self._settings.initialize()

        # Initialize core subsystems
        ThemeEngine().initialize()
        AnimationEngine().start(fps=60)

        # Initialize charging system
        try:
            ChargingManager().initialize()
        except Exception as exc:
            logger.warning("Charging system init skipped: %s", exc)

        # ── PreloadManager: scan dependencies & start background preload ──
        self._preload = PreloadManager()
        self._preload_running = False
        try:
            self._preload.initialize()
            logger.info("Preload: %d/%d deps installed (offline=%s)",
                         self._preload.report().downloaded,
                         self._preload.report().total_items,
                         self._preload.is_offline)

            # If online and missing items, start background download
            if not self._preload.is_offline and not self._preload.is_ready:
                self._start_background_preload()
        except Exception as exc:
            logger.warning("PreloadManager init skipped: %s", exc)
            self._preload = None

        # ── AI Manager ──
        try:
            AIManager().initialize()
        except Exception as exc:
            logger.warning("AIManager init skipped: %s", exc)

        # ── Evolution Bridge: wire real LLM providers into AIManager ──
        try:
            from tank_os.core.evolution_bridge import init_evolution_providers
            n = init_evolution_providers(
                discover_models=False,    # skip slow API discovery (~15s)
                register_local=True,
                preload_local=False,      # defer GGUF load to background thread
                register_rotation=True,
                set_rotation_default=True,
            )
            logger.info("Evolution bridge: %d providers registered", n)
        except ImportError:
            logger.info("Evolution bridge not available (evolution module not installed)")
        except Exception as exc:
            logger.warning("Evolution bridge init skipped: %s", exc)

        # ── AI Engine initialization (DISABLED by default — saves RAM) ──
        # Enable with: export TANK_PRELOAD_LLM=1 (also enables local LLM)
        self._ai_initialized = False
        if os.environ.get("TANK_PRELOAD_LLM", "") == "1":
            try:
                import threading
                def _init_ai_engines():
                    try:
                        ExperienceEngine().initialize()
                        KnowledgeGraph().initialize()
                        CuriosityEngine().initialize()
                        ContinuousLearningEngine().initialize()
                        LearningScheduler().initialize()
                        LearningScheduler().start()
                        self._ai_initialized = True
                        logger.info("AI engines initialized (background)")
                    except Exception as exc:
                        logger.debug("AI engine init skipped: %s", exc)
                threading.Thread(target=_init_ai_engines, daemon=True,
                                 name="ai-engines-init").start()
            except Exception as exc:
                logger.warning("AI engine init skipped: %s", exc)

        # ── Preload local LLM in background (DISABLED by default — saves 600+ MB RAM) ──
        # Enable with: export TANK_PRELOAD_LLM=1
        if os.environ.get("TANK_PRELOAD_LLM", "") == "1":
            try:
                import threading
                def _preload_llm():
                    try:
                        from tank_os.core.ai_manager import AIManager
                        from tank_os.core.local_llm_provider import (
                            LocalLlamaProvider, discover_gguf_models,
                        )
                        ai = AIManager()
                        preload_model = os.environ.get(
                            "TANK_PRELOAD_MODEL", "").strip().lower()
                        if preload_model:
                            models = discover_gguf_models()
                            match = next(
                                (m for m in models
                                 if preload_model in m.name.lower()),
                                None,
                            )
                            if match is not None:
                                llm = LocalLlamaProvider(model_path=match.path)
                                if llm.ensure_loaded():
                                    ai.register_provider("local-llama", llm)
                                    return
                        provider = ai.get_provider("local-llama")
                        if (provider is not None
                                and hasattr(provider, "ensure_loaded")):
                            if provider.ensure_loaded():
                                try:
                                    provider.chat(".", max_tokens=1)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                threading.Thread(target=_preload_llm, daemon=True,
                                 name="local-llm-preload").start()
            except Exception:
                pass

        if not self._simulation:
            self._init_qt()
        else:
            self._init_simulation()

        self._bus.emit(Event("shell_initialized", {
            "mode": "simulation" if self._simulation else "qt",
            "screen": "home",
        }, source="tank_shell"))
        logger.info("Tank Shell initialized (mode=%s)",
                     "simulation" if self._simulation else "qt")

    def _start_background_preload(self) -> None:
        """Start downloading missing dependencies in a background thread.

        Uses the EventBus to emit progress notifications that the UI
        (or simulation mode) can display to the user.
        """
        import threading

        if self._preload_running:
            return
        self._preload_running = True

        def _download_worker():
            logger.info("Preload: starting background download of missing deps...")
            self._bus.emit(Event("preload_status", {
                "status": "starting",
                "message": "Checking missing dependencies...",
            }, source="tank_shell"))

            if self._preload:
                def _on_item(progress):
                    if progress.status.value == "completed":
                        logger.info("Preload: downloaded %s", progress.item_id)
                        self._bus.emit(Event("preload_status", {
                            "status": "progress",
                            "item": progress.item_id,
                            "percent": progress.percent,
                            "message": f"Downloaded: {progress.item_id}",
                        }, source="tank_shell"))
                    elif progress.status.value == "failed":
                        logger.warning("Preload: failed %s — %s",
                                       progress.item_id, progress.error)
                        self._bus.emit(Event("preload_status", {
                            "status": "error",
                            "item": progress.item_id,
                            "error": progress.error or "Unknown",
                            "message": f"Failed: {progress.item_id}",
                        }, source="tank_shell"))

                result = self._preload.download_required(
                    progress_callback=_on_item
                )

                if result.failed == 0:
                    logger.info("Preload: all required deps downloaded successfully")
                    self._bus.emit(Event("preload_status", {
                        "status": "complete",
                        "message": "All dependencies ready",
                    }, source="tank_shell"))
                else:
                    logger.warning("Preload: %d deps failed to download", result.failed)
                    self._bus.emit(Event("preload_status", {
                        "status": "partial",
                        "message": f"{result.failed} dependencies failed",
                    }, source="tank_shell"))

            self._preload_running = False

        thread = threading.Thread(
            target=_download_worker,
            daemon=True,
            name="preload-bg"
        )
        thread.start()
        logger.info("Preload: background download thread started")

    def _init_qt(self) -> None:
        """Initialize PySide6 Qt Application and main window."""
        try:
            self._qt_app = QApplication(sys.argv)
            self._qt_app.setApplicationName("TankOS")
            self._qt_app.setOrganizationName("TankProject")
            self._qt_app.setApplicationVersion("1.0.0")
            self._main_window = _TankShellMainWindow()
            logger.info("Qt GUI initialized — TankShellMainWindow created")
        except Exception as exc:
            logger.warning("Qt init failed, falling back to simulation: %s", exc)
            self._simulation = True
            self._init_simulation()

    def _init_simulation(self) -> None:
        """Initialize text-based simulation mode."""
        self._bus.on("notification", self._sim_notification)
        logger.info("Simulation mode active — all 10 screens available via CLI")

    def _sim_notification(self, event: Event) -> None:
        print(f"[{event.data.get('priority', 'INFO')}] "
              f"{event.data.get('title', '')}: {event.data.get('message', '')}")

    def navigate(self, screen: str) -> None:
        """Navigate to a screen by name."""
        if self._main_window:
            self._main_window._navigate_to(screen)
        else:
            self._bus.emit(Event("screen_changed", {"screen": screen},
                                 source="tank_shell"))
            print(f"  → Navigated to: {screen}")
        logger.info("Navigated to screen: %s", screen)

    def run(self) -> int:
        """Start the Tank Shell main loop. Returns exit code."""
        self._running = True
        self._bus.emit(Event("shell_started", {}, source="tank_shell"))

        if not self._simulation and self._qt_app:
            return self._qt_app.exec()

        self._run_simulation_loop()
        return 0

    def _run_simulation_loop(self) -> None:
        """Interactive CLI loop for dev/CI — demonstrates all screens."""
        print("\n" + "=" * 56)
        print("  ╔══════════════════════════════════════╗")
        print("  ║       🤖  TankOS Shell v1.0.0       ║")
        print("  ║    Graphical AI Operating Environment ║")
        print("  ╚══════════════════════════════════════╝")
        print("=" * 56)
        print()
        print("  🖥 Available Screens:")
        print("     home       — Command Center Dashboard")
        print("     chat       — AI Assistant Chat")
        print("     camera     — Live Camera & Vision")
        print("     nav        — Navigation & SLAM Map")
        print("     memory     — Memory Explorer")
        print("     security   — Security & Surveillance")
        print("     patrol     — Patrol & Missions")
        print("     diag       — System Diagnostics")
        print("     settings   — System Settings")
        print("     dev        — Developer Tools")
        print("     ai         — AI Engine Dashboard")
        print("     power      — Power & Battery Management")
        print("     updates    — Software Updates")
        print("     files      — Files & Storage")
        print("     usb        — USB Devices")
        print()
        print("  💻 Commands: terminal — drop into the AI terminal REPL")
        print("  🌊 Commands: torrent <query> — search torrents → pick → download")
        print("  🧠 AI Engines: curiosity, knowledge, learning (enable: TANKOS_FULL=1)")
        print("  📦 Tools: tools, tool <name> (list ~1,166 Agent Framework tools)")
        print("  🔍 Commands: search <q>, find <q> — search everywhere (torrent, web, GitHub, YouTube)")
        print("  🔮 Commands: discover <topic> — search + learn from GitHub in one step")
        print("  🧠 Commands: learn <topic> — AI learns scripts/tools from GitHub READMEs")
        print("  🧬 Commands: evolve — daily self-evolution cycle")
        print("  🔧 Commands: apply — install discovered tools from learned knowledge")
        print("  📋 Commands: status, preload (deps), help, quit")

        try:
            import cmd as _cmd
        except ImportError:
            self._simple_loop()
            return

        class TankShellCmd(_cmd.Cmd):
            prompt = "\ntankos> "
            intro = ""
            _last_screen = ""

            def __init__(self, shell: TankShell):
                super().__init__()
                self._shell = shell

            def _show_screen(self, name: str, icon: str, title: str) -> None:
                width = 56
                print()
                print("┌" + "─" * (width - 2) + "┐")
                print(f"│  {icon}  {title:<{width - 8}}│")
                print("└" + "─" * (width - 2) + "┘")
                self._shell.navigate(name)
                self._last_screen = name

            def do_terminal(self, _arg):
                """Drop into the AI-powered terminal REPL (type `exit` to
                return to the TankOS shell)."""
                print("  🤖 Dropping into AI Terminal — type `exit` to return.\n")
                try:
                    from tank_os.shell.terminal.cli import TerminalREPL
                    TerminalREPL().cmdloop()
                except (KeyboardInterrupt, EOFError):
                    print("\n  ↩ returning to TankOS shell.")

            def do_home(self, _):
                self._show_screen("home", "🏠", "Command Center Dashboard")
                print("  Camera | AI Avatar | Live Map | System Health")

            def do_power(self, _):
                self._show_screen("power", "🔋", "Power & Battery Management")
                print("  Battery level | Performance mode | Sleep/Reboot/Shutdown")

            def do_updates(self, _):
                self._show_screen("updates", "🔄", "Software Updates")
                print("  Check | Apply | Rollback | History")

            def do_files(self, _):
                self._show_screen("files", "📁", "Files & Storage")
                print("  Volumes | File browser | Disk usage analyzer")

            def do_usb(self, _):
                self._show_screen("usb", "🔌", "USB Devices")
                print("  Live device tree | VID:PID | Class | Speed | Drivers | TTY")

            def do_chat(self, _):
                self._show_screen("chat", "💬", "AI Assistant Chat")
                print("  Conversational AI — ask me anything")

            def do_camera(self, _):
                self._show_screen("camera", "📷", "Camera & Vision")
                print("  Live camera | YOLO detections | Object tracking")

            def do_nav(self, _):
                self._show_screen("navigation", "🗺", "Navigation & SLAM")
                print("  Robot position | Waypoints | Drive controls")

            def do_memory(self, _):
                self._show_screen("memory", "🧠", "Memory Explorer")
                print("  Conversations | Episodic memory | Vector search")

            def do_security(self, _):
                self._show_screen("security", "🛡", "Security & Safety")
                print("  Surveillance | E-Stop | Authentication")

            def do_patrol(self, _):
                self._show_screen("patrol", "🚁", "Patrol & Missions")
                print("  Random / Loop / Station / Mission modes")

            def do_diag(self, _):
                self._show_screen("diagnostics", "🔍", "System Diagnostics")
                print("  CPU | RAM | Disk | Temp | Network | ROS")

            def do_settings(self, _):
                self._show_screen("settings", "⚙️", "System Settings")
                print("  8 categories: Network, Audio, Voice, AI, Display, Power, Privacy, Developer")

            def do_dev(self, _):
                self._show_screen("developer", "🛠", "Developer Mode")
                print("  ROS Topics | Event Bus | Terminal | Packages | Performance")

            # do_ai already defined above — text-based overview
            # do_ai_screen already defined above — screen navigation

            def do_status(self, _):
                try:
                    from tank_os.core.diagnostics_manager import DiagnosticsManager
                    d = DiagnosticsManager().summary()
                    from tank_os.core.power_manager import PowerManager
                    p = PowerManager()
                    print(f"  🖥 CPU: {d.get('cpu', '?')}%  🧠 RAM: {d.get('mem', '?')}%")
                    print(f"  💾 Disk: {d.get('disk', '?')}%  🌡 Temp: {d.get('temp', '?')}°C")
                    print(f"  🔋 Battery: {p.battery_percent}% {'⚡' if p.is_charging else '🔋'}")
                    print(f"  🔄 ROS: {d.get('ros_nodes', 0)} nodes")
                    print(f"  📺 Screen: {self._last_screen or 'home'}")
                    ec = self._shell._bus.registered_types()
                    print(f"  📡 EventBus: {len(ec)} event types")
                except Exception as e:
                    print(f"  Diagnostics: {e}")

            def do_preload(self, _):
                """Show preload status."""
                try:
                    pm = PreloadManager()
                    r = pm.report()
                    print(f"  📦 Preload: {r.state.value}")
                    print(f"  Total: {r.total_items} | Installed: {r.downloaded} | "
                          f"Failed: {r.failed} | Skipped: {r.skipped}")
                    print(f"  Size: {r.total_size_mb:.0f} MB | "
                          f"Downloaded: {r.downloaded_mb:.0f} MB")
                    print(f"  Offline mode: {r.offline}")
                    if r.errors:
                        print(f"  Errors ({len(r.errors)}):")
                        for err in r.errors[:3]:
                            print(f"    ✗ {err}")
                except Exception as e:
                    print(f"  Preload unavailable: {e}")

            # ── Tab-completion for Agent Framework Tool Commands ──

            _TOOLS_FLAGS = ["--category", "--risk", "--count", "--all", "--json"]

            def complete_tools(self, text: str, line: str, begidx: int, endidx: int) -> list:
                """Tab-complete 'tools --category <cat>' or 'tools --<flag>'."""
                if text.startswith("--"):
                    return [f for f in self._TOOLS_FLAGS if f.startswith(text.lower())]
                reg = _get_tool_registry()
                if reg is None:
                    return []
                try:
                    cats = sorted(reg.categories().keys())
                except Exception:
                    cats = []
                if not text:
                    return cats
                return [c for c in cats if c.startswith(text.lower())]

            def complete_tool(self, text: str, line: str, begidx: int, endidx: int) -> list:
                """Tab-complete 'tool <name>' from the live ToolRegistry."""
                reg = _get_tool_registry()
                if reg is None:
                    return []
                try:
                    names = sorted(t.name for t in reg.list())
                except Exception:
                    return []
                if not text:
                    return names[:50]
                return [n for n in names if n.lower().startswith(text.lower())][:50]

            # ── Agent Framework Tool Commands ──

            def do_tools(self, arg):
                """List all ~1,166 Agent Framework tools.

                Usage: tools [--category <cat>] [--risk <tier>]
                             [--count] [--all] [--json]
                """
                reg = _get_tool_registry()
                if reg is None:
                    return

                args = (arg or "").strip().lower().split()
                show_count = "--count" in args
                show_json = "--json" in args
                show_all = "--all" in args
                category_filter = None
                risk_filter = None

                for i, a in enumerate(args):
                    if a == "--category" and i + 1 < len(args):
                        category_filter = args[i + 1]
                    if a == "--risk" and i + 1 < len(args):
                        risk_filter = args[i + 1]

                try:
                    cats = reg.categories()
                    tools = reg.list()
                except Exception as e:
                    print(f"  ⚠ Registry read failed: {e}\n")
                    return

                # ── JSON mode ──
                if show_json:
                    import json as _json
                    print(_json.dumps(reg.as_dict(), indent=2))
                    print()
                    return

                # ── Count mode ──
                if show_count:
                    print()
                    print(f"  📦  Tool Registry — {len(tools)} tools in {len(cats)} categories")
                    print()
                    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
                        bar = "█" * min(count, 30)
                        print(f"    {cat:<25} {bar} {count}")
                    print()
                    return

                # Filter
                filtered = list(tools)
                if category_filter:
                    filtered = [t for t in filtered if t.category == category_filter]
                if risk_filter:
                    filtered = [t for t in filtered if t.risk_tier == risk_filter]
                filtered.sort(key=lambda t: t.name)

                print()
                print("  ┌──────────────────────────────────────────────────┐")
                print("  │           📦  Agent Framework Tools             │")
                print("  └──────────────────────────────────────────────────┘")
                print()

                if category_filter:
                    print(f"  Category: {category_filter}")
                if risk_filter:
                    print(f"  Risk:     {risk_filter}")
                if not category_filter and not risk_filter:
                    print(f"  {len(filtered)} tools in {len(cats)} categories")
                print()

                if not filtered:
                    print("  (no matching tools)\n")
                    return

                max_show = len(filtered) if show_all else 30
                for t in filtered[:max_show]:
                    icon = _RISK_ICONS.get(t.risk_tier, "⚪")
                    desc = (t.description or "").strip()[:90]
                    print(f"  {icon} {t.name}")
                    if desc:
                        print(f"     {desc}")
                    print()

                if len(filtered) > max_show:
                    print(f"  ... and {len(filtered) - max_show} more "
                          f"(use --all to show all)\n")

                print("  (try 'tool <name>' for details)\n")

            def do_torrent(self, arg):
                """Search torrent sites and download via interactive picker.

                Usage: torrent <search query>
                Delegates to the AI terminal REPL's torrent command.
                """
                if not (arg or "").strip():
                    print("  Usage: torrent <search query>")
                    print("  Example: torrent game of thrones")
                    return
                try:
                    from tank_os.shell.terminal.cli import TerminalREPL
                    TerminalREPL().do_torrent(arg)
                except Exception as e:
                    print(f"  ❌ Torrent command failed: {e}")

            complete_torrent = complete_tool  # tab-completion via ToolRegistry

            def do_search(self, arg):
                """Search everywhere — torrents, YouTube, web, GitHub.

                Usage: search <query>           search all sources
                       search --torrent <q>     torrents only
                       search --github <q>      GitHub repos only
                       search --web <q>         web search only
                       search --youtube <q>     YouTube only
                       search --history         view search log
                """
                if not (arg or "").strip():
                    print("  Usage: search <query>")
                    print("  Options: --torrent, --github, --web, --youtube, --history, --interactive")
                    print("  Example: search game of thrones")
                    print("           search --github aria2")
                    return
                try:
                    from pathlib import Path
                    import subprocess
                    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
                    script = scripts_dir / "search_everything.py"
                    args = arg.strip().split()
                    # Forward all args to the search script
                    subprocess.run(
                        ["python3", str(script)] + args,
                        cwd=str(scripts_dir.parent),
                    )
                except Exception as e:
                    print(f"  ❌ Search command failed: {e}")

            do_find = do_search  # alias 'find' → 'search'

            complete_search = complete_tool  # tab-completion via ToolRegistry
            complete_find = complete_search

            def do_discover(self, arg):
                """Search everywhere + learn from GitHub in one step.

                Usage: discover <topic>
                Combines search_everything + ai_github_learner.
                """
                a = (arg or "").strip()
                if not a:
                    print("  Usage: discover <topic>")
                    print("  Example: discover sms bomber")
                    return
                try:
                    from pathlib import Path
                    import subprocess
                    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
                    script = scripts_dir / "discover.py"
                    subprocess.run(
                        ["python3", str(script), a],
                        cwd=str(scripts_dir.parent),
                    )
                except Exception as e:
                    print(f"  ❌ Discover command failed: {e}")

            complete_discover = complete_tool

            def do_evolve(self, arg):
                """Run the daily self-evolution cycle.

                Self-maintaining: new discoveries get added to the ability map
                and persist across sessions. Changelog tracks every change.
                Usage: evolve              full cycle (learn + discover + expand)
                       evolve --discover   discover new abilities only
                       evolve --report     show evolution history
                       evolve --changelog  show daily changelog of map changes
                       evolve --list       list current self-maintained ability map
                """
                a = (arg or "").strip()
                try:
                    from pathlib import Path
                    import subprocess
                    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
                    script = scripts_dir / "daily_evolution.py"
                    subprocess.run(
                        ["python3", str(script)] + (a.split() if a else []),
                        cwd=str(scripts_dir.parent),
                    )
                except Exception as e:
                    print(f"  ❌ Evolution command failed: {e}")

            complete_evolve = complete_tool

            def do_learn(self, arg):
                """AI learns scripts/tools from GitHub repositories.

                Usage: learn <topic>           search GitHub, read READMEs, extract knowledge
                       learn --auto            auto-learn from ALL TankOS abilities
                       learn --auto --category torrent   learn one category
                       learn --query <q>        query learned knowledge
                       learn --list             list learned knowledge files
                """
                a = (arg or "").strip()
                try:
                    from pathlib import Path
                    import subprocess
                    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
                    # Route --auto to auto_learn.py
                    if a in ("--auto", "-a") or a.startswith("--auto ") or a.startswith("-a "):
                        script = scripts_dir / "auto_learn.py"
                        # Parse out the --auto flag, pass remaining args
                        auto_args = a.split()
                        if auto_args and auto_args[0] in ("--auto", "-a"):
                            auto_args = auto_args[1:]
                    else:
                        script = scripts_dir / "ai_github_learner.py"
                        auto_args = a.split() if a else []
                    if not script.exists():
                        print(f"  ❌ Learner script not found: {script}")
                        return
                    subprocess.run(
                        ["python3", str(script)] + auto_args,
                        cwd=str(scripts_dir.parent),
                    )
                except Exception as e:
                    print(f"  ❌ Learn command failed: {e}")

            complete_learn = complete_tool

            def do_apply(self, arg):
                """Apply learned knowledge — install packages, clone repos, create tool wrappers.

                Bridges the gap between discovering tools on GitHub and actually
                installing/registering them in TankOS.

                Usage: apply              apply all un-applied learnings
                       apply --dry-run    preview what would be installed
                       apply --status     show what's been applied so far
                       apply --recent 5   apply 5 most recent learnings only
                """
                a = (arg or "").strip()
                try:
                    from pathlib import Path
                    import subprocess
                    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
                    script = scripts_dir / "apply_learned.py"
                    if not script.exists():
                        print(f"  ❌ Apply script not found: {script}")
                        return
                    subprocess.run(
                        ["python3", str(script)] + (a.split() if a else []),
                        cwd=str(scripts_dir.parent),
                    )
                except Exception as e:
                    print(f"  ❌ Apply command failed: {e}")

            complete_apply = complete_tool

            def do_tool(self, arg):
                """Show details for a specific Agent Framework tool.

                Usage: tool <dotted.name>
                """
                name = arg.strip()
                if not name:
                    print("  Usage: tool <name>  (e.g. 'tool diagnostics.run')\n")
                    return

                reg = _get_tool_registry()
                if reg is None:
                    return

                t = reg.get(name)
                if t is None:
                    print(f"  ❌ Unknown tool: {name!r}")
                    names = sorted(t2.name for t2 in reg.list())
                    close = _close_matches(name, names)
                    if close:
                        print(f"  Did you mean: {', '.join(close)}?")
                    print()
                    return

                icon = _RISK_ICONS.get(t.risk_tier, "⚪")
                print()
                print(f"  {icon}  {t.name}")
                print(f"  ─{'─' * len(t.name) * 2}─")
                print(f"  {t.description}")
                print()
                print(f"  Category:    {t.category}")
                print(f"  Risk tier:   {t.risk_tier}")
                print(f"  Script:      {t.script_path}")
                print(f"  Subcommand:  {t.subcommand}")
                if t.fids:
                    print(f"  F-IDs:       {', '.join(f'F{fid}' for fid in t.fids)}")
                print()
                if t.args_schema and t.args_schema.get('properties'):
                    print("  Arguments:")
                    for pname, pschema in t.args_schema['properties'].items():
                        ptype = pschema.get('type', 'any')
                        pdesc = pschema.get('description', '')
                        default = pschema.get('default', None)
                        dfl = f" (default: {default})" if default is not None else ""
                        print(f"    --{pname}  <{ptype}>  {pdesc}{dfl}")
                    print()
                if t.examples:
                    print("  Examples:")
                    for ex in t.examples:
                        if ex.get('cli'):
                            print(f"    $ {ex['cli']}")
                    print()
                print("  (try 'tools --category ...' to explore more)\n")

            def do_ai_screen(self, _):
                """Navigate to the AI Engine Dashboard (Qt graphical view)."""
                self._show_screen("ai", "🧠", "AI Engine Dashboard")
                print("  Knowledge Graph | Curiosity | Learning | Scheduler | Experience")

            def do_curiosity(self, _):
                """Show curiosity engine status and explore."""
                from datetime import datetime as _dt
                print("\n  🔍 Curiosity Engine")
                print("  " + "─" * 48)
                try:
                    ce = CuriosityEngine()
                    stats = ce.get_stats()
                    print(f"  Explorations:     {stats['total_explorations']}")
                    print(f"  Successful:       {stats['successful']}")
                    print(f"  Interrupted:      {stats['interrupted']}")
                    print(f"  Auto-mode:        {'✅' if stats['auto_mode'] else '❌'}")
                    print()

                    if stats.get('by_type'):
                        print("  By type:")
                        for etype, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
                            print(f"    {etype.replace('_', ' ').title()}: {count}")
                        print()

                    gaps = stats.get('knowledge_gaps', {})
                    print(f"  Knowledge gaps:   {gaps.get('open', 0)} open, {gaps.get('filled', 0)} filled")
                    print(f"  Discoveries:      {stats['discoveries']['total']} total")
                    print(f"                     {stats['discoveries']['tested']} tested")
                    print(f"                     {stats['discoveries']['working']} working")
                    print()

                    recent = ce.get_recent_explorations(3)
                    if recent:
                        print("  Recent explorations:")
                        for exp in recent:
                            ts = _dt.fromtimestamp(exp.start_time).strftime("%H:%M:%S")
                            emoji = '✅' if exp.result == 'success' else '❌' if exp.result == 'failure' else '⏹️'
                            print(f"    {emoji} [{ts}] {exp.exploration_type.value}: {len(exp.findings)} findings")
                except Exception as e:
                    print(f"  Curiosity Engine unavailable: {e}")

            def do_knowledge(self, _):
                """Show knowledge graph status."""
                print("\n  📊 Knowledge Graph")
                print("  " + "─" * 48)
                try:
                    kg = KnowledgeGraph()
                    stats = kg.get_stats()
                    print(f"  Total entities:    {stats['total_entities']}")
                    print(f"  Relationships:     {stats['total_relationships']}")
                    print(f"  Avg strength:      {stats['average_strength']}")
                    print(f"  Communities:       {stats['communities']}")
                    print()

                    # By type
                    if stats.get('by_type'):
                        print("  Entity types:")
                        for etype, count in sorted(stats['by_type'].items(), key=lambda x: -x[1], reverse=True):
                            bar = "█" * min(count, 20)
                            print(f"    {etype:<12} {bar} {count}")
                        print()

                    # Most connected
                    if stats.get('most_connected'):
                        print("  Most connected entities:")
                        for item in stats['most_connected']:
                            print(f"    🔗 {item['name']} ({item['type']}) — {item['connections']} connections")
                except Exception as e:
                    print(f"  Knowledge Graph unavailable: {e}")

            def do_learning(self, _):
                """Show learning scheduler status and tasks."""
                from datetime import timedelta as _td
                print("\n  ⏰ Learning Scheduler")
                print("  " + "─" * 48)
                try:
                    ls = LearningScheduler()
                    status = ls.get_status()

                    mode = '🟢 running' if status['running'] else '🔴 stopped'
                    busy = 'busy' if status['system_busy'] else 'idle'
                    print(f"  Status:          {mode} ({busy})")
                    print(f"  Scheduled tasks: {status['scheduled_tasks']} ({status['enabled_tasks']} enabled)")
                    print(f"  Active task:     {status['active_task'] or 'none'}")
                    print()

                    b = status.get('budget', {})
                    used = b.get('used_today_h', 0)
                    max_h = b.get('max_daily_h', 0)
                    bar_len = 20
                    filled = int((used / max(max_h, 1)) * bar_len) if max_h else 0
                    bar = "█" * filled + "░" * (bar_len - filled)
                    print(f"  Daily budget:    [{bar}] {used:.1f}/{max_h}h")
                    print(f"  Tasks:           {b.get('tasks_completed', 0)} done, {b.get('tasks_failed', 0)} failed")
                    print()

                    nt = status.get('next_task', {})
                    if nt.get('type'):
                        remaining = nt['in_seconds']
                        print(f"  Next task:       {nt['type']} (in {_td(seconds=remaining)})")
                    print()

                    lw = status.get('learning_window', {})
                    window_active = '🟢' if lw.get('active') else '🔴'
                    print(f"  Learning window: {window_active} {lw.get('start', '?')}–{lw.get('end', '?')}")
                    print()

                    print("  Scheduled tasks:")
                    for task in ls.get_tasks():
                        remaining = max(0, int(task.next_run - time.time()))
                        label = task.task_type.value.replace('_', ' ').title()
                        due = _td(seconds=remaining) if remaining > 0 else 'now'
                        print(f"    {'🟢' if task.enabled else '⚪'} {label:<28} in {str(due):<10} ({task.run_count}x)")

                except Exception as e:
                    print(f"  Learning Scheduler unavailable: {e}")

            def do_help(self, _):
                print("  🖥 Screens:")
                print("     home, chat, camera, nav, memory, security,")
                print("     patrol, diag, settings, dev, ai, power, updates, files")
                print("  🧠 AI Engine Status (enable with TANKOS_FULL=1):")
                print("     ai-screen  — AI Engine Dashboard (full GUI)")
                print("     curiosity  — Curiosity exploration stats")
                print("     knowledge  — Knowledge graph status")
                print("     learning   — Learning scheduler status")
                print("  📦 Agent Framework:")
                print("     tools      — List all ~1,166 script tools")
                print("     tool       — Show details for a specific tool")
                print("  🔍 Search:")
                print("     search     — Search everywhere (torrent, web, GitHub, YouTube)")
                print("     find       — Alias for search")
                print("     discover   — Search + learn from GitHub in one step")
                print("     --history  — View search log")
                print("  🧠 AI Learning:")
                print("     learn      — Learn scripts/tools from GitHub repos")
                print("     learn --auto — Auto-learn from ALL TankOS abilities")
                print("     learn --query — Query learned knowledge")
                print("  🧬 Auto-Evolution:")
                print("     evolve     — Daily self-evolution (learn + discover + expand + apply)")
                print("     evolve --report — Show evolution history")
                print("  🔧 Apply Discoveries:")
                print("     apply      — Install discovered packages & tools from learning")
                print("     apply --status — Show what's been applied so far")
                print("  🌊 Torrents:")
                print("     torrent    — Search torrents → pick → add to aria2")
                print("  💻 Commands:")
                print("     terminal   — Drop into AI terminal REPL")
                print("     status     — System health status")
                print("     preload    — Preload dependency status")
                print("     help       — This message")
                print("     quit       — Exit TankOS")

            def default(self, line: str) -> None:
                """Route natural language / voice commands to the right tool."""
                lowered = line.lower().strip()
                if not lowered:
                    return False

                # ── Torrent intent: start-of-sentence patterns ──
                torrent_patterns = [
                    r"(?:get|find|search|download|show)(?: me)? (?:a |the |some )?torrent",
                    r"torrent (?:of |for |search )?",
                ]
                for pat in torrent_patterns:
                    m = re.match(pat, lowered)
                    if m:
                        query = line[m.end():].strip()
                        query = re.sub(r"^(?:of |for |a |the )+", "", query).strip()
                        if query and query != lowered:
                            print(f"\n  🌊 Detected torrent intent → searching: '{query}'")
                            self.do_torrent(query)
                            return False

                # ── Search-everything intent: "search everything", "find all", etc ──
                search_all_patterns = [
                    r"(?:search|find)(?: me)? (?:everything|all|everywhere)(?: about| for| on)?",
                    r"(?:search|find)(?: me)? (?:on |for |about )?github",
                ]
                for pat in search_all_patterns:
                    m = re.match(pat, lowered)
                    if m:
                        query = line[m.end():].strip()
                        query = re.sub(r"^(?:about |for |on )+", "", query).strip()
                        if query:
                            action = "--github" if "github" in pat.rstrip("?") else ""
                            print(f"\n  🔍 Detected search-everything intent → searching: '{query}'")
                            self.do_search(f"{action} {query}".strip())
                            return False

                # ── Torrent intent: word anywhere in sentence ──
                if re.search(r"\btorrent\b", lowered):
                    query = re.sub(r"\b(?:a |the |some )?torrent(?: of | for | search | download )?\b", "", line, flags=re.IGNORECASE).strip()
                    if query and len(query) > 2:
                        print(f"\n  🌊 Detected torrent keyword → searching: '{query}'")
                        self.do_torrent(query)
                        return False

                # ── Generic search/find intent: "search for X", "find X" ──
                generic_search = re.match(
                    r"(?:search|find)(?: me)? (?:for |about |on )?",
                    lowered,
                )
                if generic_search:
                    query = line[generic_search.end():].strip()
                    query = re.sub(r"^(?:a |the |some )+", "", query).strip()
                    if query and len(query) > 2:
                        print(f"\n  🔍 Detected search intent → searching everywhere: '{query}'")
                        self.do_search(query)
                        return False

                # ── Video / YouTube intent ──
                if any(kw in lowered for kw in ["video", "youtube", "watch"]):
                    query = line.strip()
                    print(f"\n  🎬 Video intent: '{query}'")
                    print(f"  💡 simple-internet search '{query}' --source=youtube")
                    self._speak(f"Searching for videos: {query}")
                    return False

                # ── Music intent ──
                if any(kw in lowered for kw in ["music", "song", "album", "playlist"]):
                    query = line.strip()
                    print(f"\n  🎵 Music intent: '{query}'")
                    print(f"  💡 simple-internet search '{query}' --source=soundcloud")
                    self._speak(f"Searching for music: {query}")
                    return False

                # ── Search ToolRegistry ──
                reg = _get_tool_registry()
                if reg:
                    try:
                        matches = reg.search(lowered, top_k=5)
                        if matches:
                            print(f"\n  🔧 Found {len(matches)} tools matching '{line[:40]}':")
                            for t in matches[:5]:
                                desc = (t.description or "").strip()[:80]
                                print(f"     🟢 {t.name} — {desc}")
                            print(f"  💡 Try: invoke <tool.name> or 'tools' to browse")
                            self._speak(f"Found {len(matches)} tools matching your request")
                            return False
                    except Exception:
                        pass

                # ── Fallback ──
                print(f"\n  🤔 Not sure how to handle: '{line[:60]}'")
                print(f"  💡 Try: help, tools, torrent <q>, terminal, ask <question>")
                self._speak("I didn't understand that command. Try help for options.")
                return False

            def _speak(self, text: str) -> None:
                """Send text to TTS if voice manager is available."""
                try:
                    from tank_os.core.voice_manager import VoiceManager
                    vm = VoiceManager()
                    vm.say(text)
                except Exception:
                    pass  # TTS is optional

        TankShellCmd(self).cmdloop()

    def _simple_loop(self) -> None:
        """Fallback input loop if cmd module is unavailable."""
        print("\nCommands: home, chat, camera, nav, memory, security, patrol, diag, settings, dev, status, quit")
        while self._running:
            try:
                line = input("tankos> ").strip().lower()
                if line == "quit":
                    break
                elif line == "help":
                    print("Screens: home, chat, camera, nav, memory, security, patrol, diag, settings, dev")
                elif line == "status":
                    print("  TankOS Simulation Mode — all systems nominal")
                elif line:
                    self.navigate(line)
            except (EOFError, KeyboardInterrupt):
                break
        self.shutdown()

    def shutdown(self) -> None:
        self._running = False
        self._bus.emit(Event("shell_shutdown", {}, source="tank_shell"))
        logger.info("Tank Shell shut down")


def main() -> int:
    """Entry point for ``python3 -m tank_os.shell.main``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    shell = TankShell()
    shell.initialize()
    return shell.run()


if __name__ == "__main__":
    sys.exit(main())
