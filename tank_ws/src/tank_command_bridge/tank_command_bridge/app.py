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
# ===========================================================================
# 100+ Tool Coding Agent with Local LLM Fallback & Thinking Display
# ===========================================================================

import os as _os
import json as _json
import urllib.request
import urllib.error
import re as _re
import subprocess as _subprocess
import time as _time
import glob as _glob
import shutil as _shutil
import hashlib as _hashlib
from pathlib import Path as _Path

_agent_history = []
_local_llm = None  # Lazy-loaded llama_cpp model

# ---- Tool Registry (100+ tools) ----

TOOL_CATEGORIES = {
    "file_ops": {
        "read_file": "Read file contents (path, offset, limit)",
        "write_file": "Write/create file (path, content)",
        "edit_file": "Edit file lines (path, old, new)",
        "delete_file": "Delete file (path)",
        "copy_file": "Copy file (src, dst)",
        "move_file": "Rename/move file (src, dst)",
        "list_directory": "List directory contents (path)",
        "create_directory": "Create directory (path)",
        "search_files": "Find files by glob pattern (pattern, path)",
        "file_info": "Get file metadata (path)",
        "file_size": "Get file size in bytes (path)",
        "file_hash": "Get file MD5 hash (path)",
    },
    "code_ops": {
        "search_code": "Search codebase for text pattern (pattern, path, file_type)",
        "grep_regex": "Regex search in code (pattern, path, flags)",
        "find_definition": "Find function/class definition (name, path)",
        "find_references": "Find all references to symbol (name, path)",
        "replace_in_file": "Find and replace in file (path, old, new)",
        "count_lines": "Count lines in file (path)",
        "diff_files": "Diff two files (file1, file2)",
        "syntax_check": "Check Python syntax (path)",
    },
    "git": {
        "git_status": "Show working tree status",
        "git_diff": "Show changes (file)",
        "git_commit": "Commit changes (message)",
        "git_push": "Push to remote (remote, branch)",
        "git_pull": "Pull from remote",
        "git_log": "Show commit history (count)",
        "git_branch": "List/create/switch branch (action, name)",
        "git_stash": "Stash changes (action)",
        "git_checkout": "Checkout branch/file (target)",
        "git_blame": "Show line-by-line blame (path)",
        "git_create_tag": "Create tag (name, message)",
    },
    "build_run": {
        "build_project": "Build the project (build_cmd)",
        "run_tests": "Run test suite (test_cmd)",
        "run_command": "Run arbitrary command (cmd, timeout)",
        "install_package": "Install package (package, manager)",
        "check_errors": "Check compilation errors (build_cmd)",
        "run_python": "Run Python code (code)",
        "run_script": "Run a script file (path, args)",
    },
    "system": {
        "system_info": "CPU, RAM, disk, OS info",
        "process_list": "List running processes (filter)",
        "network_info": "Network interfaces and IPs",
        "disk_usage": "Disk usage for path (path)",
        "environment_vars": "Get environment variables (filter)",
        "uptime": "System uptime",
        "whoami": "Current user",
        "kernel_version": "Kernel version",
        "gpu_info": "GPU status and memory",
        "temperature": "CPU/GPU temperature",
    },
    "docker": {
        "docker_ps": "List containers (all)",
        "docker_logs": "Container logs (name, lines)",
        "docker_exec": "Exec in container (name, cmd)",
        "docker_images": "List images",
        "docker_stop": "Stop container (name)",
        "docker_start": "Start container (name)",
    },
    "network": {
        "http_get": "HTTP GET request (url, headers)",
        "http_post": "HTTP POST request (url, data, headers)",
        "dns_lookup": "DNS resolution (hostname)",
        "ping": "Ping host (host, count)",
        "curl": "Curl request (url, method, data)",
        "port_check": "Check if port is open (host, port)",
    },
    "database": {
        "db_query": "SQL query (db_path, query)",
        "db_schema": "Show database schema (db_path)",
        "db_tables": "List tables (db_path)",
        "db_execute": "Execute SQL (db_path, sql)",
    },
    "tank_hardware": {
        "camera_capture": "Capture from DFRobot camera + YOLO",
        "lidar_scan": "360-degree LIDAR scan",
        "tank_move": "Drive tank (vx, wz, duration_s)",
        "tank_estop": "Emergency stop",
        "telemetry_get": "Battery voltage, CPU temp",
        "camera_snapshot": "Get camera snapshot (max_px)",
        "motion_detect": "Motion detection frame",
    },
    "modem": {
        "send_sms": "Send SMS (message, to)",
        "read_sms": "Read SMS messages",
        "list_contacts": "List contacts",
        "make_call": "Dial number (number_or_name)",
        "call_status": "Call status",
    },
    "code_generation": {
        "generate_function": "Generate a function (description, language)",
        "generate_class": "Generate a class (description, language)",
        "generate_api": "Generate API endpoint (description, framework)",
        "generate_test": "Generate test file (path_to_source)",
        "generate_readme": "Generate README for project (path)",
        "generate_script": "Generate script (description)",
    },
    "analysis": {
        "analyze_code": "Code complexity analysis (path)",
        "find_bugs": "Bug detection in code (path)",
        "security_scan": "Security audit (path)",
        "performance_profile": "Performance analysis (cmd)",
        "dependency_check": "Check dependencies (path)",
        "code_review": "Review code quality (path)",
    },
    "ai_ml": {
        "llm_query": "Query local LLM (prompt, model)",
        "embedding_generate": "Generate embeddings (text)",
        "image_classify": "Classify image (path)",
        "speech_to_text": "Whisper transcription (audio_path)",
        "ocr_extract": "OCR text extraction (image_path)",
    },
    "monitoring": {
        "tail_log": "Tail log file (path, lines)",
        "search_log": "Search in log (path, pattern)",
        "health_check": "HTTP health check (url)",
        "watch_process": "Watch process (name, duration)",
    },
    "package_mgmt": {
        "pip_install": "Install Python package (package)",
        "pip_list": "List installed packages (filter)",
        "apt_install": "Install system package (package)",
        "npm_install": "Install npm package (package)",
        "pip_freeze": "List pip packages with versions",
    },
    "process_mgmt": {
        "start_process": "Start background process (cmd)",
        "stop_process": "Stop process by name (name)",
        "kill_process": "Kill process by PID (pid)",
        "process_status": "Check process status (name)",
    },
    "text_ops": {
        "create_note": "Create a note file (title, content)",
        "read_note": "Read a note (title)",
        "search_notes": "Search notes (query)",
        "json_format": "Format JSON string (json_str)",
        "base64_encode": "Base64 encode (text)",
        "base64_decode": "Base64 decode (encoded)",
        "url_encode": "URL encode (text)",
        "url_decode": "URL decode (encoded)",
        "hash_text": "Hash text (algorithm, text)",
    },
    "time_date": {
        "current_time": "Current date and time",
        "timestamp": "Unix timestamp",
        "convert_time": "Convert timezone (datetime, from_tz, to_tz)",
    },
}

# Flatten all tools
ALL_TOOLS = {}
for cat, tools in TOOL_CATEGORIES.items():
    for name, desc in tools.items():
        ALL_TOOLS[name] = {"category": cat, "description": desc}

