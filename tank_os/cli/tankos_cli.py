"""tank — TankOS CLI surface (architecture plan §22).

A real operating-system-like interface over the canonical TankOS API:

    tank status          — robot state, devices, health, missions
    tank health          — health report from measurable signals
    tank devices         — device registry with lifecycle
    tank sensors         — sensor devices
    tank motors          — motor devices
    tank battery         — battery device
    tank mission list    — missions
    tank mission start   — start a mission (type)
    tank state           — canonical robot state machine
    tank command         — send a validated command (GUI/AI → safety → execute)
    tank events          — recent EventBus history
    tank safety          — E-stop / safety authority
    tank api             — the canonical API surface

Usage:
    python3 -m tank_os.cli.tankos_cli status
    python3 -m tank_os.cli.tankos_cli mission start patrol
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from tank_os.core.tankos_core import (
    Command, CommandSource, MissionState, RobotState, TankOS,
)

TANK = TankOS()


def _out(obj) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2))
    else:
        print(obj)


def _ready() -> None:
    if not TANK.state.state().value or TANK.state.state() == RobotState.BOOT:
        TANK.boot()


def cmd_status(args) -> int:
    _ready()
    _out(TANK.status())
    return 0


def cmd_health(args) -> int:
    _ready()
    _out(TANK.health.report().to_dict())
    return 0


def cmd_devices(args) -> int:
    _ready()
    devs = TANK.devices.list(device_type=args.type)
    _out([d.to_dict() for d in devs])
    return 0


def cmd_sensors(args) -> int:
    _ready()
    _out([d.to_dict() for d in TANK.devices.list(device_type="sensor") or
          TANK.devices.list(device_type="imu") or TANK.devices.list()])
    return 0


def cmd_battery(args) -> int:
    _ready()
    b = TANK.devices.get("battery")
    _out(b.to_dict() if b else {"error": "no battery device"})
    return 0


def cmd_state(args) -> int:
    _ready()
    _out({"state": TANK.state.state().value,
          "history": TANK.state.history()})
    return 0


def cmd_mission(args) -> int:
    _ready()
    if args.action == "list":
        _out([m.to_dict() for m in TANK.missions.list()])
    elif args.action == "start":
        m = TANK.missions.create(args.type)
        TANK.missions.start(m.id)
        _out(m.to_dict())
    elif args.action == "pause":
        m = TANK.missions.list()[-1] if TANK.missions.list() else None
        TANK.missions.pause(m.id) if m else None
        _out(m.to_dict() if m else {"error": "no missions"})
    elif args.action == "complete":
        m = TANK.missions.list()[-1] if TANK.missions.list() else None
        TANK.missions.complete(m.id) if m else None
        _out(m.to_dict() if m else {"error": "no missions"})
    return 0


def cmd_command(args) -> int:
    _ready()
    source = CommandSource(args.source)
    result = TANK.commands.send(Command(args.command, source,
                                        json.loads(args.args) if args.args else {}))
    _out(result)
    return 0


def cmd_safety(args) -> int:
    _ready()
    if args.action == "estop":
        TANK.commands.estop()
        _out({"safety": "E-STOP LATCHED", "state": TANK.state.state().value})
    elif args.action == "clear":
        TANK.commands.estop_clear()
        _out({"safety": "E-STOP CLEARED", "state": TANK.state.state().value})
    else:
        _out({"state": TANK.state.state().value,
              "can_accept_commands": TANK.state.can_accept_commands()})
    return 0


def cmd_events(args) -> int:
    _ready()
    _out([{"type": e.type, "summary": (e.data or {}).get("summary", "")}
          for e in TANK.bus.history(limit=args.limit)])
    return 0


def cmd_api(args) -> int:
    _out(TANK.api())
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="tank", description="TankOS CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="robot state, devices, health, missions")
    sub.add_parser("health", help="health report from measurable signals")
    p_dev = sub.add_parser("devices", help="device registry with lifecycle")
    p_dev.add_argument("--type", default=None, help="filter by device type")
    sub.add_parser("sensors", help="sensor devices")
    sub.add_parser("motors", help="motor devices")
    sub.add_parser("battery", help="battery device")
    sub.add_parser("state", help="canonical robot state machine")

    p_mission = sub.add_parser("mission", help="mission engine")
    p_mission.add_argument("action", choices=["list", "start", "pause", "complete"])
    p_mission.add_argument("--type", default="patrol", help="mission type (start)")

    p_cmd = sub.add_parser("command", help="send a validated command")
    p_cmd.add_argument("command")
    p_cmd.add_argument("--source", default="human",
                       choices=["human", "ai", "mission", "remote", "safety",
                                "system"])
    p_cmd.add_argument("--args", default="{}", help="JSON args")

    p_safety = sub.add_parser("safety", help="safety authority")
    p_safety.add_argument("action", nargs="?", default="status",
                          choices=["status", "estop", "clear"])

    p_events = sub.add_parser("events", help="recent EventBus history")
    p_events.add_argument("--limit", type=int, default=15)

    sub.add_parser("api", help="the canonical API surface")

    args = parser.parse_args(argv)
    handlers = {
        "status": cmd_status, "health": cmd_health, "devices": cmd_devices,
        "sensors": cmd_sensors, "motors": cmd_devices, "battery": cmd_battery,
        "state": cmd_state, "mission": cmd_mission, "command": cmd_command,
        "safety": cmd_safety, "events": cmd_events, "api": cmd_api,
    }
    if args.cmd == "motors":
        args.type = "motor"
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
