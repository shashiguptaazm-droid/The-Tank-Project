"""End-to-end FastAPI tests for tank_personalize.app (port 8084).

We patch the lazy singletons with tmp-file-backed stores and exercise
the routes via ``fastapi.testclient.TestClient``. Auth defaults to
``503`` (because no ``TANK_API_KEY`` is exported) unless we set the
``open-mode`` flag — we use the open mode to keep these tests
self-contained and fast.

Note on lifespan: the tests disable the ROS thread entirely via
``TANK_PERSONALIZE_NO_ROS=1`` so we don't pull in rclpy.

TestClient itself depends on ``httpx``; the entire module is skipped
via ``pytest.importorskip`` if httpx isn't installed in the dev
sandbox (Jetson production has it via ``scripts/legacy-installer.sh``).
"""
from __future__ import annotations

import os
import tempfile

# httpx is the TestClient transport. Skip the whole module when it is
# absent — pure-data tests in test_persona / test_preferences / test_memory /
# test_prompts / test_dialogue still run.
import pytest

pytest.importorskip("httpx")

# Set BOTH env vars BEFORE importing the app so module-level constants
# pick up the values, and rclpy is gated off in CI.
os.environ.setdefault("TANK_PERSONALIZE_NO_ROS", "1")

_tmpdir = tempfile.mkdtemp(prefix="tank_personalize_test_")
os.environ["TANK_PERSONALIZE_DATA"] = _tmpdir
os.environ["TANK_PERSONALIZE_PREFS_DB"] = os.path.join(_tmpdir, "prefs.db")
os.environ["TANK_PERSONALIZE_MEMORY_DB"] = os.path.join(_tmpdir, "memory.db")
os.environ["TANK_PERSONALIZE_PERSONA_DB"] = os.path.join(_tmpdir, "persona.db")
os.environ["TANK_PERSONALIZE_OPEN"] = "1"

from fastapi.testclient import TestClient

# Import AFTER env is set up so the module-level constants lock in.
from tank_personalize import app as app_module
from tank_personalize.app import PersonaStore          # lives in app.py
from tank_personalize.memory import MemoryStore
from tank_personalize.preferences import PreferenceStore


@pytest.fixture
def client() -> TestClient:
    # Re-bind the singletons to fresh tmp-backed stores per test so
    # we don't leak state across tests.
    ps = PersonaStore(os.environ["TANK_PERSONALIZE_PERSONA_DB"])
    ms = MemoryStore(os.environ["TANK_PERSONALIZE_MEMORY_DB"])
    pf = PreferenceStore(os.environ["TANK_PERSONALIZE_PREFS_DB"])
    app_module._reset_stores_for_tests(ps, ms, pf)
    return TestClient(app_module.app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "version" in body
    assert body["open_mode"] is True


def test_get_persona_returns_defaults(client: TestClient):
    r = client.get("/api/persona")
    assert r.status_code == 200
    body = r.json()
    assert "persona" in body and body["persona"]["name"] == "Tank"
    assert isinstance(body["warnings"], list)


def test_put_persona_roundtrip(client: TestClient):
    r = client.put("/api/persona",
                   json={"name": "Sparky", "tone": "quirky",
                         "voice_rate": 1.2})
    assert r.status_code == 200
    body = r.json()
    assert body["persona"]["name"] == "Sparky"
    assert body["persona"]["tone"] == "quirky"
    # Follow-up GET reflects change.
    g = client.get("/api/persona").json()
    assert g["persona"]["voice_rate"] == 1.2


def test_reset_persona(client: TestClient):
    client.put("/api/persona", {"name": "Sparky"})
    r = client.post("/api/persona/reset")
    assert r.status_code == 200
    assert r.json()["persona"]["name"] == "Tank"


def test_get_prefs_returns_three_sections(client: TestClient):
    r = client.get("/api/prefs")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"motion", "privacy", "audio"}


def test_put_pref_section(client: TestClient):
    r = client.put("/api/prefs/motion",
                   json={"max_speed_mps": 0.6, "patrol_mode": "waypoint"})
    assert r.status_code == 200
    body = r.json()
    assert body["section"] == "motion"
    assert body["values"]["max_speed_mps"] == 0.6
    assert body["values"]["patrol_mode"] == "waypoint"


def test_put_pref_unknown_section(client: TestClient):
    r = client.put("/api/prefs/bogus", json={})
    assert r.status_code == 404


def test_put_pref_unknown_key(client: TestClient):
    r = client.put("/api/prefs/motion", json={"turbo_boost": True})
    assert r.status_code == 422


