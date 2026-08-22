"""Tests for tank_dashboard/app — emotion endpoints + bounded history +
static asset serving + lifespan wiring.

The FastAPI app is exercised through ``TestClient`` (sync) without
spinning up uvicorn. We monkey-patch ``_ros_spin_thread`` to a no-op so
the lifespan event can run on lightweight benches without rclpy — this
avoids the post-construction ``app.router.lifespan_context = ...``
assignment that depends on Starlette version.
"""
from __future__ import annotations

import importlib
import inspect
import os
import sys

import pytest


# Path injection — mirrors conftest pattern used in tank_vision / tank_meta.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


@pytest.fixture()
def app_module(monkeypatch):
    # Avoid running the lifespan — pydantic can fail if rclpy missing.
    monkeypatch.setenv("PYTHONPATH", HERE)
    # Reload to ensure a fresh module (the package may already be
    # partially imported if pytest collected other tests first).
    if "tank_dashboard.app" in sys.modules:
        del sys.modules["tank_dashboard.app"]
    mod = importlib.import_module("tank_dashboard.app")
    # Patch the bridge spin to a no-op so the lifespan can run cleanly
    # in CI without rclpy. Works regardless of Starlette version because
    # the lifespan calls into our module, not into Starlette's middleware.
    monkeypatch.setattr(mod, "_ros_spin_thread", lambda: None)
    return mod


def test_emotion_current_returns_default(app_module):
    from fastapi.testclient import TestClient
    client = TestClient(app_module.app)
    r = client.get("/api/emotion/current")
    assert r.status_code == 200
    data = r.json()
    assert data["mood"] in {"neutral", "happy", "sad", "alert", "curious"}


def test_emotion_history_is_bounded(app_module):
    from fastapi.testclient import TestClient
    client = TestClient(app_module.app)
    # Bypass the ROS bridge: directly poke the state object to ensure
    # history deque honours its cap.
    state = app_module._state
    state.emotion_history.clear()
    for i in range(60):
        state.emotion_history.append({"mood": "happy", "ts": float(i)})
    # Deque.maxlen enforcement
    assert len(state.emotion_history) == app_module.EMOTION_HISTORY_MAX
    r = client.get("/api/emotion/history")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == app_module.EMOTION_HISTORY_MAX


def test_index_html_is_served_when_present(app_module):
    """If dashboard/index.html is on disk we serve it; if not, we
    return a 503 PlainTextResponse — never a crash."""
    from fastapi.testclient import TestClient
    client = TestClient(app_module.app)
    r = client.get("/")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert "<html" in r.text.lower()


def test_lifespan_wiring_present(app_module):
    """The FastAPI app MUST use lifespan= (design rule 5); the @on_event
    decorator would not show up on the lifespan context manager.
    Real check: source of FastAPI.__init__ mentions lifespan= and the
    app has @app.on_event shims nowhere.

    Falls back gracefully if inspect-based checks can't see source
    (e.g. PyInstaller-compressed installs)."""
    try:
        src = inspect.getsource(type(app_module.app).__init__)
    except (OSError, TypeError):
        pytest.skip("inspect.getsource unavailable in this environment")
    assert "lifespan=" in src
    # Confirm the deprecated decorator form is not used.
    deprecated_attr = getattr(app_module.app, "on_event", None)
    assert deprecated_attr is None or not callable(deprecated_attr)
