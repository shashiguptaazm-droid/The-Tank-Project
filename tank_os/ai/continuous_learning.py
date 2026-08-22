"""TankOS Continuous Learning Engine — automatic learning from every action.

Learns continuously from:
- Successful actions: reinforces patterns, builds confidence
- Failed actions: identifies causes, avoids repetition
- User corrections: adapts behavior to match preferences
- Repeated patterns: forms habits and optimized workflows
- Environmental feedback: updates world model and knowledge

This engine runs as a background process, constantly analyzing new
experiences and updating the AI's understanding without requiring
manual retraining or explicit "training mode" activation.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.continuous_learning")

# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path.home() / ".config" / "tank_os" / "learning.json"
LEARN_COOLDOWN_S = 5           # Minimum seconds between learning cycles
MAX_LEARNED_PATTERNS = 500
PATTERN_MIN_OBSERVATIONS = 3   # Minimum occurrences before forming a pattern


# ── Data Models ─────────────────────────────────────────────────────────

@dataclass
class LearnedPattern:
    """A pattern learned from repeated experiences."""

    id: str
    pattern_type: str            # "action_sequence", "timing", "preference",
                                 # "success_factor", "failure_cause"
    description: str
    confidence: float = 0.5      # How confident we are in this pattern
    observation_count: int = 1
    first_observed: float = 0.0
    last_observed: float = 0.0
    success_rate: float = 0.5    # How often this pattern leads to success
    context: str = ""            # When this pattern applies
    action: str = ""             # What to do when this pattern is detected
    strength: float = 0.5       # 0.0-1.0 (strengthens with repetition)
    category: str = "general"   # "navigation", "conversation", "system", "general"
    source: str = ""            # Which component identified this pattern


@dataclass
class LearnedPreference:
    """A user preference learned from interactions."""

    id: str
    preference_key: str          # e.g., "speed", "volume", "brightness"
    value: Any = None
    confidence: float = 0.3
    observed_count: int = 1
    first_observed: float = 0.0
    last_observed: float = 0.0
    source: str = ""             # How this preference was inferred


@dataclass
class LearningInsight:
    """An insight or discovery from the learning process."""

    id: str
    insight_type: str            # "efficiency_gain", "behavior_change",
                                 # "user_preference", "error_learned",
                                 # "optimization", "new_capability"
    description: str
    impact: str = "low"          # "low", "medium", "high", "critical"
    from_experience_ids: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    applied: bool = False
    feedback: str = ""           # User feedback on this insight


# ── Continuous Learning Engine ──────────────────────────────────────────

class ContinuousLearningEngine:
    """Learns automatically from every action, outcome, and observation.

    The Continuous Learning Engine is always running in the background,
    analyzing experiences as they happen and extracting patterns, preferences,
    and insights that improve TankOS behavior over time.

    Usage:
        engine = ContinuousLearningEngine()
        engine.initialize()

        # Manual triggers
        engine.learn_from_recent_experiences()
        engine.extract_preferences()
        engine.discover_patterns()

        # Auto-mode (runs periodically)
        engine.continuous_learning_cycle()

        # Query
        patterns = engine.get_patterns()
        preferences = engine.get_preferences()
        insights = engine.get_insights()
    """

    _instance: Optional["ContinuousLearningEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._patterns: Dict[str, LearnedPattern] = {}
                cls._instance._preferences: Dict[str, LearnedPreference] = {}
                cls._instance._insights: List[LearningInsight] = []
                cls._instance._store_path = DEFAULT_STORE_PATH
                cls._instance._last_learn_time = 0.0
                cls._instance._learning_enabled = True
                cls._instance._cycle_count = 0
                cls._instance._learning_in_progress = False
                cls._instance._action_outcome_memory: Dict[str, List[str]] = defaultdict(list)
            return cls._instance

    def initialize(self) -> None:
        """Load learned knowledge and register EventBus listeners."""
        self._load()
        self._register_listeners()
        logger.info(
            "ContinuousLearningEngine initialized (%d patterns, %d preferences, %d insights)",
            len(self._patterns), len(self._preferences), len(self._insights),
        )

    def _load(self) -> None:
        """Load learned state from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for p_data in data.get("patterns", []):
                self._patterns[p_data["id"]] = LearnedPattern(**p_data)
            for pref_key, p_data in data.get("preferences", {}).items():
                self._preferences[pref_key] = LearnedPreference(**p_data)
            for i_data in data.get("insights", []):
                self._insights.append(LearningInsight(**i_data))
            logger.debug("Loaded learning state from disk")
        except Exception as e:
            logger.warning("Failed to load learning state: %s", e)

    def _save(self) -> None:
        """Persist learned knowledge to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "patterns": [vars(p) for p in self._patterns.values()],
            "preferences": {k: vars(p) for k, p in self._preferences.items()},
            "insights": [vars(i) for i in self._insights[-100:]],
            "cycle_count": self._cycle_count,
            "last_update": time.time(),
        }
        self._store_path.write_text(json.dumps(data, indent=2, default=str))

    def _register_listeners(self) -> None:
        """Register EventBus listeners for continuous learning."""
        self._bus.on("experience_recorded", self._on_experience)
        self._bus.on("learning_request", self._on_learning_request)
        self._bus.on("action_completed", self._on_action_completed)
        self._bus.on("user_feedback", self._on_user_feedback)

    # ── Pattern Learning ───────────────────────────────────────────

    def learn_from_recent_experiences(self,
                                       since: Optional[float] = None) -> List[LearnedPattern]:
        """Analyze recent experiences and extract patterns.

        Discovers:
        - Sequences of actions that frequently occur together
        - Times of day when certain actions happen
        - Conditions that lead to success or failure
        - User preferences from repeated choices

        Returns newly discovered patterns.
        """
        if self._learning_in_progress:
            return []
        self._learning_in_progress = True

        new_patterns: List[LearnedPattern] = []

        try:
            from tank_os.ai.experience_engine import ExperienceEngine
            ee = ExperienceEngine()

            since = since or (time.time() - 86400)  # Last 24 hours
            experiences = ee.query(since=since, limit=200)

            if len(experiences) < 2:
                self._learning_in_progress = False
                return new_patterns

            # Pattern 1: Action sequences (what follows what)
            new_patterns.extend(self._find_action_sequences(experiences))

            # Pattern 2: Time-based patterns
            new_patterns.extend(self._find_time_patterns(experiences))

            # Pattern 3: Success factor analysis
            new_patterns.extend(self._find_success_factors(experiences))

            # Pattern 4: Failure cause analysis
            new_patterns.extend(self._find_failure_causes(experiences))

            # Register new patterns
            for pattern in new_patterns:
                if pattern.id not in self._patterns:
                    self._patterns[pattern.id] = pattern

            # Prune if over limit
            if len(self._patterns) > MAX_LEARNED_PATTERNS * 1.1:
                self._prune_patterns()

            self._cycle_count += 1
            self._save()

        except Exception as e:
            logger.warning("Learning cycle error: %s", e)
        finally:
            self._learning_in_progress = False

        return new_patterns

    def _find_action_sequences(self,
                                experiences: List) -> List[LearnedPattern]:
        """Find sequences of actions that occur together frequently."""
        patterns: List[LearnedPattern] = []

        # Group by time proximity (within 30 seconds of each other)
        sorted_exps = sorted(experiences, key=lambda e: e.timestamp)
        sequences: Dict[str, List[tuple]] = defaultdict(list)

        for i in range(len(sorted_exps) - 1):
            curr = sorted_exps[i]
            next_exp = sorted_exps[i + 1]
            if next_exp.timestamp - curr.timestamp < 30:
                key = f"{curr.experience_type}->{next_exp.experience_type}"
                sequences[key].append((
                    curr.experience_type, next_exp.experience_type,
                    curr.outcome, next_exp.outcome,
                ))

        for seq_key, seqs in sequences.items():
            if len(seqs) >= PATTERN_MIN_OBSERVATIONS:
                types = seq_key.split("->")
                # Calculate success rate
                success_count = sum(1 for s in seqs
                                    if s[2] == "success" and s[3] == "success")
                success_rate = success_count / len(seqs)

                first_observed = min(
                    e.timestamp for e in experiences
                    if e.experience_type == types[0]
                )
                pattern = LearnedPattern(
                    id=str(uuid.uuid4())[:8],
                    pattern_type="action_sequence",
                    description=f"'{types[0]}' tends to be followed by '{types[1]}'",
                    confidence=min(1.0, success_rate + 0.2),
                    observation_count=len(seqs),
                    first_observed=first_observed,
                    last_observed=time.time(),
                    success_rate=success_rate,
                    context=f"When performing {types[0]}",
                    action=f"Consider performing {types[1]} after {types[0]}",
                    strength=min(1.0, len(seqs) / 10),
                    category=self._infer_category(types[0]),
                    source="sequence_analysis",
                )
                patterns.append(pattern)

        return patterns

    def _find_time_patterns(self, experiences: List) -> List[LearnedPattern]:
        """Find time-of-day patterns in experiences."""
        patterns: List[LearnedPattern] = []

        # Group by type and hour
        hourly: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        hourly_outcomes: Dict[str, Dict[int, Tuple[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: (0, 0))  # (successes, total)
        )

        for exp in experiences:
            dt = datetime.fromtimestamp(exp.timestamp)
            hour = dt.hour
            hourly[exp.experience_type][hour] += 1
            s, t = hourly_outcomes[exp.experience_type][hour]
            if exp.outcome == "success":
                hourly_outcomes[exp.experience_type][hour] = (s + 1, t + 1)
            else:
                hourly_outcomes[exp.experience_type][hour] = (s, t + 1)

        for exp_type, hours in hourly.items():
            peak_hour = max(hours, key=hours.get)
            peak_count = hours[peak_hour]
            total = sum(hours.values())

            if peak_count >= PATTERN_MIN_OBSERVATIONS and peak_count / total > 0.3:
                s, t = hourly_outcomes[exp_type][peak_hour]
                peak_success_rate = s / max(t, 1)

                period = "morning" if 6 <= peak_hour < 12 else \
                         "afternoon" if 12 <= peak_hour < 18 else \
                         "evening" if 18 <= peak_hour < 24 else "night"

                pattern = LearnedPattern(
                    id=str(uuid.uuid4())[:8],
                    pattern_type="timing",
                    description=f"'{exp_type}' activity peaks during {period} (around {peak_hour}:00)",
                    confidence=min(1.0, (peak_count / total) * peak_success_rate),
                    observation_count=peak_count,
                    last_observed=time.time(),
                    success_rate=peak_success_rate,
                    context=f"Time: {period}",
                    action=f"Prepare for {exp_type} during {period}",
                    strength=min(1.0, peak_count / 20),
                    category=self._infer_category(exp_type),
                    source="timing_analysis",
                )
                patterns.append(pattern)

        return patterns

    def _find_success_factors(self, experiences: List) -> List[LearnedPattern]:
        """Find conditions that correlate with successful outcomes."""
        patterns: List[LearnedPattern] = []

        # Group experiences by type and outcome
        by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for exp in experiences:
            by_type[exp.experience_type][exp.outcome] = \
                by_type[exp.experience_type].get(exp.outcome, 0) + 1

        for exp_type, outcomes in by_type.items():
            total = sum(outcomes.values())
            if total >= PATTERN_MIN_OBSERVATIONS:
                success_count = outcomes.get("success", 0)
                success_rate = success_count / total

                if success_rate > 0.8:
                    patterns.append(LearnedPattern(
                        id=str(uuid.uuid4())[:8],
                        pattern_type="success_factor",
                        description=f"'{exp_type}' has high success rate ({success_rate:.0%})",
                        confidence=success_rate,
                        observation_count=total,
                        last_observed=time.time(),
                        success_rate=success_rate,
                        context=f"Executing {exp_type}",
                        action=f"Continue current {exp_type} approach",
                        strength=min(1.0, total / 20),
                        category=self._infer_category(exp_type),
                        source="success_analysis",
                    ))
                elif success_rate < 0.3 and total >= 5:
                    pattern = LearnedPattern(
                        id=str(uuid.uuid4())[:8],
                        pattern_type="success_factor",
                        description=f"'{exp_type}' has low success rate ({success_rate:.0%}) — needs improvement",
                        confidence=1.0 - success_rate,
                        observation_count=total,
                        last_observed=time.time(),
                        success_rate=success_rate,
                        context=f"Executing {exp_type}",
                        action=f"Review and improve {exp_type} approach",
                        strength=min(1.0, total / 20),
                        category=self._infer_category(exp_type),
                        source="success_analysis",
                    )
                    patterns.append(pattern)

        return patterns

    def _find_failure_causes(self, experiences: List) -> List[LearnedPattern]:
        """Analyze failures to identify recurring causes."""
        patterns: List[LearnedPattern] = []

        failures = [e for e in experiences if e.outcome == "failure"]
        if len(failures) < PATTERN_MIN_OBSERVATIONS:
            return patterns

        # Look for common tags or types in failures
        from collections import Counter as _Counter
        type_counter = _Counter(e.experience_type for e in failures)
        common_type = type_counter.most_common(1)

        if common_type and common_type[0][1] >= PATTERN_MIN_OBSERVATIONS:
            fail_type, fail_count = common_type[0]
            total_of_type = sum(
                1 for e in experiences
                if e.experience_type == fail_type
            )
            fail_rate = fail_count / max(total_of_type, 1)

            patterns.append(LearnedPattern(
                id=str(uuid.uuid4())[:8],
                pattern_type="failure_cause",
                description=f"'{fail_type}' fails frequently — {fail_count} failures ({fail_rate:.0%} failure rate)",
                confidence=fail_rate,
                observation_count=fail_count,
                last_observed=time.time(),
                success_rate=1.0 - fail_rate,
                context=f"While executing {fail_type}",
                action=f"Investigate root cause of {fail_type} failures",
                strength=min(1.0, fail_count / 10),
                category=self._infer_category(fail_type),
                source="failure_analysis",
            ))

        return patterns

    def _infer_category(self, experience_type: str) -> str:
        """Infer a category from an experience type."""
        type_lower = experience_type.lower()
        if any(t in type_lower for t in ["navigate", "move", "dock", "patrol"]):
            return "navigation"
        if any(t in type_lower for t in ["talk", "chat", "converse", "question"]):
            return "conversation"
        if any(t in type_lower for t in ["system", "boot", "start", "stop"]):
            return "system"
        return "general"

    # ── Preference Learning ────────────────────────────────────────

    def extract_preferences(self) -> List[LearnedPreference]:
        """Analyze interactions to infer user preferences.

        Looks for patterns in:
        - Repeated parameter values (speed, volume, brightness)
        - Timing preferences (when user typically interacts)
        - Feature usage frequency
        - Correction patterns (user adjusts the AI's output)
        """
        new_preferences: List[LearnedPreference] = []

        try:
            from tank_os.ai.experience_engine import ExperienceEngine
            ee = ExperienceEngine()

            recent = ee.query(since=time.time() - 86400 * 7, limit=500)

            # Analyze experience types for feature usage frequency
            type_counts: Dict[str, int] = {}
            for exp in recent:
                type_counts[exp.experience_type] = \
                    type_counts.get(exp.experience_type, 0) + 1

            # Most used feature
            if type_counts:
                most_used = max(type_counts, key=type_counts.get)
                most_count = type_counts[most_used]

                pref = LearnedPreference(
                    id=str(uuid.uuid4())[:8],
                    preference_key="most_used_feature",
                    value=most_used,
                    confidence=min(1.0, most_count / 50),
                    observed_count=most_count,
                    last_observed=time.time(),
                    source="usage_analysis",
                )
                existing_key = self._preferences.get("most_used_feature")
                if not existing_key or existing_key.value != most_used:
                    new_preferences.append(pref)
                    self._preferences["most_used_feature"] = pref

            # Interaction time preference
            hour_counts: Dict[int, int] = {}
            for exp in recent:
                dt = datetime.fromtimestamp(exp.timestamp)
                hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1

            if hour_counts:
                peak_hour = max(hour_counts, key=hour_counts.get)
                period = "morning" if 6 <= peak_hour < 12 else \
                         "afternoon" if 12 <= peak_hour < 18 else \
                         "evening" if 18 <= peak_hour < 24 else "night"

                pref = LearnedPreference(
                    id=str(uuid.uuid4())[:8],
                    preference_key="preferred_interaction_time",
                    value=period,
                    confidence=min(1.0, hour_counts[peak_hour] / 30),
                    observed_count=hour_counts[peak_hour],
                    last_observed=time.time(),
                    source="timing_analysis",
                )
                self._preferences["preferred_interaction_time"] = pref
                new_preferences.append(pref)

        except Exception as e:
            logger.debug("Preference extraction: %s", e)

        self._save()
        return new_preferences

    # ── Insight Generation ─────────────────────────────────────────

    def generate_insights(self) -> List[LearningInsight]:
        """Generate insights from learned patterns.

        Insights highlight significant discoveries like:
        - Efficiency improvements found
        - User preferences discovered
        - Recurring problems identified
        - New capabilities demonstrated
        """
        new_insights: List[LearningInsight] = []

        now = time.time()

        # Insight from failure patterns
        failure_patterns = [
            p for p in self._patterns.values()
            if p.pattern_type == "failure_cause" and p.success_rate < 0.3
        ]
        for fp in failure_patterns[:2]:
            if not any(i.description == fp.description for i in self._insights):
                new_insights.append(LearningInsight(
                    id=str(uuid.uuid4())[:8],
                    insight_type="error_learned",
                    description=f"Learned to identify: {fp.description}",
                    impact="medium",
                    timestamp=now,
                ))

        # Insight from success patterns
        success_patterns = [
            p for p in self._patterns.values()
            if p.pattern_type == "success_factor" and p.success_rate > 0.9
            and p.observation_count >= 10
        ]
        for sp in success_patterns[:2]:
            if not any(i.description == sp.description for i in self._insights):
                new_insights.append(LearningInsight(
                    id=str(uuid.uuid4())[:8],
                    insight_type="efficiency_gain",
                    description=f"Confirmed effective: {sp.description}",
                    impact="high",
                    timestamp=now,
                ))

        # Insight from timing patterns
        timing_patterns = [
            p for p in self._patterns.values()
            if p.pattern_type == "timing" and p.confidence > 0.7
        ]
        for tp in timing_patterns[:1]:
            if not any(i.description == tp.description for i in self._insights):
                new_insights.append(LearningInsight(
                    id=str(uuid.uuid4())[:8],
                    insight_type="behavior_change",
                    description=f"Behavior pattern: {tp.description}",
                    impact="medium",
                    timestamp=now,
                ))

        self._insights.extend(new_insights)
        if len(self._insights) > 200:
            self._insights = self._insights[-200:]

        self._save()
        return new_insights

    # ── Main Learning Cycle ────────────────────────────────────────

    def continuous_learning_cycle(self) -> Dict[str, Any]:
        """Run one complete continuous learning cycle.

        Performs:
        1. Pattern discovery from recent experiences
        2. Preference extraction
        3. Insight generation

        Returns a summary of what was learned.
        """
        start = time.time()

        if self._learning_in_progress:
            return {"status": "already_running"}

        self._cycle_count += 1
        logger.info("=== Continuous Learning Cycle #%d ===", self._cycle_count)

        # Step 1: Learn patterns
        new_patterns = self.learn_from_recent_experiences()

        # Step 2: Extract preferences
        new_preferences = self.extract_preferences()

        # Step 3: Generate insights
        new_insights = self.generate_insights()

        duration = time.time() - start
        self._last_learn_time = time.time()

        result = {
            "cycle": self._cycle_count,
            "new_patterns": len(new_patterns),
            "new_preferences": len(new_preferences),
            "new_insights": len(new_insights),
            "total_patterns": len(self._patterns),
            "duration_s": round(duration, 2),
        }

        self._bus.emit(Event("learning_cycle_complete", result,
                             source="continuous_learning"))

        logger.info("Learning cycle complete: %d patterns, %d preferences, %.2fs",
                     len(new_patterns), len(new_preferences), duration)
        return result

    def set_user_feedback(self, feedback_type: str, content: str) -> LearningInsight:
        """Process explicit user feedback to guide learning."""
        insight = LearningInsight(
            id=str(uuid.uuid4())[:8],
            insight_type="user_preference",
            description=content[:200],
            impact="high" if "critical" in feedback_type.lower() else "medium",
            timestamp=time.time(),
            feedback=content,
        )
        self._insights.append(insight)
        self._save()
        return insight

    # ── Event Handlers ─────────────────────────────────────────────

    def _on_experience(self, event: Event) -> None:
        """Process new experiences as they arrive."""
        # Batch learning — triggered by experience recording
        # We don't learn on every single experience to avoid overhead
        pass

    def _on_action_completed(self, event: Event) -> None:
        """Learn from completed actions."""
        action_type = event.data.get("type", "")
        outcome = event.data.get("outcome", "")
        if action_type and outcome:
            self._action_outcome_memory[action_type].append(outcome)
            # Trigger learning when we have enough data
            if len(self._action_outcome_memory[action_type]) >= 10:
                self.continuous_learning_cycle()
                # Prune action-outcome memory to prevent unbounded growth
                for atype in list(self._action_outcome_memory.keys()):
                    self._action_outcome_memory[atype] = \
                        self._action_outcome_memory[atype][-50:]

    def _on_user_feedback(self, event: Event) -> None:
        """Process direct user feedback."""
        feedback = event.data.get("feedback", "")
        feedback_type = event.data.get("type", "general")
        if feedback:
            self.set_user_feedback(feedback_type, feedback)
            self._bus.emit(Event("insight_generated", {
                "message": f"Learned from feedback: {feedback[:80]}",
            }, source="continuous_learning"))

    def _on_learning_request(self, event: Event) -> None:
        """Handle manual learning requests."""
        action = event.data.get("action", "cycle")
        if action == "cycle":
            result = self.continuous_learning_cycle()
            self._bus.emit(Event("learning_result", result,
                                 source="continuous_learning"))
        elif action == "patterns":
            self._bus.emit(Event("learning_patterns", {
                "patterns": self._patterns_summary(),
            }, source="continuous_learning"))
        elif action == "preferences":
            self._bus.emit(Event("learning_preferences", {
                "preferences": {
                    k: {"value": v.value, "confidence": v.confidence}
                    for k, v in self._preferences.items()
                },
            }, source="continuous_learning"))

    # ── Pattern Pruning ────────────────────────────────────────────

    def _prune_patterns(self) -> None:
        """Remove low-confidence, rarely-observed patterns."""
        self._patterns = {
            pid: p for pid, p in self._patterns.items()
            if p.observation_count >= PATTERN_MIN_OBSERVATIONS
            and p.confidence >= 0.1
        }
        # Keep strongest patterns
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.strength * p.confidence,
            reverse=True,
        )
        self._patterns = {
            p.id: p for p in sorted_patterns[:MAX_LEARNED_PATTERNS]
        }

    # ── Query API ─────────────────────────────────────────────────

    def get_patterns(self, pattern_type: Optional[str] = None,
                     category: Optional[str] = None,
                     min_confidence: float = 0.0) -> List[LearnedPattern]:
        """Get learned patterns, with optional filters."""
        results = list(self._patterns.values())
        if pattern_type:
            results = [p for p in results if p.pattern_type == pattern_type]
        if category:
            results = [p for p in results if p.category == category]
        if min_confidence:
            results = [p for p in results if p.confidence >= min_confidence]
        return sorted(results, key=lambda p: -p.strength)

    def get_preferences(self) -> Dict[str, LearnedPreference]:
        """Get all learned preferences."""
        return dict(self._preferences)

    def get_insights(self, impact: Optional[str] = None,
                     limit: int = 20) -> List[LearningInsight]:
        """Get generated insights, optionally filtered by impact level."""
        results = list(self._insights)
        if impact:
            results = [i for i in results if i.impact == impact]
        return sorted(results, key=lambda i: -i.timestamp)[:limit]

    def _patterns_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all patterns for display."""
        by_type: Dict[str, List[LearnedPattern]] = {}
        for p in self._patterns.values():
            by_type.setdefault(p.pattern_type, []).append(p)
        return [
            {
                "type": ptype,
                "count": len(plist),
                "examples": [
                    {"description": p.description[:60], "confidence": p.confidence}
                    for p in plist[:3]
                ],
            }
            for ptype, plist in by_type.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get learning engine statistics."""
        return {
            "total_patterns": len(self._patterns),
            "by_type": {
                ptype: len([p for p in self._patterns.values() if p.pattern_type == ptype])
                for ptype in set(p.pattern_type for p in self._patterns.values())
            },
            "total_preferences": len(self._preferences),
            "total_insights": len(self._insights),
            "cycle_count": self._cycle_count,
            "learning_enabled": self._learning_enabled,
            "last_cycle_time": self._last_learn_time,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Quick status summary."""
        return {
            "patterns": len(self._patterns),
            "preferences": len(self._preferences),
            "insights": len(self._insights),
            "cycles": self._cycle_count,
            "enabled": self._learning_enabled,
        }
