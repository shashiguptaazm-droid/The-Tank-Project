"""RAG bridge — recall from persistent memory + structured project knowledge.

Architecture
------------
1.  STT listener publishes /intent_text.
2.  The RAG node subscribes /intent_text and asks the persistent memory
    store (tank_memory) for top-k similar past events.
3.  It ALSO queries the structured coding-agent memory (tank_meta) for the
    most relevant code file, hardware component, and past decision that
    match keywords in the intent. This grounds the prompt in *project-
    specific* knowledge rather than only generic chat history.
4.  It forwards a single composite prompt on /assistant/context for the
    LLM node (or other downstream) to consume.

Note: the ROS /meta/* query publishers are best-effort and only used when
the local MetaStore handle indicates meta_node is up (i.e. the .db has
some rows). This avoids dead-letter-pile-ups on cold start.
"""
from __future__ import annotations

import json
import threading
from typing import List, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from tank_memory.memory_store import (
    InMemoryStore,
    SqliteVecStore,
    MemoryEvent,
    VECTOR_DIM,
)
from tank_meta.meta_store import MetaStore


QOS = 10
# Per-source and total context caps — keep LLM prompts bounded.
_MAX_CONTEXT_LINE_CHARS = 200
_MAX_CONTEXT_TOTAL_CHARS = 4 * 1024
# Tokens shorter than this are too generic for hardware lookups
# ("the", "and", "hey" all return the wrong component).
_HARDWARE_TOKEN_MIN_LEN = 4


class MemoryHalInterface:
    def recall(self, query_vec, top_k: int = 5) -> List[MemoryEvent]: ...
    def add(self, event) -> str: ...


class EmbeddingHalInterface:
    def encode(self, text: str): ...


class MetaHalInterface:
    """Read-only handle to the structured coding-agent memory store."""
    def search_code(self, query: str, top_k: int = 1): ...
    def find_hardware(self, component: str): ...
    def search_decisions(self, query: str, top_k: int = 1): ...
    def counts(self) -> dict: ...
    def close(self) -> None: ...


class StubEmbedding:
    """Identity embedding — collapses everything to the zero vector."""
    def encode(self, text: str):
        import numpy as np
        return np.zeros(VECTOR_DIM, dtype=np.float32)


class SentenceTransformerEmbedding:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def encode(self, text: str):
        import numpy as np
        v = self._model.encode([text], normalize_embeddings=True)[0]
        return np.asarray(v, dtype=np.float32)


def _clip(text: str, max_len: int = _MAX_CONTEXT_LINE_CHARS) -> str:
    s = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "\u2026"


