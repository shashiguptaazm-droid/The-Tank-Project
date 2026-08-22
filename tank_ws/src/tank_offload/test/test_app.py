"""End-to-end FastAPI tests for tank_offload.app (port 8085).

We bind the lazy singletons to tmp-file-backed instances and exercise
the API via ``fastapi.testclient.TestClient``. Auth defaults to open
mode (``TANK_OFFLOAD_OPEN=1``) so the suite runs unattended in the
CI sandboxes that don't have ``httpx``. A single auth test exercises
the locked-down path with a real ``TANK_API_KEY``.
"""
from __future__ import annotations

import os
import tempfile

import pytest

# Skip the entire module if httpx isn't available \u2014 TestClient needs it.
pytest.importorskip("httpx")

# Set BOTH env vars BEFORE importing the app so module-level constants
# lock in.
os.environ["TANK_OFFLOAD_NO_ROS"] = "1"
os.environ["TANK_OFFLOAD_OPEN"] = "1"

_tmpdir = tempfile.mkdtemp(prefix="tank_offload_test_")
os.environ["TANK_OFFLOAD_DATA"] = _tmpdir
os.environ["TANK_OFFLOAD_DB"] = os.path.join(_tmpdir, "offload.db")
os.environ["TANK_OFFLOAD_STAGING_DIR"] = os.path.join(_tmpdir, "stage")
os.environ["TANK_OFFLOAD_DEADLETTER_DIR"] = os.path.join(_tmpdir, "dead")
os.environ["TANK_OFFLOAD_WATCH_PATH"] = _tmpdir   # policy won't see anything
os.environ["TANK_OFFLOAD_THRESHOLD_PCT"] = "85"
os.environ["TANK_OFFLOAD_RECOVER_PCT"] = "75"


from fastapi.testclient import TestClient                       # noqa: E402

# Import AFTER env so module-level constants stabilise.
from tank_offload import app as app_module                       # noqa: E402
from tank_offload.offload_store import OffloadStore              # noqa: E402
from tank_offload.policy import OffloadPolicy, PolicyConfig      # noqa: E402
from tank_offload.rclone_facade import RcloneConfig, RcloneFacade  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    store = OffloadStore(os.environ["TANK_OFFLOAD_DB"])
    cfg = RcloneConfig(
        nextcloud_url="https://vps.example/remote.php/dav/files/u",
        nextcloud_user="u",
        nextcloud_password="pw",
        staging_dir=os.environ["TANK_OFFLOAD_STAGING_DIR"],
        deadletter_dir=os.environ["TANK_OFFLOAD_DEADLETTER_DIR"],
    )
    facade = RcloneFacade(cfg)
    policy = OffloadPolicy(PolicyConfig(
        recordings_glob=os.path.join(_tmpdir, "recordings/*.avi"),
        logs_glob=os.path.join(_tmpdir, "logs/*.log"),
        db_snapshot_glob=os.path.join(_tmpdir, "data/*.tar.gz"),
    ))
    app_module._reset_singletons_for_tests(store, policy, facade)
    return TestClient(app_module.app)


# -------------------- health / version --------------------

def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["rclpy"] is False      # rclpy missing in CI sandbox
    assert body["open_mode"] is True   # we set TANK_OFFLOAD_OPEN=1
    assert body["threshold_pct"] == 85.0
    assert body["recover_pct"] == 75.0


def test_version(client: TestClient):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["package"] == "tank_offload"


# -------------------- status --------------------

def test_status_returns_expected_shape(client: TestClient):
    r = client.get("/api/offload/status")
    assert r.status_code == 200
    body = r.json()
    for k in ("watch_path", "usage_pct", "threshold_pct",
              "recover_pct", "state", "manifest_counts",
              "total_uploaded_bytes"):
        assert k in body
    assert body["threshold_pct"] == 85.0


# -------------------- threshold --------------------

