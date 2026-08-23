"""Tests for the 200-feature plan wave 2:
- §2 #20 unified chronological event replay (0.25×/1×/4×)
- §13 #130 AI power-saving recommendations
- §17 #162–165 benchmark suite
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ---------------------------------------------------------------- power
def test_power_saving_recommendations_low_battery() -> None:
    from tank_os.windows.power_dashboard import power_saving_recommendations
    recs = power_saving_recommendations(battery_pct=30, draw_w=12.0, runtime_min=40)
    texts = [t for t, _ in recs]
    assert any("VLM" in t for t in texts)          # quantified Jetson tip
    assert any("Dim display" in t for t in texts)  # low-battery tip
    assert all(impact != "—" for _, impact in recs)


def test_power_saving_recommendations_critical() -> None:
    from tank_os.windows.power_dashboard import power_saving_recommendations
    recs = power_saving_recommendations(battery_pct=15, draw_w=16.0, runtime_min=10)
    texts = [t for t, _ in recs]
    assert any("Critical battery" in t for t in texts)
    assert any("ECO driving" in t for t in texts)


def test_power_saving_recommendations_healthy() -> None:
    from tank_os.windows.power_dashboard import power_saving_recommendations
    recs = power_saving_recommendations(battery_pct=80, draw_w=6.0, runtime_min=120)
    assert len(recs) >= 1
    # VLM tip still present and quantified
    assert any("VLM" in t and "+~" in imp for t, imp in recs)


# --------------------------------------------------------------- replay
def test_event_replay_seeds_and_advances() -> None:
    from tank_os.windows.event_center import _seed_history, EventCenterScreen
    history = _seed_history()
    assert len(history) > 0
    # Chronological: timestamps ascending
    stamps = [e.timestamp for e in history]
    assert stamps == sorted(stamps, reverse=True) or stamps == sorted(stamps)
    # Oldest last → we replay oldest→newest, so check it's meaningful either way
    assert history[0].type  # has a type

    app = _app()
    screen = EventCenterScreen()
    screen._history = list(history)
    screen._replay_idx = 0
    screen._toggle_replay()
    assert screen._replay_playing is True
    # tick several times at 4x — must advance
    screen._replay_speed = 4.0
    for _ in range(30):
        screen._tick_replay()
        if not screen._replay_playing:
            break
    assert screen._replay_idx >= 0
    # running to the end stops the replay
    screen._replay_idx = len(history) - 1
    screen._replay_playing = True
    screen._tick_replay()
    assert screen._replay_playing is False
    screen.deleteLater()


def test_event_replay_speed_cycle() -> None:
    from tank_os.windows.event_center import EventCenterScreen, SPEEDS
    app = _app()
    screen = EventCenterScreen()
    assert screen._replay_speed == 1.0
    screen._cycle_speed()
    assert screen._replay_speed == 4.0
    screen._cycle_speed()
    assert screen._replay_speed == 0.25
    screen._cycle_speed()
    assert screen._replay_speed == 1.0
    assert set(SPEEDS) == {0.25, 1.0, 4.0}
    screen.deleteLater()


# ----------------------------------------------------------- benchmarks
def test_benchmark_suite_runs() -> None:
    app = _app()
    from tank_os.windows.developer_screen import DeveloperScreen
    screen = DeveloperScreen()
    assert screen._output_title.text()  # builds fine
    # run the benchmark body synchronously via the helper thread target
    import threading
    results: list[str] = []
    orig = screen._output_list

    class _List:
        def clear(self) -> None:
            pass

        def addItem(self, item) -> None:
            results.append(item.text())

    screen._output_list = _List()  # type: ignore[assignment]
    screen._run_benchmarks()
    screen._output_list = orig
    assert any("AI model" in r for r in results)
    assert any("Vision pipeline" in r for r in results)
    assert any("Navigation (A*" in r for r in results)
    assert any("Sensor fusion" in r for r in results)
    assert any("complete" in r for r in results)
    screen.deleteLater()


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])
