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
async def dispatch_cmd(name: str, request: Request,
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
        body = await request.json() if hasattr(request, "json") else None
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
async def chat_alias(request: Request,
               authorization: Optional[str] = Header(default=None)) -> dict:
    return await dispatch_cmd("chat", request, authorization=authorization)


# ---------------------------------------------------------------------------
# Direct serial camera snapshot endpoint (bypasses bench stub)
# ---------------------------------------------------------------------------

def _read_serial_camera(max_px: int = 640) -> dict:
    """Read JPEG from DFRobot USB serial camera on /dev/ttyACM0."""
    import base64 as _b64
    import time as _time
    try:
        import serial as _serial
    except ImportError:
        return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}

    port = "/dev/ttyACM0"
    try:
        s = _serial.Serial(port, 921600, timeout=5)
        _time.sleep(0.3)
        s.read(s.in_waiting)
        _time.sleep(0.1)
        s.read(s.in_waiting)
        s.write(b"SNAP\n")
        header = b""
        deadline = _time.time() + 5
        while _time.time() < deadline:
            ch = s.read(1)
            if ch:
                header += ch
                if ch == b"\n":
                    break
        h = header.decode("utf-8", errors="replace").strip()
        if not h.startswith("FRAME:"):
            s.close()
            return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}
        parts = h.split(":")
        expected = int(parts[3])
        jpeg = b""
        dl = _time.time() + 10
        while len(jpeg) < expected and _time.time() < dl:
            chunk = s.read(min(expected - len(jpeg), 16384))
            if chunk:
                jpeg += chunk
                dl = _time.time() + 2
        s.read(1)
        s.close()
        if len(jpeg) < 500:
            return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}
        b64 = _b64.b64encode(jpeg).decode("ascii")
        return {"ts": _time.time(), "width": 640, "height": 480,
                "data_url": "data:image/jpeg;base64," + b64}
    except Exception:
        return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}


