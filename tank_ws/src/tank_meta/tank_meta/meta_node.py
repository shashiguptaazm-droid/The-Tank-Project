"""ROS2 node wrapping :class:`tank_meta.meta_store.MetaStore`.

Pure-Python package, so we keep JSON over ``std_msgs/String`` instead of
defining custom ``.srv``. The on-the-wire shape for every request::

    {"request_id": "<uuid>",
     "query":      "<text>",     # for code/decisions/knowledge
     "component":  "<name>",     # for hardware_lookup
     "top_k":      5}

Subscribes
    /meta/code_search       std_msgs/String JSON
    /meta/hardware_lookup   std_msgs/String JSON  {"component":"..."}
    /meta/decision_search   std_msgs/String JSON
    /meta/knowledge_query   std_msgs/String JSON
    /meta/index_now         std_msgs/String JSON  (triggers reindex)
    /meta/decision_append   std_msgs/String JSON  {"id":"DEC-00X", ...}

Publishes
    /meta/code_search_result        std_msgs/String JSON
    /meta/hardware_lookup_result    std_msgs/String JSON
    /meta/decision_search_result    std_msgs/String JSON
    /meta/knowledge_query_result    std_msgs/String JSON
    /meta/status                    std_msgs/String JSON {"counts":{...},"mtime":...}
    /meta/decision_append_result    std_msgs/String JSON {"id":"...", "persisted": true, "json_appended": true}

Parameters
    db_path             str   default "tank_ws/data/meta.db"
    workspace_root      str   default "<repo>/tank_ws"
    content_root        str   default "<repo>/tank_ws/src/tank_meta/content"
    docs_root           str   default "<repo>/docs"   (set "" to disable)
    auto_reindex_sec    float default 0.0             (0 = disabled)
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Optional

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from .code_indexer import index_directory as index_code_dir
from .decisions_indexer import append_decision, load_decisions_file
from .hardware_indexer import load_hardware_file
from .knowledge_indexer import index_directory as index_md_dir
from .meta_store import DecisionRow, MetaStore


QOS = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)

# Persisted decision IDs are kept deliberately short and stringy so they
# can't smuggle SQL/JSON/path injections through the JSON file. Pattern is
# enforced in `_on_decision_append` BEFORE any write step.
_DECISION_ID_PATTERN = re.compile(r"^[A-Z0-9_-]{2,32}$")


def _make_store_from_params(node: Node) -> MetaStore:
    db_path = str(node.get_parameter("db_path").value)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    return MetaStore(db_path=db_path)


class MetaNode(Node):
    def __init__(self, store: Optional[MetaStore] = None) -> None:
        super().__init__("meta_node")
        self._declare_params()
        self._store = store or _make_store_from_params(self)
        self._lock = threading.Lock()

        # Topics
        cbg = MutuallyExclusiveCallbackGroup()
        self.create_subscription(
            String, "/meta/code_search",
            self._on_code_search, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/meta/hardware_lookup",
            self._on_hw_lookup, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/meta/decision_search",
            self._on_decision_search, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/meta/knowledge_query",
            self._on_knowledge_query, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/meta/index_now",
            self._on_index_now, QOS, callback_group=cbg)
        self.create_subscription(
            String, "/meta/decision_append",
            self._on_decision_append, QOS, callback_group=cbg)

        self._code_pub = self.create_publisher(
            String, "/meta/code_search_result", QOS)
        self._hw_pub = self.create_publisher(
            String, "/meta/hardware_lookup_result", QOS)
        self._dec_pub = self.create_publisher(
            String, "/meta/decision_search_result", QOS)
        self._kn_pub = self.create_publisher(
            String, "/meta/knowledge_query_result", QOS)
        self._status_pub = self.create_publisher(
            String, "/meta/status", QOS)
        self._append_pub = self.create_publisher(
            String, "/meta/decision_append_result", QOS)

        # First-time index pass over content/ + workspace
        self._last_index_mtime: float = 0.0
        self._index_once()

        # Optional auto-reindex
        sec = float(self.get_parameter("auto_reindex_sec").value)
        if sec > 0:
            self.create_timer(sec, self._index_once)
            self.create_timer(max(5.0, sec / 2), self._publish_status)
        else:
            self.create_timer(30.0, self._publish_status)

        self.get_logger().info(
            f"meta_node ready — counts={self._store.counts()}"
        )

    def _declare_params(self) -> None:
        repo = "/root/the tank project"
        self.declare_parameter("db_path", f"{repo}/tank_ws/data/meta.db")
        self.declare_parameter("workspace_root", f"{repo}/tank_ws")
        self.declare_parameter("content_root", f"{repo}/tank_ws/src/tank_meta/content")
        self.declare_parameter("docs_root", f"{repo}/docs")
        self.declare_parameter("auto_reindex_sec", 0.0)

    # ---------------- indexer orchestrator --------------
    def _index_once(self) -> None:
        start_ts = time.time()
        content = str(self.get_parameter("content_root").value)
        workspace = str(self.get_parameter("workspace_root").value)
        docs = str(self.get_parameter("docs_root").value)

        n_hw = n_dec = n_know = 0
        try:
            hw_path = os.path.join(content, "hardware.json")
            n_hw = load_hardware_file(hw_path, self._store)
            dec_path = os.path.join(content, "decisions.json")
            n_dec = load_decisions_file(dec_path, self._store)
        except Exception as exc:
            self.get_logger().warn(f"content load failed: {exc}")

        if workspace and os.path.isdir(workspace):
            try:
                index_code_dir(workspace, self._store, verbose=False)
            except Exception as exc:
                self.get_logger().warn(f"code index failed: {exc}")

        if docs and os.path.isdir(docs):
            try:
                n_know = index_md_dir(docs, self._store, source_tag="docs", verbose=False)
            except Exception as exc:
                self.get_logger().warn(f"docs index failed: {exc}")

        self._last_index_mtime = time.time()
        self.get_logger().info(
            f"index pass: hw+={n_hw} dec+={n_dec} md+={n_know} "
            f"total={self._store.counts()} elapsed={time.time()-start_ts:.2f}s"
        )
        self._publish_status()

    def _meta_healthy(self) -> bool:
        """Cheap liveness probe — used by collaborators to gate publishing."""
        try:
            c = self._store.counts()
            return bool(c) and (
                c.get("code_files", 0) > 0 or
                c.get("hardware", 0) > 0 or
                c.get("decisions", 0) > 0
            )
        except Exception:
            return False

    # ---------------- subscriptions --------------------
    def _on_code_search(self, msg: String) -> None:
        req = self._safe_json(msg.data, require={"query"})
        if req is None:
            return
        top_k = int(req.get("top_k", 5))
        with self._lock:
            hits = self._store.search_code(req["query"], top_k=top_k)
        payload = {
            "request_id": req.get("request_id", ""),
            "query": req["query"], "top_k": top_k,
            "hits": [h.to_dict() for h in hits],
        }
        self._code_pub.publish(String(data=json.dumps(payload)))

    def _on_hw_lookup(self, msg: String) -> None:
        req = self._safe_json(msg.data, require={"component"})
        if req is None:
            return
        with self._lock:
            row = self._store.find_hardware(req["component"])
        payload = {
            "request_id": req.get("request_id", ""),
            "component": req["component"],
            "hit": (row.to_dict() if row else None),
        }
        self._hw_pub.publish(String(data=json.dumps(payload)))

    def _on_decision_search(self, msg: String) -> None:
        req = self._safe_json(msg.data, require={"query"})
        if req is None:
            return
        top_k = int(req.get("top_k", 5))
        with self._lock:
            hits = self._store.search_decisions(req["query"], top_k=top_k)
        payload = {
            "request_id": req.get("request_id", ""),
            "query": req["query"], "top_k": top_k,
            "hits": [h.to_dict() for h in hits],
        }
        self._dec_pub.publish(String(data=json.dumps(payload)))

    def _on_knowledge_query(self, msg: String) -> None:
        req = self._safe_json(msg.data, require={"query"})
        if req is None:
            return
        top_k = int(req.get("top_k", 5))
        with self._lock:
            hits = self._store.search_knowledge(req["query"], top_k=top_k)
        payload = {
            "request_id": req.get("request_id", ""),
            "query": req["query"], "top_k": top_k,
            "hits": hits,
        }
        self._kn_pub.publish(String(data=json.dumps(payload)))

    def _on_index_now(self, msg: String) -> None:
        self.get_logger().info("force reindex requested")
        try:
            self._index_once()
        except Exception as exc:
            self.get_logger().warn(f"reindex failed: {exc}")

    def _on_decision_append(self, msg: String) -> None:
        """Persist a new decision. Order is DB-first so a JSON write
        failure does NOT result in silent data loss on the next startup
        (which would otherwise overwrite the freshly-upserted row via
        ``INSERT OR REPLACE`` from JSON). JSON write is retried a few
        times with backoff before giving up.

        Payload shape::

            {
              "id":       "DEC-007",
              "problem":  "...",
              "reason":   "...",
              "solution": "...",
              "result":   "...",
              "ts":       1731550000.0   // optional
            }

        On success publishes a confirmation::

            {
              "id":            "DEC-007",
              "json_appended": true,
              "persisted":     true,
              "json_total":    7,
              "db_total":      7
            }
        """
        req = self._safe_json(msg.data, require={"id", "problem"})
        if req is None:
            self.get_logger().warn("decision_append missing 'id' or 'problem'")
            return
        decision_id = str(req["id"]).strip()
        if not _DECISION_ID_PATTERN.match(decision_id):
            self.get_logger().warn(
                f"decision_append rejected bad id: {decision_id!r} "
                f"(must match {_DECISION_ID_PATTERN.pattern})"
            )
            return
        try:
            row = DecisionRow(
                id=decision_id,
                ts=float(req.get("ts") or time.time()),
                problem=str(req.get("problem", ""))[:1000],
                reason=str(req.get("reason", ""))[:1000],
                solution=str(req.get("solution", ""))[:2000],
                result=str(req.get("result", ""))[:1000],
            )
        except Exception as exc:
            self.get_logger().warn(f"decision_append malformed: {exc}")
            return

        # DB first.
        db_ok = False
        try:
            with self._lock:
                self._store.upsert_decision(row)
            db_ok = True
        except Exception as exc:
            self.get_logger().warn(f"decision_append DB failed: {exc}")

        # JSON second, with bounded retry.
        json_total = 0
        json_ok = False
        if db_ok:
            content_root = str(self.get_parameter("content_root").value)
            decisions_json = os.path.join(content_root, "decisions.json")
            for attempt in range(3):
                try:
                    json_total = append_decision(decisions_json, row)
                    json_ok = True
                    break
                except Exception as exc:
                    self.get_logger().warn(
                        f"decision_append JSON retry {attempt+1}/3 failed: {exc}"
                    )
                    time.sleep(0.05 * (attempt + 1))

        db_total = self._store.counts().get("decisions", 0)
        payload = {
            "id":            row.id,
            "json_appended": json_ok,
            "persisted":     db_ok,
            "json_total":    json_total,
            "db_total":      db_total,
        }
        self._append_pub.publish(String(data=json.dumps(payload)))
        if db_ok:
            self.get_logger().info(
                f"decision appended id={row.id} "
                f"json_ok={json_ok} json_total={json_total} db_total={db_total}"
            )
        else:
            self.get_logger().error(
                f"decision_append FAILED id={row.id} (DB write did not succeed; "
                f"row not persisted)"
            )

    # ---------------- helpers --------------------------
    @staticmethod
    def _safe_json(raw: str, require: set) -> Optional[dict]:
        try:
            req = json.loads(raw)
        except Exception:
            return None
        for key in require:
            if not req.get(key):
                return None
        return req

    def _publish_status(self) -> None:
        self._status_pub.publish(String(data=json.dumps({
            "counts": self._store.counts(),
            "last_index": self._last_index_mtime,
        })))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MetaNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
