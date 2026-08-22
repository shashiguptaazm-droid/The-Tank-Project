"""pytest suite for :mod:`tank_os.core.application_manager`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from tank_os.core.application_manager import (
    AppInfo,
    ApplicationManager,
)
from tank_os.core.permission_manager import (
    Permission,
    PermissionManager,
)


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

def _make_app_dir(
    root: Path,
    name: str = "demo",
    manifest: Optional[dict] = None,
    body: str = "VALUE = 1\n",
) -> Path:
    app_dir = root / name
    app_dir.mkdir()
    if manifest is not None:
        (app_dir / "app_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    (app_dir / "app.py").write_text(body, encoding="utf-8")
    return app_dir


@pytest.fixture
def isolated_discovery_root(tmp_path, monkeypatch):
    """Point ApplicationManager discovery at a clean tmp_path."""
    monkeypatch.setattr(
        "tank_os.core.application_manager._DISCOVERY_ROOTS",
        [tmp_path],
    )
    return tmp_path


# ───────────────────────────────────────────────────────────────────────────
# Discovery
# ───────────────────────────────────────────────────────────────────────────

def test_discover_finds_valid_manifest(isolated_discovery_root,
                                        event_catcher):
    _make_app_dir(isolated_discovery_root, "demo", manifest={
        "name": "Demo",
        "version": "1.2.3",
        "description": "an example app",
        "category": "tools",
        "tags": ["example", "demo"],
    })
    catcher = event_catcher("applications_discovered")
    am = ApplicationManager()
    found = am.discover()
    assert any(a.name == "Demo" for a in found)
    demo = am.get("Demo")
    assert demo is not None
    assert demo.version == "1.2.3"
    assert demo.category == "tools"
    assert demo.enabled is True
    assert demo.error is None
    [event] = catcher.of("applications_discovered")
    assert event.data["count"] >= 1


def test_discover_handles_invalid_manifest(isolated_discovery_root,
                                            event_catcher):
    app_dir = isolated_discovery_root / "broken"
    app_dir.mkdir()
    (app_dir / "app_manifest.json").write_text("not json{", encoding="utf-8")
    (app_dir / "app.py").write_text("print('hi')\n", encoding="utf-8")
    am = ApplicationManager()
    found = am.discover()
    info = am.get("broken")
    assert info is not None
    assert info.enabled is False
    assert info.error is not None
    assert "manifest invalid" in info.error


def test_discover_drops_app_when_entry_missing(isolated_discovery_root):
    """If no manifest and no app.py, app is registered as disabled."""
    (isolated_discovery_root / "ghost").mkdir()
    am = ApplicationManager()
    am.discover()
    info = am.get("ghost")
    assert info is not None
    assert info.enabled is False
    assert info.error == "no app.py"


def test_discover_does_not_re_register_duplicates(isolated_discovery_root):
    _make_app_dir(isolated_discovery_root, "dupe", manifest={
        "name": "Dupe",
        "version": "1.0",
    })
    am = ApplicationManager()
    am.discover()
    am.discover()
    # Exactly one entry, not two.
    matches = [a for a in am.all() if a.name == "Dupe"]
    assert len(matches) == 1


def test_register_unregister_manual(event_catcher):
    catcher = event_catcher("app_registered", "app_unregistered")
    am = ApplicationManager()
    am.register(AppInfo(name="manual", description="x"))
    assert am.get("manual") is not None
    assert am.unregister("manual") is True
    assert am.get("manual") is None
    assert len(catcher.of("app_registered")) == 1
    assert len(catcher.of("app_unregistered")) == 1


# ───────────────────────────────────────────────────────────────────────────
# Lookup / introspection
# ───────────────────────────────────────────────────────────────────────────

def test_search_matches_across_name_description_tags():
    am = ApplicationManager()
    am.register(AppInfo(name="camera", description="viewfinder",
                        tags=["vision"]))
    am.register(AppInfo(name="settings", description="noise gate",
                        tags=["audio"]))
    am.register(AppInfo(name="mapviewer", description="2d map UI",
                        tags=["maps"]))
    names = {a.name for a in am.search("vision")}
    assert names == {"camera"}
    names = {a.name for a in am.search("audio")}
    assert names == {"settings"}
    # Empty query returns everything.
    assert len(am.search("")) == 3


def test_by_category_filter():
    am = ApplicationManager()
    am.register(AppInfo(name="a", category="tools"))
    am.register(AppInfo(name="b", category="media"))
    am.register(AppInfo(name="c", category="tools"))
    tools = {a.name for a in am.by_category("tools")}
    assert tools == {"a", "c"}


def test_running_returns_only_running_apps():
    am = ApplicationManager()
    am.register(AppInfo(name="a"))
    am.register(AppInfo(name="b"))
    # Direct attribute poke is acceptable for a synthetic state setup.
    am.apps["a"].running = True
    running = {a.name for a in am.running()}
    assert running == {"a"}


def test_unregister_unknown_name_returns_false():
    am = ApplicationManager()
    assert am.unregister("never-existed") is False


# ───────────────────────────────────────────────────────────────────────────
# Lifecycle hooks
# ───────────────────────────────────────────────────────────────────────────

def test_invoke_lifecycle_calls_on_start_with_no_args():
    am = ApplicationManager()
    calls = []

    class _Inst:
        def on_start(self):
            calls.append(("start",))

        def on_stop(self):
            calls.append(("stop",))

    info = AppInfo(name="x", instance=_Inst())
    am.register(info)
    assert am._invoke_lifecycle(info, "on_start") is True
    assert am._invoke_lifecycle(info, "on_stop") is True
    assert calls == [("start",), ("stop",)]


def test_start_invokes_on_start_and_marks_running(isolated_discovery_root,
                                                  event_catcher):
    _make_app_dir(isolated_discovery_root, "viewer", manifest={
        "name": "Viewer",
        "permissions": [],
    })
    catcher = event_catcher("app_started")
    am = ApplicationManager()
    am.initialize()
    assert am.start("Viewer") is True
    info = am.get("Viewer")
    assert info.running is True
    assert len(catcher.of("app_started")) == 1


def test_start_unknown_app_returns_false():
    am = ApplicationManager()
    am.initialize()
    assert am.start("never") is False


def test_start_denied_when_declared_permission_cant_be_granted(
    isolated_discovery_root,
    monkeypatch,
):
    """If a declared permission can't be granted, start() must abort."""
    _make_app_dir(isolated_discovery_root, "snapper", manifest={
        "name": "Snapper",
        "permissions": ["CAMERA"],
    })

    # start() calls PermissionManager.check → PermissionManager.request
    # → req.wait(timeout=5.0). Force both checks to deny so the wait()
    # call is the deciding factor.
    from tank_os.core.permission_manager import PermissionManager as PM

    class _DeniedReq:
        resolved = True
        granted = False
        def wait(self, timeout=None):
            return False

    monkeypatch.setattr(PM, "check", lambda self, perm: False)
    monkeypatch.setattr(PM, "request",
                        lambda self, *a, **k: _DeniedReq())
    am = ApplicationManager()
    am.initialize()
    assert am.start("Snapper") is False
    info = am.get("Snapper")
    assert info.running is False


def test_stop_all_clears_running_flags():
    am = ApplicationManager()
    am.register(AppInfo(name="a"))
    am.register(AppInfo(name="b"))
    am.apps["a"].running = True
    am.apps["b"].running = True
    am.stop_all()
    assert am.apps["a"].running is False
    assert am.apps["b"].running is False


def test_system_wide_start_hook_fires_for_every_running_app():
    """ApplicationManager.on('on_start', cb) registers a system hook."""
    am = ApplicationManager()
    fired = []
    am.on("on_start", lambda info, *a, **k: fired.append(info.name))
    am.register(AppInfo(name="a", instance=type(
        "Inst", (), {"on_start": lambda self, *a, **k: None}
    )()))
    am._invoke_lifecycle(am.get("a"), "on_start")
    assert fired == ["a"]


def test_on_unknown_hook_returns_false():
    am = ApplicationManager()
    assert am.on("not_a_real_hook", lambda info: None) is False
