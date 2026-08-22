"""FastAPI app for the AI ↔ Pi command bridge on port 8082.

Independent of ``tank_dashboard`` so dashboard changes never regress
AI-facing behaviour.  Lifespan-managed ROS bridge thread on a module-level
:class:`MultiThreadedExecutor` (4 workers) so timers and subs never
starve each other.

Endpoints
---------
* GET  /api/cmd/manifest         — tool manifest for AI introspection
* POST /api/cmd/<name>            — dispatch a single command
* GET  /api/cmd/audit             — last N audit records
* POST /api/cmd/chat              — alias for the ``chat`` command
* GET  /api/health                — liveness
"""
from __future__ import annotations

import base64
import collections
import json
import logging
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Deque, Dict, Optional

try:
    import rclpy                                          # noqa: F401
    from geometry_msgs.msg import Twist
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from sensor_msgs.msg import BatteryState, Image
    from std_msgs.msg import Bool, String
    _RCLPY_AVAILABLE = True
    _BRIDGE_EXECUTOR = MultiThreadedExecutor(num_threads=4)
except ImportError:
    _RCLPY_AVAILABLE = False
    _BRIDGE_EXECUTOR = None  # type: ignore[assignment]

    class _NoopPublisher:                               # type: ignore[no-redef]
        def publish(self, *_a, **_k): return None

    class _NoopLogger:                                  # type: ignore[no-redef]
        def info(self, *_a, **_k): pass
        def warn(self, *_a, **_k): pass
        def error(self, *_a, **_k): pass
        def debug(self, *_a, **_k): pass

    class _StubNode:                                    # type: ignore[no-redef]
        def __init__(self, *_a, **_k): pass
        def create_subscription(self, *_a, **_k): return None
        def create_publisher(self, *_a, **_k): return _NoopPublisher()
        def create_timer(self, *_a, **_k): return None
        def destroy_publisher(self, *_a, **_k): pass
        def get_logger(self): return _NoopLogger()

    class _StubBool:                                    # type: ignore[no-redef]
        def __init__(self, data: bool = False) -> None:
            self.data = bool(data)

    class _StubString:                                  # type: ignore[no-redef]
        def __init__(self, data: str = "") -> None:
            self.data = str(data)

    Node = _StubNode                          # type: ignore[assignment]
    Twist = type("Twist", (), {})             # type: ignore[assignment]
    BatteryState = type("BatteryState", (), {})  # type: ignore[assignment]
    Image = type("Image", (), {})             # type: ignore[assignment]
    Bool = _StubBool                          # type: ignore[assignment]
    String = _StubString                      # type: ignore[assignment]
    SingleThreadedExecutor = object           # type: ignore[assignment]
    MutuallyExclusiveCallbackGroup = object   # type: ignore[assignment]
    MultiThreadedExecutor = object            # type: ignore[assignment]
    rclpy = type("rclpy", (), {"ok": staticmethod(lambda: False),
                                "init": staticmethod(lambda: None),
                                "shutdown": staticmethod(lambda: None)})()
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .auth import AuthError, RateLimiter, authenticate
from .commands import DISPATCH, RATE_CLASS
from .manifest import manifest_json


_LOG = logging.getLogger("tank_command_bridge")
# Production diagnostic routing — without basicConfig, root WARNING only
# + uvicorn's own access logger means our pre-flight ``_LOG.error()``
# calls never reach the systemd journal or docker log driver.
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

AUDIT_LOG_MAX = 500
DEFAULT_PORT = 8082


# --------------------------------------------------------------------------- #
# Bench-mode dispatcher singleton (used only when bn is None)
# --------------------------------------------------------------------------- #

