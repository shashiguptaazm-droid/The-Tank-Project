"""
TankOS Core — System managers and foundational services.

Contains the central event bus, plugin system, theme engine, animation
engine, and all managers that coordinate TankOS subsystems.
"""

from tank_os.core.event_bus import EventBus, Event, Priority
from tank_os.core.plugin_manager import PluginManager, PluginManifest, PluginInfo
from tank_os.core.plugin_api import Plugin
from tank_os.core.theme_engine import ThemeEngine, Theme
from tank_os.core.animation_engine import AnimationEngine, Animation, Easing, Particle
from tank_os.core.settings_manager import SettingsManager
from tank_os.core.display_manager import DisplayManager
from tank_os.core.window_manager import WindowManager, Window, WindowState
from tank_os.core.hardware_manager import HardwareManager, HardwareDevice
from tank_os.core.power_manager import PowerManager
from tank_os.core.charging_manager import ChargingManager, DockInfo, DockStatus, ChargeState, BatteryHealth, ChargeSession
from tank_os.core.notification_manager import NotificationManager, Notification
from tank_os.core.preload_manager import PreloadManager, PreloadState, PreloadReport
from tank_os.core.permission_manager import (
    PermissionManager, Permission,
    PermissionRequest, PERMISSION_LABELS,
)
from tank_os.core.application_manager import ApplicationManager, AppInfo
from tank_os.core.voice_manager import (
    VoiceManager, VoiceState, VoiceEvent,
)
from tank_os.core.ai_manager import (
    AIManager, AIProvider, AIProviderError,
    AIRequest, AIResponse,
    LocalStubProvider, EchoProvider,
)
from tank_os.core.update_manager import (
    UpdateManager, UpdateProvider,
    UpdateInfo, UpdateSnapshot, UpdateChannel,
    LocalManifestProvider, ScriptsOTAProvider,
)

__all__ = [
    "EventBus", "Event", "Priority",
    "PluginManager", "PluginManifest", "PluginInfo", "Plugin",
    "ThemeEngine", "Theme",
    "AnimationEngine", "Animation", "Easing", "Particle",
    "SettingsManager",
    "DisplayManager",
    "WindowManager", "Window", "WindowState",
    "HardwareManager", "HardwareDevice",
    "PowerManager",
    "ChargingManager",
    "DockInfo", "DockStatus", "ChargeState",
    "BatteryHealth", "ChargeSession",    "NotificationManager", "Notification",
    "PreloadManager", "PreloadState", "PreloadReport",
    "PermissionManager", "Permission", "PermissionRequest", "PERMISSION_LABELS",
    "ApplicationManager", "AppInfo",
    "VoiceManager", "VoiceState", "VoiceEvent",
    "AIManager", "AIProvider", "AIProviderError",
    "AIRequest", "AIResponse",
    "LocalStubProvider", "EchoProvider",
    "UpdateManager", "UpdateProvider",
    "UpdateInfo", "UpdateSnapshot", "UpdateChannel",
    "LocalManifestProvider", "ScriptsOTAProvider",
]	
