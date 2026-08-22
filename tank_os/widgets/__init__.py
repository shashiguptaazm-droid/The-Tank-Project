"""TankOS Widgets — reusable Qt6 graphical components."""

from tank_os.widgets.top_bar import TopBar
from tank_os.widgets.bottom_dock import BottomDock
from tank_os.widgets.camera_widget import CameraWidget
from tank_os.widgets.ai_avatar import AIAvatar
from tank_os.widgets.map_widget import MapWidget
from tank_os.widgets.status_widget import StatusWidget
from tank_os.widgets.battery_widget import BatteryWidget
from tank_os.widgets.clock_widget import LiveClock
from tank_os.widgets.notifications_overlay import NotificationsOverlay

__all__ = [
    "TopBar", "BottomDock", "CameraWidget", "AIAvatar",
    "MapWidget", "StatusWidget", "BatteryWidget", "LiveClock",
    "NotificationsOverlay",
]