class _StubPub:
    """In-process bench publisher used when rclpy is missing.

    Defines the same surface as :class:`BridgeNode` so dispatch paths
    in ``commands.py`` are agnostic to whether rclpy is live. Routes
    its software-estop latch through ``self._latched`` so test
    ``test_dispatch_estop_latches_following_writes`` sees the latch
    (was hard-coded ``return False`` previously, which silently passed
    bench tests that should have failed)."""

    _VALID_PATROL_MODES = {"waypoint", "random", "pause", "stop"}

    def __init__(self) -> None:
        self._latched = False

    def publish_estop(self, state: bool) -> None:
        self._latched = bool(state)

    def publish_move(self, vx: float, wz: float) -> None:
        pass

    def publish_patrol(self, mode: str) -> bool:
        return mode in self._VALID_PATROL_MODES

    def publish_dock_enable(self, enable: bool) -> None:
        pass

    def publish_chat(self, text: str, use_external: bool) -> Dict:
        return {"reply": f"[stub] echo: {text}",
                "emotion": "neutral",
                "external_pieces": []}

    def publish_meta_query(self, kind: str, text: str, k: int) -> Dict:
        return {"kind": kind, "hits": [],
                "queued": True, "bench_stub": True}

    def schedule_zero_move(self, delay_s: float) -> None:
        pass

    def is_software_estop_latched(self) -> bool:
        return self._latched

    def snapshot_camera_jpeg(self, max_px: int = 640) -> Dict:
        return {"ts": time.time(), "width": 0, "height": 0,
                "data_url": ""}

    def snapshot_telemetry(self) -> Dict:
        return {"ok": True, "battery_v": 12.0,
                "battery_pct": 0.97, "cpu_c": 45.0,
                "estop": False, "emotion": "neutral",
                "cmd_age_ms": 0}

    def software_estop_latch(self, state: bool) -> None:
        self._latched = bool(state)


# --------------------------------------------------------------------------- #
# Shared in-process state + bridge node (ROS-coupled)
# --------------------------------------------------------------------------- #

class BridgeState:
    def __init__(self) -> None:
        self.audit: Deque[dict] = collections.deque(maxlen=AUDIT_LOG_MAX)
        self.last_health: dict = {}
        self.last_battery: dict = {}
        self.last_image_jpeg: Optional[bytes] = None
        self.last_image_dim: tuple = (0, 0)
        self.last_image_ts: float = 0.0
        self.last_telemetry_ts: float = 0.0
        self.last_estop: bool = False
        self.last_cmd_ts: float = 0.0
        self.last_emotion: str = "neutral"


_state = BridgeState()
_state_lock = threading.Lock()
_bridge_node = None  # optional ROS-port side


