"""TankOS Habit Learning Engine — pattern tracking, routine discovery, predictive assistance.

Learns user routines and habits from repeated observations:
- Time-based patterns (e.g., "user always checks camera at 9 AM")
- Sequence patterns (e.g., "after patrol, user checks battery")
- Location patterns (e.g., "user is usually in the living room at night")
- Predicts next likely action and proactively suggests it
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.habit_learner")


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class Observation:
    """A single observation of user or robot activity."""
    id: str
    timestamp: float
    activity_type: str      # "command", "location", "sensor", "interaction"
    activity_name: str      # e.g., "check_camera", "patrol_start", "voice_command"
    context: Dict[str, Any] = field(default_factory=dict)
    day_of_week: int = 0    # 0=Monday
    hour_of_day: int = 0    # 0-23


@dataclass
class Habit:
    """A discovered habit pattern."""
    id: str
    name: str
    activity_name: str
    frequency: float          # 0.0 - 1.0 how often this occurs
    times_of_day: List[int]   # Hours when this typically happens
    days_of_week: List[int]   # Days when this happens
    confidence: float = 0.0
    first_observed: float = 0.0
    last_observed: float = 0.0
    observation_count: int = 0
    category: str = "routine"  # "routine", "preference", "pattern"
    next_predicted: float = 0.0  # Predicted next occurrence


@dataclass
class Prediction:
    """A prediction about likely next action."""
    activity_name: str
    probability: float          # 0.0 - 1.0
    predicted_time: float       # When it's likely to happen
    based_on_habits: List[str] = field(default_factory=list)
    context_match: float = 0.0


# ── Habit Learning Engine ───────────────────────────────────────────────

class HabitLearningEngine:
    """Learns user habits and predicts future actions.

    Usage:
        engine = HabitLearningEngine()
        engine.initialize()

        # Observe an activity
        engine.observe("command", "check_camera", {"location": "living_room"})

        # Get habit predictions
        predictions = engine.predict_next_actions()

        # Get discovered habits
        habits = engine.get_habits()
    """

    _instance: Optional["HabitLearningEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._observations: List[Observation] = []
                cls._instance._habits: List[Habit] = []
                cls._instance._predictions: List[Prediction] = []
                cls._instance._store_path = Path.home() / ".config" / "tank_os" / "habits.json"
                cls._instance._min_observations = 3  # Minimum to form a habit
                cls._instance._learning_enabled = True
            return cls._instance

    def initialize(self) -> None:
        """Load existing habits and set up EventBus listeners."""
        self._load()
        self._bus.on("activity_observed", self._on_activity_observed)
        self._bus.on("predict_habits_request", self._on_predict_request)
        self._bus.on("daily_tick", self._on_daily_tick)
        logger.info("HabitLearningEngine initialized (%d observations, %d habits)",
                     len(self._observations), len(self._habits))

    def _load(self) -> None:
        """Load habits from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            self._observations = [Observation(**o) for o in data.get("observations", [])]
            self._habits = [Habit(**h) for h in data.get("habits", [])]
        except Exception as e:
            logger.warning("Failed to load habits: %s", e)

    def _save(self) -> None:
        """Persist habits to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "observations": [vars(o) for o in self._observations[-1000:]],
            "habits": [vars(h) for h in self._habits],
            "last_update": time.time(),
        }
        self._store_path.write_text(json.dumps(data, indent=2, default=str))

    # ── Observation ───────────────────────────────────────────────────

    def observe(self, activity_type: str, activity_name: str,
                context: Optional[Dict[str, Any]] = None,
                emit_event: bool = True) -> Observation:
        """Record an observation of an activity."""
        now = time.time()
        dt = datetime.fromtimestamp(now)

        obs = Observation(
            id=str(uuid.uuid4())[:8],
            timestamp=now,
            activity_type=activity_type,
            activity_name=activity_name,
            context=context or {},
            day_of_week=dt.weekday(),
            hour_of_day=dt.hour,
        )
        self._observations.append(obs)

        # Prune old observations (keep last 30 days)
        cutoff = now - 30 * 24 * 3600
        self._observations = [o for o in self._observations if o.timestamp >= cutoff]

        # Analyze for new habits
        self._analyze_habits()

        if emit_event:
            self._bus.emit(Event("activity_observed", {
                "type": activity_type, "name": activity_name,
            }, source="habit_learner"))

        return obs

    def _on_activity_observed(self, event: Event) -> None:
        """EventBus handler for observations."""
        self.observe(
            activity_type=event.data.get("type", "system"),
            activity_name=event.data.get("name", "unknown"),
            context=event.data.get("context"),
            emit_event=False,
        )

    # ── Habit analysis ────────────────────────────────────────────────

    def _analyze_habits(self) -> None:
        """Analyze observations to discover or update habits."""
        if not self._learning_enabled:
            return

        # Group observations by activity_name
        by_activity: Dict[str, List[Observation]] = defaultdict(list)
        for obs in self._observations:
            by_activity[obs.activity_name].append(obs)

        for activity_name, observations in by_activity.items():
            if len(observations) < self._min_observations:
                continue

            # Calculate frequency
            total_days = max(1, (max(o.timestamp for o in observations) -
                                 min(o.timestamp for o in observations)) / 86400)
            frequency = min(1.0, len(observations) / max(1, total_days))

            # Find peak times
            hours = [o.hour_of_day for o in observations]
            hour_counts = Counter(hours)
            peak_hours = [h for h, c in hour_counts.most_common(4) if c >= 2]

            # Find peak days
            days = [o.day_of_week for o in observations]
            day_counts = Counter(days)
            peak_days = [d for d, c in day_counts.most_common() if c >= 2]

            # Check time clustering (strong habit if clustered)
            hour_std = self._std(hours)
            is_strong_habit = hour_std < 3 and len(peak_hours) <= 2 and frequency > 0.3

            # Update or create habit
            existing = [h for h in self._habits if h.activity_name == activity_name]
            now = time.time()

            if existing:
                habit = existing[0]
                habit.frequency = frequency
                habit.times_of_day = peak_hours[:3]
                habit.days_of_week = peak_days
                habit.confidence = min(1.0, habit.confidence + 0.05)
                habit.observation_count = len(observations)
                habit.last_observed = now
                habit.category = "routine" if is_strong_habit else "pattern"
                # Predict next occurrence
                if peak_hours:
                    next_hour = min(peak_hours, key=lambda h: (h - datetime.now().hour) % 24)
                    next_time = datetime.now().replace(hour=next_hour, minute=0) + timedelta(hours=1)
                    habit.next_predicted = next_time.timestamp()
            else:
                if len(observations) >= self._min_observations * 2:
                    habit = Habit(
                        id=str(uuid.uuid4())[:8],
                        name=f"{activity_name.replace('_', ' ').title()}",
                        activity_name=activity_name,
                        frequency=frequency,
                        times_of_day=peak_hours[:3],
                        days_of_week=peak_days,
                        confidence=min(0.5, frequency * 0.8),
                        first_observed=min(o.timestamp for o in observations),
                        last_observed=now,
                        observation_count=len(observations),
                        category="routine" if is_strong_habit else "pattern",
                    )
                    if peak_hours:
                        next_hour = min(peak_hours, key=lambda h: (h - datetime.now().hour) % 24)
                        habit.next_predicted = datetime.now().replace(
                            hour=next_hour, minute=0
                        ).timestamp()
                    self._habits.append(habit)

        # Remove low-confidence habits
        self._habits = [h for h in self._habits if h.observation_count >= self._min_observations]
        self._save()

    @staticmethod
    def _std(values: List[int]) -> float:
        """Calculate standard deviation of a list of numbers."""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance ** 0.5

    # ── Prediction ────────────────────────────────────────────────────

    def predict_next_actions(self, top_k: int = 5) -> List[Prediction]:
        """Predict the most likely next actions based on habits."""
        now = time.time()
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        predictions: List[Prediction] = []

        for habit in self._habits:
            if not habit.times_of_day:
                continue

            # Check if today is a typical day for this habit
            if current_day not in habit.days_of_week and habit.days_of_week:
                continue

            # Check if current time is near a peak time
            for peak_hour in habit.times_of_day:
                hour_diff = (peak_hour - current_hour) % 24
                if hour_diff <= 3:  # Within next 3 hours
                    probability = habit.confidence * (1 - hour_diff / 3) * habit.frequency
                    if probability > 0.2:
                        predicted_time = datetime.now().replace(
                            hour=peak_hour, minute=0
                        ).timestamp()
                        if predicted_time < now:
                            predicted_time += 3600 * 24  # Next day

                        predictions.append(Prediction(
                            activity_name=habit.activity_name,
                            probability=round(probability, 2),
                            predicted_time=predicted_time,
                            based_on_habits=[habit.id],
                            context_match=round(habit.frequency, 2),
                        ))

        # Sort by probability
        predictions.sort(key=lambda p: -p.probability)
        self._predictions = predictions[:top_k]
        return self._predictions

    def _on_predict_request(self, event: Event) -> None:
        """Handle prediction requests from EventBus."""
        predictions = self.predict_next_actions()
        self._bus.emit(Event("habit_predictions", {
            "predictions": [
                {"activity": p.activity_name, "probability": p.probability}
                for p in predictions
            ],
        }, source="habit_learner"))

    def _on_daily_tick(self, event: Event) -> None:
        """Run daily analysis cycle."""
        logger.info("Daily habit analysis triggered")
        self._analyze_habits()
        predictions = self.predict_next_actions()
        if predictions:
            top = predictions[0]
            self._bus.emit(Event("habit_prediction", {
                "activity": top.activity_name,
                "probability": top.probability,
            }, source="habit_learner", priority=Priority.LOW))

    # ── Query ─────────────────────────────────────────────────────────

    def get_habits(self, min_confidence: float = 0.0) -> List[Habit]:
        """Get all discovered habits above a confidence threshold."""
        return sorted(
            [h for h in self._habits if h.confidence >= min_confidence],
            key=lambda h: -h.confidence,
        )

    def get_recent_observations(self, limit: int = 20) -> List[Observation]:
        """Get most recent observations."""
        return sorted(self._observations, key=lambda o: o.timestamp, reverse=True)[:limit]

    def get_predictions(self) -> List[Prediction]:
        """Get current predictions."""
        if not self._predictions:
            self.predict_next_actions()
        return self._predictions

    def is_habit_time(self, activity_name: str) -> bool:
        """Check if it's the typical time for a given activity."""
        for habit in self._habits:
            if habit.activity_name == activity_name:
                current_hour = datetime.now().hour
                return current_hour in habit.times_of_day
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary."""
        strong_habits = len([h for h in self._habits if h.confidence > 0.5])
        today_obs = [o for o in self._observations
                     if abs(o.timestamp - time.time()) < 86400]
        return {
            "total_observations": len(self._observations),
            "today_observations": len(today_obs),
            "habits_discovered": len(self._habits),
            "strong_habits": strong_habits,
            "active_predictions": len(self._predictions),
            "learning_enabled": self._learning_enabled,
            "top_habits": [h.activity_name for h in self.get_habits(0.5)[:5]],
        }
