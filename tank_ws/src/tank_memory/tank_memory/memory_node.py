"""ROS2 node wrapping the persistent-memory store.

Topic-only interface (no custom ``.srv`` types needed; pure JSON over
``std_msgs/String`` keeps the package ``ament_python``-only and avoids
spinning up an ``ament_cmake`` companion).

Subscribes
    /memory/event       std_msgs/String   JSON  {"source":..., "text":..., "meta":{...}}
    /memory/query       std_msgs/String   JSON  {"query":..., "top_k":5, "request_id":"..."}
    /memory/compact_cmd std_msgs/String   JSON  {"max_events":10000}
    /memory/export_cmd  std_msgs/String   JSON  {"path":"..."}

Publishes
    /memory/recall_result    std_msgs/String  JSON list of hits
    /memory/recent_snapshot   std_msgs/String  JSON list (publishes every ``snapshot_period_sec``)
    /memory/compact_result   std_msgs/String  JSON {"removed":N}
    /memory/status            std_msgs/String  JSON {"count": N, "vec_ext":true,false}
    /memory/added             std_msgs/String  JSON {"id":"..."}  (debug-firehose)

Parameters
    db_path            str   default "tank_ws/data/memory.db"
    embedding_model    str   default "all-MiniLM-L6-v2"  (sentence-transformers)
    snapshot_period_sec float default 30.0
    auto_compact_events int   default 10000   (0 = disabled)
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from .memory_store import (
    DEFAULT_MAX_EVENTS,
    InMemoryStore,
    MemoryEvent,
    SqliteVecStore,
    VECTOR_DIM,
)

QOS = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)


class EmbeddingModelInterface:
    def encode(self, text: str) -> np.ndarray: ...
    def close(self) -> None: ...


class SentenceTransformerEmbedding:
    """Lazy wrapper around sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:
        v = self._model.encode([text], normalize_embeddings=True)[0]
        return np.asarray(v, dtype=np.float32)

    def close(self) -> None:
        try:
            del self._model
        except Exception:
            pass


class IdentityEmbedding:
    """For tests — collapses all events to the same zero vector."""
    def encode(self, text: str) -> np.ndarray:
        return np.zeros(VECTOR_DIM, dtype=np.float32)
    def close(self) -> None: pass


