"""``tank_learn.feedback_node`` — bridge ROS topic traffic to :class:`FeedbackStore`.

Subscribes
~~~~~~~~~~
* ``/intent_command`` (``std_msgs/String`` JSON)
  Payload shape::

      {"cid": "play_music",
       "cmd": "voice.play_music",
       "params": {...},
       "slots": {...},
       "raw": "play some lo-fi music",
       "confidence": 0.92}

  On every message the node calls
  ``FeedbackStore.record_dispatch(raw, cmd, confidence, source="auto")``
  and remembers ``{plugin_name: last_dispatch_id}`` so a subsequent
  thumb-up/down can be matched when the dashboard only sends a plugin
  name.

* ``/os/feedback`` (``std_msgs/String`` JSON)
  Payload is one of three shapes (most → least specific)::

      {"dispatch_id": 42, "reward": +1, "source": "user", "note": "good"}
      {"plugin_name": "voice.play_music", "intent_text": "...",
       "reward": -1, "source": "user"}
      {"plugin_name": "voice.play_music", "reward": +1}

Publishes
~~~~~~~~~
* ``/os/feedback_audit`` — every recorded event as JSON.
* ``/os/iq_state``      — IQ rollups pushed by :mod:`tank_iq`.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from .feedback_store import FeedbackStore

try:
    import rclpy                                                 # noqa: F401
    from rclpy.node import Node
    from std_msgs.msg import String
    _RCLPY_AVAILABLE = True
except ImportError:
    # Stub mode — importers + tests can still load this module without
    # a ROS install.  Constructing the node raises clearly so the
    # operator knows what's missing.
    _RCLPY_AVAILABLE = False
    class _StubNode:                                            # type: ignore[no-redef]
        def __init__(self, *_a, **_k):
            raise ImportError(
                "rclpy is not installed; FeedbackNode requires ROS 2 Humble."
            )
    Node = _StubNode
    class _StubString:                                          # type: ignore[no-redef]
        def __init__(self, data: str = "") -> None:
            self.data = data
    String = _StubString


class FeedbackNode(Node):
    """Bridge ROS topic traffic to the SQLite-backed :class:`FeedbackStore`."""

    def __init__(self,
                 store: Optional[FeedbackStore] = None,
                 *, node_name: str = "tank_learn_feedback") -> None:
        super().__init__(node_name)
        self._store = store if store is not None else FeedbackStore()
        self._last_dispatch_ids_by_plugin: Dict[str, int] = {}

        self._cmd_sub = self.create_subscription(
            String, "/intent_command", self._on_intent_command, 20,
        )
        self._fb_sub = self.create_subscription(
            String, "/os/feedback", self._on_feedback_topic, 10,
        )
        self._audit_pub = self.create_publisher(
            String, "/os/feedback_audit", 10,
        )
        self._iq_pub = self.create_publisher(
            String, "/os/iq_state", 10,
        )
        self.get_logger().info(
            f"FeedbackNode ready (db={self._store.db_path})"
        )

    @property
    def store(self) -> FeedbackStore:
        return self._store

    # ─── /intent_command ───────────────────────────────────────────────
    def _on_intent_command(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data or "{}")
            if not isinstance(payload, dict):
                self.get_logger().warn(
                    f"/intent_command not a dict: {type(payload).__name__}"
                )
                return
        except (TypeError, ValueError) as exc:
            self.get_logger().warn(f"/intent_command unparseable: {exc}")
            return

        cid = (payload.get("cid") or "").strip()
        cmd = (payload.get("cmd") or "").strip()
        plugin_name = cmd or cid or "unknown"
        intent_text = (payload.get("raw") or "").strip()[:500]
        confidence = float(payload.get("confidence") or 0.0)
        if not intent_text and plugin_name == "unknown":
            return

        try:
            dispatch_id = self._store.record_dispatch(
                intent_text=intent_text,
                plugin_name=plugin_name,
                confidence=confidence,
                source="auto",
            )
        except Exception as exc:
            self.get_logger().warn(f"record_dispatch failed: {exc}")
            return

        self._last_dispatch_ids_by_plugin[plugin_name] = dispatch_id
        self._audit_pub.publish(String(data=json.dumps({
            "ts": time.time(),
            "event": "dispatch_recorded",
            "dispatch_id": dispatch_id,
            "plugin_name": plugin_name,
            "cid": cid,
            "confidence": confidence,
            "raw": intent_text,
        })))

    # ─── /os/feedback ──────────────────────────────────────────────────
    def _on_feedback_topic(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data or "{}")
            if not isinstance(payload, dict):
                return
        except (TypeError, ValueError) as exc:
            self.get_logger().warn(f"/os/feedback unparseable: {exc}")
            return

        plugin_name = (payload.get("plugin_name") or "").strip()
        intent_text = (payload.get("intent_text") or "").strip()
        source = (payload.get("source") or "user").strip()[:32]
        note = (payload.get("note") or "").strip()[:200]
        dispatch_id_field = payload.get("dispatch_id")

        try:
            reward = int(payload.get("reward", 0))
        except (TypeError, ValueError):
            reward = 0
        if reward not in (-1, 0, 1):
            reward = max(-1, min(1, reward))   # clamp

        event = "noop"
        dispatch_id: Optional[int] = None
        try:
            if dispatch_id_field is not None:
                dispatch_id = int(dispatch_id_field)
                ok = self._store.record_reward(
                    dispatch_id, reward, source=source, note=note,
                )
                event = "reward_updated" if ok else "reward_no_match"
            elif plugin_name and intent_text:
                dispatch_id = self._store.record_dispatch_with_reward(
                    intent_text=intent_text,
                    plugin_name=plugin_name,
                    reward=reward,
                    source=source,
                    note=note,
                )
                event = "reward_recorded_inline"
                self._last_dispatch_ids_by_plugin[plugin_name] = dispatch_id
            elif plugin_name:
                last = self._last_dispatch_ids_by_plugin.get(plugin_name)
                if last is not None:
                    ok = self._store.record_reward(
                        last, reward, source=source, note=note,
                    )
                    dispatch_id = last
                    event = "reward_updated" if ok else "reward_no_match"
                else:
                    event = "no_pending_dispatch_for_plugin"
            else:
                event = "missing_identifiers"
        except Exception as exc:
            self.get_logger().warn(f"feedback handling failed: {exc}")
            event = "exception"

        self._audit_pub.publish(String(data=json.dumps({
            "ts": time.time(),
            "event": event,
            "dispatch_id": dispatch_id,
            "plugin_name": plugin_name,
            "reward": reward,
            "source": source,
            "note": note[:120],
        })))

    # ─── helpers for tank_iq ───────────────────────────────────────────
    def publish_iq_summary(self, summary: Dict[str, Any]) -> None:
        """Publish an IQ rollup on /os/iq_state. Called by tank_iq."""
        self._iq_pub.publish(String(data=json.dumps(summary)))

    def publish_audit(self, payload: Dict[str, Any]) -> None:
        """Publish an arbitrary audit event on /os/feedback_audit."""
        self._audit_pub.publish(String(data=json.dumps(payload)))


def main(args: Any = None) -> None:
    """Entry point registered as ``feedback_node`` in ``setup.py``."""
    if not _RCLPY_AVAILABLE:
        raise SystemExit(
            "FeedbackNode.main() requires rclpy. Install ROS 2 Humble."
        )
    rclpy.init(args=args)
    node = FeedbackNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


__all__ = ["FeedbackNode", "main"]
