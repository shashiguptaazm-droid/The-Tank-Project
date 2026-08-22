"""TankOS Screens — full-screen views for the Tank Shell."""

from tank_os.windows.home_screen import HomeScreen
from tank_os.windows.chat_screen import ChatScreen
from tank_os.windows.camera_screen import CameraScreen
from tank_os.windows.navigation_screen import NavigationScreen
from tank_os.windows.memory_screen import MemoryScreen
from tank_os.windows.security_screen import SecurityScreen
from tank_os.windows.patrol_screen import PatrolScreen
from tank_os.windows.diagnostics_screen import DiagnosticsScreen
from tank_os.windows.settings_screen import SettingsScreen
from tank_os.windows.developer_screen import DeveloperScreen
from tank_os.windows.ai_screen import AIScreen

__all__ = [
    "HomeScreen", "ChatScreen", "CameraScreen",
    "NavigationScreen", "MemoryScreen", "SecurityScreen",
    "PatrolScreen", "DiagnosticsScreen", "SettingsScreen",
    "DeveloperScreen", "AIScreen",
]