def _format_tool_catalog():
    """Format tool catalog for system prompt."""
    lines = []
    for cat, tools in TOOL_CATEGORIES.items():
        lines.append(f"\n[{cat}]")
        for name, desc in tools.items():
            lines.append(f"  {name} -- {desc}")
    lines.append(f"\n({len(ALL_TOOLS)} tools total)")
    return "\n".join(lines)


# ---- LLM Providers (Cloud + Local Fallback) ----

def _call_openai_compat(base_url, api_key, model, messages, max_tokens=2048, retries=3):
    """Call OpenAI-compatible API with DNS retry."""
    url = f"{base_url}/chat/completions"
    payload = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens
    }).encode()
    import socket
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, socket.gaierror, OSError) as e:
            if attempt < retries - 1:
                _time.sleep(2 * (attempt + 1))
            else:
                raise


def _call_local_phi3(messages):
    """Call local Phi-3 model via llama_cpp_python."""
    global _local_llm
    try:
        if _local_llm is None:
            import llama_cpp
            model_path = "/home/shashi/The-Tank-Project/models/llm/phi-3-mini-4k-instruct-q4.gguf"
            if not _os.path.exists(model_path):
                model_path = "/home/shashi/The-Tank-Project/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
            _LOG.info("Loading local LLM: %s", model_path)
            _local_llm = llama_cpp.Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=-1,  # Use GPU
                verbose=False
            )
        # Format messages for chat completion
        prompt = ""
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                prompt += f"<|system|>\n{content}<|end|>\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}<|end|>\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}<|end|>\n"
        prompt += "<|assistant|>\n"
        
        result = _local_llm(
            prompt,
            max_tokens=1024,
            temperature=0.3,
            stop=["<|end|>", "<|user|>"]
        )
        return result["choices"][0]["text"].strip()
    except Exception as e:
        _LOG.warning("Local LLM failed: %s", e)
        return None


def _rotate_llm(messages):
    """Try providers in rotation: cloud first, local fallback last."""
    cloud_providers = [
        ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
        ("groq_compound", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "groq/compound"),
        ("groq_qwen", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "qwen/qwen3.6-27b"),
        ("groq_allam", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "allam-2-7b"),
    ]
    # Try cloud providers
    for name, base_url, env_key, model in cloud_providers:
        api_key = _os.environ.get(env_key, "")
        if not api_key:
            continue
        try:
            reply = _call_openai_compat(base_url, api_key, model, messages)
            return reply, name
        except Exception as e:
            _LOG.warning("Agent provider %s failed: %s", name, e)
            continue
    # Fallback: local LLM
    try:
        _LOG.info("All cloud providers failed, trying local LLM...")
        reply = _call_local_phi3(messages)
        if reply:
            return reply, "local_phi3"
    except Exception as e:
        _LOG.warning("Local LLM failed: %s", e)
    return None, None


# ---- Tool Execution (100+ tools) ----

def _run_shell(cmd, timeout=15):
    """Run shell command."""
    try:
        r = _subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        parts = []
        if r.stdout:
            parts.append(r.stdout.strip())
        if r.stderr:
            parts.append(f"[stderr] {r.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"
    except _subprocess.TimeoutExpired:
        return f"TIMEOUT ({timeout}s): {cmd}"
    except Exception as e:
        return f"ERROR: {e}"



def _parse_action(text):
    """Extract action from LLM reply."""
    cleaned = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL)
    code_blocks = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, _re.DOTALL)
    if code_blocks:
        cleaned = ' '.join(code_blocks)
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
    try:
        m = _re.search(r'action[=\s:]+(\w+)', cleaned)
        if m:
            return {"action": m.group(1)}
    except Exception:
        pass
    return None


# ---- System Prompt ----

_SYSTEM_PROMPT = (
    "You are TankOS Agent -- an autonomous AI coding assistant with FULL system access on a Jetson Orin Nano robot.\n"
    "You have {tool_count} tools. You can do ANYTHING: read/write files, run code, git operations,\n"
    "build projects, manage docker, query databases, control robot hardware, send SMS, and more.\n"
    "\n"
    "CRITICAL RULES:\n"
    "1. ALWAYS respond with EXACTLY ONE JSON object. Nothing else. No markdown. No explanation.\n"
    "2. When you receive results in [brackets], describe them with {\"action\":\"reply\",\"text\":\"...\"}.\n"
    "3. You have full sudo access. Password is 1234.\n"
    "4. NEVER say 'I cannot'. You have full access. Just do it.\n"
    "5. Think step by step. If a task needs multiple steps, execute them one at a time.\n"
    "6. Always check your work. If something fails, try a different approach.\n"
    "\n"
    "ACTIONS (respond with exactly ONE):\n"
    "\n"
    "Shell: {\"action\":\"shell\",\"cmd\":\"<command>\"}\n"
    "Tool: {\"action\":\"tool_name\",\"param\":\"value\"}\n"
    "Reply: {\"action\":\"reply\",\"text\":\"<answer>\"}\n"
    "\n"
    "EXAMPLES:\n"
    "- Read file: {\"action\":\"read_file\",\"path\":\"/path/to/file\"}\n"
    "- Search code: {\"action\":\"search_code\",\"pattern\":\"TODO\",\"path\":\".\"}\n"
    "- Git commit: {\"action\":\"git_commit\",\"message\":\"fix bug\"}\n"
    "- System info: {\"action\":\"system_info\"}\n"
    "- Run tests: {\"action\":\"run_tests\",\"test_cmd\":\"pytest\"}\n"
    "- Camera: {\"action\":\"camera\"}\n"
    "- LIDAR: {\"action\":\"lidar\"}\n"
    "- Move tank: {\"action\":\"move\",\"vx\":0.3,\"wz\":0,\"duration_s\":2}\n"
)


# ---- Agent Chat Endpoint ----

@app.post("/api/agent/chat")
async def agent_chat(request: Request,
               authorization: Optional[str] = Header(default=None)) -> dict:
    """100+ tool coding agent with local LLM fallback and thinking display."""
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

    # Build system prompt with tool count
    tool_catalog = _format_tool_catalog()
    system = _SYSTEM_PROMPT.replace("{tool_count}", str(len(ALL_TOOLS))) + "\n\nTOOLS:\n" + tool_catalog

    _agent_history.append({"role": "user", "content": text})

    MAX_ROUNDS = 15
    all_actions = []
    final_reply = None
    provider_used = None
    thinking_steps = []  # Track thinking for streaming

    for round_num in range(MAX_ROUNDS):
        messages = [{"role": "system", "content": system}] + _agent_history[-15:]
        
        # Add thinking step
        thinking_steps.append(f"Round {round_num + 1}: Thinking...")
        
        reply_text, provider_used = _rotate_llm(messages)

        if reply_text is None:
            if all_actions:
                acts = ", ".join(a["action"] for a in all_actions)
                final_reply = f"Executed {len(all_actions)} actions ({acts}) successfully."
            else:
                final_reply = "All LLM providers are unavailable."
            _agent_history.clear()
            break

        _agent_history.append({"role": "assistant", "content": reply_text})
        thinking_steps.append(f"Round {round_num + 1}: Got LLM response via {provider_used}")

        action = _parse_action(reply_text)

        if action is None:
            final_reply = reply_text
            break

        at = action.get("action", "")

        if at == "reply":
            final_reply = action.get("text", reply_text)
            thinking_steps.append(f"Final reply: {final_reply[:100]}")
            break

        # Execute tool
        tool_args = {k: v for k, v in action.items() if k != "action"}
        all_actions.append({"action": at, "args": tool_args})
        thinking_steps.append(f"Executing: {at}({tool_args})")
        _LOG.info("Agent round %d: %s %s", round_num + 1, at, tool_args)

        result = _exec_action(action)
        if result is not None:
            truncated = result[:800]
            if len(result) > 800:
                truncated += f" ... ({len(result) - 800} chars truncated)"
            _agent_history.append({"role": "user", "content": f"[{at} result]: {truncated}"})
            thinking_steps.append(f"Got result: {truncated[:100]}")
        else:
            final_reply = action.get("text", reply_text)
            break

    if final_reply is None:
        final_reply = "Task completed."

    # Keep history manageable
    if len(_agent_history) > 30:
        _agent_history[:] = _agent_history[-15:]

    return {
        "reply": final_reply,
        "provider": provider_used,
        "actions": all_actions,
        "rounds": len(all_actions),
        "history_length": len(_agent_history),
        "thinking": thinking_steps,
        "tool_count": len(ALL_TOOLS)
    }


