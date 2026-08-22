"""TankOS Self-Reflection Engine — daily learning loop, mistake analysis, self-improvement.

Reviews past actions, conversations, and outcomes. Identifies mistakes,
successes, and improvement opportunities. Generates goals and stores
reflections in long-term memory. Runs as a background scheduled task.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.reflection")


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class ActionRecord:
    """A recorded action or event for later reflection."""
    id: str
    action_type: str          # "command", "conversation", "navigation", "vision", "system"
    description: str
    outcome: str = "unknown"  # "success", "failure", "partial", "unknown"
    success_score: float = 0.5  # 0.0 = failure, 1.0 = perfect
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reflection: str = ""


@dataclass
class Reflection:
    """A single reflection entry — insight from reviewing actions."""
    id: str
    summary: str
    category: str              # "mistake", "improvement", "insight", "goal"
    action_ids: List[str] = field(default_factory=list)
    recommended_action: str = ""
    severity: str = "info"     # "critical", "warning", "info", "praise"
    timestamp: float = field(default_factory=time.time)
    applied: bool = False


@dataclass
class ImprovementGoal:
    """A self-generated improvement goal."""
    id: str
    description: str
    category: str              # "accuracy", "speed", "safety", "communication", "learning"
    metric: str = ""           # How to measure success
    target_value: float = 0.0
    current_value: float = 0.0
    created: float = field(default_factory=time.time)
    deadline: float = 0.0
    achieved: bool = False


# ── Reflection Engine ────────────────────────────────────────────────────

class ReflectionEngine:
    """Self-reflection engine — learns from actions and improves over time.

    Usage:
        engine = ReflectionEngine()
        engine.initialize()

        # Record an action
        engine.record_action("navigation", "Docking attempt", outcome="success")

        # Run daily reflection
        reflections = engine.run_reflection_cycle()

        # Get improvement goals
        goals = engine.get_active_goals()
    """

    _instance: Optional["ReflectionEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._actions: List[ActionRecord] = []
                cls._instance._reflections: List[Reflection] = []
                cls._instance._goals: List[ImprovementGoal] = []
                cls._instance._store_path = Path.home() / ".config" / "tank_os" / "reflections.json"
                cls._instance._scheduled = False
                cls._instance._cycle_count = 0
            return cls._instance

    # ── Initialization ────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load past reflections and set up EventBus listeners."""
        self._load()
        self._bus.on("action_completed", self._on_action_completed)
        self._bus.on("daily_tick", self._on_daily_tick)
        self._bus.on("reflection_request", self._on_reflection_request)
        logger.info("ReflectionEngine initialized (%d actions, %d reflections, %d goals)",
                     len(self._actions), len(self._reflections), len(self._goals))

    def _load(self) -> None:
        """Load reflections from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            self._actions = [ActionRecord(**a) for a in data.get("actions", [])]
            self._reflections = [Reflection(**r) for r in data.get("reflections", [])]
            self._goals = [ImprovementGoal(**g) for g in data.get("goals", [])]
        except Exception as e:
            logger.warning("Failed to load reflections: %s", e)

    def _save(self) -> None:
        """Persist reflections to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "actions": [vars(a) for a in self._actions[-1000:]],
            "reflections": [vars(r) for r in self._reflections],
            "goals": [vars(g) for g in self._goals],
            "last_update": time.time(),
        }
        self._store_path.write_text(json.dumps(data, indent=2, default=str))

    # ── Recording actions ─────────────────────────────────────────────

    def record_action(self, action_type: str, description: str,
                      outcome: str = "unknown", success_score: float = 0.5,
                      context: Optional[Dict[str, Any]] = None,
                      emit_event: bool = True) -> ActionRecord:
        """Record an action for later reflection."""
        action = ActionRecord(
            id=str(uuid.uuid4())[:8],
            action_type=action_type,
            description=description,
            outcome=outcome,
            success_score=success_score,
            context=context or {},
        )
        self._actions.append(action)

        if emit_event:
            self._bus.emit(Event("action_recorded", {
                "id": action.id, "type": action_type,
                "outcome": outcome, "score": success_score,
            }, source="reflection_engine"))

        return action

    def _on_action_completed(self, event: Event) -> None:
        """EventBus handler for completed actions."""
        self.record_action(
            action_type=event.data.get("type", "system"),
            description=event.data.get("description", ""),
            outcome=event.data.get("outcome", "unknown"),
            success_score=event.data.get("score", 0.5),
            context=event.data.get("context"),
            emit_event=False,
        )

    # ── Reflection cycle ──────────────────────────────────────────────

    def run_reflection_cycle(self) -> List[Reflection]:
        """Run one reflection cycle — analyze recent actions and generate insights.

        Returns:
            List of new reflections generated this cycle.
        """
        new_reflections: List[Reflection] = []
        recent = self._actions[-100:]  # Look at last 100 actions

        if not recent:
            logger.debug("No actions to reflect on")
            return new_reflections

        # 1. Analyze failure patterns
        failures = [a for a in recent if a.outcome == "failure"]
        if len(failures) >= 3:
            types = [f.action_type for f in failures]
            common = max(set(types), key=types.count)
            new_reflections.append(Reflection(
                id=str(uuid.uuid4())[:8],
                summary=f"Frequent failures in '{common}' — {len(failures)} recent failures detected",
                category="mistake",
                action_ids=[f.id for f in failures[-5:]],
                recommended_action=f"Review and improve '{common}' handling",
                severity="warning",
            ))

        # 2. Analyze improvement patterns
        partial = [a for a in recent if a.outcome == "partial"]
        if len(partial) >= 5:
            new_reflections.append(Reflection(
                id=str(uuid.uuid4())[:8],
                summary=f"Partial completions trending up — {len(partial)} tasks partially done",
                category="improvement",
                action_ids=[p.id for p in partial[-3:]],
                recommended_action="Consider breaking tasks into smaller steps",
                severity="info",
            ))

        # 3. Detect success streaks
        successes = [a for a in recent[-20:] if a.outcome == "success"]
        if len(successes) >= 10:
            new_reflections.append(Reflection(
                id=str(uuid.uuid4())[:8],
                summary=f"Strong success streak — {len(successes)}/20 recent actions succeeded",
                category="insight",
                action_ids=[s.id for s in successes[-3:]],
                recommended_action="Continue current operational pattern",
                severity="praise",
            ))

        # 4. Detect repeated same-type failures (stuck in loop)
        if len(recent) >= 6:
            last_types = [a.action_type for a in recent[-6:]]
            if all(t == last_types[0] for t in last_types):
                new_reflections.append(Reflection(
                    id=str(uuid.uuid4())[:8],
                    summary=f"Potential loop detected — last 6 actions all '{last_types[0]}'",
                    category="mistake",
                    action_ids=[a.id for a in recent[-6:]],
                    recommended_action="Consider trying a different approach",
                    severity="critical",
                ))

        # 5. Time-based: actions taking too long
        for action in recent:
            duration = action.context.get("duration_s", 0)
            if duration > 300:  # > 5 minutes
                new_reflections.append(Reflection(
                    id=str(uuid.uuid4())[:8],
                    summary=f"Long-running action: {action.description[:60]} ({duration:.0f}s)",
                    category="improvement",
                    action_ids=[action.id],
                    recommended_action="Optimize or add progress reporting",
                    severity="info",
                ))

        # Store and emit
        self._reflections.extend(new_reflections)
        self._cycle_count += 1
        self._save()

        for ref in new_reflections:
            self._bus.emit(Event("reflection_generated", {
                "id": ref.id, "summary": ref.summary,
                "category": ref.category, "severity": ref.severity,
            }, source="reflection_engine"))

        # Update goals based on reflections
        self._update_goals(new_reflections)

        logger.info("Reflection cycle complete: %d new insights", len(new_reflections))
        return new_reflections

    def _on_daily_tick(self, event: Event) -> None:
        """Run reflection on daily tick."""
        logger.info("Daily reflection triggered")
        self.run_reflection_cycle()

    def _on_reflection_request(self, event: Event) -> None:
        """Handle manual reflection request via EventBus."""
        self.run_reflection_cycle()

    # ── Goals ─────────────────────────────────────────────────────────

    def _update_goals(self, reflections: List[Reflection]) -> None:
        """Generate or update improvement goals based on reflections."""
        for ref in reflections:
            if ref.category == "mistake" and ref.severity in ("critical", "warning"):
                # Create improvement goal for recurring mistakes
                existing = [g for g in self._goals if not g.achieved
                           and g.description.startswith(ref.summary[:30])]
                if not existing:
                    goal = ImprovementGoal(
                        id=str(uuid.uuid4())[:8],
                        description=f"Fix: {ref.summary}",
                        category="accuracy",
                        metric="failure_count",
                    )
                    self._goals.append(goal)

        # Auto-archive achieved goals
        now = time.time()
        for goal in self._goals:
            if goal.deadline and now > goal.deadline and goal.current_value >= goal.target_value:
                goal.achieved = True

    def set_goal(self, description: str, category: str = "improvement",
                 metric: str = "", target: float = 1.0,
                 deadline_hours: float = 0) -> ImprovementGoal:
        """Manually set an improvement goal."""
        goal = ImprovementGoal(
            id=str(uuid.uuid4())[:8],
            description=description,
            category=category,
            metric=metric,
            target_value=target,
            deadline=time.time() + deadline_hours * 3600 if deadline_hours else 0,
        )
        self._goals.append(goal)
        self._save()
        return goal

    def update_goal_progress(self, goal_id: str, current_value: float) -> None:
        """Update progress toward a goal."""
        for goal in self._goals:
            if goal.id == goal_id:
                goal.current_value = current_value
                if goal.target_value and current_value >= goal.target_value:
                    goal.achieved = True
                    self._bus.emit(Event("goal_achieved", {
                        "id": goal.id, "description": goal.description,
                    }, source="reflection_engine"))
                break
        self._save()

    # ── Query ─────────────────────────────────────────────────────────

    def get_recent_reflections(self, limit: int = 10) -> List[Reflection]:
        """Get most recent reflections."""
        return sorted(self._reflections, key=lambda r: r.timestamp, reverse=True)[:limit]

    def get_active_goals(self) -> List[ImprovementGoal]:
        """Get goals that haven't been achieved yet."""
        return [g for g in self._goals if not g.achieved]

    def get_failures(self, action_type: Optional[str] = None,
                     limit: int = 20) -> List[ActionRecord]:
        """Get failed actions, optionally filtered by type."""
        failures = [a for a in self._actions if a.outcome == "failure"]
        if action_type:
            failures = [a for a in failures if a.action_type == action_type]
        return sorted(failures, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of reflection state."""
        return {
            "total_actions": len(self._actions),
            "total_reflections": len(self._reflections),
            "active_goals": len(self.get_active_goals()),
            "cycle_count": self._cycle_count,
            "success_rate": round(
                sum(1 for a in self._actions[-100:] if a.outcome == "success") / 100
                if len(self._actions) >= 100 else 0, 2
            ),
            "recent_reflections": [r.summary for r in self.get_recent_reflections(3)],
        }
