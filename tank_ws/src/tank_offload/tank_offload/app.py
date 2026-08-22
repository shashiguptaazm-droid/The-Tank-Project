"""FastAPI server for The Tank Project overflow-storage daemon.

Port ``8085`` (chosen to avoid collision with ``tank_dashboard:8080``,
``tank_command_bridge:8082``, ``serve_meta_api:8083``,
``tank_personalize:8084``).

Routes
------
Health + introspection
* ``GET  /api/health``                              — liveness check
* ``GET  /api/version``                             — package version

Offload
* ``GET  /api/offload/status``                      — % usage, state, queue, manifest counts
* ``GET  /api/offload/threshold``                   — current emergency threshold + recover threshold
* ``PUT  /api/offload/threshold``                   — patch one or both thresholds
* ``GET  /api/offload/history?limit=N``             — latest uploaded items
* ``GET  /api/offload/manifest``                    — every uploaded item (what is currently on VPS)
* ``GET  /api/offload/deadletter``                  — items that exhausted retries
* ``POST /api/offload/trigger``                     — immediately schedule a SWEEP
* ``POST /api/offload/trigger_emergency``           — bypass threshold + queue an emergency
* ``GET  /api/offload/dry_run``                     — what *would* be moved right now (no side-effects)
* ``GET  /api/offload/credentials``                 — redacted creds + missing-field list

Auth
----
Bearer-token auth (single shared ``TANK_API_KEY``). The same token
``tank_command_bridge`` and ``tank_personalize`` accept. Set
``TANK_OFFLOAD_OPEN=1`` to skip auth for first-boot benches.

Nextcloud credentials come from environment only:
    TANK_NEXTCLOUD_URL           https://<vps>/remote.php/dav/files/<user>
    TANK_NEXTCLOUD_USER          <user>
    TANK_NEXTCLOUD_PASSWORD      <nextcloud-app-password, NOT the main account pw>

Optional: ``TANK_OFFLOAD_CRYPT_PASSWORD`` to add a client-side
encryption overlay (rclone ``crypt`` remote). The password is never
logged in plaintext \u2014 only a ``sha256[:16]`` hash.

Notes
-----
* ``lifespan=`` (no deprecated ``@app.on_event``).
* SQLite + per-store ``threading.Lock`` already lives in
  :class:`OffloadStore`; we don't reopen the DB here.
* ROS spin runs an :class:`OffloadNode` in a
  ``MultiThreadedExecutor`` thread, exactly like tank_command_bridge.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import shutil
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

try:
    import rclpy                                            # noqa: F401
    from rclpy.executors import MultiThreadedExecutor
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
    MultiThreadedExecutor = object  # type: ignore[assignment,misc]
    rclpy = type("rclpy", (), {"ok": staticmethod(lambda: False),
                                "init": staticmethod(lambda: None),
                                "shutdown": staticmethod(lambda: None)})()

    class _StubString:
        def __init__(self, data: str = "") -> None:
            self.data = data
    String = _StubString  # type: ignore[assignment]

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .offload_store import (
    STATUS_DEAD_LETTER,
    STATUS_PENDING,
    STATUS_STAGING,
    STATUS_UPLOADED,
    OffloadStore,
)
from .offload_node import OffloadNode, ORDER_EMERGENCY, ORDER_SWEEP
from .policy import ALL_KINDS, OffloadPolicy, PolicyConfig
from .rclone_facade import RcloneConfig, RcloneFacade

# Logging \u2014 stderr so journal / docker log drivers can pick it up.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=__import__("sys").stderr,
)
_LOG = logging.getLogger("tank_offload.app")

__version__ = "0.1.0"

DEFAULT_PORT = 8085

DEFAULT_DATA_DIR = os.environ.get(
    "TANK_OFFLOAD_DATA",
    "/root/the tank project/tank_ws/data",
)
DEFAULT_DB_PATH = os.environ.get(
    "TANK_OFFLOAD_DB",
    os.path.join(DEFAULT_DATA_DIR, "offload_manifest.db"),
)
DEFAULT_WATCH_PATH = os.environ.get("TANK_OFFLOAD_WATCH_PATH", "/var/tank")
DEFAULT_STAGING_DIR = os.environ.get("TANK_OFFLOAD_STAGING_DIR",
                                      "/var/tank/offload_staging")
DEFAULT_DEADLETTER_DIR = os.environ.get("TANK_OFFLOAD_DEADLETTER_DIR",
                                         "/var/tank/offload_deadletter")
DEFAULT_THRESHOLD_PCT = float(os.environ.get("TANK_OFFLOAD_THRESHOLD_PCT",
                                              "85"))
DEFAULT_RECOVER_PCT = float(os.environ.get("TANK_OFFLOAD_RECOVER_PCT",
                                             "75"))
DEFAULT_WATCH_PERIOD = float(os.environ.get("TANK_OFFLOAD_PERIOD_SEC",
                                              "60"))


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #

def _password_hash(s: str) -> str:
    """Log-tag redaction helper \u2014 matches the rclone_facade style so
    the two layers produce identical tags."""
    if not s:
        return ""
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _load_keys() -> Dict[str, str]:
    """Same auth surface as tank_command_bridge / tank_personalize."""
    fallback = os.environ.get("TANK_API_KEY", "")
    raw = os.environ.get("TANK_API_KEYS")
    if raw:
        try:
            import json as _json
            data = _json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    if fallback:
        return {fallback: "admin"}
    return {}


_OPEN_MODE = bool(int(os.environ.get("TANK_OFFLOAD_OPEN", "0")))


def authenticate(request: Request) -> str:
    """Compare bearer via ``secrets.compare_digest``."""
    if _OPEN_MODE:
        return "open"
    keys = _load_keys()
    if not keys:
        raise HTTPException(
            status_code=503,
            detail="no TANK_API_KEY / TANK_API_KEYS configured on the server")
    header = request.headers.get("Authorization", "")
    if not header:
        raise HTTPException(
            status_code=401, detail="missing Authorization header")
    parts = header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="malformed Authorization header "
                   "(expected 'Bearer <token>')")
    token = parts[1].strip()
    for k in keys.keys():
        if secrets.compare_digest(k, token):
            return _password_hash(token)  # reuse tag helper
    raise HTTPException(status_code=401, detail="invalid API key")


# --------------------------------------------------------------------------- #
# RcloneConfig + OffloadStore + Policy singletons (lazy, lock-guarded)
# --------------------------------------------------------------------------- #

def _build_rclone_config() -> RcloneConfig:
    return RcloneConfig(
        nextcloud_url=os.environ.get("TANK_NEXTCLOUD_URL", ""),
        nextcloud_user=os.environ.get("TANK_NEXTCLOUD_USER", ""),
        nextcloud_password=os.environ.get("TANK_NEXTCLOUD_PASSWORD", ""),
        staging_dir=DEFAULT_STAGING_DIR,
        deadletter_dir=DEFAULT_DEADLETTER_DIR,
        crypt_remote_name=(
            "tankcrypt" if os.environ.get(
                "TANK_OFFLOAD_CRYPT_PASSWORD") else ""),
    )


_store: Optional[OffloadStore] = None
_rclone: Optional[RcloneFacade] = None
_policy: Optional[OffloadPolicy] = None
_singletons_lock = threading.Lock()

# Threshold state lives in a tiny mutable holder because we want
# ``OffloadNode`` to read it live on each tick. Threading.Lock so
# PUT /threshold doesn't race with the watcher.
class _Thresholds:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.threshold_pct = DEFAULT_THRESHOLD_PCT
        self.recover_pct = DEFAULT_RECOVER_PCT


_thresholds = _Thresholds()


def get_store() -> OffloadStore:
    global _store
    if _store is None:
        with _singletons_lock:
            if _store is None:
                _store = OffloadStore(DEFAULT_DB_PATH)
    return _store


def get_policy() -> OffloadPolicy:
    global _policy
    if _policy is None:
        with _singletons_lock:
            if _policy is None:
                _policy = OffloadPolicy(PolicyConfig())
    return _policy


def get_rclone() -> RcloneFacade:
    global _rclone
    if _rclone is None:
        with _singletons_lock:
            if _rclone is None:
                _rclone = RcloneFacade(_build_rclone_config())
    return _rclone


def _reset_singletons_for_tests(store: OffloadStore,
                                  policy: OffloadPolicy,
                                  facade: RcloneFacade) -> None:
    global _store, _policy, _rclone
    with _singletons_lock:
        _store = store
        _policy = policy
        _rclone = facade


# --------------------------------------------------------------------------- #
# ROS bridge thread
# --------------------------------------------------------------------------- #

class _OffloadBridge(Node):
    """A single ROS 2 node that wraps :class:`OffloadNode`."""

    def __init__(self) -> None:
        super().__init__("tank_offload_bridge")
        self._inner: OffloadNode = OffloadNode(
            store=get_store(),
            policy=get_policy(),
            facade=get_rclone(),
            watch_path=DEFAULT_WATCH_PATH,
            threshold_pct=_thresholds.threshold_pct,
            recover_pct=_thresholds.recover_pct,
            watch_period_sec=DEFAULT_WATCH_PERIOD,
        )
        self.get_logger().info("tank_offload_bridge initialised")

    def trigger(self, kind: str = ORDER_SWEEP) -> bool:
        try:
            if kind == ORDER_EMERGENCY:
                return self._inner.trigger_emergency()
            return self._inner.trigger_sweep()
        except Exception as exc:                              # pragma: no cover
            self.get_logger().warn(f"trigger failed: {exc}")
            return False

    def shutdown(self) -> None:
        try:
            self._inner.shutdown()
        except Exception:                                      # pragma: no cover
            pass


_bridge: Optional[_OffloadBridge] = None
_bridge_lock = threading.Lock()


def _ros_spin_thread() -> None:
    global _bridge
    try:
        if not rclpy.ok():
            rclpy.init()
        with _bridge_lock:
            _bridge = _OffloadBridge()
            executor = MultiThreadedExecutor(num_threads=4)
            executor.add_node(_bridge)
            executor.spin()
    except Exception as exc:
        _LOG.warning("ROS offload bridge thread failed to start: %s", exc)
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


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    if _RCLPY_AVAILABLE and os.environ.get("TANK_OFFLOAD_NO_ROS",
                                             "0") != "1":
        t = threading.Thread(target=_ros_spin_thread, daemon=True,
                              name="tank_offload_ros")
        t.start()
    try:
        yield
    finally:
        if _bridge is not None:
            try:
                _bridge.shutdown()
            except Exception:
                pass


app = FastAPI(
    title="The Tank Offload API",
    version=__version__,
    lifespan=lifespan,
    description=(
        "FastAPI over the tank_offload overflow-storage daemon."
    ),
)

# A flat alias for ``_bridge`` so non-ROS code paths can publish-stubs
# without importability concerns in tests.
get_bridge = lambda: _bridge  # noqa: E731


# --------------------------------------------------------------------------- #
# Routes \u2014 health
# --------------------------------------------------------------------------- #

@app.get("/api/health")
def health() -> Dict[str, Any]:
    cfg = get_rclone().config
    return {
        "ok": True,
        "version": __version__,
        "rclpy": _RCLPY_AVAILABLE,
        "open_mode": _OPEN_MODE,
        "credentialed": cfg.is_credentialed(),
        "watch_path": DEFAULT_WATCH_PATH,
        "threshold_pct": _thresholds.threshold_pct,
        "recover_pct": _thresholds.recover_pct,
    }


@app.get("/api/version")
def version() -> Dict[str, Any]:
    return {"version": __version__, "package": "tank_offload"}


# --------------------------------------------------------------------------- #
# Routes \u2014 status / threshold / history / manifest / deadletter
# --------------------------------------------------------------------------- #

@app.get("/api/offload/status")
def status(request: Request) -> Dict[str, Any]:
    authenticate(request)
    store = get_store()
    try:
        usage = shutil.disk_usage(DEFAULT_WATCH_PATH)
        pct = (usage.used / usage.total) * 100.0 if usage.total else 0.0
    except OSError as exc:
        pct = -1.0
        usage = None
    return {
        "watch_path": DEFAULT_WATCH_PATH,
        "usage_pct": round(pct, 2),
        "usage_used": getattr(usage, "used", None),
        "usage_total": getattr(usage, "total", None),
        "threshold_pct": _thresholds.threshold_pct,
        "recover_pct": _thresholds.recover_pct,
        "state": ("EMERGENCY" if pct >= _thresholds.threshold_pct
                  else "NORMAL"),
        "rclpy": _RCLPY_AVAILABLE,
        "bridge_alive": _bridge is not None,
        "manifest_counts": store.counts(),
        "total_uploaded_bytes": store.total_uploaded_bytes(),
        "oldest_uploaded_at": store.oldest_uploaded_at(),
        "ts": __import__("time").time(),
    }


@app.get("/api/offload/threshold")
def get_threshold(request: Request) -> Dict[str, Any]:
    authenticate(request)
    with _thresholds.lock:
        return {
            "threshold_pct": _thresholds.threshold_pct,
            "recover_pct": _thresholds.recover_pct,
        }


@app.put("/api/offload/threshold")
def put_threshold(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    authenticate(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422,
                            detail="payload must be a JSON object")
    with _thresholds.lock:
        if "threshold_pct" in payload:
            try:
                v = float(payload["threshold_pct"])
            except (TypeError, ValueError):
                raise HTTPException(422, detail="threshold_pct not numeric")
            if not (1.0 <= v <= 99.0):
                raise HTTPException(
                    422, detail="threshold_pct must be in [1, 99]")
            _thresholds.threshold_pct = v
        if "recover_pct" in payload:
            try:
                v = float(payload["recover_pct"])
            except (TypeError, ValueError):
                raise HTTPException(422, detail="recover_pct not numeric")
            if not (1.0 <= v <= 99.0):
                raise HTTPException(
                    422, detail="recover_pct must be in [1, 99]")
            _thresholds.recover_pct = v
        if _thresholds.recover_pct >= _thresholds.threshold_pct:
            raise HTTPException(
                422,
                detail="recover_pct must be strictly < threshold_pct")
        return {
            "threshold_pct": _thresholds.threshold_pct,
            "recover_pct": _thresholds.recover_pct,
        }


@app.get("/api/offload/history")
def offload_history(limit: int = 50, request: Request = None) -> Dict[str, Any]:  # type: ignore[assignment]
    authenticate(request)
    limit = max(1, min(int(limit), 500))
    store = get_store()
    uploads = store.list_uploads(limit=limit)
    deadletters = store.list_by_status(
        STATUS_DEAD_LETTER, limit=limit)
    return {
        "limit": limit,
        "uploads": [it.to_dict() for it in uploads],
        "deadletters": [it.to_dict() for it in deadletters],
        "uploads_count": len(uploads),
        "deadletter_count": len(deadletters),
    }


@app.get("/api/offload/manifest")
def offload_manifest(request: Request,
                       limit: int = 200) -> Dict[str, Any]:
    authenticate(request)
    store = get_store()
    limit = max(1, min(int(limit), 1000))
    items = store.list_by_status(STATUS_UPLOADED, limit=limit)
    return {
        "count": len(items),
        "items": [
            {
                "uuid": it.uuid,
                "original_path": it.original_path,
                "remote_path": it.remote_path,
                "size_bytes": it.size_bytes,
                "kind": it.kind,
                "uploaded_at": it.updated_at,
            } for it in items
        ],
    }


@app.get("/api/offload/deadletter")
def offload_deadletter(request: Request,
                         limit: int = 100) -> Dict[str, Any]:
    authenticate(request)
    store = get_store()
    limit = max(1, min(int(limit), 500))
    items = store.list_by_status(STATUS_DEAD_LETTER, limit=limit)
    return {"count": len(items),
            "items": [it.to_dict() for it in items]}


@app.post("/api/offload/trigger")
def trigger_sweep(request: Request) -> Dict[str, Any]:
    authenticate(request)
    if _bridge is None:
        # No ROS bridge thread (CI benches); simulate by walking the
        # policy ourselves so the endpoint always returns 200 with a
        # tangible count.
        return {"ok": False, "queued": 0,
                "note": "no ROS bridge thread; call policies via CLI"}
    return {"ok": bool(_bridge.trigger(ORDER_SWEEP)), "queued": 1,
            "kind": "SWEEP"}


@app.post("/api/offload/trigger_emergency")
def trigger_emergency(request: Request) -> Dict[str, Any]:
    authenticate(request)
    if _bridge is None:
        return {"ok": False, "queued": 0,
                "note": "no ROS bridge thread"}
    return {"ok": bool(_bridge.trigger(ORDER_EMERGENCY)),
            "queued": 1, "kind": "EMERGENCY"}


@app.get("/api/offload/dry_run")
def offload_dry_run(request: Request) -> Dict[str, Any]:
    authenticate(request)
    policy = get_policy()
    by_kind = policy.dry_run()
    return {
        "would_pick": {k: [c.as_dict() for c in cs]
                       for k, cs in by_kind.items()},
        "total_bytes": sum(c.size_bytes
                            for cs in by_kind.values() for c in cs),
        "total_files": sum(len(cs) for cs in by_kind.values()),
    }


@app.get("/api/offload/credentials")
def offload_credentials(request: Request) -> Dict[str, Any]:
    authenticate(request)
    cfg = get_rclone().config
    missing: List[str] = []
    if not cfg.nextcloud_url:
        missing.append("TANK_NEXTCLOUD_URL")
    if not cfg.nextcloud_user:
        missing.append("TANK_NEXTCLOUD_USER")
    if not cfg.nextcloud_password:
        missing.append("TANK_NEXTCLOUD_PASSWORD")
    return {
        "credentialed": cfg.is_credentialed(),
        "missing": missing,
        "redacted": cfg.redact(),
        "open_mode": _OPEN_MODE,
    }


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Run the tank_offload FastAPI server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-ros", action="store_true",
                        help="Skip ROS bridge thread (bench).")
    parser.add_argument("--open", action="store_true",
                        help="Disable bearer auth (TANK_OFFLOAD_OPEN=1).")
    args = parser.parse_args()

    if args.no_ros:
        os.environ["TANK_OFFLOAD_NO_ROS"] = "1"
    if args.open:
        os.environ["TANK_OFFLOAD_OPEN"] = "1"

    try:
        import uvicorn                                  # type: ignore[import-not-found]
    except ImportError:
        print("uvicorn not installed; pip install 'tank_offload[server]'",
              flush=True)
        return 2
    uvicorn.run("tank_offload.app:app",
                host=args.host, port=args.port,
                log_level="info")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