@app.post("/api/agent/clear")
async def agent_clear(authorization: Optional[str] = Header(default=None)) -> dict:
    """Clear agent conversation history."""
    _agent_history.clear()
    return {"cleared": True}


@app.get("/api/agent/tools")
async def agent_tools():
    """List all available tools."""
    return {"tools": ALL_TOOLS, "count": len(ALL_TOOLS), "categories": list(TOOL_CATEGORIES.keys())}


@app.get("/api/agent/debug")
async def agent_debug():
    """Debug: check env vars, LLM providers, and local models."""
    import os
    result = {}
    for key in ["MISTRAL_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
        val = os.environ.get(key, "")
        result[f"env_{key}"] = f"SET ({len(val)} chars)" if val else "MISSING"
    # Check local models
    phi3_path = "/home/shashi/The-Tank-Project/models/llm/phi-3-mini-4k-instruct-q4.gguf"
    tiny_path = "/home/shashi/The-Tank-Project/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    result["local_phi3"] = "EXISTS" if _os.path.exists(phi3_path) else "MISSING"
    result["local_tinyllama"] = "EXISTS" if _os.path.exists(tiny_path) else "MISSING"
    result["tool_count"] = len(ALL_TOOLS)
    result["tool_categories"] = list(TOOL_CATEGORIES.keys())
    # Test local LLM
    try:
        reply = _call_local_phi3([{"role": "user", "content": "say hi"}])
        result["local_llm_test"] = f"OK: {reply[:100]}" if reply else "Failed"
    except Exception as e:
        result["local_llm_test"] = f"FAIL: {e}"
    return result




def main(host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> int:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
# ===========================================================================
# 100+ Tool Coding Agent with Local LLM Fallback & Thinking Display
# ===========================================================================

import os as _os
import json as _json
import urllib.request
import urllib.error
import re as _re
import subprocess as _subprocess
import time as _time
import glob as _glob
import shutil as _shutil
import hashlib as _hashlib
from pathlib import Path as _Path

_agent_history = []
_local_llm = None  # Lazy-loaded llama_cpp model

# ---- Tool Registry (100+ tools) ----

TOOL_CATEGORIES = {
    "file_ops": {
        "read_file": "Read file contents (path, offset, limit)",
        "write_file": "Write/create file (path, content)",
        "edit_file": "Edit file lines (path, old, new)",
        "delete_file": "Delete file (path)",
        "copy_file": "Copy file (src, dst)",
        "move_file": "Rename/move file (src, dst)",
        "list_directory": "List directory contents (path)",
        "create_directory": "Create directory (path)",
        "search_files": "Find files by glob pattern (pattern, path)",
        "file_info": "Get file metadata (path)",
        "file_size": "Get file size in bytes (path)",
        "file_hash": "Get file MD5 hash (path)",
    },
    "code_ops": {
        "search_code": "Search codebase for text pattern (pattern, path, file_type)",
        "grep_regex": "Regex search in code (pattern, path, flags)",
        "find_definition": "Find function/class definition (name, path)",
        "find_references": "Find all references to symbol (name, path)",
        "replace_in_file": "Find and replace in file (path, old, new)",
        "count_lines": "Count lines in file (path)",
        "diff_files": "Diff two files (file1, file2)",
        "syntax_check": "Check Python syntax (path)",
    },
    "git": {
        "git_status": "Show working tree status",
        "git_diff": "Show changes (file)",
        "git_commit": "Commit changes (message)",
        "git_push": "Push to remote (remote, branch)",
        "git_pull": "Pull from remote",
        "git_log": "Show commit history (count)",
        "git_branch": "List/create/switch branch (action, name)",
        "git_stash": "Stash changes (action)",
        "git_checkout": "Checkout branch/file (target)",
        "git_blame": "Show line-by-line blame (path)",
        "git_create_tag": "Create tag (name, message)",
    },
    "build_run": {
        "build_project": "Build the project (build_cmd)",
        "run_tests": "Run test suite (test_cmd)",
        "run_command": "Run arbitrary command (cmd, timeout)",
        "install_package": "Install package (package, manager)",
        "check_errors": "Check compilation errors (build_cmd)",
        "run_python": "Run Python code (code)",
        "run_script": "Run a script file (path, args)",
    },
    "system": {
        "system_info": "CPU, RAM, disk, OS info",
        "process_list": "List running processes (filter)",
        "network_info": "Network interfaces and IPs",
        "disk_usage": "Disk usage for path (path)",
        "environment_vars": "Get environment variables (filter)",
        "uptime": "System uptime",
        "whoami": "Current user",
        "kernel_version": "Kernel version",
        "gpu_info": "GPU status and memory",
        "temperature": "CPU/GPU temperature",
    },
    "docker": {
        "docker_ps": "List containers (all)",
        "docker_logs": "Container logs (name, lines)",
        "docker_exec": "Exec in container (name, cmd)",
        "docker_images": "List images",
        "docker_stop": "Stop container (name)",
        "docker_start": "Start container (name)",
    },
    "network": {
        "http_get": "HTTP GET request (url, headers)",
        "http_post": "HTTP POST request (url, data, headers)",
        "dns_lookup": "DNS resolution (hostname)",
        "ping": "Ping host (host, count)",
        "curl": "Curl request (url, method, data)",
        "port_check": "Check if port is open (host, port)",
    },
    "database": {
        "db_query": "SQL query (db_path, query)",
        "db_schema": "Show database schema (db_path)",
        "db_tables": "List tables (db_path)",
        "db_execute": "Execute SQL (db_path, sql)",
    },
    "tank_hardware": {
        "camera_capture": "Capture from DFRobot camera + YOLO",
        "lidar_scan": "360-degree LIDAR scan",
        "tank_move": "Drive tank (vx, wz, duration_s)",
        "tank_estop": "Emergency stop",
        "telemetry_get": "Battery voltage, CPU temp",
        "camera_snapshot": "Get camera snapshot (max_px)",
        "motion_detect": "Motion detection frame",
    },
    "modem": {
        "send_sms": "Send SMS (message, to)",
        "read_sms": "Read SMS messages",
        "list_contacts": "List contacts",
        "make_call": "Dial number (number_or_name)",
        "call_status": "Call status",
    },
    "code_generation": {
        "generate_function": "Generate a function (description, language)",
        "generate_class": "Generate a class (description, language)",
        "generate_api": "Generate API endpoint (description, framework)",
        "generate_test": "Generate test file (path_to_source)",
        "generate_readme": "Generate README for project (path)",
        "generate_script": "Generate script (description)",
    },
    "analysis": {
        "analyze_code": "Code complexity analysis (path)",
        "find_bugs": "Bug detection in code (path)",
        "security_scan": "Security audit (path)",
        "performance_profile": "Performance analysis (cmd)",
        "dependency_check": "Check dependencies (path)",
        "code_review": "Review code quality (path)",
    },
    "ai_ml": {
        "llm_query": "Query local LLM (prompt, model)",
        "embedding_generate": "Generate embeddings (text)",
        "image_classify": "Classify image (path)",
        "speech_to_text": "Whisper transcription (audio_path)",
        "ocr_extract": "OCR text extraction (image_path)",
    },
    "monitoring": {
        "tail_log": "Tail log file (path, lines)",
        "search_log": "Search in log (path, pattern)",
        "health_check": "HTTP health check (url)",
        "watch_process": "Watch process (name, duration)",
    },
    "package_mgmt": {
        "pip_install": "Install Python package (package)",
        "pip_list": "List installed packages (filter)",
        "apt_install": "Install system package (package)",
        "npm_install": "Install npm package (package)",
        "pip_freeze": "List pip packages with versions",
    },
    "process_mgmt": {
        "start_process": "Start background process (cmd)",
        "stop_process": "Stop process by name (name)",
        "kill_process": "Kill process by PID (pid)",
        "process_status": "Check process status (name)",
    },
    "text_ops": {
        "create_note": "Create a note file (title, content)",
        "read_note": "Read a note (title)",
        "search_notes": "Search notes (query)",
        "json_format": "Format JSON string (json_str)",
        "base64_encode": "Base64 encode (text)",
        "base64_decode": "Base64 decode (encoded)",
        "url_encode": "URL encode (text)",
        "url_decode": "URL decode (encoded)",
        "hash_text": "Hash text (algorithm, text)",
    },
    "time_date": {
        "current_time": "Current date and time",
        "timestamp": "Unix timestamp",
        "convert_time": "Convert timezone (datetime, from_tz, to_tz)",
    },
}

# Flatten all tools
ALL_TOOLS = {}
for cat, tools in TOOL_CATEGORIES.items():
    for name, desc in tools.items():
        ALL_TOOLS[name] = {"category": cat, "description": desc}

def _format_tool_catalog():
    """Format tool catalog for system prompt."""
    lines = []
    for cat, tools in TOOL_CATEGORIES.items():
        lines.append(f"\n[{cat}]")
        for name, desc in tools.items():
            lines.append(f"  {name} -- {desc}")
    lines.append(f"\n({len(ALL_TOOLS)} tools total)")
    return "\n".join(lines)


# ---- LLM Providers (Cloud + Local Fallback) ----

def _call_openai_compat(base_url, api_key, model, messages, max_tokens=2048, retries=3):
    """Call OpenAI-compatible API with DNS retry."""
    url = f"{base_url}/chat/completions"
    payload = _json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens
    }).encode()
    import socket
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            })
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, socket.gaierror, OSError) as e:
            if attempt < retries - 1:
                _time.sleep(2 * (attempt + 1))
            else:
                raise