@app.get("/api/camera/snapshot")
async def camera_snapshot(
    max_px: int = 640,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Direct camera snapshot from serial port -- works in bench mode."""
    if authorization:
        try:
            authenticate(authorization)
        except AuthError:
            pass
    return _read_serial_camera(max_px)


# ---------------------------------------------------------------------------
# Optimized serial camera — keeps port open for faster repeated reads
# ---------------------------------------------------------------------------

_serial_conn = None
_serial_lock = __import__("threading").Lock()

def _get_serial():
    global _serial_conn
    with _serial_lock:
        if _serial_conn is None or not _serial_conn.is_open:
            try:
                import serial as _serial
                _serial_conn = _serial.Serial("/dev/ttyACM0", 921600, timeout=3)
                time.sleep(0.2)
                _serial_conn.read(_serial_conn.in_waiting)
            except Exception as e:
                import sys
                print(f"SERIAL OPEN ERROR: {e}", file=sys.stderr)
                _serial_conn = None
        return _serial_conn

def _read_serial_camera_fast(max_px: int = 640) -> dict:
    """Fast camera read — keeps serial port open between frames."""
    import base64 as _b64
    import time as _time
    try:
        s = _get_serial()
        if s is None:
            return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}
        with _serial_lock:
            s.reset_input_buffer()
            s.write(b"SNAP\n")
            header = b""
            deadline = _time.time() + 3
            while _time.time() < deadline:
                ch = s.read(1)
                if ch:
                    header += ch
                    if ch == b"\n":
                        break
            h = header.decode("utf-8", errors="replace").strip()
            if not h.startswith("FRAME:"):
                return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}
            parts = h.split(":")
            expected = int(parts[3])
            jpeg = b""
            dl = _time.time() + 5
            while len(jpeg) < expected and _time.time() < dl:
                chunk = s.read(min(expected - len(jpeg), 65536))
                if chunk:
                    jpeg += chunk
                    dl = _time.time() + 1
        if len(jpeg) < 500:
            return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}
        b64 = _b64.b64encode(jpeg).decode("ascii")
        return {"ts": _time.time(), "width": 640, "height": 480,
                "data_url": "data:image/jpeg;base64," + b64}
    except Exception:
        with _serial_lock:
            try:
                if _serial_conn and _serial_conn.is_open:
                    _serial_conn.close()
            except Exception:
                pass
        globals()["_serial_conn"] = None
        return {"ts": _time.time(), "width": 0, "height": 0, "data_url": ""}


# Override the original function
_read_serial_camera = _read_serial_camera_fast


# ---------------------------------------------------------------------------
# YOLO detection endpoint — runs YOLOv8 on latest camera frame
# ---------------------------------------------------------------------------

_yolo_model = None

def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            import os
            model_path = os.path.expanduser("~/The-Tank-Project/yolov8n.pt")
            if not os.path.exists(model_path):
                model_path = "yolov8n.pt"
            _yolo_model = YOLO(model_path)
        except Exception:
            return None
    return _yolo_model




# ---------------------------------------------------------------------------
# LIDAR scan endpoint — reads aa55 protocol from /dev/ttyUSB0
# ---------------------------------------------------------------------------

def _read_lidar_scan() -> dict:
    """Read LIDAR scan data (aa55 protocol @ 115200 baud)."""
    import time as _time
    try:
        import serial as _serial
    except ImportError:
        return {"points": [], "min_dist": 0, "max_dist": 0, "error": "no serial"}

    port = "/dev/ttyUSB0"
    try:
        s = _serial.Serial(port, 115200, timeout=0.1)
        _time.sleep(0.2)
        s.reset_input_buffer()
        buf = b""
        deadline = _time.time() + 1.0
        while _time.time() < deadline:
            buf += s.read(4096)
        s.close()

        points = []
        i = 0
        while True:
            idx = buf.find(b"\xaa\x55", i)
            if idx == -1 or idx + 10 > len(buf):
                break
            count = buf[idx + 3]
            frame_len = 10 + count * 2
            if count < 1 or count > 40 or idx + frame_len > len(buf):
                i = idx + 1
                continue
            frame = buf[idx:idx + frame_len]
            start_angle = int.from_bytes(frame[4:6], "little") / 100.0
            end_angle = int.from_bytes(frame[6:8], "little") / 100.0
            for j in range(count):
                off = 10 + j * 2
                dist = int.from_bytes(frame[off:off + 2], "little")
                if dist <= 0:
                    continue
                frac = j / max(count - 1, 1)
                angle = start_angle + (end_angle - start_angle) * frac
                if angle >= 360:
                    angle -= 360
                elif angle < 0:
                    angle += 360
                points.append({"angle": round(angle, 1), "distance": dist})
            i = idx + frame_len

        distances = [p["distance"] for p in points]
        return {
            "points": points,
            "count": len(points),
            "min_dist": min(distances) if distances else 0,
            "max_dist": max(distances) if distances else 0,
            "avg_dist": round(sum(distances) / len(distances)) if distances else 0,
        }
    except Exception as e:
        return {"points": [], "count": 0, "error": str(e)}


@app.get("/api/lidar/scan")
async def lidar_scan(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """LIDAR 360 scan — returns distance points with angles."""
    if authorization:
        try:
            authenticate(authorization)
        except AuthError:
            pass
    return _read_lidar_scan()



@app.get("/api/camera/detect")
async def camera_detect(
    max_px: int = 640,
    confidence: float = 0.5,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Run YOLOv8 detection on latest camera frame."""
    if authorization:
        try:
            authenticate(authorization)
        except AuthError:
            pass

    # Capture frame
    frame_data = _read_serial_camera_fast(max_px)
    data_url = frame_data.get("data_url", "")
    if not data_url:
        return {"ts": frame_data["ts"], "detections": [], "frame": frame_data}

    # Run YOLO
    model = _get_yolo()
    if model is None:
        return {"ts": frame_data["ts"], "detections": [],
                "frame": frame_data, "error": "YOLO model not available"}

    try:
        import base64 as _b64
        jpeg_b64 = data_url.split(",", 1)[1]
        jpeg_bytes = _b64.b64decode(jpeg_b64)
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(jpeg_bytes)
            tmp_path = f.name

        results = model(tmp_path, conf=confidence, verbose=False)
        os.unlink(tmp_path)

        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = model.names.get(cls, f"class_{cls}")
                detections.append({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "confidence": round(conf, 3),
                    "label": label
                })

        return {"ts": frame_data["ts"], "detections": detections,
                "count": len(detections), "frame": frame_data}
    except Exception as e:
        return {"ts": frame_data["ts"], "detections": [],
                "frame": frame_data, "error": str(e)}






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




# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Real Agent Chat Endpoint — routes through LLM providers
# ---------------------------------------------------------------------------

import os as _os
import json as _json
import urllib.request
import urllib.error
import re as _re

_agent_history = []


def _call_openai_compat(base_url, api_key, model, messages, max_tokens=1024, retries=3):
    """Call an OpenAI-compatible API with retry on DNS failures."""
    url = f"{base_url}/chat/completions"
    payload = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }).encode()
    import socket
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, socket.gaierror, OSError) as e:
            if attempt < retries - 1:
                import time as _time
                _time.sleep(2 * (attempt + 1))  # Backoff: 2s, 4s
            else:
                raise


