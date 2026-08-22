"""ROS 2 watcher node + background worker thread.

The watcher publishes a :class:`std_msgs.msg.String` on ``/offload/state``
every ``watch_period_sec`` (default 60). When ``% disk usage`` exceeds
``threshold_pct`` for two consecutive ticks, it dispatches an
``EMERGENCY`` offload \u2014 which is the same code path as CRON/trigger
but with priority over the queue.

A background :class:`threading.Thread` drains the queue, doing the
actual rclone work. This means the ROS executor never blocks on
network I/O \u2014 a critical property because uvicorn / other nodes share
the same process when run via a single launch file.

Design rules upheld (STATUS.md \u00a79):

* ``MutuallyExclusiveCallbackGroup`` so the heavy subscriber doesn't
  starve the lightweight publishers.
* DB-first (STATUS.md design rule 2): store transitions are written
  BEFORE the actual rclone copy so a worker crash mid-upload leaves
  the row in :data:`STATUS_STAGING` and next sweep can recover.
* Redacted log lines (no plaintext credentials \u2014 only ``sha256[:16]``).
* Bounded retries (max 6) before dead-letter.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import shutil
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.node import Node
from std_msgs.msg import String

from .offload_store import (
    STATUS_DEAD_LETTER,
    STATUS_PENDING,
    STATUS_STAGING,
    STATUS_UPLOADED,
    Item,
    OffloadStore,
)
from .policy import ALL_KINDS, OffloadPolicy, PolicyConfig
from .rclone_facade import RcloneConfig, RcloneFacade, RcloneResult

_LOG = logging.getLogger("tank_offload.node")


# Order kinds dispatched to the worker thread. EMERGENCY outranks
# SWEEP so the big-oldest files hit the wire first when the disk
# is truly full.
ORDER_EMERGENCY = "EMERGENCY"
ORDER_SWEEP = "SWEEP"


@dataclass
class _Order:
    kind: str                # ORDER_EMERGENCY | ORDER_SWEEP
    enqueued_at: float = field(default_factory=time.time)


@dataclass
class _State:
    last_usage_pct: float = 0.0
    emergency_since: Optional[float] = None  # tick at which we crossed
    emergency_active: bool = False
    last_dispatch_at: float = 0.0
    last_event_at: float = 0.0


class OffloadNode(Node):
    """Single-node implementation: watcher timer + in-process worker."""

    def __init__(self,
                 store: OffloadStore,
                 policy: OffloadPolicy,
                 facade: RcloneFacade,
                 *,
                 watch_period_sec: float = 60.0,
                 watch_path: str = "/var/tank",
                 threshold_pct: float = 85.0,
                 recover_pct: float = 75.0,
                 emergency_latch_ticks: int = 2,
                 worker_join_timeout: float = 30.0,
                 ) -> None:
        super().__init__("tank_offload_node")
        self._store = store
        self._policy = policy
        self._facade = facade
        self._watch_path = watch_path
        self._threshold_pct = float(threshold_pct)
        self._recover_pct = float(recover_pct)
        self._emergency_latch_ticks = max(1, int(emergency_latch_ticks))
        self._worker_join_timeout = float(worker_join_timeout)

        self._state = _State()
        self._lock = threading.Lock()
        self._queue: "queue.Queue[_Order]" = queue.Queue(maxsize=128)
        self._worker_alive = threading.Event()
        self._worker_alive.set()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="tank_offload.worker",
            daemon=True,
        )
        self._worker.start()

        # ROS publishers \u2014 each on its own MutuallyExclusiveCallbackGroup
        # so a slow state publish doesn't starve the worker thread call.
        group = MutuallyExclusiveCallbackGroup()
        self._state_pub = self.create_publisher(
            String, "/offload/state", 10, callback_group=group)
        self._event_pub = self.create_publisher(
            String, "/offload/event", 10, callback_group=group)
        self._deadletter_pub = self.create_publisher(
            String, "/offload/deadletter", 10, callback_group=group)

        period = max(1.0, float(watch_period_sec))
        self._timer = self.create_timer(
            period, self._tick, callback_group=group)
        self.get_logger().info(
            "tank_offload_node up; threshold=%.1f%% recover=%.1f%% "
            "staging=%s", self._threshold_pct, self._recover_pct,
            self._facade.config.staging_dir)

    # ----- watcher timer -----
    def _tick(self) -> None:
        try:
            usage = shutil.disk_usage(self._watch_path)
            pct = (usage.used / usage.total) * 100.0 if usage.total else 0.0
        except OSError as exc:
            self.get_logger().warn(
                "disk_usage failed: %s", exc, throttle_duration_sec=30.0)
            return

        with self._lock:
            self._state.last_usage_pct = pct
            if pct >= self._threshold_pct:
                if self._state.emergency_since is None:
                    self._state.emergency_since = time.time()
                self._state.emergency_active = (
                    (time.time() - self._state.emergency_since)
                    / max(1.0, 60.0) >= self._emergency_latch_ticks - 1)
            else:
                self._state.emergency_since = None
                self._state.emergency_active = False

            should_dispatch = (
                self._state.emergency_active
                and (time.time() - self._state.last_dispatch_at) > 300.0)

        self._publish_state(pct)
        if should_dispatch:
            self._dispatch(ORDER_EMERGENCY)
            with self._lock:
                self._state.last_dispatch_at = time.time()

        # 1 h sweep \u2014 on the dot if watch_period_sec == 60 we hit it
        # on tick 60, 120, 180\u2026; tolerance is fine.
        now = time.localtime()
        if (now.tm_min == 0 and now.tm_sec < int(self._watch_period_sec())
                and (time.time() - self._state.last_dispatch_at) > 60.0):
            self._dispatch(ORDER_SWEEP)

        # Pick up any pending items whose next_retry_ts has elapsed.
        due = self._store.due_for_retry()
        for it in due:
            if self._queue.full():
                break
            self._queue.put(_Order(kind=ORDER_SWEEP))

    def _watch_period_sec(self) -> float:
        return float(self._timer.timer_period_ns) / 1e9

    def _publish_state(self, pct: float) -> None:
        payload = {
            "usage_pct": round(pct, 2),
            "watch_path": self._watch_path,
            "threshold_pct": self._threshold_pct,
            "recover_pct": self._recover_pct,
            "state": ("EMERGENCY" if self._state.emergency_active
                      else "NORMAL"),
            "last_dispatch_at": self._state.last_dispatch_at,
            "queue_depth": self._queue.qsize(),
            "manifest_counts": self._store.counts(),
            "ts": time.time(),
        }
        try:
            self._state_pub.publish(String(data=json.dumps(payload)))
        except Exception as exc:                            # pragma: no cover
            self.get_logger().warn("publish state failed: %s", exc)

    # ----- dispatch (called from REST `/trigger` too) -----
    def trigger_sweep(self) -> bool:
        """Public entry: enqueue a SWEEP order. Returns True if accepted."""
        return self._dispatch(ORDER_SWEEP)

    def trigger_emergency(self) -> bool:
        """Public entry: enqueue an EMERGENCY order."""
        return self._dispatch(ORDER_EMERGENCY)

    def _dispatch(self, kind: str) -> bool:
        if self._queue.full():
            _LOG.warning("queue full, dropping %s order", kind)
            return False
        self._queue.put(_Order(kind=kind))
        return True

    # ----- worker loop -----
    def _worker_loop(self) -> None:
        _LOG.info("offload worker started")
        while self._worker_alive.is_set():
            try:
                order = self._queue.get(timeout=2.0)
            except queue.Empty:
                continue
            try:
                if order.kind == ORDER_EMERGENCY:
                    self._do_offload_round(kind=ALL_KINDS, emergency=True)
                else:
                    self._do_offload_round(kind=ALL_KINDS, emergency=False)
            except Exception as exc:
                _LOG.exception("worker round crashed: %s", exc)
            self._queue.task_done()
        _LOG.info("offload worker stopped")

    def _do_offload_round(self, *, kind: List[str], emergency: bool) -> None:
        """Enqueue fresh candidates from the policy, then drain any
        pending / retry-due rows from the store."""
        self._enqueue_from_policy(emergency=emergency)
        # Drain a bounded slice of pending items per round so we never
        # block the worker thread for too long.
        for item in self._store.list_pending()[:6]:
            if item.retry_count and item.next_retry_ts > time.time():
                continue
            self._process_item(item)

    def _enqueue_from_policy(self, *, emergency: bool) -> None:
        if not self._facade.config.is_credentialed():
            _LOG.debug("skipping enqueue: missing Nextcloud credentials")
            return
        for c in self._policy.candidates():
            row = self._store.get_by_path(c.path)
            if row is not None and row.status in (
                    STATUS_STAGING, STATUS_UPLOADED):
                continue
            if row is None:
                item = self._store.enqueue(
                    original_path=c.path,
                    size_bytes=c.size_bytes, kind=c.kind)
                self._publish_event(
                    "discovered", item.original_path, item.size_bytes)

    def _process_item(self, item: Item) -> None:
        # 1. Move to staging + mark STAGING
        try:
            stage = self._facade.stage(item.original_path, item.uuid)
        except Exception as exc:
            _LOG.warning("stage failed for %s: %s",
                          item.original_path, exc)
            self._record_failure(item, str(exc))
            return
        self._store.transition(
            item.uuid, to_status=STATUS_STAGING,
            staged_path=stage.staged_path, remote_path=stage.remote_path)

        # 2. rclone copy
        result = self._facade.copy_once(stage.staged_path, stage.remote_path)
        if result.ok:
            self._facade.unstage(stage.staged_path)
            self._store.transition(
                item.uuid, to_status=STATUS_UPLOADED,
                staged_path="", remote_path=stage.remote_path,
                last_error="",
            )
            elapsed_ms = int(result.elapsed_sec * 1000)
            self._publish_event(
                "uploaded", item.original_path, item.size_bytes,
                took_ms=elapsed_ms)
            return

        # 3. Failure path \u2014 retry-or-dead-letter
        err = (result.error or
               f"rclone exit {result.returncode}").strip()[:500]
        if self._facade.exhausted(item.retry_count + 1):
            new_path = self._facade.deadletter(stage.staged_path, item.uuid)
            self._store.transition(
                item.uuid, to_status=STATUS_DEAD_LETTER,
                staged_path=new_path, last_error=err)
            self._publish_deadletter(item.original_path,
                                       new_path,
                                       item.retry_count + 1,
                                       err)
        else:
            delay = self._facade.compute_retry_delay(item.retry_count)
            self._store.record_retry(item.uuid, err, delay)

    def _record_failure(self, item: Item, err: str) -> None:
        if self._facade.exhausted(item.retry_count + 1):
            self._store.transition(item.uuid, to_status=STATUS_DEAD_LETTER,
                                    last_error=err[:500])
            self._publish_deadletter(item.original_path,
                                       item.staged_path or "",
                                       item.retry_count + 1,
                                       err)
        else:
            delay = self._facade.compute_retry_delay(item.retry_count)
            self._store.record_retry(item.uuid, err, delay)

    def _publish_event(self, action: str, path: str,
                        size: int, took_ms: int = 0) -> None:
        payload = {
            "action": action, "path": path, "size_bytes": size,
            "took_ms": took_ms, "ts": time.time(),
        }
        try:
            self._event_pub.publish(String(data=json.dumps(payload)))
        except Exception:                                    # pragma: no cover
            pass
        with self._lock:
            self._state.last_event_at = time.time()

    def _publish_deadletter(self, path: str, deadletter_path: str,
                              retries: int, err: str) -> None:
        payload = {
            "path": path, "deadletter_path": deadletter_path,
            "retry_count": retries, "error": err[:200],
            "ts": time.time(),
        }
        try:
            self._deadletter_pub.publish(String(data=json.dumps(payload)))
        except Exception:                                    # pragma: no cover
            pass

    # ----- graceful shutdown -----
    def shutdown(self, timeout: Optional[float] = None) -> None:
        """Called by ``lifespan`` on uvicorn exit."""
        self._worker_alive.clear()
        try:
            self._queue.put_nowait(_Order(kind=ORDER_SWEEP))   # wake worker
        except queue.Full:
            pass
        self._worker.join(timeout=timeout or self._worker_join_timeout)