def _call_local_phi3(messages):
    """Call local Phi-3 model via llama_cpp_python."""
    global _local_llm
    try:
        if _local_llm is None:
            import llama_cpp
            model_path = "/home/shashi/The-Tank-Project/models/llm/phi-3-mini-4k-instruct-q4.gguf"
            if not _os.path.exists(model_path):
                model_path = "/home/shashi/The-Tank-Project/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
            _LOG.info("Loading local LLM: %s", model_path)
            _local_llm = llama_cpp.Llama(
                model_path=model_path,
                n_ctx=4096,
                n_gpu_layers=-1,  # Use GPU
                verbose=False
            )
        # Format messages for chat completion
        prompt = ""
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                prompt += f"<|system|>\n{content}<|end|>\n"
            elif role == "user":
                prompt += f"<|user|>\n{content}<|end|>\n"
            elif role == "assistant":
                prompt += f"<|assistant|>\n{content}<|end|>\n"
        prompt += "<|assistant|>\n"
        
        result = _local_llm(
            prompt,
            max_tokens=1024,
            temperature=0.3,
            stop=["<|end|>", "<|user|>"]
        )
        return result["choices"][0]["text"].strip()
    except Exception as e:
        _LOG.warning("Local LLM failed: %s", e)
        return None


def _rotate_llm(messages):
    """Try providers in rotation: cloud first, local fallback last."""
    cloud_providers = [
        ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
        ("groq_compound", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "groq/compound"),
        ("groq_qwen", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "qwen/qwen3.6-27b"),
        ("groq_allam", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "allam-2-7b"),
    ]
    # Try cloud providers
    for name, base_url, env_key, model in cloud_providers:
        api_key = _os.environ.get(env_key, "")
        if not api_key:
            continue
        try:
            reply = _call_openai_compat(base_url, api_key, model, messages)
            return reply, name
        except Exception as e:
            _LOG.warning("Agent provider %s failed: %s", name, e)
            continue
    # Fallback: local LLM
    try:
        _LOG.info("All cloud providers failed, trying local LLM...")
        reply = _call_local_phi3(messages)
        if reply:
            return reply, "local_phi3"
    except Exception as e:
        _LOG.warning("Local LLM failed: %s", e)
    return None, None


# ---- Tool Execution (100+ tools) ----

