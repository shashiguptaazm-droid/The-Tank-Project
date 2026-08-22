"""Shared fixtures for TankOS core manager tests.

* ``_reset_singletons`` (autouse) — every core singleton starts fresh
  in each test (Voice / AI / Permission / Application / Update /
  Settings / EventBus).
* ``event_catcher`` — factory that returns a small helper which
  subscribes to a list of event types and stores every event that
  fires so a test can introspect the actual bus emissions.
* ``silence_tts_worker`` — disables VoiceManager's real playback
  thread, so synchronous queue / state-machine tests don't flake.
* ``_quiet_logs`` (autouse) — keeps INFO-level manager log noise
  out of the pytest transcript.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Callable, Dict, List

import pytest

# Make ``tank_os.core.*`` importable regardless of pytest CWD.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tank_os.core.ai_manager import AIManager  # noqa: E402
from tank_os.core.application_manager import ApplicationManager  # noqa: E402
from tank_os.core.event_bus import Event, EventBus  # noqa: E402
from tank_os.core.permission_manager import PermissionManager  # noqa: E402
from tank_os.core.settings_manager import SettingsManager  # noqa: E402
from tank_os.core.update_manager import UpdateManager  # noqa: E402
from tank_os.core.voice_manager import VoiceManager  # noqa: E402


_SINGLETONS_TO_RESET = (
    EventBus,
    SettingsManager,
    VoiceManager,
    AIManager,
    PermissionManager,
    ApplicationManager,
    UpdateManager,
)


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch: pytest.MonkeyPatch):
    """Clear every core singleton before each test.

    The managers use ``_instance = None`` with a class-level lock —
    this is the cleanest way to wipe state without touching the
    production code.
    """
    for cls in _SINGLETONS_TO_RESET:
        monkeypatch.setattr(cls, "_instance", None)
    yield


@pytest.fixture(autouse=True)
def _quiet_logs():
    """Drop tank_os INFO logs to ERROR so pytest output stays readable."""
    logging.getLogger("tank_os").setLevel(logging.ERROR)
    logging.getLogger("tank_os.voice_manager").setLevel(logging.ERROR)
    logging.getLogger("tank_os.ai_manager").setLevel(logging.ERROR)
    logging.getLogger("tank_os.permissions").setLevel(logging.ERROR)
    logging.getLogger("tank_os.app_manager").setLevel(logging.ERROR)
    logging.getLogger("tank_os.update_manager").setLevel(logging.ERROR)
    yield
    for name in ("tank_os", "tank_os.voice_manager", "tank_os.ai_manager",
                 "tank_os.permissions", "tank_os.app_manager",
                 "tank_os.update_manager"):
        logging.getLogger(name).setLevel(logging.NOTSET)


class EventCatcher:
    """Subscribe to many event types, store payload, expose queries."""

    def __init__(self, *event_types: str) -> None:
        self.by_type: Dict[str, List[Event]] = {t: [] for t in event_types}
        self._bus = EventBus()
        self._bus_id = id(self._bus)
        for event_type in event_types:
            self._bus.on(event_type, self._make_handler(event_type))

    def _make_handler(self, event_type: str) -> Callable[[Event], None]:
        def _h(evt: Event) -> None:
            self.by_type[event_type].append(evt)
        return _h

    def of(self, event_type: str) -> List[Event]:
        return list(self.by_type.get(event_type, []))

    def count(self, event_type: str) -> int:
        return len(self.by_type.get(event_type, []))


@pytest.fixture
def event_catcher() -> Callable[..., EventCatcher]:
    """Factory: ``event_catcher("a", "b")`` returns an :class:`EventCatcher`."""
    def _factory(*event_types: str) -> EventCatcher:
        return EventCatcher(*event_types)
    return _factory


@pytest.fixture
def silence_tts_worker(monkeypatch: pytest.MonkeyPatch):
    """Replace VoiceManager._start_tts_thread with a no-op for the test."""
    monkeypatch.setattr(VoiceManager, "_start_tts_thread",
                        lambda self: None)
    return monkeypatch
