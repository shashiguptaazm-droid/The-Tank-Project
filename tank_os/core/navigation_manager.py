"""TankOS Navigation Manager — mapping, localization, path planning, waypoints."""

from __future__ import annotations
import logging, threading, json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from tank_os.core.event_bus import Event, EventBus


@dataclass
class Waypoint:
    name: str; x: float; y: float; yaw: float = 0.0
    tolerance: float = 0.5


@dataclass
class Pose:
    x: float = 0.0; y: float = 0.0; yaw: float = 0.0


class NavigationManager:
    _instance: Optional["NavigationManager"] = None; _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._pose = Pose()
                cls._instance._waypoints: Dict[str, Waypoint] = {}
                cls._instance._waypoint_file = Path.home() / ".config" / "tank_os" / "waypoints.json"
                cls._instance._slam_active = False
                cls._instance._map_path = ""
            return cls._instance

    def initialize(self) -> None:
        self._load_waypoints()
        logger.info("NavigationManager initialized")

    def _load_waypoints(self) -> None:
        if self._waypoint_file.exists():
            try:
                data = json.loads(self._waypoint_file.read_text())
                for w in data:
                    self._waypoints[w["name"]] = Waypoint(**w)
            except Exception: pass

    def save_waypoints(self) -> None:
        self._waypoint_file.parent.mkdir(parents=True, exist_ok=True)
        data = [{"name": w.name, "x": w.x, "y": w.y, "yaw": w.yaw, "tolerance": w.tolerance}
                for w in self._waypoints.values()]
        self._waypoint_file.write_text(json.dumps(data, indent=2))

    def add_waypoint(self, name: str, x: float, y: float, yaw: float = 0.0) -> Waypoint:
        wp = Waypoint(name=name, x=x, y=y, yaw=yaw)
        self._waypoints[name] = wp
        self.save_waypoints()
        self._bus.emit(Event("waypoint_added", {"name": name, "x": x, "y": y}))
        return wp

    def remove_waypoint(self, name: str) -> bool:
        if name in self._waypoints:
            del self._waypoints[name]
            self.save_waypoints()
            return True
        return False

    def get_waypoint(self, name: str) -> Optional[Waypoint]:
        return self._waypoints.get(name)

    @property
    def waypoints(self) -> List[Waypoint]: return list(self._waypoints.values())
    @property
    def pose(self) -> Pose: return self._pose
    @property
    def is_slam_active(self) -> bool: return self._slam_active

    def navigate_to(self, x: float, y: float) -> None:
        self._bus.emit(Event("navigate_to", {"x": x, "y": y}, source="nav_manager"))

    def navigate_waypoint(self, name: str) -> bool:
        wp = self._waypoints.get(name)
        if wp:
            self.navigate_to(wp.x, wp.y)
            self._bus.emit(Event("navigating_to_waypoint", {"name": name}))
            return True
        return False


logger = logging.getLogger("tank_os.navigation_manager")