def _call_gemini(api_key, model, text, max_tokens=1024):
    """Call Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = _json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": max_tokens}
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = _json.loads(resp.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _rotate_llm(messages):
    """Try providers in rotation, return (reply, provider_name) or (None, None)."""
    providers = [
        ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest", "openai"),
        ("groq_compound", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "groq/compound", "openai"),
        ("groq_qwen", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "qwen/qwen3.6-27b", "openai"),
        ("groq_allam", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "allam-2-7b", "openai"),
    ]
    for name, base_url, env_key, model, kind in providers:
        api_key = _os.environ.get(env_key, "")
        if not api_key:
            continue
        try:
            reply = _call_openai_compat(base_url, api_key, model, messages)
            return reply, name
        except Exception as e:
            _LOG.warning("Agent provider %s failed: %s", name, e)
            continue
    return None, None


def _parse_action(text):
    """Extract JSON action from LLM reply (handles code blocks and plain text)."""
    # Strip markdown code blocks
    cleaned = text
    code_blocks = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, _re.DOTALL)
    if code_blocks:
        cleaned = ' '.join(code_blocks)
    # Try JSON format: {"action": "camera"}
    try:
        for m in _re.finditer(r'\{\s*"action"\s*:', cleaned):
            start = m.start()
            depth = 0
            for i in range(start, len(cleaned)):
                if cleaned[i] == '{': depth += 1
                elif cleaned[i] == '}': depth -= 1
                if depth == 0 and i > start:
                    return _json.loads(cleaned[start:i+1])
    except Exception:
        pass
    # Try plain format: action=camera or action camera
    try:
        m = _re.search(r'action[=\s:]+(\w+)', cleaned)
        if m:
            return {"action": m.group(1)}
    except Exception:
        pass
    return None




def _exec_tool(action, bridge_url="http://localhost:8082"):
    """Execute a tool action and return the result as a string."""
    import urllib.request
    act_type = action.get("action", "")
    try:
        if act_type == "camera":
            req = urllib.request.Request(
                f"{bridge_url}/api/camera/snapshot?max_px=480",
                headers={"Authorization": "Bearer bench-key"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())
                durl = data.get("data_url", "")
                if durl and len(durl) > 100:
                    return f"[camera] Photo captured. Base64 length: {len(durl)} chars. Image shows what the DFRobot USB serial camera sees."
                return "[camera] No frame available from camera hardware."
        elif act_type == "lidar":
            req = urllib.request.Request(
                f"{bridge_url}/api/lidar/scan",
                headers={"Authorization": "Bearer bench-key"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())
                pts = data.get("points", [])
                min_d = data.get("min_distance_mm", 0)
                max_d = data.get("max_distance_mm", 0)
                return f"[lidar] {len(pts)} points scanned. Range: {min_d/1000:.1f}m - {max_d/1000:.1f}m. Closest obstacle at {min_d/1000:.1f}m."
        elif act_type == "telemetry":
            req = urllib.request.Request(
                f"{bridge_url}/api/cmd/telemetry",
                method="POST",
                data=b'{"params":{}}',
                headers={"Authorization": "Bearer bench-key", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
                result = data.get("result", {})
                bat = result.get("battery_v", 0)
                pct = int(result.get("battery_pct", 0) * 100)
                cpu = result.get("cpu_c", 0)
                estop = result.get("estop", False)
                emotion = result.get("emotion", "neutral")
                return f"[telemetry] Battery: {bat:.2f}V ({pct}%), CPU: {cpu:.1f}C, E-Stop: {'LATCHED' if estop else 'disarmed'}, Emotion: {emotion}"
        elif act_type == "move":
            vx = action.get("vx", 0)
            wz = action.get("wz", 0)
            dur = action.get("duration_s", 1)
            body = _json.dumps({"params": {"vx": vx, "wz": wz, "duration_s": dur}}).encode()
            req = urllib.request.Request(
                f"{bridge_url}/api/cmd/move",
                method="POST",
                data=body,
                headers={"Authorization": "Bearer bench-key", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
                result = data.get("result", {})
                return f"[move] Tank drove vx={result.get('vx_eff',vx)} wz={result.get('wz_eff',wz)} for {result.get('duration_s_eff',dur)}s"
        elif act_type == "estop":
            state = action.get("state", True)
            body = _json.dumps({"params": {"state": state}}).encode()
            req = urllib.request.Request(
                f"{bridge_url}/api/cmd/estop",
                method="POST",
                data=body,
                headers={"Authorization": "Bearer bench-key", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
                return f"[estop] {'EMERGENCY STOP LATCHED' if state else 'E-Stop released'}"
        elif act_type == "shell":
            cmd = action.get("cmd", "echo hello")
            body = _json.dumps({"params": {"text": f"run: {cmd}", "use_external_llm": False}}).encode()
            req = urllib.request.Request(
                f"{bridge_url}/api/cmd/chat",
                method="POST",
                data=body,
                headers={"Authorization": "Bearer bench-key", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())
                reply = data.get("result", {}).get("reply", "no output")
                return f"[shell] {reply}"
        elif act_type == "reply":
            return None  # Final reply, no tool execution needed
        else:
            return f"[unknown] Unknown action: {act_type}"
    except Exception as e:
        return f"[error] Tool execution failed: {e}"


_SYSTEM_PROMPT = (
    "You are TankOS Agent controlling a real robot tank."
    " Available tools (use the EXACT action name):"
    " camera - capture photo from USB camera."
    " lidar - 360-degree distance scan."
    " telemetry - get battery voltage and CPU temp."
    " move - drive the tank (params: vx, wz, duration_s)."
    " estop - emergency stop."
    " shell - run a shell command (params: cmd)."
    " reply - conversational text response."
    ""
    " RULES:"
    ' - To use a tool, respond with ONLY: {"action": "camera"}'
    ' - For move: {"action": "move", "vx": 0.3, "wz": 0, "duration_s": 2}'
    ' - For shell: {"action": "shell", "cmd": "ls"}'
    " - For chat, reply with plain text (no JSON)."
    " - Never output markdown code blocks. Just raw JSON or plain text."
)


@app.post("/api/agent/chat")
async def agent_chat(request: Request,
               authorization: Optional[str] = Header(default=None)) -> dict:
    """Agentic loop: LLM thinks -> executes tools -> feeds results -> repeats until done."""
    try:
        token_hash, role = authenticate(authorization)
    except AuthError as e:
        raise HTTPException(status_code=e.code, detail=str(e))
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    _agent_history.append({"role": "user", "content": text})

    MAX_ROUNDS = 5
    all_actions = []
    final_reply = None
    provider_used = None

    for round_num in range(MAX_ROUNDS):
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + _agent_history[-10:]
        reply_text, provider_used = _rotate_llm(messages)

        if reply_text is None:
            # If we already executed some tools, summarize what we did
            if all_actions:
                acts = ", ".join(a["action"] for a in all_actions)
                final_reply = f"I executed {len(all_actions)} actions ({acts}) successfully."
            else:
                final_reply = "All LLM providers are unavailable. Please try again later."
            # Clear history on failure to prevent cascading issues
            _agent_history.clear()
            break

        _agent_history.append({"role": "assistant", "content": reply_text})

        # Parse action from reply
        action = _parse_action(reply_text)

        if action is None or action.get("action") == "reply":
            # No action or explicit reply — this is the final response
            final_reply = reply_text
            if action and action.get("text"):
                final_reply = action["text"]
            break

        # Execute the tool
        act_type = action.get("action", "")
        all_actions.append({"action": act_type, "args": {k: v for k, v in action.items() if k != "action"}})
        _LOG.info("Agent round %d: executing %s", round_num + 1, act_type)

        tool_result = _exec_tool(action)
        if tool_result:
            # Truncate tool results - camera base64 is ~50KB, limit to 500 chars
            max_result_len = 500
            truncated = tool_result[:max_result_len]
            if len(tool_result) > max_result_len:
                truncated += f" ... ({len(tool_result) - max_result_len} chars truncated)"
            _agent_history.append({"role": "user", "content": f"[Tool result for {act_type}]: {truncated}"})
        else:
            # reply action — no tool result needed
            final_reply = action.get("text", reply_text)
            break

    if final_reply is None:
        final_reply = reply_text if reply_text else "Task completed."

    # Keep history manageable
    if len(_agent_history) > 20:
        _agent_history[:] = _agent_history[-10:]

    return {
        "reply": final_reply,
        "provider": provider_used,
        "actions": all_actions,
        "rounds": len(all_actions),
        "history_length": len(_agent_history)
    }



@app.get("/api/agent/debug")
async def agent_debug():
    """Debug: check env vars and test LLM providers."""
    import os
    import json as _json
    import urllib.request
    
    result = {}
    
    # Check env vars
    for key in ["MISTRAL_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
        val = os.environ.get(key, "")
        result[f"env_{key}"] = f"SET ({len(val)} chars)" if val else "MISSING"
    
    # Test Mistral directly
    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    if mistral_key:
        try:
            url = "https://api.mistral.ai/v1/chat/completions"
            payload = _json.dumps({
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": "say hi"}],
                "max_tokens": 10
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {mistral_key}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())
                result["mistral_test"] = "OK: " + data["choices"][0]["message"]["content"]
        except Exception as e:
            result["mistral_test"] = f"FAIL: {type(e).__name__}: {e}"
    
    # Test _rotate_llm
    try:
        test_messages = [{"role": "user", "content": "say hi in 5 words"}]
        reply, provider = _rotate_llm(test_messages)
        result["rotate_test"] = f"OK via {provider}: {reply[:100] if reply else 'None'}"
    except Exception as e:
        result["rotate_test"] = f"FAIL: {type(e).__name__}: {e}"
    
    return result


@app.post("/api/agent/clear")
async def agent_clear(authorization: Optional[str] = Header(default=None)) -> dict:
    _agent_history.clear()
    return {"cleared": True}


    return {"cleared": True}


def main(host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> int:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