class BridgeNode(Node):  # type: ignore[no-redef]
    """ROS-coupled side of the bridge. Receives audit info, publishes
    motion / estop / patrol / dock commands. ALL cold-start or hardware
    sensors + camera go through here so the FastAPI layer stays pure."""

    def __init__(self) -> None:
        super().__init__("tank_command_bridge")
        self._cbg = MutuallyExclusiveCallbackGroup()
        self._estop_pub = self.create_publisher(Bool, "/estop_external", 10)
        self._move_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._patrol_pub = self.create_publisher(String, "/patrol/cmd", 10)
        self._dock_pub = self.create_publisher(Bool, "/dock/enable", 10)
        self._meta_query_pub = self.create_publisher(
            String, "/meta/decision_search", 10,
        )
        self._chat_pub = self.create_publisher(String, "/external_chat", 10)
        self.create_subscription(
            BatteryState, "/battery/state", self._on_battery, 10,
            callback_group=self._cbg,
        )
        self.create_subscription(
            Image, "/camera/image_raw", self._on_image, 10,
            callback_group=self._cbg,
        )
        self.create_subscription(
            String, "/health/state", self._on_health, 10,
            callback_group=self._cbg,
        )
        self.create_subscription(
            String, "/assistant_text", self._on_assistant_text, 10,
            callback_group=self._cbg,
        )
        self.create_subscription(
            Bool, "/estop", self._on_estop_topic, 10,
            callback_group=self._cbg,
        )
        self.get_logger().info("tank_command_bridge ready")

    def publish_estop(self, state: bool) -> None:
        self._estop_pub.publish(Bool(data=bool(state)))

    def publish_move(self, vx: float, wz: float) -> None:
        t = Twist()
        t.linear.x = float(vx)
        t.angular.z = float(wz)
        self._move_pub.publish(t)

    def publish_patrol(self, mode: str) -> bool:
        if mode not in ("waypoint", "random", "pause", "stop"):
            return False
        self._patrol_pub.publish(String(data=mode))
        return True

    def publish_dock_enable(self, enable: bool) -> None:
        self._dock_pub.publish(Bool(data=bool(enable)))

    def publish_chat(self, text: str, use_external: bool) -> Dict:
        # External LLM integration handled by external_llm_client when
        # ``use_external`` is True. The chat reply is published to
        # /assistant_text and read back via /ws/feed. The bridge
        # returns a sentinel so the AI knows the call landed.
        self._chat_pub.publish(String(data=text))
        return {"reply": "[pending /assistant_text]",
                "emotion": "neutral",
                "external_pieces": []}

    def publish_meta_query(self, kind: str, text: str, k: int) -> Dict:
        if not _RCLPY_AVAILABLE:
            return {"kind": kind, "hits": []}
        payload = {"query": text, "top_k": k}
        topic = {
            "code":      "/meta/code_search",
            "hardware":  "/meta/hardware_lookup",
            "decisions": "/meta/decision_search",
            "knowledge": "/meta/knowledge_query",
        }.get(kind, "/meta/knowledge_query")
        try:
            tmp = self.create_publisher(String, topic, 1)
            tmp.publish(String(data=json.dumps(payload)))
            self.destroy_publisher(tmp)
            return {"kind": kind, "hits": [],
                    "queued": True, "topic": topic}
        except Exception as exc:
            return {"kind": kind, "hits": [], "error": str(exc)}

    _zero_move_timers: list = []

    def schedule_zero_move(self, delay_s: float) -> None:
        def _cb():
            try:
                self.publish_move(0.0, 0.0)
            finally:
                self._zero_move_timers[:] = [
                    t for t in self._zero_move_timers if not t.done()
                ]

        timer = self.create_timer(max(0.05, float(delay_s)), _cb)
        self._zero_move_timers.append(timer)

    def _on_battery(self, msg: BatteryState) -> None:
        with _state_lock:
            _state.last_battery = {
                "voltage":    float(msg.voltage),
                "percentage": float(msg.percentage),
                "current":    float(msg.current),
                "ts":         time.time(),
            }

    def _on_image(self, msg: Image) -> None:
        try:
            arr = bytes(msg.data) if msg.data else b""
            with _state_lock:
                _state.last_image_dim = (int(msg.width), int(msg.height))
                _state.last_image_ts  = time.time()
                _state.last_image_jpeg = arr if len(arr) < 200_000 else None
        except Exception:
            return

    def _on_health(self, msg: String) -> None:
        try:
            data = json.loads(msg.data or "{}")
        except Exception:
            return
        with _state_lock:
            _state.last_health = data
            _state.last_emotion = data.get("emotion", "neutral") or \
                _state.last_emotion
            _state.last_telemetry_ts = time.time()

    def _on_assistant_text(self, msg: String) -> None:
        with _state_lock:
            _state.last_health.setdefault(
                "last_reply", msg.data or "")[:200]

    def _on_estop_topic(self, msg: Bool) -> None:
        with _state_lock:
            _state.last_estop = bool(msg.data)
            _state.last_cmd_ts = time.time()

    def is_software_estop_latched(self) -> bool:
        return _state.last_estop

    def snapshot_camera_jpeg(self, max_px: int = 640) -> Dict:
        with _state_lock:
            jpeg = _state.last_image_jpeg
            dim  = _state.last_image_dim
            ts   = _state.last_image_ts
        if not jpeg:
            return {"ts": ts, "width": 0, "height": 0,
                    "data_url": ""}
        b64 = base64.b64encode(jpeg).decode("ascii")
        return {"ts": ts, "width": dim[0], "height": dim[1],
                "data_url": "data:image/jpeg;base64," + b64}

    def snapshot_telemetry(self) -> Dict:
        with _state_lock:
            bat = dict(_state.last_battery)
            hl  = dict(_state.last_health)
        return {
            "ok":          True,
            "battery_v":   bat.get("voltage"),
            "battery_pct": bat.get("percentage"),
            "cpu_c":       hl.get("cpu_c"),
            "estop":       _state.last_estop,
            "emotion":     _state.last_emotion,
            "cmd_age_ms":  (time.time() - _state.last_cmd_ts) * 1000
                           if _state.last_cmd_ts else None,
        }

    def software_estop_latch(self, state: bool) -> None:
        with _state_lock:
            _state.last_estop = bool(state)


# --------------------------------------------------------------------------- #
# FastAPI app + lifespan
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    if _RCLPY_AVAILABLE:
        app.state.bridge_node = start_bridge_thread()
    try:
        yield
    finally:
        pass


app = FastAPI(
    title="The Tank Command Bridge",
    version="0.1.0",
    lifespan=lifespan,
)