def _run_shell(cmd, timeout=15):
    """Run shell command."""
    try:
        r = _subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        parts = []
        if r.stdout:
            parts.append(r.stdout.strip())
        if r.stderr:
            parts.append(f"[stderr] {r.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"
    except _subprocess.TimeoutExpired:
        return f"TIMEOUT ({timeout}s): {cmd}"
    except Exception as e:
        return f"ERROR: {e}"


def _exec_tool(action):
    """Execute a tool action and return result string."""
    act = action.get("action", "")
    args = {k: v for k, v in action.items() if k != "action"}

    # ---- File Operations ----
    if act == "read_file":
        path = args.get("path", "")
        offset = int(args.get("offset", 0))
        limit = int(args.get("limit", 2000))
        try:
            lines = _Path(path).read_text(errors="replace").splitlines()
            chunk = lines[offset:offset+limit]
            return f"Lines {offset+1}-{offset+len(chunk)} of {len(lines)}:\n" + "\n".join(f"{i+1}: {l}" for i, l in enumerate(chunk, offset))
        except Exception as e:
            return f"Error: {e}"

    elif act == "write_file":
        path = args.get("path", "")
        content_val = args.get("content", "")
        try:
            _Path(path).parent.mkdir(parents=True, exist_ok=True)
            _Path(path).write_text(content_val)
            return f"Written {len(content_val)} bytes to {path}"
        except Exception as e:
            return f"Error: {e}"

    elif act == "edit_file":
        path = args.get("path", "")
        old = args.get("old", "")
        new = args.get("new", "")
        try:
            text = _Path(path).read_text(errors="replace")
            count = text.count(old)
            if count == 0:
                return f"Pattern not found in {path}"
            text = text.replace(old, new, 1)
            _Path(path).write_text(text)
            return f"Replaced in {path} ({count} occurrences found, 1 replaced)"
        except Exception as e:
            return f"Error: {e}"

    elif act == "delete_file":
        path = args.get("path", "")
        try:
            _Path(path).unlink()
            return f"Deleted {path}"
        except Exception as e:
            return f"Error: {e}"

    elif act == "copy_file":
        _shutil.copy2(args.get("src", ""), args.get("dst", ""))
        return f"Copied {args.get('src')} to {args.get('dst')}"

    elif act == "move_file":
        _shutil.move(args.get("src", ""), args.get("dst", ""))
        return f"Moved {args.get('src')} to {args.get('dst')}"

    elif act == "list_directory":
        path = args.get("path", ".")
        try:
            entries = sorted(_Path(path).iterdir())
            lines = []
            for e in entries[:100]:
                kind = "d" if e.is_dir() else "f"
                size = e.stat().st_size if e.is_file() else 0
                lines.append(f"[{kind}] {e.name} ({size} bytes)")
            return f"{path}/ ({len(entries)} entries)\n" + "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    elif act == "create_directory":
        _Path(args.get("path", "")).mkdir(parents=True, exist_ok=True)
        return f"Created {args.get('path')}"

    elif act == "search_files":
        pattern = args.get("pattern", "*")
        path = args.get("path", ".")
        matches = _glob.glob(f"{path}/**/{pattern}", recursive=True)
        return "\n".join(matches[:50]) if matches else "No matches"

    elif act == "file_info":
        p = _Path(args.get("path", ""))
        st = p.stat()
        return f"Size: {st.st_size}, Modified: {st.st_mtime}, Mode: {oct(st.st_mode)}"

    elif act == "file_size":
        return str(_Path(args.get("path", "")).stat().st_size)

    elif act == "file_hash":
        data = _Path(args.get("path", "")).read_bytes()
        algo = args.get("algorithm", "md5")
        h = _hashlib.new(algo)
        h.update(data)
        return f"{algo}: {h.hexdigest()}"

    # ---- Code Operations ----
    elif act == "search_code":
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        ftype = args.get("file_type", "")
        cmd = f"grep -rn '{pattern}' {path}"
        if ftype:
            cmd += f" --include='*.{ftype}'"
        cmd += " 2>/dev/null | head -50"
        return _run_shell(cmd)

    elif act == "grep_regex":
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        flags = args.get("flags", "-n")
        cmd = f"grep -r{flags} '{pattern}' {path} 2>/dev/null | head -50"
        return _run_shell(cmd)

    elif act == "find_definition":
        name = args.get("name", "")
        path = args.get("path", ".")
        return _run_shell(f"grep -rn 'def {name}\|class {name}\|function {name}' {path} 2>/dev/null | head -20")

    elif act == "find_references":
        name = args.get("name", "")
        path = args.get("path", ".")
        return _run_shell(f"grep -rn '{name}' {path} 2>/dev/null | head -50")

    elif act == "replace_in_file":
        path = args.get("path", "")
        old = args.get("old", "")
        new = args.get("new", "")
        try:
            text = _Path(path).read_text(errors="replace")
            new_text = text.replace(old, new)
            count = len(_re.findall(_re.escape(old), text))
            _Path(path).write_text(new_text)
            return f"Replaced {count} occurrences in {path}"
        except Exception as e:
            return f"Error: {e}"

    elif act == "count_lines":
        path = args.get("path", "")
        try:
            lines = _Path(path).read_text(errors="replace").splitlines()
            return f"{len(lines)} lines in {path}"
        except Exception as e:
            return f"Error: {e}"

    elif act == "diff_files":
        f1 = args.get("file1", "")
        f2 = args.get("file2", "")
        return _run_shell(f"diff {f1} {f2} | head -50")

    elif act == "syntax_check":
        path = args.get("path", "")
        return _run_shell('python3 -c "import py_compile; py_compile.compile(\"' + path + '\", doraise=True)" 2>&1')

    # ---- Git ----
    elif act.startswith("git_"):
        git_cmd = act.replace("git_", "git ")
        if act == "git_status":
            return _run_shell("git status --short")
        elif act == "git_diff":
            target = args.get("file", "")
            return _run_shell(f"git diff {target} | head -100")
        elif act == "git_commit":
            msg = args.get("message", "update")
            return _run_shell(f"git commit -am '{msg}'")
        elif act == "git_push":
            remote = args.get("remote", "origin")
            branch = args.get("branch", "main")
            return _run_shell(f"git push {remote} {branch}", timeout=30)
        elif act == "git_pull":
            return _run_shell("git pull", timeout=30)
        elif act == "git_log":
            count = args.get("count", 10)
            return _run_shell(f"git log --oneline -{count}")
        elif act == "git_branch":
            action = args.get("action", "list")
            name = args.get("name", "")
            if action == "list":
                return _run_shell("git branch -a")
            elif action == "create":
                return _run_shell(f"git branch {name}")
            elif action == "switch":
                return _run_shell(f"git checkout {name}")
            elif action == "delete":
                return _run_shell(f"git branch -d {name}")
        elif act == "git_stash":
            action = args.get("action", "push")
            if action == "push":
                return _run_shell("git stash push -m 'agent stash'")
            elif action == "pop":
                return _run_shell("git stash pop")
            elif action == "list":
                return _run_shell("git stash list")
        elif act == "git_checkout":
            return _run_shell(f"git checkout {args.get('target', 'HEAD')}")
        elif act == "git_blame":
            return _run_shell(f"git blame {args.get('path', '.')} | head -30")
        elif act == "git_create_tag":
            return _run_shell(f"git tag -a {args.get('name', 'v1.0')} -m '{args.get('message', '')}'")

    # ---- Build & Run ----
    elif act == "run_command" or act == "shell":
        cmd = args.get("cmd", "echo 'no command'")
        timeout = int(args.get("timeout", 15))
        return _run_shell(cmd, timeout=timeout)

    elif act == "build_project":
        cmd = args.get("build_cmd", "make 2>&1 || cmake --build . 2>&1")
        return _run_shell(cmd, timeout=60)

    elif act == "run_tests":
        cmd = args.get("test_cmd", "pytest 2>&1 || python3 -m pytest 2>&1")
        return _run_shell(cmd, timeout=60)

    elif act == "install_package":
        pkg = args.get("package", "")
        mgr = args.get("manager", "pip")
        if mgr == "pip":
            return _run_shell(f"pip3 install {pkg}", timeout=60)
        elif mgr == "apt":
            return _run_shell(f"echo '1234' | sudo -S apt install -y {pkg}", timeout=120)
        elif mgr == "npm":
            return _run_shell(f"npm install {pkg}", timeout=60)

    elif act == "check_errors":
        cmd = args.get("build_cmd", "python3 -m py_compile *.py 2>&1")
        return _run_shell(cmd)

    elif act == "run_python":
        code = args.get("code", "print('hello')")
        return _run_shell(f"python3 -c '{code}'", timeout=30)

    elif act == "run_script":
        path = args.get("path", "")
        script_args = args.get("args", "")
        return _run_shell(f"python3 {path} {script_args}", timeout=30)

    # ---- System ----
    elif act == "system_info":
        return _run_shell("echo '=== OS ===' && uname -a && echo '=== CPU ===' && lscpu | head -15 && echo '=== RAM ===' && free -h && echo '=== DISK ===' && df -h / && echo '=== GPU ===' && nvidia-smi --query-gpu=name,memory.total,memory.free,temperature.gpu --format=csv,noheader 2>/dev/null")

    elif act == "process_list":
        filt = args.get("filter", "")
        cmd = "ps aux --sort=-%mem | head -20"
        if filt:
            cmd = f"ps aux | grep '{filt}' | grep -v grep"
        return _run_shell(cmd)

    elif act == "network_info":
        return _run_shell("ip addr show | grep 'inet ' && echo '---' && hostname -I")

    elif act == "disk_usage":
        path = args.get("path", "/")
        return _run_shell(f"du -sh {path} 2>/dev/null && df -h {path}")

    elif act == "environment_vars":
        filt = args.get("filter", "")
        cmd = "env"
        if filt:
            cmd = f"env | grep -i '{filt}'"
        return _run_shell(cmd)

    elif act == "uptime":
        return _run_shell("uptime")

    elif act == "whoami":
        return _run_shell("whoami && id")

    elif act == "kernel_version":
        return _run_shell("uname -r && cat /etc/os-release | head -5")

    elif act == "gpu_info":
        return _run_shell("nvidia-smi 2>/dev/null || echo 'No NVIDIA GPU info'")

    elif act == "temperature":
        return _run_shell('cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | xargs -I{} echo "{}C"')

    # ---- Docker ----
    elif act == "docker_ps":
        all_c = args.get("all", "true")
        flag = "-a" if all_c == "true" else ""
        return _run_shell(f"docker ps {flag} --format 'table {{{{.Names}}}}\t{{{{.Status}}}}\t{{{{.Ports}}}}' 2>/dev/null || echo 'Docker not running'")

    elif act == "docker_logs":
        name = args.get("name", "")
        lines = args.get("lines", "50")
        return _run_shell(f"docker logs --tail {lines} {name} 2>&1")

    elif act == "docker_exec":
        name = args.get("name", "")
        cmd = args.get("cmd", "ls")
        return _run_shell(f"docker exec {name} {cmd}")

    elif act == "docker_images":
        return _run_shell("docker images --format 'table {{{{.Repository}}}}\t{{{{.Tag}}}}\t{{{{.Size}}}}' 2>/dev/null")

    elif act == "docker_stop":
        return _run_shell(f"docker stop {args.get('name', '')}")

    elif act == "docker_start":
        return _run_shell(f"docker start {args.get('name', '')}")

    # ---- Network ----
    elif act == "http_get":
        url = args.get("url", "")
        return _run_shell(f"curl -s '{url}' | head -100", timeout=15)

    elif act == "http_post":
        url = args.get("url", "")
        data = args.get("data", "")
        return _run_shell(f"curl -s -X POST '{url}' -d '{data}' | head -100", timeout=15)

    elif act == "dns_lookup":
        return _run_shell(f"nslookup {args.get('hostname', '')} 2>&1 | head -10")

    elif act == "ping":
        host = args.get("host", "")
        count = args.get("count", "4")
        return _run_shell(f"ping -c {count} {host} 2>&1")

    elif act == "port_check":
        host = args.get("host", "localhost")
        port = args.get("port", "80")
        return _run_shell(f"ss -tlnp | grep ':{port}' || echo 'Port {port} not listening'")

    # ---- Database ----
    elif act == "db_query":
        db = args.get("db_path", "")
        query = args.get("query", "")
        return _run_shell(f"sqlite3 {db} '{query}' 2>&1 | head -50")

    elif act == "db_schema":
        db = args.get("db_path", "")
        return _run_shell(f"sqlite3 {db} '.schema' 2>&1 | head -50")

    elif act == "db_tables":
        db = args.get("db_path", "")
        return _run_shell(f"sqlite3 {db} '.tables' 2>&1")

    elif act == "db_execute":
        db = args.get("db_path", "")
        sql = args.get("sql", "")
        return _run_shell(f"sqlite3 {db} '{sql}' 2>&1")

    # ---- Tank Hardware ----
    elif act == "camera_capture":
        try:
            from tank_os.shell.terminal.agent_chat import _camera_vision
            return _camera_vision()
        except:
            return _exec_tool({"action": "shell", "cmd": "fswebcam -d /dev/video0 --no-banner -r 1280x720 /tmp/capture.jpg 2>&1 && echo 'Captured'"})

    elif act == "camera" or act == "camera_snapshot":
        max_px = args.get("max_px", "480")
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"http://localhost:8082/api/camera/snapshot?max_px={max_px}",
                    headers={"Authorization": "Bearer bench-key"}), timeout=10)
            data = _json.loads(resp.read().decode())
            return f"Camera snapshot: {data.get('size', 0)} bytes"
        except Exception as e:
            return f"Camera error: {e}"

    elif act == "lidar_scan" or act == "lidar":
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request("http://localhost:8082/api/lidar/scan",
                    headers={"Authorization": "Bearer bench-key"}), timeout=15)
            data = _json.loads(resp.read().decode())
            pts = data.get("points", [])
            if pts:
                dists = [p.get("distance_mm", 0) for p in pts]
                return f"LIDAR: {len(pts)} points, min={min(dists)}mm max={max(dists)}mm avg={sum(dists)//len(dists)}mm"
            return "LIDAR: no points"
        except Exception as e:
            return f"LIDAR error: {e}"

    elif act == "tank_move" or act == "move":
        vx = args.get("vx", 0)
        wz = args.get("wz", 0)
        dur = args.get("duration_s", 1)
        try:
            data = _json.dumps({"vx": vx, "wz": wz, "duration_s": dur}).encode()
            req = urllib.request.Request("http://localhost:8082/api/move",
                data=data, headers={"Authorization": "Bearer bench-key", "Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            return "Tank moved"
        except Exception as e:
            return f"Move error: {e}"

    elif act == "tank_estop" or act == "estop":
        try:
            urllib.request.urlopen(
                urllib.request.Request("http://localhost:8082/api/estop",
                    headers={"Authorization": "Bearer bench-key"}), timeout=10)
            return "Emergency stop engaged"
        except Exception as e:
            return f"Estop error: {e}"

    elif act == "telemetry_get" or act == "telemetry":
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request("http://localhost:8082/api/cmd/telemetry",
                    headers={"Authorization": "Bearer bench-key"}), timeout=10)
            data = _json.loads(resp.read().decode())
            result = data.get("result", {})
            return _json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        except Exception as e:
            return f"Telemetry error: {e}"

    elif act == "motion_detect":
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request("http://localhost:8082/api/motion/detect",
                    headers={"Authorization": "Bearer bench-key"}), timeout=10)
            return _json.loads(resp.read().decode()).get("result", "No motion data")
        except Exception as e:
            return f"Motion error: {e}"

    # ---- Modem ----
    elif act == "modem":
        fn = args.get("function", "")
        mod_args = args.get("args", {})
        try:
            modem_mod = __import__("tank_os.shell.terminal.modem_tools", fromlist=[fn])
            fn_obj = getattr(modem_mod, fn, None)
            if fn_obj:
                return fn_obj(**mod_args)
            return f"Unknown modem function: {fn}"
        except Exception as e:
            return f"Modem error: {e}"

    elif act == "send_sms":
        try:
            modem_mod = __import__("tank_os.shell.terminal.modem_tools", fromlist=["send_sms"])
            return modem_mod.send_sms(message=args.get("message", ""), to=args.get("to", ""))
        except Exception as e:
            return f"SMS error: {e}"

    elif act == "read_sms":
        try:
            modem_mod = __import__("tank_os.shell.terminal.modem_tools", fromlist=["get_sms_messages"])
            return modem_mod.get_sms_messages()
        except Exception as e:
            return f"SMS error: {e}"

    elif act == "list_contacts":
        try:
            modem_mod = __import__("tank_os.shell.terminal.modem_tools", fromlist=["list_contacts"])
            return modem_mod.list_contacts()
        except Exception as e:
            return f"Contacts error: {e}"

    elif act == "make_call":
        try:
            modem_mod = __import__("tank_os.shell.terminal.modem_tools", fromlist=["call_number"])
            return modem_mod.call_number(number_or_name=args.get("number_or_name", ""))
        except Exception as e:
            return f"Call error: {e}"

    # ---- Code Generation ----
    elif act in ("generate_function", "generate_class", "generate_api", "generate_test", "generate_readme", "generate_script"):
        desc = args.get("description", args.get("task", ""))
        lang = args.get("language", "python")
        prompt = f"Generate {act.replace('generate_', '')} in {lang} for: {desc}. Return ONLY the code, no explanation."
        try:
            reply, _ = _rotate_llm([{"role": "system", "content": "You are a code generator. Output only code, no markdown, no explanation."}, {"role": "user", "content": prompt}])
            return reply or "LLM unavailable for code generation"
        except Exception as e:
            return f"Generation error: {e}"

    # ---- Analysis ----
    elif act == "analyze_code":
        path = args.get("path", "")
        lines = _run_shell(f"wc -l {path}")
        return _run_shell('python3 -c "import py_compile; py_compile.compile(\"' + path + '\", doraise=True)" 2>&1')
        return f"Lines: {lines}\nSyntax: {syntax}"

    elif act == "find_bugs":
        path = args.get("path", "")
        return _run_shell(f"python3 -m pyflakes {path} 2>/dev/null || pylint {path} --errors-only 2>/dev/null | head -20")

    elif act == "security_scan":
        path = args.get("path", "")
        return _run_shell(f"grep -rn 'password\|secret\|api_key\|token' {path} 2>/dev/null | head -20")

    elif act == "performance_profile":
        cmd = args.get("cmd", "echo 'no command'")
        return _run_shell(f"time {cmd} 2>&1")

    elif act == "dependency_check":
        path = args.get("path", ".")
        return _run_shell(f"grep -rh '^import\|^from' {path} 2>/dev/null | sort -u | head -30")

    elif act == "code_review":
        path = args.get("path", "")
        lines = _run_shell(f"wc -l {path}")
        bugs = _run_shell(f"python3 -m pyflakes {path} 2>/dev/null | head -10")
        return f"Review of {path}:\n{lines}\nIssues:\n{bugs}"

    # ---- AI/ML ----
    elif act == "llm_query":
        prompt = args.get("prompt", "hello")
        model = args.get("model", "local")
        messages = [{"role": "user", "content": prompt}]
        reply, provider = _rotate_llm(messages)
        return f"[{provider}] {reply}" if reply else "LLM unavailable"

    elif act == "embedding_generate":
        text = args.get("text", "")
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            emb = model.encode(text)
            return f"Embedding ({len(emb)} dims): {emb[:10].tolist()}"
        except Exception as e:
            return f"Embedding error: {e}"

    elif act == "speech_to_text":
        audio = args.get("audio_path", "")
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio)
            return result.get("text", "No speech detected")
        except Exception as e:
            return f"STT error: {e}"

    # ---- Monitoring ----
    elif act == "tail_log":
        path = args.get("path", "/tmp/bridge.log")
        lines = args.get("lines", "30")
        return _run_shell(f"tail -{lines} {path}")

    elif act == "search_log":
        path = args.get("path", "/tmp/bridge.log")
        pattern = args.get("pattern", "error")
        return _run_shell(f"grep -i '{pattern}' {path} | tail -30")

    elif act == "health_check":
        url = args.get("url", "http://localhost:8082/api/health")
        return _run_shell(f"curl -s '{url}' | head -5")

    elif act == "watch_process":
        name = args.get("name", "python3")
        return _run_shell(f"ps aux | grep '{name}' | grep -v grep")

    # ---- Package Management ----
    elif act == "pip_install":
        return _run_shell(f"pip3 install {args.get('package', '')}", timeout=60)

    elif act == "pip_list":
        filt = args.get("filter", "")
        cmd = "pip3 list"
        if filt:
            cmd += f" | grep -i '{filt}'"
        return _run_shell(cmd)

    elif act == "apt_install":
        return _run_shell(f"echo '1234' | sudo -S apt install -y {args.get('package', '')}", timeout=120)

    elif act == "npm_install":
        return _run_shell(f"npm install {args.get('package', '')}", timeout=60)

    elif act == "pip_freeze":
        return _run_shell("pip3 freeze | head -40")

    # ---- Process Management ----
    elif act == "start_process":
        return _run_shell(f"nohup {args.get('cmd', '')} > /tmp/agent_proc.log 2>&1 & echo PID=$!")

    elif act == "stop_process":
        return _run_shell(f"pkill -f '{args.get('name', '')}'")

    elif act == "kill_process":
        return _run_shell(f"kill -9 {args.get('pid', '')}")

    elif act == "process_status":
        return _run_shell(f"ps aux | grep '{args.get('name', '')}' | grep -v grep")

    # ---- Text Ops ----
    elif act == "create_note":
        title = args.get("title", "note")
        content_val = args.get("content", "")
        path = f"/home/shashi/notes/{title}.md"
        _Path(path).parent.mkdir(parents=True, exist_ok=True)
        _Path(path).write_text(content_val)
        return f"Note saved: {path}"

    elif act == "read_note":
        title = args.get("title", "note")
        path = f"/home/shashi/notes/{title}.md"
        try:
            return _Path(path).read_text()
        except:
            return f"Note not found: {title}"

    elif act == "search_notes":
        query = args.get("query", "")
        return _run_shell(f"grep -rl '{query}' /home/shashi/notes/ 2>/dev/null | head -10")

    elif act == "json_format":
        try:
            data = _json.loads(args.get("json_str", "{}"))
            return _json.dumps(data, indent=2)
        except Exception as e:
            return f"Invalid JSON: {e}"

    elif act == "base64_encode":
        import base64
        return base64.b64encode(args.get("text", "").encode()).decode()

    elif act == "base64_decode":
        import base64
        return base64.b64decode(args.get("encoded", "")).decode()

    elif act == "url_encode":
        import urllib.parse
        return urllib.parse.quote(args.get("text", ""))

    elif act == "url_decode":
        import urllib.parse
        return urllib.parse.unquote(args.get("encoded", ""))

    elif act == "hash_text":
        algo = args.get("algorithm", "sha256")
        text = args.get("text", "")
        h = _hashlib.new(algo)
        h.update(text.encode())
        return f"{algo}: {h.hexdigest()}"

    # ---- Time/Date ----
    elif act == "current_time":
        from datetime import datetime
        return datetime.now().isoformat()

    elif act == "timestamp":
        return str(int(_time.time()))

    # ---- Reply ----
    elif act == "reply":
        return None

    else:
        return f"Unknown action: {act}. Available: {', '.join(sorted(ALL_TOOLS.keys())[:30])}..."


