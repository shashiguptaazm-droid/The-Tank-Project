"""``tank unoq`` — consolidated UNO Q command surface (master-plan §P).

One command, real managers underneath. Covers the P0/P1 priority list
without adding new subsystems: everything delegates to the existing
PowerManager, DiagnosticsManager, HardwareManager, BootSequence and the
new ESP32FleetManager.

Usage:
    python3 -m tank_os.cli.unoq_cli status
    python3 -m tank_os.cli.unoq_cli diagnostics
    python3 -m tank_os.cli.unoq_cli power
    python3 -m tank_os.cli.unoq_cli sensors
    python3 -m tank_os.cli.unoq_cli motors
    python3 -m tank_os.cli.unoq_cli mcu
    python3 -m tank_os.cli.unoq_cli esp32 [--self-test]
    python3 -m tank_os.cli.unoq_cli self-test
    python3 -m tank_os.cli.unoq_cli safety-test
    python3 -m tank_os.cli.unoq_cli all
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# ─── Box drawing helpers (match the TankOS terminal aesthetic) ────────

def _bar(title: str, width: int = 58) -> str:
    inner = f" {title} ".center(width - 2)
    return f"┌{'─' * (width - 2)}┐\n│{inner}│\n└{'─' * (width - 2)}┘"


def _kv(key: str, value: Any, width: int = 58) -> str:
    line = f"  {key:<18} {value}"
    return line[:width]


def _ok(cond: bool) -> str:
    return "✅" if cond else "❌"


# ─── Sub-command implementations (all delegate to existing managers) ──

def cmd_status(args) -> int:
    """System overview — CPU, RAM, disk, temp, tools (#321)."""
    from tank_os.core.diagnostics_manager import DiagnosticsManager
    from tank_os.core.power_manager import PowerManager
    from tank_os.core.esp32_fleet import ESP32FleetManager

    d = DiagnosticsManager().collect()
    pm = PowerManager()
    fleet = ESP32FleetManager().summary()
    print(_bar("UNO Q — System Status"))
    print(_kv("CPU", f"{d.get('cpu', {}).get('percent', '?')}% ({d.get('cpu', {}).get('count', '?')} cores)"))
    mem = d.get("memory", {})
    print(_kv("RAM", f"{mem.get('percent', '?')}% ({mem.get('available_gb', '?')} GB avail)"))
    disk = d.get("disk", {})
    print(_kv("Disk", f"{disk.get('percent', '?')}% ({disk.get('used_gb', '?')} GB used)"))
    temp = d.get("temperature", {})
    print(_kv("Temp", f"{temp.get('cpu_c', '?')} °C"))
    print(_kv("Uptime", f"{d.get('uptime', 0) / 3600:.1f} h"))
    print(_kv("Battery", f"{pm.battery_percent}% {'⚡' if pm.is_charging else '🔋'} {pm.voltage} V"))
    print(_kv("ESP32 fleet", f"{fleet['online']}/{fleet['total']} online"))
    return 0


def cmd_diagnostics(args) -> int:
    """Full diagnostics snapshot as JSON (#322, #12)."""
    from tank_os.core.diagnostics_manager import DiagnosticsManager
    d = DiagnosticsManager().collect()
    if args.json:
        print(json.dumps(d, indent=2))
    else:
        print(_bar("UNO Q — Diagnostics"))
        for key in ("cpu", "memory", "disk", "temperature", "network", "ros", "uptime"):
            print(_kv(key, json.dumps(d.get(key, {}), default=str)))
    return 0


def cmd_power(args) -> int:
    """Battery / power rail telemetry (#326, #9)."""
    from tank_os.core.power_manager import PowerManager
    pm = PowerManager()
    print(_bar("UNO Q — Power"))
    print(_kv("Battery", f"{pm.battery_percent}%"))
    print(_kv("Voltage", f"{pm.voltage} V"))
    print(_kv("Current", f"{pm.current_ma} mA"))
    print(_kv("Temp", f"{pm.battery_temp_c} °C"))
    print(_kv("Charge cycles", pm.charge_cycles))
    print(_kv("Charging", "⚡ yes" if pm.is_charging else "no"))
    print(_kv("Performance", pm.performance_mode))
    return 0


def cmd_sensors(args) -> int:
    """Serial / USB sensor inventory (#323, #11–18)."""
    from tank_os.core.hardware_manager import HardwareManager
    hw = HardwareManager()
    if not hw.get_devices():
        hw.initialize()
    devs = hw.get_devices("serial")
    print(_bar(f"UNO Q — Sensors ({len(devs)})"))
    for dev in devs[:15]:
        print(_kv(dev.device_type, f"{dev.name} {dev.path} {_ok(dev.connected)}"))
    return 0


def cmd_motors(args) -> int:
    """Motor controller status from the ROS2 motion package (#324, #61–85)."""
    try:
        from tank_motion.motor_controller import get_motor_controller
        mc = get_motor_controller()
        print(_bar("UNO Q — Motors"))
        print(_kv("State", getattr(mc, "state", "unknown")))
        print(_kv("Speed L/R", f"{getattr(mc, 'left_speed', '?')} / {getattr(mc, 'right_speed', '?')}"))
        print(_kv("Enabled", getattr(mc, "enabled", "?")))
        print(_kv("Fault", getattr(mc, "fault", "none")))
    except ImportError:
        print(_bar("UNO Q — Motors"))
        print("  ⚠ tank_motion not importable on this host — motors live on the Jetson.")
        return 1
    return 0


def cmd_mcu(args) -> int:
    """MCU heartbeat / communication bridge status (#327, #41–60)."""
    try:
        from tank_motion.bridge import get_bridge
        bridge = get_bridge()
        print(_bar("UNO Q — MCU Bridge"))
        print(_kv("Connected", _ok(bridge.is_connected())))
        print(_kv("Last heartbeat", bridge.last_heartbeat()))
    except ImportError:
        print(_bar("UNO Q — MCU Bridge"))
        print("  ⚠ tank_motion.bridge not importable here — MCU link lives on the Jetson.")
        return 1
    return 0


def cmd_esp32(args) -> int:
    """ESP32 fleet status / self-test (#329, #281–300)."""
    from tank_os.core.esp32_fleet import ESP32FleetManager
    fleet = ESP32FleetManager()
    fleet.discover()
    if args.self_test:
        report = fleet.fleet_self_test()
        print(_bar("UNO Q — ESP32 Fleet Self-Test"))
        print(_kv("Passed", _ok(report["passed"])))
        print(_kv("Detected", ", ".join(report["detected"]) or "—"))
        print(_kv("Missing", ", ".join(report["missing"]) or "—"))
        return 0 if report["passed"] else 1
    summary = fleet.summary()
    print(_bar(f"UNO Q — ESP32 Fleet ({summary['online']}/{summary['total']} online)"))
    for b in summary["boards"]:
        print(_kv(b["name"], f"{b['status']} {b['path']} ({b['heartbeats']} hb)"))
    if summary["offline"]:
        print(_kv("Note", "offline boards live on the Jetson (dual-eyes, DFRobot)"))
    return 0


def cmd_self_test(args) -> int:
    """End-to-end hardware self-test (#1, #235): boot steps + diagnostics + fleet."""
    from tank_os.startup.boot_sequence import BootSequence
    from tank_os.core.esp32_fleet import ESP32FleetManager

    print(_bar("UNO Q — Hardware Self-Test"))
    boot = BootSequence()
    ok = boot.run()
    for step, passed in boot.results().items():
        print(_kv(step, _ok(passed)))
    fleet = ESP32FleetManager().fleet_self_test()
    print(_kv("ESP32 fleet", _ok(fleet["passed"])))
    return 0 if ok else 1


def cmd_safety_test(args) -> int:
    """Safety-class validation of representative commands (#332, #166–190)."""
    from tank_os.shell.terminal.safety import CommandSafety, SafetyClass

    safety = CommandSafety()
    probes: List[tuple] = [
        ("echo hello", SafetyClass.SAFE),
        ("ls -la", SafetyClass.READ),
        ("df -h", SafetyClass.READ),
        ("rm -rf /", SafetyClass.BLOCKED),
        ("sudo poweroff", SafetyClass.DANGEROUS),
    ]
    print(_bar("UNO Q — Safety Test"))
    passed = True
    for cmd, expected in probes:
        got = safety.classify(cmd)
        ok = got == expected
        passed = passed and ok
        print(_kv(cmd, f"{got.name} (expect {expected.name}) {_ok(ok)}"))
    print(_kv("RESULT", "PASS ✅" if passed else "FAIL ❌"))
    return 0 if passed else 1


def cmd_all(args) -> int:
    """Run status + self-test + safety-test back to back."""
    rc = 0
    for fn in (cmd_status, cmd_self_test, cmd_safety_test):
        print()
        rc = rc or fn(args)
    return rc


# ─── Argparse ─────────────────────────────────────────────────────────

SUBCOMMANDS = {
    "status": (cmd_status, "system overview (CPU/RAM/disk/temp/battery/fleet)"),
    "diagnostics": (cmd_diagnostics, "full diagnostics snapshot (JSON with --json)"),
    "power": (cmd_power, "battery & power rail telemetry"),
    "sensors": (cmd_sensors, "serial/USB sensor inventory"),
    "motors": (cmd_motors, "motor controller status (Jetson-side)"),
    "mcu": (cmd_mcu, "MCU bridge heartbeat (Jetson-side)"),
    "esp32": (cmd_esp32, "ESP32 fleet status (--self-test for full check)"),
    "self-test": (cmd_self_test, "boot steps + fleet end-to-end self-test"),
    "safety-test": (cmd_safety_test, "validate safety classification of commands"),
    "all": (cmd_all, "status + self-test + safety-test"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tank unoq",
        description="Consolidated UNO Q command surface (master-plan §P).",
    )
    parser.add_argument("command", choices=sorted(SUBCOMMANDS),
                        help="subcommand to run")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output (diagnostics)")
    parser.add_argument("--self-test", action="store_true",
                        help="run full self-test (esp32)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    fn = SUBCOMMANDS[args.command][0]
    try:
        return fn(args)
    except Exception as exc:                                        # noqa: BLE001
        print(f"⚠ {args.command} failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