_RATE = RateLimiter()


def _record_audit(token_hash: str, role: str, name: str, audit_id: str,
                  params: Dict, status: int, error: Optional[str] = None
                  ) -> None:
    payload = {
        "ts":             time.time(),
        "audit_id":       audit_id,
        "token_hash":     token_hash,
        "role":           role,
        "command":        name,
        "params_summary": {k: type(v).__name__ for k, v in params.items()},
        "status":         status,
    }
    if error:
        payload["error"] = error[:200]
    with _state_lock:
        _state.audit.append(payload)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": app.version,
            "uptime": time.time()}


@app.get("/api/cmd/manifest")
def get_manifest() -> dict:
    return manifest_json()


@app.get("/api/cmd/audit")
def get_audit(authorization: Optional[str] = Header(default=None),
              limit: int = 50) -> dict:
    try:
        token_hash, role = authenticate(authorization)
        _RATE.check(token_hash, role, is_write=False)
    except AuthError as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    with _state_lock:
        items = list(_state.audit)[-int(limit):]
    return {"count": len(items), "items": items}


@app.post("/api/cmd/{name}")
def dispatch_cmd(name: str, request: Request,
                 authorization: Optional[str] = Header(default=None)
                 ) -> dict:
    if name not in DISPATCH:
        raise HTTPException(status_code=404,
                            detail=f"unknown command: {name!r}")
    try:
        token_hash, role = authenticate(authorization)
        is_write = RATE_CLASS.get(name, "read") == "write"
        _RATE.check(token_hash, role, is_write=is_write)
    except AuthError as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    try:
        body = request.json() if hasattr(request, "json") else None
        if body is None:
            body = json.loads(getattr(request, "_body", b"{}") or b"{}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad JSON: {exc}")
    audit_id = str(body.get("audit_id") or str(uuid.uuid4())).strip()
    params   = body.get("params") or {}
    bn = getattr(app.state, "bridge_node", None) or _bridge_node
    if bn is None:
        bn = _StubPub()  # module-level singleton — one per request
    try:
        out = DISPATCH[name](params, bn)
    except Exception as exc:
        _record_audit(token_hash, role, name, audit_id, params,
                      status=500, error=str(exc))
        raise HTTPException(status_code=500, detail=repr(exc))
    _record_audit(token_hash, role, name, audit_id, params, status=200)
    return {"audit_id": audit_id, "command": name, "result": out}


@app.post("/api/cmd/chat")
def chat_alias(request: Request,
               authorization: Optional[str] = Header(default=None)) -> dict:
    return dispatch_cmd("chat", request, authorization=authorization)


# --------------------------------------------------------------------------- #
# Bridge thread spin
# --------------------------------------------------------------------------- #

def start_bridge_thread() -> Optional[BridgeNode]:
    """Spin the ROS bridge on the module-level :class:`MultiThreadedExecutor`
    (4 workers) so timers (``schedule_zero_move`` after a ``move``) and the
    bridge's subscriptions never starve each other.

    Returns the live :class:`BridgeNode` on success or ``None`` when
    rclpy is missing or init fails. Falls back to bench-stub
    :class:`_StubPub` per request in that case — ``_LOG.error`` is called
    so operators can spot the broken Pi from the systemd journal."""
    global _bridge_node
    if not _RCLPY_AVAILABLE:
        _LOG.error(
            "tank_command_bridge: rclpy missing — every real command "
            "will run on the bench stub. CHECK YOUR ENV."
        )
        return None
    if not rclpy.ok():
        try:
            rclpy.init()
        except Exception as exc:
            _LOG.error(
                "tank_command_bridge: rclpy.init() failed (%s); bridge "
                "fell back to bench stub. ROBOT WILL NOT MOVE.", exc,
            )
            return None
    bn = BridgeNode()
    _bridge_node = bn
    # Lazy executor allocation so this is the only point that spins
    # the 4 worker threads. Use the top-level MultiThreadedExecutor
    # already imported above to avoid duplicate rclpy.executors
    # import paths.
    _BRIDGE_EXECUTOR = MultiThreadedExecutor(num_threads=4)
    _BRIDGE_EXECUTOR.add_node(bn)
    threading.Thread(
        target=_BRIDGE_EXECUTOR.spin, daemon=True,
        name="tank_command_bridge_spin",
    ).start()
    return bn


def main(host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> int:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
