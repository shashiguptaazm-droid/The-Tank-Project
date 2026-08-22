"""FastAPI dashboard backend for The Tank Project.

Exposes:
  * GET  /api/health                  — liveness
  * GET  /api/telemetry               — latest /health/prometheus text
  * GET  /api/telemetry/state         — latest /health/state string
  * GET  /api/recording/list          — list /var/tank/recordings/
  * GET  /api/emotion/current         — most recent /emotion/state
  * GET  /api/emotion/history         — deque of recent moods (≤50)
  * GET  /api/torrent/results         — most recent voice.torrent_search rows
  * POST /api/torrent/pick            — confirm + dispatch voice.aria2_add
  * POST /api/torrent/cancel          — cancel an active torrent by GID
  * GET  /                              — static dashboard UI (face + log)
  * WS   /ws/feed                     — stream of /health/state events
  * WS   /ws/emotion                  — stream of /emotion/state events
  * POST /api/cmd/estop               — publish Bool(True) on /estop_external
  * POST /api/cmd/move                — publish Twist on /cmd_vel

Note on lifespan: we use the FastAPI ``lifespan`` context manager
(per STATUS.md design rule 5) to start/stop the ROS bridge thread.

Run uvicorn directly with::

    uvicorn tank_dashboard.app:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import asyncio
import collections
import glob
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

try:
    import rclpy                                       # noqa: F401
    from geometry_msgs.msg import Twist
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from std_msgs.msg import Bool, String
    _RCLPY_AVAILABLE = True
except ImportError:
    # ImportError in CI benches — stubs so the FastAPI app can still
    # import and the pure-Python state object can be tested.
    _RCLPY_AVAILABLE = False

    class _NoopPublisher:                       # type: ignore[no-redef]
        def publish(self, *_a, **_k): return None

    class _NoopLogger:                          # type: ignore[no-redef]
        def info(self, *_a, **_k): pass
        def warn(self, *_a, **_k): pass
        def error(self, *_a, **_k): pass
        def debug(self, *_a, **_k): pass

    class _StubNode:                            # type: ignore[no-redef]
        def __init__(self, *_a, **_k): pass
        def create_subscription(self, *_a, **_k): return None
        def create_publisher(self, *_a, **_k): return _NoopPublisher()
        def create_timer(self, *_a, **_k): return None
        def get_logger(self): return _NoopLogger()

    Node = _StubNode               # type: ignore[assignment]
    Twist = type("Twist", (), {})  # type: ignore[assignment,misc]

    class _StubBool:
        def __init__(self, data: bool = False) -> None:
            self.data = data
    class _StubString:
        def __init__(self, data: str = "") -> None:
            self.data = data
    Bool = _StubBool    # type: ignore[assignment]
    String = _StubString  # type: ignore[assignment]
    SingleThreadedExecutor = object  # type: ignore[assignment,misc]
    rclpy = type("rclpy", (), {"ok": staticmethod(lambda: False),
                                "init": staticmethod(lambda: None),
                                "shutdown": staticmethod(lambda: None)})()

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel  # noqa: F401  — used implicitly by FastAPI


# ──── wire the in-process torrent display stores ────────────────────────────
# The torrent display plugins live in tank_command_bridge. We add the
# colcon workspace's ``src/`` dir to sys.path so the dashboard can read
# the SAME module-level singletons (RECENT_RESULTS, ACTIVE_DOWNLOADS)
# without round-tripping through a ROS topic. ROS Python packages use
# the ``<pkg>/<pkg>/`` layout (package directory containing an inner
# Python module of the same name), so adding ``src/`` to sys.path then
# importing ``tank_command_bridge.plugins._torrent_display`` resolves
# to the inner package directly. This is safe in the dashboard's own
# process and in CI benches where rclpy is missing.
# Layout: .../tank_ws/src/tank_dashboard/tank_dashboard/app.py
#         ^^^^^^^  parents[2]  →  tank_ws/src/  ← what we want on sys.path
_TCB_SRC_PARENT = Path(__file__).resolve().parents[2]
if str(_TCB_SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(_TCB_SRC_PARENT))
try:
    from tank_command_bridge.plugins._torrent_display import (
        ACTIVE_DOWNLOADS as _TORRENT_ACTIVE,
        RECENT_RESULTS as _TORRENT_RECENT,
    )
    _TORRENT_AVAILABLE = True
except Exception as exc:                                              # noqa: BLE001
    _TORRENT_AVAILABLE = False
    _TORRENT_RECENT = None  # type: ignore[assignment]
    _TORRENT_ACTIVE = None  # type: ignore[assignment]
    _torrent_import_error = str(exc)
else:
    _torrent_import_error = ""


# ──── wire the in-process tank_learn feedback store ─────────────────────────
# tank_learn ships an SQLite-WAL FeedbackStore that's used by the ROS
# feedback_node AND the dashboard's POST /api/feedback. The dashboard
# instantiates its own :class:`FeedbackStore` (same DB file as the ROS
# node, WAL gives us concurrent readers + one writer). Failures here
# are non-fatal: the dashboard keeps running, just with the
# ``/api/feedback`` family of routes returning 503.
try:
    from tank_learn.feedback_store import (
        FeedbackStore as _FeedbackStoreClass,
    )
    _FEEDBACK_STORE_SINGLETON = _FeedbackStoreClass()
    _FEEDBACK_AVAILABLE = True
except Exception as exc:                                              # noqa: BLE001
    _FEEDBACK_AVAILABLE = False
    _FEEDBACK_STORE_SINGLETON = None  # type: ignore[assignment]
    _feedback_import_error = str(exc)
else:
    _feedback_import_error = ""


# ──── wire the in-process tank_learn phase-3 memory store ────────────────────
# Phase 3 long-term memory (episodic + semantic + procedural + sleep-time
# consolidation). Mirrors the feedback-store failover pattern: failures are
# non-fatal; the four /api/learn/memory/* routes return 503 if the import
# errors. Two distinct MemoryStore instances on the same DB file (one per
# store class) are safe via WAL + busy_timeout.
try:
    from tank_learn.memory_store import (
        MemoryStore as _MemoryStoreClass,
    )
    _MEMORY_STORE_SINGLETON = _MemoryStoreClass()
    _MEMORY_AVAILABLE = True
except Exception as exc:                                              # noqa: BLE001
    _MEMORY_AVAILABLE = False
    _MEMORY_STORE_SINGLETON = None  # type: ignore[assignment]
    _memory_import_error = str(exc)
else:
    _memory_import_error = ""


EMOTION_HISTORY_MAX = 50
DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), os.pardir,
                             "dashboard")


# --------------------------------------------------------------------------- #
# Module-level bridge state — single source of truth for dashboard reads.
# --------------------------------------------------------------------------- #
class _BridgeState:
    def __init__(self) -> None:
        self.prom_text: str = ""
        self.health_state: str = ""
        self.emotion_current: str = "neutral"
        self.emotion_history: Deque[dict] = collections.deque(
            maxlen=EMOTION_HISTORY_MAX
        )
        self.emotion_last_update: float = 0.0


_state = _BridgeState()
_state_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# ROS 2 bridge node
# --------------------------------------------------------------------------- #
class _BridgeNode(Node):
    """A small ROS2 node that bridges topics to in-process state."""

    def __init__(self) -> None:
        super().__init__("dashboard_bridge")

        self.create_subscription(String, "/health/prometheus",
                                  self._on_prom, 10)
        self.create_subscription(String, "/health/state",
                                  self._on_health, 10)
        self.create_subscription(String, "/emotion/state",
                                  self._on_emotion, 10)
        self._estop_pub = self.create_publisher(Bool, "/estop_external", 10)
        self._move_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_clients: List[WebSocket] = []
        self._ws_lock = threading.Lock()
        self.get_logger().info("dashboard_bridge node initialised")

    def attach_ws(self, ws: WebSocket) -> None:
        with self._ws_lock:
            self._ws_clients.append(ws)

    def detach_ws(self, ws: WebSocket) -> None:
        with self._ws_lock:
            try:
                self._ws_clients.remove(ws)
            except ValueError:
                pass

    def _broadcast_emotion(self, mood: str, ts: float) -> None:
        if not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._fan_out_emotion(mood, ts), self._loop)
        except Exception:
            pass

    async def _fan_out_emotion(self, mood: str, ts: float) -> None:
        msg = json_dumps({"mood": mood, "ts": ts})
        with self._ws_lock:
            snapshot = list(self._ws_clients)
        dead: List[WebSocket] = []
        for ws in snapshot:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        if dead:
            with self._ws_lock:
                for ws in dead:
                    try:
                        self._ws_clients.remove(ws)
                    except ValueError:
                        pass

    def _on_prom(self, msg: String) -> None:
        with _state_lock:
            _state.prom_text = msg.data or ""

    def _on_health(self, msg: String) -> None:
        with _state_lock:
            _state.health_state = msg.data or ""

    def _on_emotion(self, msg: String) -> None:
        mood = (msg.data or "neutral").strip().lower() or "neutral"
        ts = time.time()
        with _state_lock:
            _state.emotion_current = mood
            _state.emotion_history.append({"mood": mood, "ts": ts})
            _state.emotion_last_update = ts
        self._broadcast_emotion(mood, ts)

    def publish_estop(self, latch: bool = True) -> None:
        self._estop_pub.publish(Bool(data=latch))

    def publish_move(self, vx: float = 0.0, wz: float = 0.0) -> None:
        t = Twist()
        t.linear.x = vx
        t.angular.z = wz
        self._move_pub.publish(t)


def json_dumps(obj: dict) -> str:
    import json
    return json.dumps(obj)


# --------------------------------------------------------------------------- #
# FastAPI app + lifespan
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_ros_spin_thread, daemon=True)
    t.start()
    for _ in range(50):
        if _bridge is not None:
            try:
                _bridge._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            break
        await asyncio.sleep(0.05)
    try:
        yield
    finally:
        pass


app = FastAPI(title="The Tank Project Dashboard",
              version="0.3.0", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# HTTP routes
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health_check() -> dict:
    return {"ok": True,
            "torrent_store": _TORRENT_AVAILABLE,
            "torrent_store_error": _torrent_import_error}


@app.get("/api/telemetry")
def telemetry() -> PlainTextResponse:
    with _state_lock:
        return PlainTextResponse(_state.prom_text or "")


@app.get("/api/telemetry/state")
def telemetry_state() -> PlainTextResponse:
    with _state_lock:
        return PlainTextResponse(_state.health_state or "")


@app.get("/api/recording/list")
def recording_list() -> List[str]:
    base = os.environ.get("TANK_RECORDINGS", "/var/tank/recordings")
    if not os.path.isdir(base):
        return []
    return sorted(os.path.basename(p)
                  for p in glob.glob(os.path.join(base, "*.avi")))


@app.get("/api/emotion/current")
def emotion_current() -> dict:
    with _state_lock:
        return {"mood": _state.emotion_current,
                "ts": _state.emotion_last_update}


@app.get("/api/emotion/history")
def emotion_history() -> dict:
    with _state_lock:
        items = list(_state.emotion_history)
    return {"count": len(items), "items": items}


# ──── torrent display routes ────────────────────────────────────────────────
@app.get("/api/torrent/results")
def torrent_results() -> dict:
    """Return the most recent torrent search results for the UI."""
    if _TORRENT_RECENT is None:
        return {"available": False,
                "error": _torrent_import_error or "torrent store not loaded",
                "items": [], "query": "", "age_s": 0.0}
    items = _TORRENT_RECENT.list()
    return {"available": True,
            "items": items,
            "query": _TORRENT_RECENT.last_query(),
            "age_s": round(_TORRENT_RECENT.age_s(), 2),
            "count": len(items)}


@app.post("/api/torrent/pick")
def torrent_pick(ordinal: int = 1, auto_confirm: bool = True) -> dict:
    """Stage + queue aria2.add for the N-th recent result."""
    if _TORRENT_RECENT is None:
        return {"_ok": False, "error": "torrent store not loaded"}
    items = _TORRENT_RECENT.list()
    if not items:
        return {"_ok": False, "ordinal": ordinal,
                "tts_text": "No recent torrent results to pick."}
    idx = max(0, min(ordinal - 1, len(items) - 1))
    row = items[idx]
    if not auto_confirm:
        return {"_ok": True, "staged": True, "picked": row,
                "ordinal": idx + 1,
                "tts_text": "Staged. Open the dashboard to confirm."}
    return {"_ok": True, "staged": True, "picked": row,
            "ordinal": idx + 1,
            "auto_dispatch": "voice.aria2_add",     # operator may dispatch
            "tts_text": f"Staged {row.get('title','result')}. "
                       "Calling aria2.add."}


@app.post("/api/torrent/cancel")
def torrent_cancel(gid: str = "") -> dict:
    if _TORRENT_ACTIVE is None:
        return {"_ok": False, "error": "torrent store not loaded"}
    if not gid or not _TORRENT_ACTIVE.contains(gid):
        return {"_ok": False, "cancelled": False,
                "tts_text": "No matching GID to cancel."}
    _TORRENT_ACTIVE.mark_done(gid)
    return {"_ok": True, "cancelled": True, "gid": gid,
            "tts_text": "Cancelled."}


# ──── feedback / IQ routes (tank_learn SQLite-WAL) ─────────────────────────
@app.get("/api/feedback/health")
def feedback_health() -> dict:
    return {"ok": _FEEDBACK_AVAILABLE,
            "error": _feedback_import_error,
            "db_path": (_FEEDBACK_STORE_SINGLETON.db_path
                        if _FEEDBACK_AVAILABLE
                        and _FEEDBACK_STORE_SINGLETON is not None
                        else "")}


@app.post("/api/feedback")
def feedback_apply(payload: Dict[str, Any]) -> dict:
    """Apply a user reward or log an inline feedback row.

    Request body (one of the three shapes the ROS node also accepts)::

        {"dispatch_id": 42, "reward": +1, "source": "user", "note": "good"}
        {"plugin_name": "voice.play_music",
         "intent_text": "play lo-fi",
         "reward": -1, "source": "dashboard", "note": "wrong movie"}
        {"plugin_name": "voice.play_music", "reward": +1}
    """
    if not _FEEDBACK_AVAILABLE or _FEEDBACK_STORE_SINGLETON is None:
        return {"_ok": False, "error": "feedback store not loaded",
                "detail": _feedback_import_error}
    reward = payload.get("reward", 0)
    plugin_name = (payload.get("plugin_name") or "").strip()
    intent_text = (payload.get("intent_text") or "").strip()
    source = (payload.get("source") or "dashboard").strip()[:32]
    note = (payload.get("note") or "").strip()[:200]
    dispatch_id_field = payload.get("dispatch_id")

    try:
        if dispatch_id_field is not None:
            ok = _FEEDBACK_STORE_SINGLETON.record_reward(
                int(dispatch_id_field), reward,
                source=source, note=note,
            )
            return {"_ok": ok, "dispatch_id": int(dispatch_id_field),
                    "event": "reward_updated" if ok else "reward_no_match"}
        if plugin_name and intent_text:
            new_id = _FEEDBACK_STORE_SINGLETON.record_dispatch_with_reward(
                intent_text, plugin_name, reward,
                source=source, note=note,
            )
            return {"_ok": True, "dispatch_id": new_id,
                    "event": "reward_recorded_inline"}
        if plugin_name:
            # No target row — create one with reward=0 so the dashboard
            # can still register an undo-able event later.
            new_id = _FEEDBACK_STORE_SINGLETON.record_dispatch(
                intent_text="", plugin_name=plugin_name,
                source=source, note=note,
            )
            ok = _FEEDBACK_STORE_SINGLETON.record_reward(
                new_id, reward, source=source, note=note,
            )
            return {"_ok": ok, "dispatch_id": new_id,
                    "event": "reward_recorded_inline_no_text"}
        return {"_ok": False, "error":
                "payload must include dispatch_id, plugin_name, "
                "or (plugin_name + intent_text)"}
    except ValueError as exc:
        return {"_ok": False, "error": str(exc)}


@app.get("/api/feedback/recent")
def feedback_recent(limit: int = 50) -> dict:
    """Return the latest N feedback_log rows (newest first)."""
    if not _FEEDBACK_AVAILABLE or _FEEDBACK_STORE_SINGLETON is None:
        return {"available": False, "items": [], "count": 0,
                "error": _feedback_import_error or "feedback store not loaded"}
    rows = _FEEDBACK_STORE_SINGLETON.recent(limit)
    return {"available": True, "count": len(rows),
            "items": [r.to_dict() for r in rows]}


@app.get("/api/feedback/stats")
def feedback_stats(plugin_name: str = "") -> dict:
    """Aggregate reward + sample count, optionally filtered by plugin_name."""
    if not _FEEDBACK_AVAILABLE or _FEEDBACK_STORE_SINGLETON is None:
        return {"available": False, "items": [], "plugins": 0,
                "error": _feedback_import_error or "feedback store not loaded"}
    if plugin_name:
        return {"available": True, "plugins": 1,
                "items": [_FEEDBACK_STORE_SINGLETON.plugin_stats(plugin_name)]}
    rows = _FEEDBACK_STORE_SINGLETON.all_plugin_stats()
    return {"available": True, "plugins": len(rows), "items": rows}


@app.get("/api/feedback/iq")
def feedback_iq(plugin_name: str = "", limit: int = 50) -> dict:
    """Return most-recent IQ samples (Phase 2 data; populated by tank_iq)."""
    if not _FEEDBACK_AVAILABLE or _FEEDBACK_STORE_SINGLETON is None:
        return {"available": False, "items": [], "count": 0,
                "error": _feedback_import_error or "feedback store not loaded"}
    pname = plugin_name.strip() or None
    rows = _FEEDBACK_STORE_SINGLETON.recent_iq(pname, limit=limit)
    return {"available": True, "count": len(rows),
            "plugin_name": pname or "", "items": rows}


@app.get("/api/feedback/grammar_weights")
def feedback_grammar_weights() -> dict:
    """Return the current per-cid grammar weight map (intent_router's
    online-learning table). Read-only; updated by :mod:`tank_learn`
    when a reward=-1 comes in."""
    if not _FEEDBACK_AVAILABLE or _FEEDBACK_STORE_SINGLETON is None:
        return {"available": False, "items": {},
                "error": _feedback_import_error or "feedback store not loaded"}
    return {"available": True,
            "items": _FEEDBACK_STORE_SINGLETON.all_grammar_weights()}


# ──── learn / memory routes (tank_learn phase-3) ─────────────────────────────
@app.get("/api/learn/memory/health")
def learn_memory_health() -> dict:
    """Liveness + import-error surface for the memory subsystem."""
    return {
        "ok": _MEMORY_AVAILABLE,
        "error": _memory_import_error,
        "db_path": (_MEMORY_STORE_SINGLETON.db_path
                    if _MEMORY_AVAILABLE and _MEMORY_STORE_SINGLETON is not None
                    else ""),
    }


@app.get("/api/learn/memory/recall")
def learn_memory_recall(q: str = "", top_k: int = 10,
                        tier: str = "all") -> dict:
    """Semantic recall: top-k facts/skills/episodes ranked against ``q``.

    We import :mod:`tank_learn.recall` lazily so a bare import error
    here doesn't blow away the rest of the dashboard.
    """
    if not _MEMORY_AVAILABLE or _MEMORY_STORE_SINGLETON is None:
        return {"available": False, "hits": [], "count": 0,
                "error": _memory_import_error or "memory store not loaded"}
    if not (q or "").strip():
        return {"available": True, "hits": [], "count": 0,
                "query": "", "tier": tier}
    try:
        from tank_learn.recall import recall as _recall
    except Exception as exc:                                          # noqa: BLE001
        return {"available": False, "hits": [], "count": 0,
                "error": f"recall import failed: {exc}", "query": q}
    hits = _recall(q.strip(), _MEMORY_STORE_SINGLETON,
                   top_k=top_k, tier=tier)
    return {"available": True, "query": q, "tier": tier,
            "count": len(hits),
            "hits": [h.to_dict() for h in hits]}


@app.get("/api/learn/memory/skills")
def learn_memory_skills(min_proficiency: float = 0.05,
                        limit: int = 100) -> dict:
    """Read the procedural-memory (skills) table.

    ``min_proficiency`` defaults to the floor (0.05) so the operator sees
    ALL learned abilities, even ones that have decayed to "barely known".
    """
    if not _MEMORY_AVAILABLE or _MEMORY_STORE_SINGLETON is None:
        return {"available": False, "items": [], "count": 0,
                "error": _memory_import_error or "memory store not loaded"}
    skills = _MEMORY_STORE_SINGLETON.skills(
        min_proficiency=float(min_proficiency), limit=int(limit),
    )
    return {"available": True, "count": len(skills),
            "min_proficiency": float(min_proficiency),
            "items": [s.to_dict() for s in skills]}


@app.get("/api/learn/memory/episodes")
def learn_memory_episodes(since_days: float = 7.0,
                          source: str = "",
                          limit: int = 100) -> dict:
    """Episodes in the last ``since_days`` (default 7 = the consolidation
    promotion window). Filterable by ``source`` (e.g., ``discovery``,
    ``user_teach``, ``voice_command``).
    """
    if not _MEMORY_AVAILABLE or _MEMORY_STORE_SINGLETON is None:
        return {"available": False, "items": [], "count": 0,
                "error": _memory_import_error or "memory store not loaded"}
    now = time.time()
    since_ts = now - float(since_days) * 86400.0
    episodes = _MEMORY_STORE_SINGLETON.recent_episodes(
        since_ts=since_ts,
        source=(source.strip() or None),
        limit=int(limit),
    )
    return {"available": True, "count": len(episodes),
            "since_days": float(since_days),
            "source": source,
            "items": [e.to_dict() for e in episodes]}


@app.get("/api/learn/memory/consolidation_status")
def learn_memory_consolidation_status() -> dict:
    """Latest consolidation audit row + summary counts of the active
    memory state. Single round-trip so the dashboard tile stays cheap."""
    if not _MEMORY_AVAILABLE or _MEMORY_STORE_SINGLETON is None:
        return {"available": False, "last_run": None,
                "totals": {"facts": 0, "skills": 0, "episodes": 0,
                           "edges": 0},
                "error": _memory_import_error or "memory store not loaded"}
    last = _MEMORY_STORE_SINGLETON.latest_consolidation()
    facts_active = _MEMORY_STORE_SINGLETON.facts(
        min_proficiency=_MEMORY_STORE_SINGLETON.CONFIDENCE_FLOOR,
        limit=10_000,
    )
    skills = _MEMORY_STORE_SINGLETON.skills(
        min_proficiency=_MEMORY_STORE_SINGLETON.SKILL_MIN_PROFICIENCY,
        limit=10_000,
    )
    edges = _MEMORY_STORE_SINGLETON.edges(min_strength=0.0, limit=10_000)
    return {
        "available": True,
        "last_run": last.to_dict() if last is not None else None,
        "totals": {
            "facts":    len(facts_active),
            "skills":   len(skills),
            "episodes": len(_MEMORY_STORE_SINGLETON.recent_episodes(limit=10_000)),
            "edges":    len(edges),
        },
    }


@app.post("/api/cmd/estop")
def cmd_estop(latch: bool = True):
    bridge.publish_estop(latch=latch)
    return {"latch": latch}


@app.post("/api/cmd/move")
def cmd_move(vx: float = 0.0, wz: float = 0.0):
    bridge.publish_move(vx=vx, wz=wz)
    return {"vx": vx, "wz": wz}


@app.get("/")
def root():
    index_html = os.path.join(DASHBOARD_DIR, "index.html")
    if not os.path.isfile(index_html):
        return PlainTextResponse("dashboard UI not built yet", status_code=503)
    return FileResponse(index_html, media_type="text/html")


# --------------------------------------------------------------------------- #
# WebSockets
# --------------------------------------------------------------------------- #
@app.websocket("/ws/feed")
async def ws_feed(ws: WebSocket) -> None:
    await ws.accept()
    last_seen = ""
    try:
        while True:
            with _state_lock:
                cur = _state.health_state
            if cur != last_seen:
                await ws.send_text(cur or "")
                last_seen = cur
            await asyncio.sleep(0.5)
    except Exception:
        return


@app.websocket("/ws/emotion")
async def ws_emotion(ws: WebSocket) -> None:
    await ws.accept()
    if _bridge is not None:
        _bridge.attach_ws(ws)
    try:
        with _state_lock:
            cur = _state.emotion_current
            ts = _state.emotion_last_update
        await ws.send_text(json_dumps({"mood": cur, "ts": ts}))
        while True:
            await asyncio.sleep(60.0)
    except Exception:
        if _bridge is not None:
            _bridge.detach_ws(ws)
        return


# --------------------------------------------------------------------------- #
# ROS bridge thread
# --------------------------------------------------------------------------- #
_bridge: Optional[_BridgeNode] = None
bridge = None  # type: ignore[assignment]


def _ros_spin_thread() -> None:
    global _bridge, bridge
    if not rclpy.ok():
        rclpy.init()
    _bridge = _BridgeNode()
    bridge = _bridge
    executor = SingleThreadedExecutor()
    executor.add_node(_bridge)
    executor.spin()
