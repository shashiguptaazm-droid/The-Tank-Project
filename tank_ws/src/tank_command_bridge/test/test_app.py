"""Tests for tank_command_bridge.app — manifest, dispatch, audit.

Uses :class:`fastapi.testclient.TestClient` + uvicorn-mock so we can
exercise the FastAPI surface area in CI without rclpy.

Monkeypatches:
- ``_RCLPY_AVAILABLE`` reuses the bench stub path (BridgeState alone).
- ``_RATE`` reuses a fresh RateLimiter with a deterministic clock.
- Bridge spin thread is bypassed; the dispatch path uses the
  ``_StubPub`` synthesised in app.py when ``bn is None``.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import uuid

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # so conftest is auto-found


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("TANK_API_KEYS", '{"goodkey":"admin"}')
    monkeypatch.delenv("TANK_API_KEY", raising=False)
    if "tank_command_bridge.app" in sys.modules:
        del sys.modules["tank_command_bridge.app"]
    mod = importlib.import_module("tank_command_bridge.app")
    # Don't spin a ROS thread in the lifespan.
    monkeypatch.setattr(mod, "start_bridge_thread", lambda: None)
    return mod


@pytest.fixture()
def client(app_module):
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)


def test_manifest_endpoint_returns_doc(client):
    r = client.get("/api/cmd/manifest")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "1"
    tools = {t["name"] for t in data["tools"]}
    # All commands ship in the manifest
    for expected in ("estop", "move", "patrol", "dock", "capture",
                     "telemetry", "query", "chat"):
        assert expected in tools, f"missing {expected} from manifest"


def test_dispatch_move_clamps_extremes(client):
    r = client.post(
        "/api/cmd/move",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": str(uuid.uuid4()),
              "params": {"vx": 5.0, "wz": 99.0, "duration_s": 99.0}},
    )
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["vx_eff"] == 0.5            # clamped to MAX_VX
    assert result["wz_eff"] == 1.5            # clamped to MAX_WZ
    assert result["duration_s_eff"] == 5.0    # clamped to MAX_DURATION_S


def test_dispatch_estop_latches_following_writes(client):
    r1 = client.post(
        "/api/cmd/estop",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": str(uuid.uuid4()), "params": {"state": True}},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/cmd/move",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": str(uuid.uuid4()),
              "params": {"vx": 0.1, "wz": 0.0, "duration_s": 0.5}},
    )
    assert r2.status_code == 200
    assert r2.json()["result"].get("rejected") == "estop_latched"
    # Release
    r3 = client.post(
        "/api/cmd/estop",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": str(uuid.uuid4()), "params": {"state": False}},
    )
    assert r3.status_code == 200


def test_audit_log_records_dispatch_with_audit_id(client):
    audit_id = str(uuid.uuid4())
    client.post(
        "/api/cmd/chat",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": audit_id, "params": {"text": "ping"}})

    r = client.get(
        "/api/cmd/audit?limit=5",
        headers={"Authorization": "Bearer goodkey"},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(it["audit_id"] == audit_id for it in items), \
        f"audit_id {audit_id} not found in {items}"
    found = next(it for it in items if it["audit_id"] == audit_id)
    assert found["command"] == "chat"
    assert found["status"] == 200


def test_unknown_command_returns_404(client):
    r = client.post(
        "/api/cmd/teleport",
        headers={"Authorization": "Bearer goodkey"},
        json={"audit_id": str(uuid.uuid4()), "params": {}},
    )
    assert r.status_code == 404


def test_missing_auth_returns_401(client):
    r = client.post(
        "/api/cmd/chat",
        json={"audit_id": str(uuid.uuid4()), "params": {"text": "x"}},
    )
    # r.status_code in 401..503 — must NOT be 200, must not be 422
    assert r.status_code in (401, 503)
