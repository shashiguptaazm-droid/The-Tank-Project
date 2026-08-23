"""Tests for the consolidated ``tank unoq`` CLI (master-plan §P)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tank_os.cli.unoq_cli import main, build_parser, SUBCOMMANDS


def test_parser_exposes_all_priority_subcommands() -> None:
    parser = build_parser()
    assert set(SUBCOMMANDS) == {
        "status", "diagnostics", "power", "sensors", "motors", "mcu",
        "esp32", "doctor", "supervisor", "self-test", "safety-test", "all",
    }
    args = parser.parse_args(["status"])
    assert args.command == "status"


def test_status_exits_zero() -> None:
    assert main(["status"]) == 0


def test_power_exits_zero() -> None:
    assert main(["power"]) == 0


def test_sensors_exits_zero() -> None:
    assert main(["sensors"]) == 0


def test_esp32_exits_zero() -> None:
    assert main(["esp32"]) == 0


def test_diagnostics_json_flag() -> None:
    assert main(["diagnostics", "--json"]) == 0


def test_safety_test_passes() -> None:
    assert main(["safety-test"]) == 0


def test_doctor_exits_zero() -> None:
    assert main(["doctor"]) == 0


def test_supervisor_exits_zero() -> None:
    assert main(["supervisor"]) == 0


def test_unknown_command_fails() -> None:
    with pytest.raises(SystemExit):
        main(["not-a-command"])
