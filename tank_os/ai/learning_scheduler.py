"""TankOS Learning Scheduler — orchestrates all background learning activities.

The Learning Scheduler coordinates when each learning engine runs to ensure
learning never interferes with real-time robot operation. It supports:

- Scheduled cycles (daily, hourly, every N minutes)
- Idle-triggered learning (runs when system is not busy)
- Priority-based scheduling (important learning runs first)
- Resource-aware timing (avoids high CPU/memory usage)
- Configurable learning windows (time-of-day restrictions)
- Learning budget management (max hours per day)

Integrates with: ReflectionEngine, ContinuousLearningEngine, ExperienceEngine,
CuriosityEngine, HabitLearningEngine, SelfCodingSystem.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.scheduler")

# ── Constants ───────────────────────────────────────────────────────────

CYCLE_INTERVAL_S = 60          # Check for scheduled tasks every 60s
MAX_DAILY_LEARNING_HOURS = 4    # Cap learning at 4 hours per day
LEARNING_COOLDOWN_S = 30       # Min seconds between different learning tasks


class LearningPriority(Enum):
    """Priority levels for scheduled learning tasks."""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    IDLE = 0


class LearningTaskType(Enum):
    """Types of learning tasks that can be scheduled."""
    REFLECTION = "reflection"
    PATTERN_LEARNING = "pattern_learning"
    KNOWLEDGE_CONSOLIDATION = "knowledge_consolidation"
    PREFERENCE_EXTRACTION = "preference_extraction"
    CURIOSITY_EXPLORATION = "curiosity_exploration"
    CODE_IMPROVEMENT = "code_improvement"
    MEMORY_MAINTENANCE = "memory_maintenance"
    EXPERIENCE_REVIEW = "experience_review"
    HABIT_ANALYSIS = "habit_analysis"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"
    WORLD_MODEL_UPDATE = "world_model_update"
    INSIGHT_GENERATION = "insight_generation"


@dataclass
class ScheduledTask:
    """A scheduled learning task."""

    id: str
    task_type: LearningTaskType
    description: str
    priority: LearningPriority = LearningPriority.NORMAL
    interval_s: float = 3600.0         # How often to run (default: hourly)
    last_run: float = 0.0
    next_run: float = 0.0
    enabled: bool = True
    run_count: int = 0
    last_duration: float = 0.0
    average_duration: float = 0.0
    resource_intensive: bool = False   # Only run when system is not busy
    requires_idle: bool = False        # Only run when system is idle
    timeout_s: float = 300.0          # Max time before task is force-stopped


@dataclass
class LearningWindow:
    """Time window when learning is allowed to run."""

    start_hour: int = 0        # 0-23
    end_hour: int = 23         # 0-23
    days: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Monday
    max_daily_hours: float = MAX_DAILY_LEARNING_HOURS


@dataclass
class LearningBudget:
    """Track daily learning time usage."""

    date: str = ""                     # YYYY-MM-DD
    seconds_used: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0


@dataclass
class TaskResult:
    """Result of executing a scheduled task."""

    task_id: str
    task_type: LearningTaskType
    success: bool
    duration_s: float
    output: str = ""
    error: str = ""


# ── Learning Scheduler ─────────────────────────────────────────────────

class LearningScheduler:
    """Orchestrates all background AI learning activities.

    Runs as a background service, scheduling and executing learning
    tasks at appropriate times. Ensures learning never interferes with
    real-time robot operation.

    Usage:
        scheduler = LearningScheduler()
        scheduler.initialize()

        # Start background scheduling
        scheduler.start()

        # Add custom tasks
        scheduler.add_task(
            LearningTaskType.REFLECTION,
            description="Daily reflection cycle",
            interval_s=86400,  # Daily
            callable=my_reflection_function,
        )

        # Manual triggers
        scheduler.run_task_now(task_id)

        # Check status
        status = scheduler.get_status()
    """

    _instance: Optional["LearningScheduler"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._tasks: Dict[str, ScheduledTask] = {}
                cls._instance._results: List[TaskResult] = []
                cls._instance._window = LearningWindow()
                cls._instance._budget = LearningBudget()
                cls._instance._running = False
                cls._instance._scheduler_thread: Optional[threading.Thread] = None
                cls._instance._active_task: Optional[str] = None
                cls._instance._system_busy = False
                cls._instance._pause_learning = False
                cls._instance._task_registry: Dict[LearningTaskType, Callable] = {}
            return cls._instance

    def initialize(self) -> None:
        """Set up default tasks and register EventBus listeners."""
        self._register_default_tasks()
        self._load_budget()
        self._register_listeners()
        logger.info(
            "LearningScheduler initialized (%d tasks, budget=%.1f/%.1f hours)",
            len(self._tasks), self._budget.seconds_used / 3600,
            self._window.max_daily_hours,
        )

    def _register_default_tasks(self) -> None:
        """Register the default set of learning tasks."""
        defaults = [
            # (task_type, description, priority, interval_s, requires_idle, resource_intensive)
            (LearningTaskType.REFLECTION, "Analyze recent actions and generate improvement insights",
             LearningPriority.HIGH, 86400, False, False),         # Daily

            (LearningTaskType.EXPERIENCE_REVIEW, "Review and consolidate recent experiences",
             LearningPriority.NORMAL, 43200, True, False),        # Every 12 hours

            (LearningTaskType.PATTERN_LEARNING, "Discover patterns in recent experiences",
             LearningPriority.NORMAL, 3600, True, False),         # Hourly

            (LearningTaskType.PREFERENCE_EXTRACTION, "Extract user preferences from interactions",
             LearningPriority.LOW, 21600, True, False),           # Every 6 hours

            (LearningTaskType.KNOWLEDGE_CONSOLIDATION, "Consolidate knowledge graph entities",
             LearningPriority.NORMAL, 86400, True, True),         # Daily, resource-intensive

            (LearningTaskType.CURIOSITY_EXPLORATION, "Explore environment and discover new knowledge",
             LearningPriority.IDLE, 7200, True, True),            # Every 2 hours, IDLE only

            (LearningTaskType.HABIT_ANALYSIS, "Analyze observations for habit patterns",
             LearningPriority.NORMAL, 3600, True, False),         # Hourly

            (LearningTaskType.MEMORY_MAINTENANCE, "Compact and optimize memory storage",
             LearningPriority.LOW, 86400, True, True),            # Daily, resource-intensive

            (LearningTaskType.KNOWLEDGE_GRAPH_UPDATE, "Update entity relationships from experiences",
             LearningPriority.LOW, 3600, True, False),            # Hourly

            (LearningTaskType.WORLD_MODEL_UPDATE, "Update room and object positions",
             LearningPriority.LOW, 1800, True, False),            # Every 30 min

            (LearningTaskType.INSIGHT_GENERATION, "Analyze and extract meaningful insights",
             LearningPriority.NORMAL, 43200, True, False),        # Every 12 hours

            (LearningTaskType.CODE_IMPROVEMENT, "Self-improvement: analyze and optimize code",
             LearningPriority.IDLE, 86400, True, True),           # Daily, IDLE + resource-intensive
        ]

        for task_type, desc, priority, interval, idle, intensive in defaults:
            task = ScheduledTask(
                id=str(uuid.uuid4())[:8],
                task_type=task_type,
                description=desc,
                priority=priority,
                interval_s=interval,
                last_run=0.0,
                next_run=time.time() + hash(task_type.value) % 3600,  # Spread out start times
                requires_idle=idle,
                resource_intensive=intensive,
                timeout_s=600.0 if intensive else 180.0,
            )
            self._tasks[task.id] = task

    def _register_listeners(self) -> None:
        """Register EventBus listeners."""
        self._bus.on("system_busy", self._on_system_busy)
        self._bus.on("system_idle", self._on_system_idle)
        self._bus.on("scheduler_request", self._on_scheduler_request)
        self._bus.on("daily_tick", self._on_daily_tick)

    def _load_budget(self) -> LearningBudget:
        """Load today's learning budget."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._budget.date != today:
            self._budget = LearningBudget(date=today)
        return self._budget

    # ── Task Registration ──────────────────────────────────────────

    def register_task_handler(self, task_type: LearningTaskType,
                               handler: Callable[[], Dict[str, Any]]) -> None:
        """Register a handler function for a learning task type.

        Args:
            task_type: The task type this handler executes
            handler: Function that performs the task and returns a result dict
        """
        self._task_registry[task_type] = handler

    def add_task(self, task_type: LearningTaskType, description: str,
                 priority: LearningPriority = LearningPriority.NORMAL,
                 interval_s: float = 3600.0,
                 requires_idle: bool = False,
                 resource_intensive: bool = False,
                 handler: Optional[Callable] = None) -> str:
        """Add a custom scheduled task.

        Args:
            task_type: Type of learning task
            description: Human-readable description
            priority: When this task should run
            interval_s: How often to run (seconds)
            requires_idle: Only run when system is idle
            resource_intensive: High CPU/memory usage
            handler: Optional handler function

        Returns:
            Task ID
        """
        task = ScheduledTask(
            id=str(uuid.uuid4())[:8],
            task_type=task_type,
            description=description,
            priority=priority,
            interval_s=interval_s,
            next_run=time.time() + interval_s / 2,  # Half-interval delay
            requires_idle=requires_idle,
            resource_intensive=resource_intensive,
        )
        self._tasks[task.id] = task

        if handler:
            self._task_registry[task_type] = handler

        return task.id

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task by ID."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID."""
        return self._tasks.get(task_id)

    def get_tasks(self, task_type: Optional[LearningTaskType] = None,
                  enabled_only: bool = True) -> List[ScheduledTask]:
        """Get scheduled tasks, optionally filtered."""
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return sorted(tasks, key=lambda t: t.priority.value, reverse=True)

    # ── Scheduler Execution ────────────────────────────────────────

    def start(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="learning-scheduler",
        )
        self._scheduler_thread.start()
        logger.info("Learning scheduler started")

    def stop(self) -> None:
        """Stop the background scheduler loop."""
        self._running = False

    def _scheduler_loop(self) -> None:
        """Main scheduler loop — checks for tasks to run every N seconds."""
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.error("Scheduler loop error: %s", e)
            time.sleep(CYCLE_INTERVAL_S)

    def _check_and_run_tasks(self) -> None:
        """Check if any tasks are due to run, and execute them."""
        now = time.time()

        # Check if we've exceeded daily budget
        self._load_budget()
        daily_used = self._budget.seconds_used / 3600
        if daily_used >= self._window.max_daily_hours:
            return  # Budget exhausted for today

        # Check if we're in a learning window
        if not self._in_learning_window():
            return

        # Find tasks that are due
        due_tasks = [
            t for t in self._tasks.values()
            if t.enabled
            and t.next_run <= now
            and (not t.requires_idle or not self._system_busy)
            and (not t.resource_intensive or not self._system_busy)
            and t.id != self._active_task  # Don't re-run active task
        ]

        # Sort by priority (highest first)
        due_tasks.sort(key=lambda t: -t.priority.value)

        # Run the highest-priority task (run one at a time)
        if due_tasks:
            task = due_tasks[0]
            # Check if enough time has passed since last task
            recent_results = [
                r for r in self._results[-5:]
                if r.duration_s > 0
            ]
            if recent_results:
                last_finish = max(r.duration_s for r in recent_results) + LEARNING_COOLDOWN_S
                now_is_ok = now - (task.last_run + last_finish) > 0
                if not now_is_ok and not task.resource_intensive:
                    # Try next task that's not resource-intensive
                    for alt_task in due_tasks[1:]:
                        if not alt_task.resource_intensive:
                            task = alt_task
                            break

            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask) -> TaskResult:
        """Execute a single scheduled learning task.

        Invokes the registered handler for the task type, or uses
        built-in logic for default task types.
        """
        self._active_task = task.id
        start = time.time()
        success = True
        output = ""

        try:
            # Check if there's a registered handler
            handler = self._task_registry.get(task.task_type)
            if handler:
                result = handler()
                output = str(result.get("status", "completed"))
                success = result.get("success", True)
            else:
                # Built-in handler
                result = self._builtin_handler(task)
                output = result.get("message", "completed")
                success = result.get("success", True)

        except Exception as e:
            logger.warning("Task %s failed: %s", task.task_type.value, e)
            success = False
            output = str(e)
        finally:
            duration = time.time() - start
            task.last_run = time.time()
            task.next_run = task.last_run + task.interval_s
            task.run_count += 1
            task.last_duration = duration
            task.average_duration = (
                (task.average_duration * (task.run_count - 1) + duration)
                / task.run_count
            )
            self._active_task = None

        # Record result
        result = TaskResult(
            task_id=task.id,
            task_type=task.task_type,
            success=success,
            duration_s=duration,
            output=output,
            error="" if success else output,
        )
        self._results.append(result)
        if len(self._results) > 200:
            self._results = self._results[-200:]

        # Update budget
        self._budget.seconds_used += duration
        if success:
            self._budget.tasks_completed += 1
        else:
            self._budget.tasks_failed += 1

        logger.debug("Task %s: %s (%.1fs)",
                      task.task_type.value, "✅" if success else "❌", duration)

        return result

    def _builtin_handler(self, task: ScheduledTask) -> Dict[str, Any]:
        """Built-in handler for default learning tasks."""
        result: Dict[str, Any] = {"success": True, "message": "completed"}

        try:
            if task.task_type == LearningTaskType.REFLECTION:
                from tank_os.ai.reflection_engine import ReflectionEngine
                refs = ReflectionEngine().run_reflection_cycle()
                result["message"] = f"Generated {len(refs)} reflections"
                result["reflections"] = len(refs)

            elif task.task_type == LearningTaskType.PATTERN_LEARNING:
                from tank_os.ai.continuous_learning import ContinuousLearningEngine
                patterns = ContinuousLearningEngine().learn_from_recent_experiences()
                result["message"] = f"Discovered {len(patterns)} patterns"
                result["patterns"] = len(patterns)

            elif task.task_type == LearningTaskType.PREFERENCE_EXTRACTION:
                from tank_os.ai.continuous_learning import ContinuousLearningEngine
                prefs = ContinuousLearningEngine().extract_preferences()
                result["message"] = f"Extracted {len(prefs)} preferences"
                result["preferences"] = len(prefs)

            elif task.task_type == LearningTaskType.KNOWLEDGE_CONSOLIDATION:
                from tank_os.ai.knowledge_graph import KnowledgeGraph
                kg = KnowledgeGraph()
                stats = kg.get_stats()
                result["message"] = f"Graph has {stats['total_entities']} entities"
                result["entities"] = stats["total_entities"]

            elif task.task_type == LearningTaskType.CURIOSITY_EXPLORATION:
                from tank_os.ai.curiosity_engine import CuriosityEngine
                exp = CuriosityEngine().auto_explore()
                if exp:
                    result["message"] = f"Explored: {len(exp.findings)} findings"
                    result["findings"] = len(exp.findings)
                else:
                    result["message"] = "Nothing to explore (cooldown)"

            elif task.task_type == LearningTaskType.HABIT_ANALYSIS:
                from tank_os.ai.habit_learner import HabitLearningEngine
                habits = HabitLearningEngine().get_habits()
                result["message"] = f"Tracking {len(habits)} habits"
                result["habits"] = len(habits)

            elif task.task_type == LearningTaskType.WORLD_MODEL_UPDATE:
                from tank_os.ai.world_model import WorldModel
                wm = WorldModel()
                stats = wm.get_stats()
                result["message"] = f"World model: {stats['rooms']['total']} rooms"
                result["rooms"] = stats["rooms"]["total"]

            elif task.task_type == LearningTaskType.INSIGHT_GENERATION:
                from tank_os.ai.continuous_learning import ContinuousLearningEngine
                insights = ContinuousLearningEngine().generate_insights()
                result["message"] = f"Generated {len(insights)} insights"
                result["insights"] = len(insights)

            else:
                result["message"] = f"Task {task.task_type.value} executed (no specific handler)"
                result["handled"] = False

        except Exception as e:
            result["success"] = False
            result["message"] = str(e)
            logger.warning("Built-in handler for %s failed: %s",
                           task.task_type.value, e)

        return result

    # ── Helper Methods ─────────────────────────────────────────────

    def _in_learning_window(self) -> bool:
        """Check if current time is within the configured learning window."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()

        if day not in self._window.days:
            return False
        if hour < self._window.start_hour or hour >= self._window.end_hour:
            return False
        return True

    # ── Event Handlers ─────────────────────────────────────────────

    def _on_system_busy(self, event: Event) -> None:
        """System is processing high-priority tasks — pause learning."""
        self._system_busy = True
        # Interrupt current task if it's a low-priority one
        if self._active_task:
            task = self._tasks.get(self._active_task)
            if task and task.priority.value <= LearningPriority.LOW.value:
                logger.debug("Interrupted task %s due to system activity",
                             task.task_type.value)

    def _on_system_idle(self, event: Event) -> None:
        """System is idle — learning can proceed."""
        self._system_busy = False

    def _on_daily_tick(self, event: Event) -> None:
        """Reset daily budget for the new day."""
        self._load_budget()  # Already resets self._budget if date changed

    def _on_scheduler_request(self, event: Event) -> None:
        """Handle manual requests via EventBus."""
        action = event.data.get("action", "status")
        if action == "status":
            self._bus.emit(Event("scheduler_status", self.get_status(),
                                 source="learning_scheduler"))
        elif action == "run_now":
            task_id = event.data.get("task_id", "")
            if task_id in self._tasks:
                self._execute_task(self._tasks[task_id])
        elif action == "enable":
            task_id = event.data.get("task_id", "")
            if task_id in self._tasks:
                self._tasks[task_id].enabled = True
        elif action == "disable":
            task_id = event.data.get("task_id", "")
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
        elif action == "run_all_due":
            self._check_and_run_tasks()

    def run_task_now(self, task_id: str) -> Optional[TaskResult]:
        """Manually trigger a task immediately."""
        if task_id in self._tasks:
            return self._execute_task(self._tasks[task_id])
        return None

    # ── Query API ─────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get full scheduler status."""
        tasks_by_type: Dict[str, int] = {}
        for task in self._tasks.values():
            tasks_by_type[task.task_type.value] = \
                tasks_by_type.get(task.task_type.value, 0) + 1

        now = time.time()
        next_task = min(
            (t for t in self._tasks.values() if t.enabled),
            key=lambda t: t.next_run,
            default=None,
        )

        return {
            "running": self._running,
            "system_busy": self._system_busy,
            "scheduled_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "active_task": self._active_task,
            "by_type": tasks_by_type,
            "budget": {
                "used_today_h": round(self._budget.seconds_used / 3600, 2),
                "max_daily_h": self._window.max_daily_hours,
                "remaining_h": round(
                    self._window.max_daily_hours - self._budget.seconds_used / 3600, 2
                ),
                "tasks_completed": self._budget.tasks_completed,
                "tasks_failed": self._budget.tasks_failed,
            },
            "learning_window": {
                "start": f"{self._window.start_hour}:00",
                "end": f"{self._window.end_hour}:00",
                "active": self._in_learning_window(),
            },
            "next_task": {
                "type": next_task.task_type.value if next_task else None,
                "in_seconds": round(next_task.next_run - now) if next_task else None,
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        recent_results = self._results[-100:]
        success_count = sum(1 for r in recent_results if r.success)
        by_type: Dict[str, int] = {}
        avg_durations: Dict[str, float] = {}

        for r in recent_results:
            ttype = r.task_type.value
            by_type[ttype] = by_type.get(ttype, 0) + 1

        for task in self._tasks.values():
            ttype = task.task_type.value
            if task.run_count > 0:
                avg_durations[ttype] = round(task.average_duration, 1)

        return {
            "total_runs": sum(t.run_count for t in self._tasks.values()),
            "recent_success_rate": f"{success_count}/{len(recent_results)}" if recent_results else "N/A",
            "by_type_runs": by_type,
            "avg_durations_s": avg_durations,
            "running": self._running,
            "tasks_count": len(self._tasks),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Quick status summary."""
        return {
            "running": self._running,
            "tasks": len(self._tasks),
            "active": self._active_task is not None,
            "budget_used": round(self._budget.seconds_used / 3600, 2),
            "busy": self._system_busy,
        }