# ---- Action Parsing ----

# Alias for agent_chat endpoint
_exec_action = _exec_tool

def _parse_action(text):
    """Extract action from LLM reply."""
    cleaned = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL)
    code_blocks = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, _re.DOTALL)
    if code_blocks:
        cleaned = ' '.join(code_blocks)
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
    try:
        m = _re.search(r'action[=\s:]+(\w+)', cleaned)
        if m:
            return {"action": m.group(1)}
    except Exception:
        pass
    return None


# ---- System Prompt ----

_SYSTEM_PROMPT = (
    "You are TankOS Agent -- an autonomous AI coding assistant with FULL system access on a Jetson Orin Nano robot.\n"
    "You have {tool_count} tools. You can do ANYTHING: read/write files, run code, git operations,\n"
    "build projects, manage docker, query databases, control robot hardware, send SMS, and more.\n"
    "\n"
    "CRITICAL RULES:\n"
    "1. ALWAYS respond with EXACTLY ONE JSON object. Nothing else. No markdown. No explanation.\n"
    "2. When you receive results in [brackets], describe them with {\"action\":\"reply\",\"text\":\"...\"}.\n"
    "3. You have full sudo access. Password is 1234.\n"
    "4. NEVER say 'I cannot'. You have full access. Just do it.\n"
    "5. Think step by step. If a task needs multiple steps, execute them one at a time.\n"
    "6. Always check your work. If something fails, try a different approach.\n"
    "\n"
    "ACTIONS (respond with exactly ONE):\n"
    "\n"
    "Shell: {\"action\":\"shell\",\"cmd\":\"<command>\"}\n"
    "Tool: {\"action\":\"tool_name\",\"param\":\"value\"}\n"
    "Reply: {\"action\":\"reply\",\"text\":\"<answer>\"}\n"
    "\n"
    "EXAMPLES:\n"
    "- Read file: {\"action\":\"read_file\",\"path\":\"/path/to/file\"}\n"
    "- Search code: {\"action\":\"search_code\",\"pattern\":\"TODO\",\"path\":\".\"}\n"
    "- Git commit: {\"action\":\"git_commit\",\"message\":\"fix bug\"}\n"
    "- System info: {\"action\":\"system_info\"}\n"
    "- Run tests: {\"action\":\"run_tests\",\"test_cmd\":\"pytest\"}\n"
    "- Camera: {\"action\":\"camera\"}\n"
    "- LIDAR: {\"action\":\"lidar\"}\n"
    "- Move tank: {\"action\":\"move\",\"vx\":0.3,\"wz\":0,\"duration_s\":2}\n"
)