def _cap(text: str, max_chars: int = _MAX_CONTEXT_TOTAL_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "\u2026[truncated]"


class RagNode(Node):
    def __init__(self, memory: Optional[MemoryHalInterface] = None,
                 embedder: Optional[EmbeddingHalInterface] = None,
                 meta: Optional[MetaHalInterface] = None) -> None:
        super().__init__("rag_node")
        self._declare_params()
        memory_provided = memory is not None
        if memory_provided:
            self._memory = memory
        else:
            try:
                self._memory = SqliteVecStore(
                    db_path=str(self.get_parameter("memory_db").value),
                    dim=VECTOR_DIM,
                )
                self.get_logger().info(
                    f"using sqlite-vec at {self.get_parameter('memory_db').value}"
                )
            except Exception as exc:
                self.get_logger().warn(
                    f"sqlite-vec unavailable ({exc}); using in-memory"
                )
                self._memory = InMemoryStore(dim=VECTOR_DIM)

        embedder_provided = embedder is not None
        self._embedder = embedder or SentenceTransformerEmbedding(
            str(self.get_parameter("embedding_model").value)
        )
        if not embedder_provided:
            self.get_logger().info(
                f"embedder: {self.get_parameter('embedding_model').value}"
            )
        self._top_k = int(self.get_parameter("top_k").value)

        meta_provided = meta is not None
        if meta_provided:
            self._meta = meta
        else:
            meta_db = str(self.get_parameter("meta_db").value)
            try:
                self._meta = MetaStore(db_path=meta_db)
                self.get_logger().info(
                    f"meta store open at {meta_db} counts={self._meta.counts()}"
                )
            except Exception as exc:
                self.get_logger().warn(
                    f"meta store open failed ({exc}); meta context disabled"
                )
                self._meta = None
        self._meta_top_k = int(self.get_parameter("meta_top_k").value)

        self._lock = threading.Lock()
        self.create_subscription(String, "/intent_text",
                                  self._on_intent, QOS)
        self._ctx_pub   = self.create_publisher(String, "/assistant/context", QOS)
        self._ass_pub   = self.create_publisher(String, "/assistant_text", QOS)

        # Best-effort cross-process meta queries. We only create the
        # publishers; we'll skip actual publishes when local meta hasn't
        # indexed anything yet (gate in _publish_ros_meta_queries).
        self._code_query_pub = self.create_publisher(
            String, "/meta/code_search", QOS)
        self._hw_query_pub = self.create_publisher(
            String, "/meta/hardware_lookup", QOS)
        self._dec_query_pub = self.create_publisher(
            String, "/meta/decision_search", QOS)
        self.create_subscription(
            String, "/meta/code_search_result",
            self._on_meta_code_result, QOS)
        self.create_subscription(
            String, "/meta/hardware_lookup_result",
            self._on_meta_hw_result, QOS)
        self.create_subscription(
            String, "/meta/decision_search_result",
            self._on_meta_dec_result, QOS)

        self._last_code_hits: List[dict] = []
        self._last_hw_hit: Optional[dict] = None
        self._last_dec_hits: List[dict] = []
        self.get_logger().info("rag_node initialised")

    # ----------------------- parameters -----------------------
    def _declare_params(self) -> None:
        self.declare_parameter("memory_db", "tank_ws/data/memory.db")
        self.declare_parameter("meta_db", "tank_ws/data/meta.db")
        self.declare_parameter("embedding_model", "all-MiniLM-L6-v2")
        self.declare_parameter("top_k", 5)
        self.declare_parameter("meta_top_k", 1)
        self.declare_parameter("temperature", 0.7)

    # ----------------------- intent handler -----------------------
    def _on_intent(self, msg: String) -> None:
        intent = (msg.data or "").strip()
        if not intent:
            return
        try:
            vec = self._embedder.encode(intent)
        except Exception as exc:
            self.get_logger().warn(f"embedding failed: {exc}")
            return
        with self._lock:
            try:
                hits = self._memory.recall(vec, top_k=self._top_k)
            except Exception as exc:
                self.get_logger().warn(f"recall failed: {exc}")
                hits = []
        try:
            self._memory.add(MemoryEvent(
                id="", ts=0.0, source="intent", text=intent, vec=vec,
                meta={"top_k": self._top_k},
            ))
        except Exception:
            pass

        meta_context = self._meta_context_block(intent)
        self._publish_ros_meta_queries(intent)  # best-effort, gated
        memory_context = self._render_context(hits)
        composite = _cap(
            f"{self.get_parameter('system_prompt_render').value or ''}\n\n"
            f"=== Structured project knowledge ===\n{meta_context}\n\n"
            f"=== Past relevant memory ===\n{memory_context}\n"
            f"=== Current user intent ===\n{intent}"
        )
        self._ctx_pub.publish(String(data=composite))
        self._ass_pub.publish(String(
            data=f"assistant/intent + memory + meta context (k={len(hits)})\n{composite}"
        ))

    # ----------------------- meta helpers -----------------------
    def _meta_healthy(self) -> bool:
        if self._meta is None:
            return False
        try:
            c = self._meta.counts()
        except Exception:
            return False
        return sum(int(v) for v in c.values()) > 0

    def _meta_context_block(self, intent: str) -> str:
        if self._meta is None:
            return "(structured knowledge disabled)"
        try:
            with self._lock:
                code_hits = self._meta.search_code(intent, top_k=self._meta_top_k)
                candidate = None
                for w in intent.lower().replace(",", " ").replace(".", " ").split():
                    if len(w) < _HARDWARE_TOKEN_MIN_LEN:
                        continue
                    h = self._meta.find_hardware(w)
                    if h is not None:
                        candidate = h
                        break
                hw_hit = candidate
                dec_hits = self._meta.search_decisions(intent, top_k=self._meta_top_k)
        except Exception as exc:
            self.get_logger().warn(f"meta query failed: {exc}")
            return "(structured knowledge query failed)"

        blocks: List[str] = []
        if code_hits:
            blocks.append("--- Relevant code ---")
            for c in code_hits[: self._meta_top_k]:
                blocks.append(
                    f"[{c.module}] {_clip(c.path)}\n"
                    f"  purpose: {_clip(c.purpose)}\n"
                    f"  functions: {_clip(', '.join(c.functions) or '-')}\n"
                    f"  deps: {_clip(', '.join(c.deps) or '-')}"
                )
        if hw_hit is not None:
            blocks.append(
                f"--- Hardware reference ---\n"
                f"{_clip(hw_hit.component)}: {_clip(hw_hit.kind)} "
                f"on {_clip(hw_hit.bus)} ({_clip(hw_hit.pin)})"
                + (f"\n  driver: {_clip(hw_hit.driver)}" if hw_hit.driver else "")
                + (f"\n  notes: {_clip(hw_hit.notes)}" if hw_hit.notes else "")
            )
        if dec_hits:
            blocks.append("--- Relevant past decisions ---")
            for d in dec_hits[: self._meta_top_k]:
                blocks.append(
                    f"[{d.id}] {_clip(d.problem)}\n"
                    f"  solution: {_clip(d.solution)}\n"
                    f"  result: {_clip(d.result)}"
                )
        return "\n".join(blocks) if blocks else "(no structured match)"

    def _publish_ros_meta_queries(self, intent: str) -> None:
        """Kick off cross-process meta queries ONLY when we have a healthy
        local MetaStore — this prevents dead-letter-pile-ups while meta_node
        is still booting. Each publish is best-effort; failures are warned
        once per ~20s so they don't bury the log."""
        if not self._meta_healthy():
            return
        for name, payload in (
            ("code",       {"query": intent, "top_k": self._meta_top_k}),
            ("hardware",   {"component": next(
                                (w for w in intent.lower().split()
                                 if len(w) >= _HARDWARE_TOKEN_MIN_LEN),
                                "")}),
            ("decision",   {"query": intent, "top_k": self._meta_top_k}),
        ):
            try:
                pub = getattr(self, f"_{name}_query_pub", None)
                if pub is None:
                    continue
                pub.publish(String(data=json.dumps(payload)))
            except Exception as exc:
                # throttled warn — at most one per ~20s
                now = self.get_clock().now().nanoseconds
                last = getattr(self, f"_last_pub_warn_{name}", 0)
                if (now - last) > 20_000_000_000:  # 20 s
                    self.get_logger().warn(
                        f"meta publish /meta/{name}_search failed: {exc}"
                    )
                    setattr(self, f"_last_pub_warn_{name}", now)

    def _on_meta_code_result(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        with self._lock:
            self._last_code_hits = list(payload.get("hits", []))

    def _on_meta_hw_result(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        with self._lock:
            self._last_hw_hit = payload.get("hit")

    def _on_meta_dec_result(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            return
        with self._lock:
            self._last_dec_hits = list(payload.get("hits", []))

    # ----------------------- render -----------------------
    @staticmethod
    def _render_context(hits: List[MemoryEvent]) -> str:
        if not hits:
            return "(no relevant past events)"
        blocks = []
        for ev in hits:
            blocks.append(
                f"[ts={ev.ts:.3f} src={ev.source}] {_clip(ev.text)}"
            )
        joined = "\n".join(blocks)
        return _cap(joined, max_chars=_MAX_CONTEXT_TOTAL_CHARS // 2)

    def destroy_node(self) -> None:
        try:
            if self._meta is not None:
                self._meta.close()
        finally:
            super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RagNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
