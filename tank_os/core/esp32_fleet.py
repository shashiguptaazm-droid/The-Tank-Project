"""ESP32FleetManager — discover, heartbeat and aggregate the tank's ESP32 fleet.

Covers UNO Q master-plan items #281–300 (ESP32 fleet management):
discovery, identity registry, heartbeat, health state, telemetry
aggregation, timeout detection and fleet self-test — consolidated onto the
existing :class:`HardwareManager` / ``usb_detector`` scan so we add one
manager, not a dozen files.

The three known boards (see FLEET_INVENTORY.md §5):

    * ESP32-S3 CAM       — ESPHome camera, unoq /dev/ttyACM0, MAC 14:C1:9F:C1:2C:24
    * ESP32-S3 Dual-eyes — round-eye driver,  Jetson /dev/ttyACM1, MAC A0:F2:62:E3:DF:F4
    * DFRobot AI Camera  — vision + IMU,    Jetson /dev/ttyACM0, MAC 28:84:85:4C:84:04
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.esp32_fleet")

#: Known boards — identity registry (master-plan #282).
#: ``match`` substrings are matched against a device's path/serial/description.
KNOWN_BOARDS: List[Dict[str, Any]] = [
    {
        "id": "esp32-cam",
        "name": "ESP32-S3 CAM",
        "role": "ESPHome camera",
        "serial": "14:C1:9F:C1:2C:24",
        "host": "unoq",
        "match": ("ttyACM", "14:C1:9F:C1:2C:24", "esphome"),
    },
    {
        "id": "esp32-dual-eyes",
        "name": "ESP32-S3 Dual-eyes",
        "role": "Round-eye display driver",
        "serial": "A0:F2:62:E3:DF:F4",
        "host": "jetson",
        "match": ("ttyACM", "A0:F2:62:E3:DF:F4"),
    },
    {
        "id": "dfrobot-ai-cam",
        "name": "DFRobot AI Camera",
        "role": "Vision + IMU (SEN0611)",
        "serial": "28:84:85:4C:84:04",
        "host": "jetson",
        "match": ("ttyACM", "28:84:85:4C:84:04", "dfrobot"),
    },
]


@dataclass
class Esp32Board:
    """Runtime state for one discovered ESP32 board."""

    board_id: str
    name: str
    role: str
    serial: str
    host: str
    path: str = ""
    status: str = "offline"           # online | offline | unknown
    last_seen: float = 0.0
    heartbeat_count: int = 0
    firmware: str = ""
    telemetry: Dict[str, Any] = field(default_factory=dict)
    faults: List[str] = field(default_factory=list)

    def is_online(self, timeout: float) -> bool:
        if self.last_seen <= 0:
            return False
        return (time.time() - self.last_seen) <= timeout


class ESP32FleetManager:
    """Singleton that tracks the ESP32 fleet against a discovery source.

    The discovery source is injectable (default: :class:`HardwareManager`
    serial devices) so unit tests can pass a fake and still exercise the
    full heartbeat / timeout / aggregation logic.
    """

    _instance: Optional["ESP32FleetManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ESP32FleetManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._boards: Dict[str, Esp32Board] = {}
                cls._instance._bus = EventBus()
                cls._instance._heartbeat_timeout = 15.0
                cls._instance._discovery_fn = None
            return cls._instance

    # ── Configuration ─────────────────────────────────────────────────
    def configure(self, *, discovery_fn=None, heartbeat_timeout: float = 15.0) -> None:
        """Inject a discovery function and/or timeout (test-friendly)."""
        if discovery_fn is not None:
            self._discovery_fn = discovery_fn
        self._heartbeat_timeout = heartbeat_timeout

    def _default_discovery(self) -> List[Dict[str, Any]]:
        """Pull candidate devices from usb_detector + HardwareManager.

        usb_detector reads real sysfs serials (e.g. the ESP32 JTAG MAC),
        so boards are matched by their known serial even when the generic
        HardwareManager description has no serial in it.
        """
        devices: List[Dict[str, Any]] = []

        # 1) usb_detector — real VID:PID + serial strings
        try:
            from tank_os.core import usb_detector as ud
            for dev in ud.list_usb_devices():
                blob = " ".join([
                    dev.label or "", dev.vidpid or "", dev.serial or "",
                    ",".join(dev.ttys or []),
                ]).lower()
                devices.append({"path": ",".join(dev.ttys or []), "description": blob})
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("usb_detector unavailable: %s", exc)

        # 2) HardwareManager serial scan — paths for ttys
        try:
            from tank_os.core.hardware_manager import HardwareManager
            hw = HardwareManager()
            for dev in hw.get_devices("serial"):
                devices.append({
                    "path": dev.path,
                    "description": f"{dev.path} {dev.description} {dev.metadata}".lower(),
                })
        except Exception as exc:                                    # noqa: BLE001
            logger.debug("hardware scan unavailable: %s", exc)

        return devices

    # ── Discovery ─────────────────────────────────────────────────────
    def discover(self) -> Dict[str, Esp32Board]:
        """Match known boards against the discovery source."""
        fn = self._discovery_fn or self._default_discovery
        candidates = fn()
        now = time.time()
        seen: set = set()

        for board in KNOWN_BOARDS:
            path, desc = self._match(board, candidates)
            board_id = board["id"]
            if board_id not in self._boards:
                self._boards[board_id] = Esp32Board(
                    board_id=board_id,
                    name=board["name"],
                    role=board["role"],
                    serial=board["serial"],
                    host=board["host"],
                )
            entry = self._boards[board_id]
            if path or desc:
                # Board matched in discovery (serial/VID-PID found) — online
                # even if the tty path mapping is empty on this host.
                entry.status = "online"
                entry.path = path
                entry.last_seen = now
                seen.add(board_id)
            else:
                entry.status = "offline"

        # Emit events for newly-seen boards
        for board_id in seen:
            if board_id not in getattr(self, "_seen_events", set()):
                self._bus.emit(Event("esp32_online", {
                    "board": self._boards[board_id].name,
                    "serial": self._boards[board_id].serial,
                }, source="esp32_fleet"))
        self._seen_events = seen
        return self._boards

    def _match(self, board: Dict[str, Any],
               candidates: List[Dict[str, Any]]) -> tuple:
        """Return (path, description) of the first candidate matching a board.

        Matching rules, in order:
          1. board serial (MAC) appears in the candidate blob,
          2. Espressif JTAG VID:PID ``303a:1001`` + any board match token,
          3. all of the board's ``match`` tokens appear (ttyACM + role hint).
        """
        for cand in candidates:
            blob = f"{cand.get('path', '')} {cand.get('description', '')}".lower()
            if board["serial"].lower() in blob:
                return cand.get("path", ""), cand.get("description", "")
        for cand in candidates:
            blob = f"{cand.get('path', '')} {cand.get('description', '')}".lower()
            is_esp32 = "303a:1001" in blob or "espressif" in blob
            if is_esp32 and any(m.lower() in blob for m in board["match"] if m):
                return cand.get("path", ""), cand.get("description", "")
        for cand in candidates:
            blob = f"{cand.get('path', '')} {cand.get('description', '')}".lower()
            if all(m.lower() in blob for m in board["match"] if m):
                return cand.get("path", ""), cand.get("description", "")
        return "", ""

    # ── Heartbeat / timeout ───────────────────────────────────────────
    def mark_heartbeat(self, board_id: str, *,
                       firmware: str = "", **telemetry: Any) -> Optional[Esp32Board]:
        """Record a heartbeat from a board (telemetry optional)."""
        entry = self._boards.get(board_id)
        if entry is None:
            entry = self._make_unknown(board_id)
        entry.last_seen = time.time()
        entry.status = "online"
        entry.heartbeat_count += 1
        if firmware:
            entry.firmware = firmware
        if telemetry:
            entry.telemetry.update(telemetry)
        return entry

    def _make_unknown(self, board_id: str) -> Esp32Board:
        known = next((b for b in KNOWN_BOARDS if b["id"] == board_id), None)
        entry = Esp32Board(
            board_id=board_id,
            name=known["name"] if known else board_id,
            role=known["role"] if known else "unknown",
            serial=known["serial"] if known else "",
            host=known["host"] if known else "",
        )
        self._boards[board_id] = entry
        return entry

    def check_timeouts(self) -> List[str]:
        """Flag boards that exceeded the heartbeat timeout. Returns flagged ids."""
        flagged = []
        for board_id, entry in self._boards.items():
            if entry.last_seen > 0 and not entry.is_online(self._heartbeat_timeout):
                entry.status = "offline"
                entry.faults.append("heartbeat-timeout")
                flagged.append(board_id)
        return flagged

    # ── Queries ───────────────────────────────────────────────────────
    def list(self) -> List[Esp32Board]:
        return [self._boards[b] for b in
                [k["id"] for k in KNOWN_BOARDS] if b in self._boards]

    def get(self, board_id: str) -> Optional[Esp32Board]:
        return self._boards.get(board_id)

    def summary(self) -> Dict[str, Any]:
        """Fleet health summary (master-plan #299)."""
        boards = self.list()
        online = sum(1 for b in boards if b.status == "online")
        return {
            "total": len(boards),
            "online": online,
            "offline": len(boards) - online,
            "heartbeat_timeout_s": self._heartbeat_timeout,
            "boards": [
                {"id": b.board_id, "name": b.name, "status": b.status,
                 "path": b.path, "heartbeats": b.heartbeat_count}
                for b in boards
            ],
        }

    def fleet_self_test(self) -> Dict[str, Any]:
        """Run discovery + timeout check, return a pass/fail report (#300)."""
        self.discover()
        flagged = self.check_timeouts()
        boards = self.list()
        missing = [b.name for b in boards if b.status != "online"]
        return {
            "passed": not flagged and not missing,
            "detected": [b.name for b in boards if b.status == "online"],
            "missing": missing,
            "flagged": flagged,
        }