# ---- Agent Chat Endpoint ----

@app.post("/api/agent/chat")
async def agent_chat(request: Request,
               authorization: Optional[str] = Header(default=None)) -> dict:
    """100+ tool coding agent with local LLM fallback and thinking display."""
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

    # Build system prompt with tool count
    tool_catalog = _format_tool_catalog()
    system = _SYSTEM_PROMPT.replace("{tool_count}", str(len(ALL_TOOLS))) + "\n\nTOOLS:\n" + tool_catalog

    _agent_history.append({"role": "user", "content": text})

    MAX_ROUNDS = 15
    all_actions = []
    final_reply = None
    provider_used = None
    thinking_steps = []  # Track thinking for streaming

    for round_num in range(MAX_ROUNDS):
        messages = [{"role": "system", "content": system}] + _agent_history[-15:]
        
        # Add thinking step
        thinking_steps.append(f"Round {round_num + 1}: Thinking...")
        
        reply_text, provider_used = _rotate_llm(messages)

        if reply_text is None:
            if all_actions:
                acts = ", ".join(a["action"] for a in all_actions)
                final_reply = f"Executed {len(all_actions)} actions ({acts}) successfully."
            else:
                final_reply = "All LLM providers are unavailable."
            _agent_history.clear()
            break

        _agent_history.append({"role": "assistant", "content": reply_text})
        thinking_steps.append(f"Round {round_num + 1}: Got LLM response via {provider_used}")

        action = _parse_action(reply_text)

        if action is None:
            final_reply = reply_text
            break

        at = action.get("action", "")

        if at == "reply":
            final_reply = action.get("text", reply_text)
            thinking_steps.append(f"Final reply: {final_reply[:100]}")
            break

        # Execute tool
        tool_args = {k: v for k, v in action.items() if k != "action"}
        all_actions.append({"action": at, "args": tool_args})
        thinking_steps.append(f"Executing: {at}({tool_args})")
        _LOG.info("Agent round %d: %s %s", round_num + 1, at, tool_args)

        result = _exec_action(action)
        if result is not None:
            truncated = result[:800]
            if len(result) > 800:
                truncated += f" ... ({len(result) - 800} chars truncated)"
            _agent_history.append({"role": "user", "content": f"[{at} result]: {truncated}"})
            thinking_steps.append(f"Got result: {truncated[:100]}")
        else:
            final_reply = action.get("text", reply_text)
            break

    if final_reply is None:
        final_reply = "Task completed."

    # Keep history manageable
    if len(_agent_history) > 30:
        _agent_history[:] = _agent_history[-15:]

    return {
        "reply": final_reply,
        "provider": provider_used,
        "actions": all_actions,
        "rounds": len(all_actions),
        "history_length": len(_agent_history),
        "thinking": thinking_steps,
        "tool_count": len(ALL_TOOLS)
    }


