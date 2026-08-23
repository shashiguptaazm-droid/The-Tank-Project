"""Tests for the ESP32 fleet manager (master-plan §N, #281–300)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tank_os.core.esp32_fleet import ESP32FleetManager, KNOWN_BOARDS


@pytest.fixture()
def fleet() -> ESP32FleetManager:
    """Fresh singleton with a fake discovery source."""
    f = ESP32FleetManager()
    # reset instance state for test isolation
    f._boards = {}
    f._seen_events = set()
    f.configure(
        discovery_fn=lambda: [
            {"path": "/dev/ttyACM0", "description": "usb jtag/serial debug unit 303a:1001 14:c1:9f:c1:2c:24"},
            {"path": "/dev/ttyACM1", "description": "usb jtag/serial debug unit 303a:1001 a0:f2:62:e3:df:f4"},
            {"path": "/dev/ttyACM2", "description": "usb jtag/serial debug unit 303a:1001 28:84:85:4c:84:04"},
        ],
        heartbeat_timeout=1.0,
    )
    return f


def test_discover_all_three_boards(fleet: ESP32FleetManager) -> None:
    fleet.discover()
    boards = fleet.list()
    assert len(boards) == 3
    assert all(b.status == "online" for b in boards)
    assert {b.board_id for b in boards} == {k["id"] for k in KNOWN_BOARDS}


def test_discover_serial_match_is_online_even_without_tty(fleet: ESP32FleetManager) -> None:
    fleet.configure(discovery_fn=lambda: [
        {"path": "", "description": "usb jtag/serial debug unit 303a:1001 14:c1:9f:c1:2c:24"},
    ])
    fleet.discover()
    cam = fleet.get("esp32-cam")
    assert cam is not None
    assert cam.status == "online"


def test_heartbeat_and_telemetry(fleet: ESP32FleetManager) -> None:
    fleet.discover()
    entry = fleet.mark_heartbeat("esp32-cam", firmware="esphome-2024.6",
                                 ip="192.168.31.145", rssi=-45)
    assert entry.heartbeat_count == 1
    assert entry.firmware == "esphome-2024.6"
    assert entry.telemetry["rssi"] == -45
    assert fleet.summary()["boards"][0]["heartbeats"] == 1


def test_timeout_flags_board(fleet: ESP32FleetManager) -> None:
    fleet.discover()
    fleet.mark_heartbeat("esp32-cam")
    fleet._boards["esp32-cam"].last_seen = time.time() - 10  # older than 1s timeout
    flagged = fleet.check_timeouts()
    assert "esp32-cam" in flagged
    assert fleet.get("esp32-cam").status == "offline"


def test_fleet_self_test_passes_when_all_online(fleet: ESP32FleetManager) -> None:
    fleet.discover()
    report = fleet.fleet_self_test()
    assert report["passed"] is True
    assert len(report["detected"]) == 3


def test_fleet_self_test_reports_missing(fleet: ESP32FleetManager) -> None:
    fleet.configure(discovery_fn=lambda: [])  # nothing present
    report = fleet.fleet_self_test()
    assert report["passed"] is False
    assert len(report["missing"]) == 3
