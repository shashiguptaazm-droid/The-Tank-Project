"""FastAPI server for The Tank Project persona + preferences + memory.

Port ``8084`` (chosen to avoid collision with ``tank_dashboard:8080``,
``tank_command_bridge:8082``, ``serve_meta_api:8083``).

Routes
------

Health + introspection
* ``GET  /api/health``                              — liveness check
* ``GET  /api/version``                             — package version

Persona
* ``GET  /api/persona``                             — current persona (defaults if unset)
* ``PUT  /api/persona``                             — replace partial persona
* ``POST /api/persona/reset``                       — back to defaults

User memory
* ``GET  /api/persona/memory``                      — name + facts + moods
* ``PUT  /api/persona/memory``                      — bulk patch (name|add_fact|mood|remove_fact|clear_facts|clear_name|clear_all)
* ``POST /api/persona/memory/touch``                — bump last-seen ts

Preferences
* ``GET  /api/prefs``                               — all three sections
* ``PUT  /api/prefs/<section>``                     — patch a single section
* ``POST /api/prefs/<section>/reset``               — back to defaults
* ``POST /api/prefs/reset``                         — reset all sections

LLM-facing previews
* ``GET  /api/prompt``                              — composed system prompt (with optional ?extra=...)
* ``GET  /api/dialogue``                            — greeting + empathy + farewell one-liners for the persona
* ``POST /api/dialogue/accent``                     — return a single short line tagged by the requested style

Dashboard
* ``GET  /``                                         — bundled static UI

Auth
-----
Bearer-token auth (single shared key ``TANK_API_KEY``) — the same key
``tank_command_bridge`` accepts, read from the environment. To skip
auth (bench testing / Pi first-boot), export ``TANK_PERSONALIZE_OPEN=1``.

Notes
-----
* Uses ``lifespan=`` not ``@app.on_event`` (STATUS.md §9 design rule 5).
* SQLite stores are opened with ``check_same_thread=False`` and writes
  go through per-store ``threading.Lock`` instances.
* We never log a raw API key; only the ``token_hash`` is recorded.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

try:
    import rclpy                                            # noqa: F401
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from std_msgs.msg import String
    _RCLPY_AVAILABLE = True
except ImportError:                                          # pragma: no cover
    _RCLPY_AVAILABLE = False

    class _NoopPublisher:                                   # type: ignore[no-redef]
        def publish(self, *_a, **_k): return None

    class _NoopLogger:                                      # type: ignore[no-redef]
        def info(self, *_a, **_k): pass
        def warn(self, *_a, **_k): pass
        def error(self, *_a, **_k): pass
        def debug(self, *_a, **_k): pass

    class _StubNode:                                        # type: ignore[no-redef]
        def __init__(self, *_a, **_k): pass
        def create_subscription(self, *_a, **_k): return None
        def create_publisher(self, *_a, **_k): return _NoopPublisher()
        def create_timer(self, *_a, **_k): return None
        def get_logger(self): return _NoopLogger()

    Node = _StubNode                  # type: ignore[assignment]
    SingleThreadedExecutor = object  # type: ignore[assignment,misc]
    rclpy = type("rclpy", (), {"ok": staticmethod(lambda: False),
                                "init": staticmethod(lambda: None),
                                "shutdown": staticmethod(lambda: None)})()

    class _StubString:
        def __init__(self, data: str = "") -> None:
            self.data = data
    String = _StubString  # type: ignore[assignment]

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse

from .dialogue import (
    ContextSignals,
    VALID_FAREWELL_REASONS,
    acknowledge_fact,
    compose_acknowledgements,
    empathy_prefix,
    farewell,
    missing_name_ask,
)
from .memory import MemoryStore, UserMemory
from .persona import Persona
from .preferences import (
    ALLOWED_SECTIONS,
    AudioPrefs,
    MotionPrefs,
    PrefKeyError,
    PreferenceStore,
    PrivacyPrefs,
    SECTION_CLASSES,
)
from .prompts import build_system_prompt, greeting_line

# Always-on logging (STATUS.md design rule for ops dashboards).
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=__import__("sys").stderr,
)
_LOG = logging.getLogger("tank_personalize.app")

__version__ = "0.1.0"

DEFAULT_PORT = 8084
DEFAULT_DATA_DIR = os.environ.get(
    "TANK_PERSONALIZE_DATA",
    "/root/the tank project/tank_ws/data",
)
PREFS_DB = os.environ.get(
    "TANK_PERSONALIZE_PREFS_DB",
    os.path.join(DEFAULT_DATA_DIR, "personalize_prefs.db"),
)
MEMORY_DB = os.environ.get(
    "TANK_PERSONALIZE_MEMORY_DB",
    os.path.join(DEFAULT_DATA_DIR, "personalize_memory.db"),
)
PERSONA_DB = os.environ.get(
    "TANK_PERSONALIZE_PERSONA_DB",
    os.path.join(DEFAULT_DATA_DIR, "personalize_persona.db"),
)


# --------------------------------------------------------------------------- #
# Persona store (single-row)
# --------------------------------------------------------------------------- #

class PersonaStore:
    """Single-row store; keyed by id=1.

    Stored as a JSON blob to keep migrations cheap: new fields can be
    added to the dataclass and existing devices will load them with
    their pre-existing values intact.
    """

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._init_schema()
        # Seed row if absent.
        if not self.read().to_dict():
            self._write(Persona.defaults())

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0,
                               check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS persona ("
                    "id      INTEGER PRIMARY KEY CHECK(id = 1),"
                    "json    TEXT NOT NULL,"
                    "ts      REAL NOT NULL)")

    def _write(self, p: Persona) -> None:
        payload = json_dumps(p.to_dict())
        with self._lock, self._connect() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO persona(id, json, ts) "
                    "VALUES(1, ?, ?)",
                    (payload, time.time()))

    def read(self) -> Persona:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT json FROM persona WHERE id=1"
            ).fetchone()
        if not row or not row[0]:
            return Persona.defaults()
        try:
            data = json_loads(row[0])
        except Exception:
            return Persona.defaults()
        # Merge with defaults so newly-added dataclass fields appear.
        merged = dict(Persona.defaults().to_dict())
        if isinstance(data, dict):
            merged.update(data)
        return Persona.from_dict(merged)

    def patch(self, patch: Dict[str, Any]) -> Persona:
        cur = self.read()
        cur_dict = cur.to_dict()
        if not isinstance(patch, dict):
            raise PrefKeyError("persona patch must be a JSON object")
        # Tolerate unknown keys silently (forward-compat).
        for k, v in patch.items():
            if k in cur_dict and isinstance(cur_dict[k], list) \
                    and isinstance(v, list):
                cur_dict[k] = v
            else:
                cur_dict[k] = v
        new = Persona.from_dict(cur_dict)
        self._write(new)
        return new

    def reset(self) -> Persona:
        defaults = Persona.defaults()
        self._write(defaults)
        return defaults


def json_dumps(o: Any) -> str:
    import json as _json
    return _json.dumps(o, ensure_ascii=False, sort_keys=False)


def json_loads(s: str) -> Any:
    import json as _json
    return _json.loads(s)


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #

def _load_keys() -> Dict[str, str]:
    """Single shared key — falls back to the same one as
    ``tank_command_bridge`` so the user only has to mint one token."""
    fallback = os.environ.get("TANK_API_KEY", "")
    raw = os.environ.get("TANK_API_KEYS")
    if raw:
        try:
            data = json_loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    if fallback:
        return {fallback: "admin"}
    return {}


def _hash_token(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


_OPEN_MODE = bool(int(os.environ.get("TANK_PERSONALIZE_OPEN", "0")))


def authenticate(request: Request) -> str:
    """Validate ``Authorization: Bearer <token>`` and return a
    token-hash. Honors ``TANK_PERSONALIZE_OPEN=1`` for first-boot."""
    if _OPEN_MODE:
        return "open"
    keys = _load_keys()
    if not keys:
        # 503 so the user understands the server hasn't been keyed yet.
        raise HTTPException(
            status_code=503,
            detail="no TANK_API_KEY / TANK_API_KEYS configured on the server")
    header = request.headers.get("Authorization", "")
    if not header:
        raise HTTPException(
            status_code=401,
            detail="missing Authorization header")
    parts = header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="malformed Authorization header "
                   "(expected 'Bearer <token>')")
    token = parts[1].strip()
    for k in keys.keys():
        if secrets.compare_digest(k, token):
            return _hash_token(token)
    raise HTTPException(status_code=401, detail="invalid API key")


def _require_write(request: Request, header: Optional[str]) -> str:
    """Per-method split: this server treats all writes the same.

    Splitting read vs write here lets callers add per-method quotas
    later without changing the topology."""
    return authenticate(request)


# --------------------------------------------------------------------------- #
# ROS bridge (very thin: just publishes persona changes to /assistant/persona)
# --------------------------------------------------------------------------- #

class _PersonaBridge(Node):
    """Mirror persona changes onto a ROS topic so other nodes
    (``tank_assistant/llm_node.py``) can react.

    Publishes ``/assistant/persona`` (compact JSON, ≤ 600 chars)
    and ``/assistant/memory_summary`` (≤ 400 chars) when either
    is updated so the LLM has a fresh system-prompt seed.
    """

    def __init__(self, persona_getter,
                 memory_getter,
                 prefs_getter) -> None:
        super().__init__("persona_bridge")
        self._persona_pub = self.create_publisher(String,
                                                  "/assistant/persona", 10)
        self._memory_pub = self.create_publisher(String,
                                                 "/assistant/memory_summary",
                                                 10)
        self._prefs_pub = self.create_publisher(String,
                                                "/assistant/prefs_summary",
                                                10)
        # Capture the *getters* (not the singletons) so a hot-rebind
        # via `_reset_stores_for_tests()` doesn't leave the bridge
        # publishing stale state.
        self._persona_getter = persona_getter
        self._memory_getter = memory_getter
        self._prefs_getter = prefs_getter
        self.get_logger().info("persona_bridge initialised")

    def push_persona(self) -> None:
        p = self._persona_getter().read()
        summary = {
            "name": p.name,
            "tone": p.tone,
            "response_style": p.response_style,
            "emoji_use": p.emoji_use,
        }
        self._persona_pub.publish(
            String(data=json_dumps(summary)[:600]))

    def push_memory(self) -> None:
        m = self._memory_getter().read()
        summary = {
            "name": m.remembered_name,
            "fact_count": len(m.custom_facts),
            "moods": m.moods_seen,
        }
        self._memory_pub.publish(
            String(data=json_dumps(summary)[:400]))

    def push_prefs(self) -> None:
        # Slim summary — only the slice the LLM prompt actually reads.
        # Full sections stay accessible via the HTTP API.
        try:
            all_prefs = self._prefs_getter().get_all()
        except Exception:                                  # pragma: no cover
            return
        slim = {
            "motion": {
                "max_speed_mps":  all_prefs.get("motion", {}).get("max_speed_mps"),
                "follow_distance_m": all_prefs.get("motion", {}).get("follow_distance_m"),
                "patrol_mode":   all_prefs.get("motion", {}).get("patrol_mode"),
            },
            "privacy": {
                "telemetry_to_ai": all_prefs.get("privacy", {}).get("telemetry_to_ai"),
                "remember_conversations": all_prefs.get("privacy", {}).get("remember_conversations"),
            },
            "audio": {
                "wake_sensitivity":  all_prefs.get("audio",  {}).get("wake_sensitivity"),
                "tts_voice":         all_prefs.get("audio",  {}).get("tts_voice"),
            },
        }
        self._prefs_pub.publish(String(data=json_dumps(slim)[:600]))


_bridge: Optional[_PersonaBridge] = None
_bridge_lock = threading.Lock()


def _ros_spin_thread() -> None:
    global _bridge
    try:
        if not rclpy.ok():
            rclpy.init()
        with _bridge_lock:
            _bridge = _PersonaBridge(get_persona_store,
                                     get_memory_store,
                                     get_pref_store)
            executor = SingleThreadedExecutor()
            executor.add_node(_bridge)
            executor.spin()
    except Exception as exc:
        _LOG.warning("ROS bridge thread failed to start: %s", exc)
        if _bridge is not None:
            try:
                _bridge.destroy_node()
            except Exception:
                pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except Exception:
                pass


def _notify_bridge(topic: str) -> None:
    """Used in handlers to push fresh state over ROS. Never raises."""
    if _bridge is None:
        return
    try:
        if topic == "persona":
            _bridge.push_persona()
        elif topic == "memory":
            _bridge.push_memory()
        elif topic == "prefs":
            _bridge.push_prefs()
    except Exception as exc:                                # pragma: no cover
        _LOG.debug("notify_bridge(%s) failed: %s", topic, exc)


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Real data stores are constructed lazily at module load so
    # importing the package works without env vars — see below.
    if _RCLPY_AVAILABLE and os.environ.get("TANK_PERSONALIZE_NO_ROS",
                                            "0") != "1":
        t = threading.Thread(target=_ros_spin_thread, daemon=True,
                              name="tank_persona_ros")
        t.start()
    try:
        yield
    finally:
        # Nothing to clean up: singleton-per-process, FastAPI workers
        # die when uvicorn dies.
        pass


app = FastAPI(
    title="The Tank Persona API",
    version=__version__,
    lifespan=lifespan,
    description=(
        "Persona + preferences + user-memory + system-prompt preview "
        "for The Tank's onboard AI."
    ),
)

# Lazy singletons — keys are real paths in production, but tests can
# monkey-patch BEFORE any request hits (see test_app.py).
_persona_store: Optional[PersonaStore] = None
_memory_store: Optional[MemoryStore] = None
_pref_store: Optional[PreferenceStore] = None
_stores_lock = threading.Lock()


def get_persona_store() -> PersonaStore:
    global _persona_store
    if _persona_store is None:
        with _stores_lock:
            if _persona_store is None:
                _persona_store = PersonaStore(PERSONA_DB)
    return _persona_store


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        with _stores_lock:
            if _memory_store is None:
                _memory_store = MemoryStore(MEMORY_DB)
    return _memory_store


def get_pref_store() -> PreferenceStore:
    global _pref_store
    if _pref_store is None:
        with _stores_lock:
            if _pref_store is None:
                _pref_store = PreferenceStore(PREFS_DB)
    return _pref_store


def _reset_stores_for_tests(p: PersonaStore,
                            m: MemoryStore,
                            pf: PreferenceStore) -> None:
    """Test-only: re-bind the module-level singletons."""
    global _persona_store, _memory_store, _pref_store
    with _stores_lock:
        _persona_store = p
        _memory_store = m
        _pref_store = pf


# --------------------------------------------------------------------------- #
# Routes — health
# --------------------------------------------------------------------------- #

@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "rclpy": _RCLPY_AVAILABLE,
        "open_mode": _OPEN_MODE,
    }


@app.get("/api/version")
def version() -> Dict[str, Any]:
    return {"version": __version__, "package": "tank_personalize"}


# --------------------------------------------------------------------------- #
# Routes — persona
# --------------------------------------------------------------------------- #

@app.get("/api/persona")
def get_persona(request: Request) -> Dict[str, Any]:
    authenticate(request)
    p = get_persona_store().read()
    warnings = p.validate()
    return {
        "persona": p.to_dict(),
        "warnings": warnings,
    }


@app.put("/api/persona")
def put_persona(payload: Dict[str, Any],
                 request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be object")
    # Allow partial updates: merge into current + persist.
    store = get_persona_store()
    cur = store.read().to_dict()
    allowed = set(Persona.defaults().to_dict().keys())
    cur.update({k: v for k, v in payload.items() if k in allowed})
    updated = Persona.from_dict(cur)
    store._write(updated)
    _notify_bridge("persona")
    warnings = updated.validate()
    return {
        "persona": updated.to_dict(),
        "warnings": warnings,
    }


@app.post("/api/persona/reset")
def reset_persona(request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    defaults = get_persona_store().reset()
    _notify_bridge("persona")
    return {"persona": defaults.to_dict()}


# --------------------------------------------------------------------------- #
# Routes — user memory
# --------------------------------------------------------------------------- #

@app.get("/api/persona/memory")
def get_memory(request: Request) -> Dict[str, Any]:
    authenticate(request)
    return get_memory_store().read().to_dict()


@app.put("/api/persona/memory")
def put_memory(payload: Dict[str, Any],
                request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be object")
    store = get_memory_store()
    out = store
    if "name" in payload:
        if payload["name"] is None:
            out = store.clear_name()
        else:
            name = str(payload["name"]).strip()
            out = store.set_name(name)
    if "add_fact" in payload:
        out = store.add_fact(str(payload["add_fact"]))
    if "remove_fact" in payload:
        out = store.remove_fact(str(payload["remove_fact"]))
    if payload.get("clear_facts"):
        out = store.clear_facts()
    if payload.get("clear_all"):
        out = store.clear_all()
    if "mood" in payload:
        out = store.bump_mood(str(payload["mood"]))
    _notify_bridge("memory")
    return out.read().to_dict()


@app.post("/api/persona/memory/touch")
def touch_memory(request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    out = get_memory_store().touch()
    _notify_bridge("memory")
    return out.to_dict()


# --------------------------------------------------------------------------- #
# Routes — preferences
# --------------------------------------------------------------------------- #

@app.get("/api/prefs")
def get_all_prefs(request: Request) -> Dict[str, Any]:
    authenticate(request)
    return get_pref_store().get_all()


@app.put("/api/prefs/{section}")
def put_pref_section(section: str, payload: Dict[str, Any],
                      request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown section {section!r}; "
                    f"expected one of {ALLOWED_SECTIONS}")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be object")
    try:
        result = get_pref_store().patch_section(section, payload)
    except PrefKeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    _notify_bridge("prefs")
    return {"section": section, "values": result}


@app.post("/api/prefs/{section}/reset")
def reset_pref_section(section: str, request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown section {section!r}; "
                    f"expected one of {ALLOWED_SECTIONS}")
    result = get_pref_store().reset_section(section)
    _notify_bridge("prefs")
    return {"section": section, "values": result}


@app.post("/api/prefs/reset")
def reset_all_prefs(request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    out = get_pref_store().reset_all()
    _notify_bridge("prefs")
    return out


@app.get("/api/prefs/{section}/diff")
def diff_prefs(section: str, request: Request) -> Dict[str, Any]:
    authenticate(request)
    if section not in ALLOWED_SECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown section {section!r}")
    return {"section": section,
            "diff": get_pref_store().diff_from_defaults(section)}


# --------------------------------------------------------------------------- #
# Routes — LLM-facing previews
# --------------------------------------------------------------------------- #

@app.get("/api/prompt")
def preview_prompt(request: Request,
                    extra: Optional[str] = None) -> Dict[str, Any]:
    authenticate(request)
    prompt = build_system_prompt(
        get_persona_store().read(),
        get_memory_store().read(),
        extra_notes=extra or "",
    )
    return {
        "prompt": prompt,
        "length": len(prompt),
        "cap": 4000,
    }


@app.get("/api/dialogue")
def preview_dialogue(request: Request,
                      reason: str = "idle") -> Dict[str, Any]:
    authenticate(request)
    persona = get_persona_store().read()
    memory = get_memory_store().read()
    if reason not in VALID_FAREWELL_REASONS:
        reason = "idle"
    return {
        "persona_name": persona.name,
        "greeting": greeting_line(persona, memory),
        "farewell": farewell(persona, reason=reason),
        "missing_name_ask": missing_name_ask(persona),
        "acknowledgements": compose_acknowledgements(persona, memory),
        "empathy_prefix": empathy_prefix(ContextSignals(), persona),
    }


@app.post("/api/dialogue/accent")
def accent_line(payload: Dict[str, Any],
                 request: Request) -> Dict[str, Any]:
    _require_write(request, request.headers.get("Authorization"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be object")
    persona = get_persona_store().read()
    style = str(payload.get("style", "empathy")).lower()
    ctx_in = payload.get("context") or {}
    if not isinstance(ctx_in, dict):
        ctx_in = {}
    ctx = ContextSignals(
        has_error=bool(ctx_in.get("has_error")),
        is_short_input=bool(ctx_in.get("is_short_input")),
        seconds_since_user_input=float(ctx_in.get("seconds_since_user_input", 0)),
        battery_low=bool(ctx_in.get("battery_low")),
        just_woke=bool(ctx_in.get("just_woke")),
        just_estop=bool(ctx_in.get("just_estop")),
        user_input=str(ctx_in.get("user_input", "")),
    )
    if style == "empathy":
        line = empathy_prefix(ctx, persona)
    elif style == "acknowledge":
        line = acknowledge_fact(persona,
                                fact=str(payload.get("fact", "")))
    elif style == "farewell":
        line = farewell(persona,
                        reason=str(payload.get("reason", "idle")))
    elif style == "missing_name":
        line = missing_name_ask(persona)
    elif style == "greeting":
        line = greeting_line(persona,
                              get_memory_store().read())
    else:
        raise HTTPException(status_code=422,
                            detail=f"unknown style {style!r}")
    return {"style": style, "line": line}


# --------------------------------------------------------------------------- #
# Routes — root + static UI
# --------------------------------------------------------------------------- #

STATIC_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "static"))


@app.get("/")
def root() -> Any:
    index_html = os.path.join(STATIC_DIR, "index.html")
    if not os.path.isfile(index_html):
        return PlainTextResponse(
            "tank_personalize UI not built; "
            "expect /root/.../tank_personalize/static/index.html",
            status_code=503,
        )
    return FileResponse(index_html, media_type="text/html")


@app.get("/static/app.js")
def static_app_js() -> Any:
    path = os.path.join(STATIC_DIR, "app.js")
    if not os.path.isfile(path):
        return PlainTextResponse("// app.js missing", status_code=404,
                                  media_type="application/javascript")
    return FileResponse(path, media_type="application/javascript")


@app.get("/static/style.css")
def static_style_css() -> Any:
    path = os.path.join(STATIC_DIR, "style.css")
    if not os.path.isfile(path):
        return PlainTextResponse("/* style.css missing */",
                                  status_code=404,
                                  media_type="text/css")
    return FileResponse(path, media_type="text/css")


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    """Console-script shim for ``personalize`` / ``run_personalize``.

    Use ``python -m tank_personalize.scripts.run_personalize`` instead
    if you've installed colcon-style.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the tank_personalize FastAPI server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-ros", action="store_true",
                        help="Skip ROS bridge thread (bench testing)")
    parser.add_argument("--open", action="store_true",
                        help="Bypass bearer auth — bench-only flag.")
    args = parser.parse_args()

    if args.no_ros:
        os.environ["TANK_PERSONALIZE_NO_ROS"] = "1"
    if args.open:
        os.environ["TANK_PERSONALIZE_OPEN"] = "1"

    try:
        import uvicorn                                  # type: ignore[import-not-found]
    except ImportError:
        print("uvicorn not installed; pip install 'tank_personalize[server]'",
              flush=True)
        return 2

    uvicorn.run("tank_personalize.app:app",
                host=args.host, port=args.port,
                log_level="info")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