class MemoryNode(Node):
    def __init__(
        self,
        store: Optional[object] = None,
        embedder: Optional[EmbeddingModelInterface] = None,
    ) -> None:
        super().__init__("memory_node")
        self._declare_params()
        db_path = str(self.get_parameter("db_path").value)
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        store_provided = store is not None
        if store_provided:
            self._store = store
        else:
            try:
                self._store = SqliteVecStore(db_path=db_path, dim=VECTOR_DIM)
                self.get_logger().info(
                    f"using sqlite-vec at {db_path} "
                    f"(extension loaded={self._store._has_vec})"
                )
            except Exception as exc:
                self.get_logger().warn(
                    f"sqlite-vec unavailable ({exc}); falling back to InMemoryStore"
                )
                self._store = InMemoryStore(dim=VECTOR_DIM)

        embedder_provided = embedder is not None
        self._embedder = embedder or SentenceTransformerEmbedding(
            str(self.get_parameter("embedding_model").value)
        )
        if not embedder_provided:
            self.get_logger().info(
                f"embedding model: {self.get_parameter('embedding_model').value}"
            )
        self._lock = threading.Lock()

        # MutuallyExclusiveCallbackGroup so embedding work doesn't starve
        # wake_word or audio_common callbacks running in parallel.
        cbg = MutuallyExclusiveCallbackGroup()
        self.create_subscription(
            String, "/memory/event", self._on_event,  QOS, callback_group=cbg)
        self.create_subscription(
            String, "/memory/query", self._on_query,  QOS, callback_group=cbg)
        self.create_subscription(
            String, "/memory/compact_cmd",
            self._on_compact_cmd, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/memory/export_cmd",
            self._on_export_cmd, QOS, callback_group=cbg)
        self._recall_pub = self.create_publisher(
            String, "/memory/recall_result", QOS)
        self._recent_pub = self.create_publisher(
            String, "/memory/recent_snapshot", QOS)
        self._compact_pub = self.create_publisher(
            String, "/memory/compact_result", QOS)
        self._status_pub = self.create_publisher(
            String, "/memory/status", QOS)

        snap_sec = max(1.0, float(self.get_parameter("snapshot_period_sec").value))
        self._snap_timer = self.create_timer(snap_sec, self._publish_recent)
        # Optional auto-compaction
        cap = int(self.get_parameter("auto_compact_events").value)
        if cap > 0:
            self._auto_timer = self.create_timer(
                max(60.0, snap_sec * 5), self._auto_compact_tick
            )
        self.get_logger().info("memory_node initialised")

    # --------------------- parameters ---------------------
    def _declare_params(self) -> None:
        self.declare_parameter("db_path", "tank_ws/data/memory.db")
        self.declare_parameter("embedding_model", "all-MiniLM-L6-v2")
        self.declare_parameter("snapshot_period_sec", 30.0)
        self.declare_parameter("auto_compact_events", DEFAULT_MAX_EVENTS)

    # --------------------- subscriptions -------------------
    def _on_event(self, msg: String) -> None:
        try:
            data = json.loads(msg.data)
        except Exception as exc:
            self.get_logger().warn(f"event JSON parse: {exc}")
            return
        text = str(data.get("text", ""))
        if not text:
            self.get_logger().warn("event missing 'text'")
            return
        try:
            vec = self._embedder.encode(text)
        except Exception as exc:
            self.get_logger().warn(f"embedding failed: {exc}")
            return
        ev = MemoryEvent(
            id="",
            ts=float(data.get("ts", time.time())),
            source=str(data.get("source", "unknown")),
            text=text,
            vec=vec,
            meta=dict(data.get("meta") or {}),
        )
        with self._lock:
            ev_id = self._store.add(ev)
        self.get_logger().info(
            f"memory <- id={ev_id} src={ev.source} ({len(text)} chars)"
        )

    def _on_query(self, msg: String) -> None:
        try:
            req = json.loads(msg.data)
        except Exception as exc:
            self.get_logger().warn(f"query JSON parse: {exc}")
            return
        text = str(req.get("query", ""))
        if not text:
            self.get_logger().warn("query missing 'query'")
            return
        try:
            vec = self._embedder.encode(text)
        except Exception as exc:
            self.get_logger().warn(f"embedding (query) failed: {exc}")
            return
        top_k = int(req.get("top_k", 5))
        with self._lock:
            hits = self._store.recall(vec, top_k=top_k)
        result = {
            "request_id": req.get("request_id", ""),
            "query": text,
            "top_k": top_k,
            "hits": [h.to_dict() for h in hits],
        }
        self._recall_pub.publish(String(data=json.dumps(result)))

    def _on_compact_cmd(self, msg: String) -> None:
        try:
            req = json.loads(msg.data)
        except Exception:
            req = {}
        max_events = int(req.get("max_events", DEFAULT_MAX_EVENTS))
        with self._lock:
            removed = self._store.compact(max_events=max_events)
        self._compact_pub.publish(String(data=json.dumps({
            "max_events": max_events, "removed": removed,
        })))

    def _on_export_cmd(self, msg: String) -> None:
        try:
            req = json.loads(msg.data)
        except Exception:
            req = {}
        path = str(req.get("path", ""))
        if not path:
            self.get_logger().warn("export missing 'path'")
            return
        try:
            n = self._export_jsonl(path)
        except Exception as exc:
            self.get_logger().warn(f"export failed: {exc}")
            return
        self.get_logger().info(f"exported {n} events to {path}")

    # --------------------- timers --------------------------
    def _publish_recent(self) -> None:
        with self._lock:
            events = self._store.recent(n=20)
        payload = {
            "count": self._store.count(),
            "events": [e.to_dict() for e in events],
        }
        self._recent_pub.publish(String(data=json.dumps(payload)))

    def _auto_compact_tick(self) -> None:
        cap = int(self.get_parameter("auto_compact_events").value)
        if cap <= 0:
            return
        with self._lock:
            removed = self._store.compact(max_events=cap)
        if removed > 0:
            self.get_logger().info(
                f"auto-compact dropped {removed} events (cap={cap})"
            )

    # --------------------- helpers ------------------------
    def _export_jsonl(self, path: str) -> int:
        with self._lock:
            events = self._store.recent(n=max(self._store.count(), 1))
        # That's "all of them in reverse ts order", since recent() returns
        # everything when count < n. We re-fetch all events via SQLiteScan
        # to get correct order.
        # Cheap fallback: re-use the recent path. For >20 entries we still
        # want a deterministic export so we use roll-your-own serialize:
        with self._lock:
            # SqliteVecStore exposes the same .recent() — to get *all* rows
            # we call recent() with n == count.
            all_events = self._store.recent(n=max(self._store.count(), 1))
        with open(path, "w") as fh:
            for ev in all_events:
                fh.write(json.dumps({
                    "id":     ev.id,
                    "ts":     ev.ts,
                    "source": ev.source,
                    "text":   ev.text,
                    "meta":   ev.meta,
                }) + "\n")
        return len(all_events)


def _make_default_arguments():
    return None, None


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MemoryNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._embedder.close()
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
