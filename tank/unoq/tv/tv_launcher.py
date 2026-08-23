"""
tv_launcher.py - Android TV-Style Home Launcher for UNO Q
Features 91-100: TV Mode, remote input, display detect, home launcher
"""
import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger("tank.unoq.tv")


class TankMode(Enum):
    ROBOT = "robot"
    TV = "tv"
    DEVELOPER = "developer"
    MAINTENANCE = "maintenance"


class InputDevice(Enum):
    TOUCHSCREEN = "touchscreen"
    GAMEPAD = "gamepad"
    BLUETOOTH_REMOTE = "bluetooth_remote"
    USB_KEYBOARD = "usb_keyboard"
    USB_MOUSE = "usb_mouse"


class TVLauncher:
    """Android TV-style 10-foot interface for UNO Q."""

    def __init__(self):
        self.current_mode = TankMode.ROBOT
        self.display_connected = False
        self.display_resolution = (0, 0)
        self.fullscreen = True
        self.input_device = InputDevice.TOUCHSCREEN
        self.mode_switch_callbacks = []
        self.tiles = [
            {"id": "robot", "icon": "🤖", "label": "ROBOT", "mode": TankMode.ROBOT, "color": "green"},
            {"id": "tv", "icon": "📺", "label": "TV", "mode": TankMode.TV, "color": "blue"},
            {"id": "games", "icon": "🎮", "label": "GAMES", "mode": TankMode.DEVELOPER, "color": "purple"},
            {"id": "settings", "icon": "⚙️", "label": "SETTINGS", "mode": TankMode.MAINTENANCE, "color": "gray"},
            {"id": "camera", "icon": "📷", "label": "CAMERA", "mode": TankMode.ROBOT, "color": "cyan"},
            {"id": "nav", "icon": "🗺", "label": "NAV", "mode": TankMode.ROBOT, "color": "blue"},
            {"id": "voice", "icon": "🎙", "label": "VOICE", "mode": TankMode.ROBOT, "color": "amber"},
            {"id": "ai", "icon": "🧠", "label": "AI", "mode": TankMode.ROBOT, "color": "purple"},
            {"id": "security", "icon": "🔐", "label": "SECURITY", "mode": TankMode.DEVELOPER, "color": "red"},
            {"id": "system", "icon": "💻", "label": "SYSTEM", "mode": TankMode.MAINTENANCE, "color": "gray"},
        ]
        self.selected_index = 0
        self.keyboard_shortcuts = {
            "r": TankMode.ROBOT,
            "t": TankMode.TV,
            "d": TankMode.DEVELOPER,
            "m": TankMode.MAINTENANCE,
            "f": "toggle_fullscreen",
            "q": "quit",
        }

    def detect_display(self, connected: bool, resolution: tuple = (1920, 1080)):
        self.display_connected = connected
        self.display_resolution = resolution
        if connected and resolution[0] > 0:
            self.fullscreen = True
        logger.info(f"Display: {'connected' if connected else 'disconnected'} {resolution}")

    def switch_mode(self, mode: TankMode) -> bool:
        old = self.current_mode
        self.current_mode = mode
        logger.info(f"Mode switched: {old.value} -> {mode.value}")
        for cb in self.mode_switch_callbacks:
            try:
                cb({"from": old.value, "to": mode.value})
            except Exception:
                pass
        return True

    def handle_gamepad(self, button: str) -> Optional[str]:
        if button == "up":
            self.selected_index = max(0, self.selected_index - 4)
        elif button == "down":
            self.selected_index = min(len(self.tiles) - 1, self.selected_index + 4)
        elif button == "left":
            self.selected_index = max(0, self.selected_index - 1)
        elif button == "right":
            self.selected_index = min(len(self.tiles) - 1, self.selected_index + 1)
        elif button == "a" or button == "enter":
            tile = self.tiles[self.selected_index]
            self.switch_mode(tile["mode"])
            return tile["id"]
        elif button == "home":
            self.selected_index = 0
        return None

    def handle_keyboard(self, key: str) -> Optional[str]:
        action = self.keyboard_shortcuts.get(key.lower())
        if action == "toggle_fullscreen":
            self.fullscreen = not self.fullscreen
            return "fullscreen_toggled"
        elif action == "quit":
            return "quit"
        elif isinstance(action, TankMode):
            self.switch_mode(action)
            return f"mode_{action.value}"
        return None

    def render_home_screen(self) -> Dict[str, Any]:
        return {
            "title": "THE TANK",
            "subtitle": "Autonomous AI Robot",
            "mode": self.current_mode.value,
            "tiles": self.tiles,
            "selected": self.selected_index,
            "display": {
                "connected": self.display_connected,
                "resolution": self.display_resolution,
                "fullscreen": self.fullscreen,
            },
            "input_device": self.input_device.value,
            "keyboard_shortcuts": self.keyboard_shortcuts,
        }

    def get_system_bar(self, status: Dict[str, Any]) -> str:
        jetson = status.get("jetson", "❌")
        unoq = status.get("unoq", "❌")
        esp32 = status.get("esp32", "❌")
        return (
            f"┌──────────────────────────────────────────┐\n"
            f"│              THE TANK                    │\n"
            f"│   🤖 ROBOT       📺 TV        🎮 GAMES  │\n"
            f"│   📷 CAMERA      🗺 NAV       🎙 VOICE   │\n"
            f"│   🧠 AI          🔐 SECURITY  ⚙ SYSTEM  │\n"
            f"│   UNO Q {unoq}    JETSON {jetson}    ESP32 {esp32}    │\n"
            f"└──────────────────────────────────────────┘"
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_mode": self.current_mode.value,
            "display_connected": self.display_connected,
            "display_resolution": self.display_resolution,
            "fullscreen": self.fullscreen,
            "input_device": self.input_device.value,
            "selected_tile": self.tiles[self.selected_index]["label"],
            "total_tiles": len(self.tiles),
        }
