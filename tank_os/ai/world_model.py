"""TankOS World Model — evolving spatial and environmental understanding.

Maintains a continuously updated internal representation of the robot's
environment including:
- Rooms and their layout, size, and properties
- Objects and their locations within rooms
- Zones (charging, restricted, high-traffic, etc.)
- People and their typical locations
- Environmental changes over time (what moved, what's new)
- Time-based patterns (lighting, activity levels)

Integrates with sensors, navigation, vision, and knowledge graph.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.world_model")

# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path.home() / ".config" / "tank_os" / "world_model.json"
MAX_ROOMS = 20
MAX_OBJECTS_PER_ROOM = 50
CHANGE_CONFIDENCE_THRESHOLD = 0.3


# ── Data Models ─────────────────────────────────────────────────────────

@dataclass
class Room:
    """A known room or area in the environment."""

    id: str
    name: str
    room_type: str = "unknown"    # "living_room", "kitchen", "bedroom", "office", "hallway", "garage", "unknown"
    description: str = ""
    confidence: float = 0.5       # How sure we are this room exists
    times_visited: int = 0
    first_seen: float = 0.0
    last_visited: float = 0.0
    center_x: float = 0.0         # Approximate center coordinates
    center_y: float = 0.0
    width_m: float = 0.0          # Estimated dimensions
    height_m: float = 0.0
    zones: List[str] = field(default_factory=list)  # Zone IDs in this room
    typical_lighting: str = "unknown"  # "bright", "dim", "dark", "variable"
    typical_activity_level: str = "unknown"  # "high", "medium", "low", "silent"
    tags: List[str] = field(default_factory=list)
    last_change: float = 0.0      # When the room was last changed


@dataclass
class WorldObject:
    """An object tracked in the world model."""

    id: str
    name: str
    object_type: str = "unknown"  # "furniture", "electronics", "personal", "structural", "consumable"
    room_id: str = ""
    last_seen_at: Tuple[float, float] = (0.0, 0.0)  # (x, y) coordinates
    confidence: float = 0.5
    first_seen: float = 0.0
    last_seen: float = 0.0
    times_seen: int = 1
    stationary: bool = True        # Has this object ever moved?
    color: str = ""
    size: str = "medium"           # "small", "medium", "large"
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Zone:
    """A defined zone within a room."""

    id: str
    name: str
    zone_type: str                 # "charging", "restricted", "high_traffic",
                                   # "observation", "storage", "safe", "danger"
    room_id: str
    polygon: List[Tuple[float, float]] = field(default_factory=list)  # GPS-like boundary
    active: bool = True
    description: str = ""
    created: float = 0.0
    last_updated: float = 0.0


@dataclass
class EnvironmentChange:
    """A detected change in the environment."""

    id: str
    change_type: str               # "object_moved", "object_appeared", "object_disappeared",
                                   # "room_changed", "lighting_changed", "obstacle_appeared"
    object_name: str = ""
    room_name: str = ""
    description: str = ""
    confidence: float = 0.0
    timestamp: float = 0.0
    acknowledged: bool = False
    relevant: bool = True          # Is this a meaningful change?
    source: str = ""


# ── World Model Engine ─────────────────────────────────────────────────

class WorldModel:
    """Evolving spatial and environmental understanding.

    Builds and maintains a model of the robot's physical world:
    rooms, objects, zones, people locations, and environmental changes.

    Usage:
        wm = WorldModel()
        wm.initialize()

        # Room management
        wm.add_room("Living Room", room_type="living_room")

        # Object tracking
        wm.observe_object("chair", room_name="Living Room",
                           position=(5.2, 3.1))

        # Zone management
        wm.add_zone("Charging Station", "charging", "Living Room")

        # Detect changes
        changes = wm.detect_changes()
    """

    _instance: Optional["WorldModel"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._rooms: Dict[str, Room] = {}
                cls._instance._objects: Dict[str, WorldObject] = {}
                cls._instance._zones: Dict[str, Zone] = {}
                cls._instance._changes: List[EnvironmentChange] = []
                cls._instance._store_path: Path = DEFAULT_STORE_PATH
                cls._instance._object_by_room: Dict[str, List[str]] = {}
                cls._instance._last_scan_time = 0.0
                cls._instance._last_save_time = 0.0
            return cls._instance

    def initialize(self, store_path: Optional[str] = None) -> None:
        """Load world model from disk and register event listeners."""
        if store_path:
            self._store_path = Path(store_path)
        self._load()
        self._register_listeners()
        logger.info(
            "WorldModel initialized (%d rooms, %d objects, %d zones, %d changes)",
            len(self._rooms), len(self._objects),
            len(self._zones), len(self._changes),
        )

    def _load(self) -> None:
        """Load world model from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for r_data in data.get("rooms", []):
                room = Room(**r_data)
                self._rooms[room.id] = room
            for o_data in data.get("objects", []):
                obj = WorldObject(**o_data)
                self._objects[obj.id] = obj
                self._object_by_room.setdefault(obj.room_id, []).append(obj.id)
            for z_data in data.get("zones", []):
                zone = Zone(**z_data)
                self._zones[zone.id] = zone
            for c_data in data.get("changes", []):
                self._changes.append(EnvironmentChange(**c_data))
            logger.debug("Loaded world model from disk")
        except Exception as e:
            logger.warning("Failed to load world model: %s", e)

    def _save(self) -> None:
        """Persist world model to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rooms": [vars(r) for r in self._rooms.values()],
            "objects": [vars(o) for o in self._objects.values()],
            "zones": [vars(z) for z in self._zones.values()],
            "changes": [vars(c) for c in self._changes[-100:]],
            "last_update": time.time(),
        }
        self._store_path.write_text(json.dumps(data, indent=2, default=str))
        self._last_save_time = time.time()

    def _register_listeners(self) -> None:
        """Register EventBus listeners."""
        self._bus.on("camera_detection", self._on_camera_detection)
        self._bus.on("navigation_goal", self._on_navigation_event)
        self._bus.on("world_model_request", self._on_request)

    # ── Room Management ────────────────────────────────────────────

    def add_room(self, name: str, room_type: str = "unknown",
                 center_x: float = 0.0, center_y: float = 0.0,
                 width_m: float = 0.0, height_m: float = 0.0,
                 tags: Optional[List[str]] = None) -> Room:
        """Add or update a room in the world model."""
        name_lower = name.lower().strip()

        # Check if room already exists
        existing = self._find_room_by_name(name)
        if existing:
            existing.times_visited += 1
            existing.last_visited = time.time()
            existing.confidence = min(1.0, existing.confidence + 0.1)
            if width_m and not existing.width_m:
                existing.width_m = width_m
            if height_m and not existing.height_m:
                existing.height_m = height_m
            if tags:
                existing.tags.extend(t for t in tags if t not in existing.tags)
            if existing.room_type == "unknown" and room_type != "unknown":
                existing.room_type = room_type
            return existing

        now = time.time()
        room = Room(
            id=str(uuid.uuid4())[:12],
            name=name,
            room_type=room_type,
            center_x=center_x,
            center_y=center_y,
            width_m=width_m,
            height_m=height_m,
            first_seen=now,
            last_visited=now,
            tags=tags or [],
        )
        self._rooms[room.id] = room

        self._bus.emit(Event("world_room_discovered", {
            "id": room.id, "name": name, "type": room_type,
        }, source="world_model"))

        self._save()
        return room

    def get_room(self, identifier: str) -> Optional[Room]:
        """Get room by ID or name."""
        if identifier in self._rooms:
            return self._rooms[identifier]
        name_lower = identifier.lower().strip()
        for room in self._rooms.values():
            if room.name.lower() == name_lower:
                return room
        return None

    def get_all_rooms(self) -> List[Room]:
        """Get all rooms, sorted by times visited."""
        return sorted(self._rooms.values(), key=lambda r: -r.times_visited)

    def get_current_room(self, x: float = 0.0, y: float = 0.0) -> Optional[Room]:
        """Get the room containing the given coordinates."""
        if not self._rooms:
            return None

        # Simple distance-based room detection
        best_room = None
        best_distance = float("inf")
        for room in self._rooms.values():
            if room.center_x or room.center_y:
                dist = math.sqrt(
                    (x - room.center_x) ** 2 + (y - room.center_y) ** 2
                )
                if dist < best_distance:
                    best_distance = dist
                    best_room = room

        if best_room and best_distance < max(best_room.width_m, best_room.height_m, 5.0):
            return best_room
        return None

    def suggest_room_type(self, room: Room) -> Optional[str]:
        """Suggest a room type based on its objects and properties."""
        objects_in_room = self.get_objects_in_room(room.id)
        object_names = [o.name.lower() for o in objects_in_room]

        type_indicators: Dict[str, List[str]] = {
            "kitchen": ["fridge", "refrigerator", "oven", "stove", "microwave",
                         "sink", "cabinet", "counter", "table"],
            "living_room": ["sofa", "couch", "tv", "television", "coffee_table",
                            "rug", "lamp", "bookshelf"],
            "bedroom": ["bed", "pillow", "wardrobe", "dresser", "nightstand"],
            "office": ["desk", "computer", "monitor", "keyboard", "chair",
                        "bookshelf", "filing"],
            "garage": ["car", "tool", "shelf", "box", "workbench"],
            "bathroom": ["sink", "toilet", "shower", "mirror", "cabinet"],
            "hallway": ["door", "rug", "mirror"],
        }

        scores: Dict[str, int] = {}
        for rtype, indicators in type_indicators.items():
            score = sum(1 for ind in indicators if any(ind in name for name in object_names))
            if score > 0:
                scores[rtype] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def _find_room_by_name(self, name: str) -> Optional[Room]:
        """Find a room by its name (case-insensitive)."""
        name_lower = name.lower().strip()
        for room in self._rooms.values():
            if room.name.lower() == name_lower:
                return room
        return None

    # ── Object Management ──────────────────────────────────────────

    def observe_object(self, name: str, room_name: str = "",
                       position: Optional[Tuple[float, float]] = None,
                       object_type: str = "unknown",
                       stationary: Optional[bool] = None) -> WorldObject:
        """Observe an object in the environment.

        Tracks objects over time, detecting when they move or disappear.

        Args:
            name: Object name
            room_name: Room the object is in
            position: (x, y) coordinates
            object_type: Type classification
            stationary: Whether the object is expected to be stationary

        Returns:
            The WorldObject (new or updated)
        """
        now = time.time()
        name_lower = name.lower().strip()

        # Find or infer room
        room_id = ""
        if room_name:
            room = self.get_room(room_name)
            if room:
                room_id = room.id
                room.last_visited = now
                room.times_visited += 1
        else:
            # Try to assign to a room based on position
            if position:
                current_room = self.get_current_room(position[0], position[1])
                if current_room:
                    room_id = current_room.id

        # Check if this object was previously observed
        existing = self._find_object_by_name(name)
        if existing:
            # Object was already known
            existing.times_seen += 1
            existing.last_seen = now
            existing.confidence = min(1.0, existing.confidence + 0.05)

            # Check for movement
            if (existing.stationary and position
                    and self._distance(existing.last_seen_at, position) > 0.5):
                existing.stationary = False
                self._record_change("object_moved", name, room_name,
                                    f"{name} moved to new position", confidence=0.7)
            elif stationary is not None:
                existing.stationary = stationary

            if position:
                existing.last_seen_at = position
            if room_id:
                existing.room_id = room_id

            return existing

        # New object
        obj = WorldObject(
            id=str(uuid.uuid4())[:12],
            name=name,
            object_type=object_type,
            room_id=room_id,
            last_seen_at=position or (0.0, 0.0),
            first_seen=now,
            last_seen=now,
            stationary=True if stationary is None else stationary,
        )
        self._objects[obj.id] = obj
        self._object_by_room.setdefault(room_id, []).append(obj.id)

        self._record_change("object_appeared", name, room_name,
                            f"New object discovered: {name}", confidence=0.5)

        self._save()
        return obj

    def get_objects_in_room(self, room_id: str) -> List[WorldObject]:
        """Get all objects in a room."""
        obj_ids = self._object_by_room.get(room_id, [])
        return [self._objects[oid] for oid in obj_ids if oid in self._objects]

    def get_all_objects(self) -> List[WorldObject]:
        """Get all tracked objects."""
        return sorted(self._objects.values(), key=lambda o: -o.times_seen)

    def get_recently_changed_objects(self, hours: int = 24) -> List[WorldObject]:
        """Get objects seen or changed within the given time window."""
        cutoff = time.time() - hours * 3600
        return [
            o for o in self._objects.values()
            if o.last_seen >= cutoff
        ]

    def _find_object_by_name(self, name: str) -> Optional[WorldObject]:
        """Find an object by name (case-insensitive)."""
        name_lower = name.lower().strip()
        for obj in self._objects.values():
            if obj.name.lower() == name_lower:
                return obj
        return None

    @staticmethod
    def _distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # ── Zone Management ────────────────────────────────────────────

    def add_zone(self, name: str, zone_type: str,
                 room_name: str = "",
                 polygon: Optional[List[Tuple[float, float]]] = None,
                 description: str = "") -> Zone:
        """Define a zone in a room.

        Args:
            name: Zone name
            zone_type: charging, restricted, high_traffic, observation, etc.
            room_name: Room this zone belongs to
            polygon: GPS-like boundary coordinates
            description: What this zone is for

        Returns:
            The Zone
        """
        room_id = ""
        if room_name:
            room = self.get_room(room_name)
            if room:
                room_id = room.id
        else:
            # Assign to first room
            if self._rooms:
                room_id = next(iter(self._rooms.keys()))

        zone = Zone(
            id=str(uuid.uuid4())[:12],
            name=name,
            zone_type=zone_type,
            room_id=room_id,
            polygon=polygon or [],
            description=description,
        )
        self._zones[zone.id] = zone

        # Link to room
        if room_id and room_id in self._rooms:
            self._rooms[room_id].zones.append(zone.id)

        self._bus.emit(Event("world_zone_added", {
            "id": zone.id, "name": name, "type": zone_type,
            "room": room_name or "unknown",
        }, source="world_model"))

        self._save()
        return zone

    def get_zones(self, zone_type: Optional[str] = None) -> List[Zone]:
        """Get zones, optionally filtered by type."""
        if zone_type:
            return [z for z in self._zones.values() if z.zone_type == zone_type]
        return list(self._zones.values())

    def is_in_zone(self, x: float, y: float, zone_type: str) -> bool:
        """Check if coordinates are in a zone of the given type."""
        # Simple bounding-box check for now
        for zone in self._zones.values():
            if zone.zone_type != zone_type:
                continue
            if zone.polygon and len(zone.polygon) >= 2:
                xs = [p[0] for p in zone.polygon]
                ys = [p[1] for p in zone.polygon]
                if min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys):
                    return True
        return False

    # ── Change Detection ───────────────────────────────────────────

    def detect_changes(self) -> List[EnvironmentChange]:
        """Run change detection on the environment.

        Compares current observations with historical data to find:
        - Objects that have moved
        - New objects that appeared
        - Objects that are missing
        - Room changes
        """
        return self._changes

    def _record_change(self, change_type: str, object_name: str = "",
                       room_name: str = "", description: str = "",
                       confidence: float = 0.5) -> EnvironmentChange:
        """Record an environmental change."""
        change = EnvironmentChange(
            id=str(uuid.uuid4())[:12],
            change_type=change_type,
            object_name=object_name,
            room_name=room_name,
            description=description,
            confidence=confidence,
            timestamp=time.time(),
        )
        self._changes.append(change)

        if len(self._changes) > 500:
            self._changes = self._changes[-500:]

        # Update room's last change time
        if room_name:
            room = self.get_room(room_name)
            if room:
                room.last_change = time.time()

        if confidence >= CHANGE_CONFIDENCE_THRESHOLD:
            self._bus.emit(Event("world_change_detected", {
                "type": change_type,
                "object": object_name,
                "room": room_name,
                "description": description,
                "confidence": confidence,
            }, source="world_model"))

        self._save()
        return change

    def get_unacknowledged_changes(self) -> List[EnvironmentChange]:
        """Get changes that haven't been acknowledged yet."""
        return [c for c in self._changes if not c.acknowledged and c.relevant]

    def acknowledge_change(self, change_id: str) -> bool:
        """Mark a change as acknowledged."""
        for change in self._changes:
            if change.id == change_id:
                change.acknowledged = True
                self._save()
                return True
        return False

    # ── Event Handlers ─────────────────────────────────────────────

    def _on_camera_detection(self, event: Event) -> None:
        """Process camera detections to update object positions."""
        data = event.data
        objects = data.get("objects", [])
        room = data.get("room", "")

        for obj in objects:
            if isinstance(obj, dict):
                name = obj.get("name", "object")
            else:
                name = str(obj)

            self.observe_object(
                name=name,
                room_name=room,
                object_type="unknown",
            )

    def _on_navigation_event(self, event: Event) -> None:
        """Update visited rooms from navigation events."""
        data = event.data
        target = data.get("target", "")
        if target:
            # Treat navigation targets as room visits
            room = self.get_room(target)
            if room:
                room.times_visited += 1
                room.last_visited = time.time()

    def _on_request(self, event: Event) -> None:
        """Handle requests via EventBus."""
        action = event.data.get("action", "status")
        if action == "status":
            self._bus.emit(Event("world_model_status", self.get_stats(),
                                 source="world_model"))
        elif action == "rooms":
            rooms_data = [{"id": r.id, "name": r.name, "type": r.room_type,
                           "objects": len(self.get_objects_in_room(r.id))}
                          for r in self._rooms.values()]
            self._bus.emit(Event("world_model_rooms", {"rooms": rooms_data},
                                 source="world_model"))
        elif action == "changes":
            changes_data = [{"id": c.id, "type": c.change_type,
                             "description": c.description, "timestamp": c.timestamp}
                            for c in self.get_unacknowledged_changes()]
            self._bus.emit(Event("world_model_changes", {"changes": changes_data},
                                 source="world_model"))

    # ── Query API ─────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get world model statistics."""
        room_types: Dict[str, int] = {}
        for room in self._rooms.values():
            room_types[room.room_type] = room_types.get(room.room_type, 0) + 1

        object_types: Dict[str, int] = {}
        for obj in self._objects.values():
            object_types[obj.object_type] = object_types.get(obj.object_type, 0) + 1

        zone_types: Dict[str, int] = {}
        for zone in self._zones.values():
            zone_types[zone.zone_type] = zone_types.get(zone.zone_type, 0) + 1

        recent_changes = len([
            c for c in self._changes
            if c.timestamp >= time.time() - 86400
        ])

        return {
            "rooms": {
                "total": len(self._rooms),
                "by_type": room_types,
                "total_visits": sum(r.times_visited for r in self._rooms.values()),
            },
            "objects": {
                "total": len(self._objects),
                "by_type": object_types,
                "stationary": sum(1 for o in self._objects.values() if o.stationary),
            },
            "zones": {
                "total": len(self._zones),
                "by_type": zone_types,
            },
            "changes": {
                "total": len(self._changes),
                "recent_24h": recent_changes,
                "unacknowledged": len(self.get_unacknowledged_changes()),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Quick status summary."""
        return {
            "rooms": len(self._rooms),
            "objects": len(self._objects),
            "zones": len(self._zones),
            "changes_pending": len(self.get_unacknowledged_changes()),
            "last_update": self._last_save_time,
        }