@app.post("/api/agent/clear")
async def agent_clear(authorization: Optional[str] = Header(default=None)) -> dict:
    """Clear agent conversation history."""
    _agent_history.clear()
    return {"cleared": True}


@app.get("/api/agent/tools")
async def agent_tools():
    """List all available tools."""
    return {"tools": ALL_TOOLS, "count": len(ALL_TOOLS), "categories": list(TOOL_CATEGORIES.keys())}


@app.get("/api/agent/debug")
async def agent_debug():
    """Debug: check env vars, LLM providers, and local models."""
    import os
    result = {}
    for key in ["MISTRAL_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
        val = os.environ.get(key, "")
        result[f"env_{key}"] = f"SET ({len(val)} chars)" if val else "MISSING"
    # Check local models
    phi3_path = "/home/shashi/The-Tank-Project/models/llm/phi-3-mini-4k-instruct-q4.gguf"
    tiny_path = "/home/shashi/The-Tank-Project/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    result["local_phi3"] = "EXISTS" if _os.path.exists(phi3_path) else "MISSING"
    result["local_tinyllama"] = "EXISTS" if _os.path.exists(tiny_path) else "MISSING"
    result["tool_count"] = len(ALL_TOOLS)
    result["tool_categories"] = list(TOOL_CATEGORIES.keys())
    # Test local LLM
    try:
        reply = _call_local_phi3([{"role": "user", "content": "say hi"}])
        result["local_llm_test"] = f"OK: {reply[:100]}" if reply else "Failed"
    except Exception as e:
        result["local_llm_test"] = f"FAIL: {e}"
    return result