def test_threshold_get_default(client: TestClient):
    r = client.get("/api/offload/threshold")
    assert r.status_code == 200
    body = r.json()
    assert body == {"threshold_pct": 85.0, "recover_pct": 75.0}


def test_threshold_put_roundtrip(client: TestClient):
    r = client.put("/api/offload/threshold",
                   json={"threshold_pct": 90.0, "recover_pct": 80.0})
    assert r.status_code == 200
    assert r.json() == {"threshold_pct": 90.0, "recover_pct": 80.0}


def test_threshold_put_rejects_recover_greater_than_threshold(client: TestClient):
    r = client.put("/api/offload/threshold",
                   json={"threshold_pct": 80, "recover_pct": 90})
    assert r.status_code == 422


def test_threshold_put_rejects_out_of_range(client: TestClient):
    r = client.put("/api/offload/threshold", json={"threshold_pct": 120})
    assert r.status_code == 422
    r = client.put("/api/offload/threshold", json={"threshold_pct": 0.5})
    assert r.status_code == 422


# -------------------- history / manifest / deadletter --------------------

def test_history_empty(client: TestClient):
    r = client.get("/api/offload/history?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["uploads_count"] == 0
    assert body["deadletter_count"] == 0


def test_manifest_empty(client: TestClient):
    r = client.get("/api/offload/manifest?limit=10")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_deadletter_empty(client: TestClient):
    r = client.get("/api/offload/deadletter?limit=10")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_history_with_rows(client: TestClient):
    store = app_module.get_store()
    a = store.enqueue("/p/a", size_bytes=10, kind="recording")
    store.transition(a.uuid, to_status="uploaded", remote_path="by-uuid/a")
    r = client.get("/api/offload/history?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["uploads_count"] == 1
    assert body["uploads"][0]["uuid"] == a.uuid


# -------------------- trigger / dry-run / credentials --------------------

def test_trigger_sweep_returns_no_bridge_note(client: TestClient):
    r = client.post("/api/offload/trigger")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False          # no ROS bridge thread in CI
    assert "note" in body


def test_trigger_emergency_returns_no_bridge_note(client: TestClient):
    r = client.post("/api/offload/trigger_emergency")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "EMERGENCY"


def test_dry_run_returns_empty_in_test_layout_with_no_files(client: TestClient):
    r = client.get("/api/offload/dry_run")
    assert r.status_code == 200
    body = r.json()
    assert body["total_files"] == 0
    assert body["total_bytes"] == 0


def test_credentials_redacts_password_hash(client: TestClient):
    r = client.get("/api/offload/credentials")
    assert r.status_code == 200
    body = r.json()
    assert body["credentialed"] is True
    assert body["missing"] == []
    red = body["redacted"]
    # raw password never appears
    red_str = str(red)
    assert "pw" not in red_str
    # hash is exposed
    assert red["nextcloud_password_hash"].startswith("sha256:")


# -------------------- auth (locks the open flag down) --------------------

def test_auth_blocks_when_open_mode_off():
    """Verify auth rejects unknown keys when TANK_OFFLOAD_OPEN=0."""
    saved_open = app_module._OPEN_MODE
    saved_key = os.environ.get("TANK_API_KEY", "")
    os.environ["TANK_API_KEY"] = "secret-key-xyz"
    app_module._OPEN_MODE = False
    try:
        c = TestClient(app_module.app)
        # No bearer \u2192 401 (not 503 because a key IS configured).
        g = c.get("/api/offload/status")
        assert g.status_code == 401, g.text
        bad = c.get("/api/offload/status",
                     headers={"Authorization": "Bearer nope"})
        assert bad.status_code == 401, bad.text
        ok = c.get("/api/offload/status",
                    headers={"Authorization": "Bearer secret-key-xyz"})
        assert ok.status_code == 200, ok.text
    finally:
        app_module._OPEN_MODE = saved_open
        if saved_key:
            os.environ["TANK_API_KEY"] = saved_key
        else:
            os.environ.pop("TANK_API_KEY", None)