def test_reset_pref_section(client: TestClient):
    client.put("/api/prefs/audio", {"wake_sensitivity": 0.91})
    r = client.post("/api/prefs/audio/reset")
    assert r.status_code == 200
    assert r.json()["values"]["wake_sensitivity"] == 0.55


def test_diff_pref(client: TestClient):
    client.put("/api/prefs/audio", {"wake_sensitivity": 0.91})
    r = client.get("/api/prefs/audio/diff")
    assert r.status_code == 200
    body = r.json()
    assert "wake_sensitivity" in body["diff"]


def test_get_memory_default(client: TestClient):
    r = client.get("/api/persona/memory")
    assert r.status_code == 200
    body = r.json()
    assert body["remembered_name"] is None
    assert body["custom_facts"] == []


def test_put_memory_set_name(client: TestClient):
    r = client.put("/api/persona/memory", {"name": "Aisha"})
    assert r.status_code == 200
    body = r.json()
    assert body["remembered_name"] == "Aisha"


def test_put_memory_add_fact(client: TestClient):
    r = client.put("/api/persona/memory",
                   {"add_fact": "loves dark mode"})
    assert r.status_code == 200
    assert "loves dark mode" in r.json()["custom_facts"]


def test_put_memory_clear_all(client: TestClient):
    client.put("/api/persona/memory", {"name": "Sam"})
    client.put("/api/persona/memory", {"add_fact": "tea"})
    client.put("/api/persona/memory", {"mood": "calm"})
    r = client.put("/api/persona/memory", {"clear_all": True})
    body = r.json()
    assert body["remembered_name"] is None
    assert body["custom_facts"] == []
    assert body["moods_seen"] == {}


def test_touch_memory(client: TestClient):
    r = client.post("/api/persona/memory/touch")
    assert r.status_code == 200
    assert r.json()["last_seen_ts"] > 0


def test_get_prompt_contains_persona_name(client: TestClient):
    client.put("/api/persona", {"name": "Sparky"})
    r = client.get("/api/prompt")
    assert r.status_code == 200
    prompt = r.json()["prompt"]
    assert "Sparky" in prompt
    assert r.json()["length"] <= r.json()["cap"]


def test_prompt_truncates_long_extra_notes(client: TestClient):
    long = "z" * 7000
    r = client.get("/api/prompt", params={"extra": long})
    prompt = r.json()["prompt"]
    assert len(prompt) <= r.json()["cap"]


def test_get_dialogue(client: TestClient):
    r = client.get("/api/dialogue?reason=wake")
    assert r.status_code == 200
    body = r.json()
    assert body["persona_name"] == "Tank"
    assert body["greeting"] and body["farewell"]
    assert isinstance(body["acknowledgements"], list)


def test_accent_line(client: TestClient):
    r = client.post("/api/dialogue/accent",
                     json={"style": "acknowledge",
                           "fact": "loves the rain"})
    assert r.status_code == 200
    assert "loves the rain" in r.json()["line"]


def test_accent_line_unknown_style(client: TestClient):
    r = client.post("/api/dialogue/accent", json={"style": "bogus"})
    assert r.status_code == 422


def test_get_version(client: TestClient):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["package"] == "tank_personalize"


def test_root_serves_static_when_present(client: TestClient):
    # Static UI may or may not exist in CI; we expect either a 200
    # HTML response OR a 503 with a helpful message.
    r = client.get("/")
    assert r.status_code in (200, 503)


def test_static_files_endpoint(client: TestClient):
    """/static/app.js and /static/style.css may 404 if not built; that's
    acceptable, but the route must exist and not 500."""
    for path in ("/static/app.js", "/static/style.css"):
        r = client.get(path)
        assert r.status_code in (200, 404)


def test_auth_blocks_when_open_mode_off():
    """Verify auth rejects unknown keys when TANK_PERSONALIZE_OPEN=0."""
    saved_open = app_module._OPEN_MODE
    saved_key = os.environ.get("TANK_API_KEY", "")
    os.environ["TANK_API_KEY"] = "secret-key-xyz"
    app_module._OPEN_MODE = False
    try:
        c = TestClient(app_module.app)
        # No bearer \u2192 401 (not 503 because a key IS configured).
        g = c.get("/api/persona")
        assert g.status_code == 401, g.text
        bad = c.get("/api/persona",
                     headers={"Authorization": "Bearer nope"})
        assert bad.status_code == 401, bad.text
        ok = c.get("/api/persona",
                    headers={"Authorization": "Bearer secret-key-xyz"})
        assert ok.status_code == 200, ok.text
    finally:
        app_module._OPEN_MODE = saved_open
        if saved_key:
            os.environ["TANK_API_KEY"] = saved_key
        else:
            os.environ.pop("TANK_API_KEY", None)
