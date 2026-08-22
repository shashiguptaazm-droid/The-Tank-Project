"""TankOS Behavior Tree System — autonomous behavior control with composable nodes.

Implements a standard behavior tree architecture with:
- Sequence (all children succeed)
- Selector (first child succeeds)
- Condition (checks state)
- Action (performs work)
- Decorator (modifies child behavior)
- Parallel (concurrent execution)

Blackboard provides shared state across the tree.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.ai.behavior_tree")


# ── Node status ─────────────────────────────────────────────────────────

class NodeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    ERROR = "error"


# ── Blackboard (shared state) ───────────────────────────────────────────

class Blackboard:
    """Shared state accessible by all nodes in a behavior tree.

    Thread-safe key-value store with change notifications.
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._watchers: Dict[str, List[Callable]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
        if key in self._watchers:
            for cb in self._watchers[key]:
                try:
                    cb(key, value)
                except Exception:
                    logger.exception("Blackboard watcher failed for %s", key)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def watch(self, key: str, callback: Callable) -> None:
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def update(self, data: Dict[str, Any]) -> None:
        for k, v in data.items():
            self.set(k, v)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# ── Base node ───────────────────────────────────────────────────────────

class Node:
    """Base class for all behavior tree nodes."""

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        self.id = str(uuid.uuid4())[:8]
        self._status = NodeStatus.SUCCESS
        self._bb: Optional[Blackboard] = None

    def tick(self, bb: Blackboard) -> NodeStatus:
        """Execute one tick of this node. Must be implemented by subclasses."""
        raise NotImplementedError

    @property
    def status(self) -> NodeStatus:
        return self._status

    def reset(self) -> None:
        """Reset node state for re-execution."""
        self._status = NodeStatus.SUCCESS


# ── Composite nodes ─────────────────────────────────────────────────────

class CompositeNode(Node):
    """Node that contains children."""

    def __init__(self, name: str = "", children: Optional[List[Node]] = None):
        super().__init__(name)
        self.children = children or []

    def add_child(self, child: Node) -> "CompositeNode":
        self.children.append(child)
        return self

    def reset(self) -> None:
        super().reset()
        for child in self.children:
            child.reset()


class Sequence(CompositeNode):
    """Run children in order. Succeeds if ALL succeed. Fails if ANY fails."""

    def tick(self, bb: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(bb)
            if status == NodeStatus.FAILURE:
                self._status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            if status == NodeStatus.RUNNING:
                self._status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        self._status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class Selector(CompositeNode):
    """Run children in order. Succeeds if ANY succeeds. Fails if ALL fail."""

    def tick(self, bb: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(bb)
            if status == NodeStatus.SUCCESS:
                self._status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            if status == NodeStatus.RUNNING:
                self._status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
        self._status = NodeStatus.FAILURE
        return NodeStatus.FAILURE


class Parallel(CompositeNode):
    """Run all children simultaneously. Configurable success/failure thresholds."""

    def __init__(self, name: str = "", children: Optional[List[Node]] = None,
                 success_count: int = 1, failure_count: int = 1):
        super().__init__(name, children)
        self.success_count = success_count
        self.failure_count = failure_count

    def tick(self, bb: Blackboard) -> NodeStatus:
        successes = 0
        failures = 0
        all_done = True
        for child in self.children:
            status = child.tick(bb)
            if status == NodeStatus.SUCCESS:
                successes += 1
            elif status == NodeStatus.FAILURE:
                failures += 1
            elif status == NodeStatus.RUNNING:
                all_done = False
        if successes >= self.success_count:
            self._status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        if failures >= self.failure_count:
            self._status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        if not all_done:
            self._status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        self._status = NodeStatus.SUCCESS if successes > 0 else NodeStatus.FAILURE
        return self._status


# ── Leaf nodes ──────────────────────────────────────────────────────────

class ConditionNode(Node):
    """Check a condition. Returns SUCCESS if true, FAILURE if false."""

    def __init__(self, name: str = "", check: Optional[Callable[[Blackboard], bool]] = None):
        super().__init__(name)
        self._check = check or (lambda bb: True)

    def tick(self, bb: Blackboard) -> NodeStatus:
        try:
            if self._check(bb):
                self._status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            self._status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        except Exception as e:
            logger.warning("Condition '%s' failed: %s", self.name, e)
            self._status = NodeStatus.ERROR
            return NodeStatus.ERROR


class ActionNode(Node):
    """Perform an action. Configurable duration and async support."""

    def __init__(self, name: str = "",
                 action: Optional[Callable[[Blackboard], NodeStatus]] = None,
                 duration_s: float = 0.0):
        super().__init__(name)
        self._action = action or (lambda bb: NodeStatus.SUCCESS)
        self._duration_s = duration_s
        self._start_time: float = 0.0

    def tick(self, bb: Blackboard) -> NodeStatus:
        if self._start_time == 0:
            self._start_time = time.time()
        if self._duration_s > 0 and time.time() - self._start_time < self._duration_s:
            self._status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        try:
            self._status = self._action(bb)
            self._start_time = 0
            return self._status
        except Exception as e:
            logger.warning("Action '%s' failed: %s", self.name, e)
            self._start_time = 0
            self._status = NodeStatus.ERROR
            return NodeStatus.ERROR


class InvertDecorator(Node):
    """Invert child result: SUCCESS ↔ FAILURE."""

    def __init__(self, child: Node, name: str = "Invert"):
        super().__init__(name)
        self.child = child

    def tick(self, bb: Blackboard) -> NodeStatus:
        status = self.child.tick(bb)
        if status == NodeStatus.SUCCESS:
            self._status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            self._status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        self._status = status
        return status


class RetryDecorator(Node):
    """Retry child N times on failure."""

    def __init__(self, child: Node, max_retries: int = 3, name: str = "Retry"):
        super().__init__(name)
        self.child = child
        self.max_retries = max_retries
        self._attempts = 0

    def tick(self, bb: Blackboard) -> NodeStatus:
        while self._attempts < self.max_retries:
            status = self.child.tick(bb)
            if status == NodeStatus.SUCCESS:
                self._attempts = 0
                self._status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            self._attempts += 1
            self.child.reset()
        self._attempts = 0
        self._status = NodeStatus.FAILURE
        return NodeStatus.FAILURE


class TimeoutDecorator(Node):
    """Fail child if it takes longer than timeout_s."""

    def __init__(self, child: Node, timeout_s: float = 10.0, name: str = "Timeout"):
        super().__init__(name)
        self.child = child
        self.timeout_s = timeout_s
        self._start = 0.0

    def tick(self, bb: Blackboard) -> NodeStatus:
        if self._start == 0:
            self._start = time.time()
        if time.time() - self._start > self.timeout_s:
            self._start = 0
            self._status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        status = self.child.tick(bb)
        if status != NodeStatus.RUNNING:
            self._start = 0
        self._status = status
        return status


# ── Behavior Tree ───────────────────────────────────────────────────────

class BehaviorTree:
    """A complete behavior tree with tick execution.

    Usage:
        tree = BehaviorTree("patrol")

        tree.root = Sequence("patrol_sequence", [
            ConditionNode("battery_ok", lambda bb: bb.get("battery", 100) > 20),
            ActionNode("move_to_waypoint", lambda bb: NodeStatus.SUCCESS, duration_s=5.0),
            ActionNode("scan_area", lambda bb: NodeStatus.SUCCESS, duration_s=3.0),
        ])

        # Run one tick
        status = tree.tick()

        # Run continuously
        tree.run(interval_s=0.1)
    """

    def __init__(self, name: str = "behavior_tree"):
        self.name = name
        self.root: Optional[Node] = None
        self.blackboard = Blackboard()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._bus = EventBus()
        self._tick_count = 0
        self._last_status = NodeStatus.SUCCESS

    def tick(self) -> NodeStatus:
        """Execute one tick starting from root."""
        if self.root is None:
            return NodeStatus.ERROR
        try:
            self._tick_count += 1
            self._last_status = self.root.tick(self.blackboard)
            return self._last_status
        except Exception as e:
            logger.error("Behavior tree '%s' tick failed: %s", self.name, e)
            self._last_status = NodeStatus.ERROR
            return NodeStatus.ERROR

    def run(self, interval_s: float = 0.1, max_ticks: int = 0) -> None:
        """Run the tree in a loop. Blocks until complete."""
        ticks = 0
        while max_ticks <= 0 or ticks < max_ticks:
            status = self.tick()
            if status in (NodeStatus.SUCCESS, NodeStatus.FAILURE):
                self._bus.emit(Event("behavior_tree_complete", {
                    "tree": self.name, "status": status.value,
                    "ticks": self._tick_count,
                }, source="behavior_tree"))
                break
            ticks += 1
            time.sleep(interval_s)

    def start_background(self, interval_s: float = 0.1) -> None:
        """Start running the tree in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._bg_loop, args=(interval_s,),
            daemon=True, name=f"bt-{self.name[:10]}"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop background execution."""
        self._running = False

    def _bg_loop(self, interval_s: float) -> None:
        while self._running:
            status = self.tick()
            if status in (NodeStatus.SUCCESS, NodeStatus.FAILURE, NodeStatus.ERROR):
                self._running = False
                self._bus.emit(Event("behavior_tree_complete", {
                    "tree": self.name, "status": status.value,
                    "ticks": self._tick_count,
                }, source="behavior_tree"))
            time.sleep(interval_s)

    def reset(self) -> None:
        """Reset entire tree for re-execution."""
        if self.root:
            self.root.reset()
        self._tick_count = 0

    def with_root(self, root: Node) -> "BehaviorTree":
        """Set the root node and return self for chaining."""
        self.root = root
        return self


# ── Pre-built behavior tree factory ─────────────────────────────────────

class BehaviorFactory:
    """Create common behavior trees for TankOS."""

    @staticmethod
    def patrol_tree() -> BehaviorTree:
        """Autonomous patrol behavior tree."""
        return BehaviorTree("patrol").with_root(
            Selector("patrol_behavior", [
                # Priority 1: Emergency
                Sequence("emergency_override", [
                    ConditionNode("estop_active", lambda bb: bb.get("estop", False)),
                    ActionNode("halt_and_report", lambda bb: NodeStatus.SUCCESS),
                ]),
                # Priority 2: Low battery → return to dock
                Sequence("return_to_dock", [
                    ConditionNode("battery_critical", lambda bb: bb.get("battery_pct", 100) < 20),
                    ActionNode("navigate_to_dock", lambda bb: NodeStatus.SUCCESS, duration_s=30.0),
                    ActionNode("initiate_charging", lambda bb: NodeStatus.SUCCESS, duration_s=5.0),
                ]),
                # Priority 3: Active patrol
                Sequence("patrol_route", [
                    ConditionNode("patrol_enabled", lambda bb: bb.get("patrol_mode", False)),
                    ActionNode("move_to_next_waypoint", lambda bb: NodeStatus.SUCCESS, duration_s=10.0),
                    ActionNode("scan_and_report", lambda bb: NodeStatus.SUCCESS, duration_s=3.0),
                    ActionNode("update_position", lambda bb: NodeStatus.SUCCESS),
                ]),
                # Fallback: Idle
                ActionNode("idle", lambda bb: NodeStatus.SUCCESS, duration_s=1.0),
            ])
        )

    @staticmethod
    def docking_tree() -> BehaviorTree:
        """Precision docking behavior tree."""
        return BehaviorTree("docking").with_root(
            Sequence("dock_sequence", [
                # Phase 1: Approach
                ActionNode("approach_dock", lambda bb: NodeStatus.SUCCESS, duration_s=15.0),
                # Phase 2: Align using AprilTag
                RetryDecorator(
                    Sequence("align_attempt", [
                        ConditionNode("apriltag_visible", lambda bb: bb.get("tag_visible", False)),
                        ActionNode("fine_align", lambda bb: NodeStatus.SUCCESS, duration_s=5.0),
                    ]),
                    max_retries=3,
                ),
                # Phase 3: Connect and charge
                ActionNode("extend_contacts", lambda bb: NodeStatus.SUCCESS, duration_s=2.0),
                ConditionNode("charging_verified", lambda bb: bb.get("charging", False)),
            ])
        )

    @staticmethod
    def security_response_tree() -> BehaviorTree:
        """Security alert response behavior tree."""
        return BehaviorTree("security_response").with_root(
            Selector("security_behavior", [
                # Priority 1: Critical alert
                Sequence("critical_alert", [
                    ConditionNode("is_critical", lambda bb: bb.get("alert_severity", 0) >= 9),
                    ActionNode("sound_alarm", lambda bb: NodeStatus.SUCCESS, duration_s=3.0),
                    ActionNode("record_evidence", lambda bb: NodeStatus.SUCCESS, duration_s=10.0),
                    ActionNode("notify_owner", lambda bb: NodeStatus.SUCCESS),
                ]),
                # Priority 2: Standard alert
                Sequence("standard_alert", [
                    ActionNode("turn_toward_event", lambda bb: NodeStatus.SUCCESS, duration_s=2.0),
                    ActionNode("capture_image", lambda bb: NodeStatus.SUCCESS),
                    ActionNode("log_and_report", lambda bb: NodeStatus.SUCCESS),
                ]),
                # Fallback
                ActionNode("continue_patrol", lambda bb: NodeStatus.SUCCESS),
            ])
        )



