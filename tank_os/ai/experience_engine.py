"""TankOS Experience Engine — records every interaction as structured experiences.

Every conversation, command, success, failure, observation, and sensor event is
recorded as a structured experience for future learning. Experiences are tagged,
timestamped, and stored in an append-only JSONL file.

Integrates with:
- EventBus: subscribes to all action/event types for auto-recording
- ReflectionEngine: feeds experiences for analysis
- MemoryManager: promotes important experiences to long-term memory
- HabitLearningEngine: provides observation data for pattern detection
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.experience")

# ── Constants ───────────────────────────────────────────────────────────

MAX_MEMORY_EXPERIENCES = 10000  # Keep last 10K in memory
DEFAULT_STORE_PATH = Path.home() / ".config" / "tank_os" / "experiences.jsonl"


# ── Data Models ─────────────────────────────────────────────────────────

@dataclass
class Experience:
    """A single structured experience record."""

    id: str
    timestamp: float
    experience_type: str  # "conversation", "command", "navigation", "vision",
                         # "sensor", "system", "interaction", "error", "learning"
    summary: str          # Short one-line description
    outcome: str = "unknown"  # "success", "failure", "partial", "info", "unknown"
    confidence: float = 0.0   # How confident we are in this experience
    duration_s: float = 0.0   # How long it took
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = ""          # Which component generated this
    importance: float = 0.5   # 0.0 = forget, 1.0 = vital
    related_ids: List[str] = field(default_factory=list)
    consolidated: bool = False  # Has this been summarized into long-term memory?


@dataclass
class ExperienceSummary:
    """Aggregated view of experiences over a time window."""

    period_start: float
    period_end: float
    total_count: int
    by_type: Dict[str, int]
    by_outcome: Dict[str, int]
    successes: int
    failures: int
    top_tags: List[Tuple[str, int]]
    average_importance: float
    key_events: List[Experience]


# ── Experience Engine ───────────────────────────────────────────────────

class ExperienceEngine:
    """Records every interaction as structured experiences for AI learning.

    The Experience Engine is the foundation of TankOS's learning system.
    Every module, agent, and user interaction feeds into it.

    Usage:
        engine = ExperienceEngine()
        engine.initialize()

        # Record a simple experience
        engine.record("conversation", "User asked about weather",
                       outcome="success", tags=["weather", "question"])

        # Record with rich context
        engine.record("navigation", "Docking completed",
                       outcome="success", duration_s=45.0,
                       context={"waypoint": "dock_A", "distance_m": 2.3},
                       importance=0.8)

        # Query recent experiences
        recent = engine.query(experience_type="navigation", limit=10)

        # Get daily summary
        summary = engine.daily_summary()
    """

    _instance: Optional["ExperienceEngine"] = None
    _lock = threading.Lock()

    # ── Auto-recording event type map ──────────────────────────────
    # Maps EventBus event types to experience types and extractors
    AUTO_RECORD_EVENTS: Dict[str, Dict[str, Any]] = {
        "action_completed": {
            "experience_type": "action",
            "summary": lambda d: d.get("description", "Action completed"),
            "outcome": lambda d: d.get("outcome", "unknown"),
        },
        "action_recorded": {
            "experience_type": "action",
            "summary": lambda d: d.get("description", "Action recorded"),
            "outcome": lambda d: d.get("outcome", "unknown"),
        },
        "wake_detected": {
            "experience_type": "interaction",
            "summary": lambda d: f"Wake word detected (confidence: {d.get('confidence', 0):.2f})",
            "tags": lambda d: ["wake_word", "voice"],
        },
        "intent_processed": {
            "experience_type": "conversation",
            "summary": lambda d: f"Intent: {d.get('intent', 'unknown')}",
            "outcome": lambda d: d.get("status", "unknown"),
            "tags": lambda d: ["intent", d.get("intent", "unknown")],
        },
        "navigation_goal": {
            "experience_type": "navigation",
            "summary": lambda d: f"Navigate to {d.get('target', 'unknown')}",
            "outcome": lambda d: d.get("result", "unknown"),
            "tags": lambda d: ["navigation", d.get("target", "")],
        },
        "battery_changed": {
            "experience_type": "sensor",
            "summary": lambda d: f"Battery: {d.get('percent', 0)}%",
            "tags": lambda d: ["battery", "power"],
            "importance": 0.3,
        },
        "emotion_changed": {
            "experience_type": "system",
            "summary": lambda d: f"Emotion: {d.get('name', 'neutral')}",
            "tags": lambda d: ["emotion", d.get("name", "")],
            "importance": 0.2,
        },
        "memory_stored": {
            "experience_type": "learning",
            "summary": lambda d: f"Memory stored: {d.get('type', 'episodic')}",
            "tags": lambda d: ["memory", d.get("type", "")],
        },
        "camera_detection": {
            "experience_type": "vision",
            "summary": lambda d: f"Camera detected: {d.get('objects', 'nothing')}",
            "outcome": lambda d: "success" if d.get("objects") else "info",
            "tags": lambda d: ["vision", "detection"],
        },
        "error_occurred": {
            "experience_type": "error",
            "summary": lambda d: d.get("message", "An error occurred"),
            "outcome": "failure",
            "importance": 0.9,
            "tags": lambda d: ["error", d.get("component", "")],
        },
        "estop_triggered": {
            "experience_type": "system",
            "summary": "E-STOP triggered",
            "outcome": "failure",
            "importance": 1.0,
            "tags": ["safety", "critical", "estop"],
        },
        "security_event": {
            "experience_type": "system",
            "summary": lambda d: f"Security: {d.get('event', 'unknown event')}",
            "outcome": lambda d: d.get("severity", "info"),
            "importance": 0.8,
            "tags": lambda d: ["security", d.get("event", "")],
        },
        "dock_completed": {
            "experience_type": "navigation",
            "summary": lambda d: f"Docking {'successful' if d.get('success') else 'failed'}",
            "outcome": lambda d: "success" if d.get("success") else "failure",
            "importance": 0.7,
            "tags": ["docking", "charging"],
        },
        "robot_moving": {
            "experience_type": "navigation",
            "summary": lambda d: f"Moving at {d.get('speed', 0)} m/s",
            "tags": ["movement", "drive"],
            "importance": 0.3,
        },
        "ai_response_complete": {
            "experience_type": "conversation",
            "summary": lambda d: f"AI response ({d.get('duration_ms', 0):.0f}ms)",
            "outcome": "success",
            "tags": ["ai", "response"],
        },
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._experiences: List[Experience] = []
                cls._instance._store_path: Path = DEFAULT_STORE_PATH
                cls._instance._auto_record = True
                cls._instance._listeners_registered = False
                cls._instance._total_recorded = 0
                cls._instance._daily_counts: Dict[str, int] = {}
                cls._instance._last_daily_reset = time.time()
            return cls._instance

    # ── Initialization ─────────────────────────────────────────────

    def initialize(self, store_path: Optional[str] = None) -> None:
        """Load past experiences and register EventBus listeners.

        Args:
            store_path: Optional custom path for the JSONL store.
        """
        if store_path:
            self._store_path = Path(store_path)
        self._load()
        self._register_auto_listeners()
        logger.info(
            "ExperienceEngine initialized (%d experiences loaded, auto-record=%s)",
            len(self._experiences), self._auto_record,
        )

    def _load(self) -> None:
        """Load experiences from the JSONL store."""
        if not self._store_path.exists():
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        exp = Experience(**data)
                        self._experiences.append(exp)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.debug("Skipping malformed experience line: %s", e)
            # Trim to max
            if len(self._experiences) > MAX_MEMORY_EXPERIENCES:
                self._experiences = self._experiences[-MAX_MEMORY_EXPERIENCES:]
            logger.debug("Loaded %d experiences from %s",
                         len(self._experiences), self._store_path)
        except Exception as e:
            logger.warning("Failed to load experiences: %s", e)

    def _save(self) -> None:
        """Append new experiences to the JSONL store.

        Uses append-only write mode so the file is never corrupted.
        """
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Only write experiences that haven't been persisted yet
            # We track this by comparing total_recorded vs file line count
            with open(self._store_path, "a") as f:
                for exp in self._experiences[-self._total_recorded:]:
                    if exp.id and not self._is_persisted(exp.id):
                        f.write(json.dumps(vars(exp), default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to save experiences: %s", e)

    def _is_persisted(self, exp_id: str) -> bool:
        """Check if an experience ID has already been written.

        Uses a simple set-based bloom filter to avoid O(n) checks.
        """
        if not hasattr(self, "_persisted_ids"):
            self._persisted_ids: Set[str] = set()
            if self._store_path.exists():
                try:
                    with open(self._store_path) as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                if "id" in data:
                                    self._persisted_ids.add(data["id"])
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    pass
        return exp_id in self._persisted_ids

    def _register_auto_listeners(self) -> None:
        """Register EventBus listeners for automatic experience recording."""
        if self._listeners_registered or not self._auto_record:
            return

        for event_type, config in self.AUTO_RECORD_EVENTS.items():
            self._bus.on(event_type, self._make_auto_recorder(event_type, config))

        # Register additional handlers
        self._bus.on("experience_summary_request", self._on_summary_request)
        self._bus.on("record_experience_request", self._on_record_request)

        self._listeners_registered = True
        logger.debug("Registered %d auto-record event listeners + handlers",
                     len(self.AUTO_RECORD_EVENTS) + 2)

    def _make_auto_recorder(self, event_type: str,
                            config: Dict[str, Any]) -> Callable:
        """Factory for auto-recording event handlers."""

        def handler(event: Event) -> None:
            try:
                data = event.data or {}

                # Extract fields using callable or direct values
                summary = config.get("summary", "Auto-recorded event")
                if callable(summary):
                    summary = summary(data)
                outcome = config.get("outcome", "info")
                if callable(outcome):
                    outcome = outcome(data)

                # Extract tags
                tags: List[str] = []
                tags_config = config.get("tags", [])
                if callable(tags_config):
                    tags = tags_config(data)
                elif isinstance(tags_config, list):
                    tags = list(tags_config)

                importance = config.get("importance", 0.5)

                self.record(
                    experience_type=config.get("experience_type", "system"),
                    summary=summary,
                    outcome=outcome,
                    tags=tags,
                    context=data,
                    source=event.source or event_type,
                    importance=importance,
                    emit_event=False,  # Prevent infinite loops
                )
            except Exception as e:
                logger.debug("Auto-record failed for %s: %s", event_type, e)

        return handler

    # ── Recording ──────────────────────────────────────────────────

    def record(self, experience_type: str, summary: str,
               outcome: str = "info",
               tags: Optional[List[str]] = None,
               context: Optional[Dict[str, Any]] = None,
               source: str = "",
               importance: float = 0.5,
               duration_s: float = 0.0,
               confidence: float = 0.0,
               related_ids: Optional[List[str]] = None,
               emit_event: bool = True) -> Experience:
        """Record a new experience.

        This is the primary recording method used by all TankOS components.

        Args:
            experience_type: Category (conversation, command, navigation, etc.)
            summary: Short one-line description
            outcome: success/failure/partial/info/unknown
            tags: Categorization tags
            context: Rich structured data about the experience
            source: Component that generated this experience
            importance: 0.0-1.0 (how important to remember this)
            duration_s: How long the experience took
            confidence: How confident we are in the experience data
            related_ids: IDs of related experiences
            emit_event: Whether to emit an event (avoid infinite loops)

        Returns:
            The newly created Experience instance
        """
        now = time.time()
        exp = Experience(
            id=str(uuid.uuid4())[:12],
            timestamp=now,
            experience_type=experience_type,
            summary=summary[:200],  # Cap length
            outcome=outcome,
            tags=[t.lower().strip() for t in (tags or []) if t],
            context={k: v for k, v in (context or {}).items()
                     if len(str(k)) < 100},
            source=source[:50] if source else "",
            importance=max(0.0, min(1.0, importance)),
            duration_s=abs(duration_s),
            confidence=max(0.0, min(1.0, confidence)),
            related_ids=related_ids or [],
        )

        self._experiences.append(exp)
        self._total_recorded += 1

        # Update daily counts
        today_key = datetime.now().strftime("%Y-%m-%d")
        self._daily_counts[today_key] = self._daily_counts.get(today_key, 0) + 1

        # Periodic pruning
        if len(self._experiences) > MAX_MEMORY_EXPERIENCES * 1.1:
            self._prune()

        # Periodic save (every 10 records)
        if self._total_recorded % 10 == 0:
            self._save()

        if emit_event:
            self._bus.emit(Event("experience_recorded", {
                "id": exp.id,
                "type": experience_type,
                "summary": summary[:80],
                "outcome": outcome,
                "importance": importance,
            }, source="experience_engine", priority=Priority.LOW))

        return exp

    def record_batch(self, experiences: List[Dict[str, Any]]) -> List[Experience]:
        """Record multiple experiences at once."""
        results = []
        for exp_data in experiences:
            exp = self.record(
                experience_type=exp_data.get("type", "system"),
                summary=exp_data.get("summary", ""),
                outcome=exp_data.get("outcome", "info"),
                tags=exp_data.get("tags"),
                context=exp_data.get("context"),
                source=exp_data.get("source", ""),
                importance=exp_data.get("importance", 0.5),
                emit_event=False,
            )
            results.append(exp)
        self._save()
        return results

    def _prune(self) -> None:
        """Remove old, low-importance experiences to stay within memory limits."""
        if len(self._experiences) <= MAX_MEMORY_EXPERIENCES:
            return

        # Sort by importance (ascending), then timestamp (ascending - oldest first)
        self._experiences.sort(
            key=lambda e: (e.importance, e.timestamp)
        )
        # Keep most important + most recent
        keep_count = MAX_MEMORY_EXPERIENCES
        self._experiences = self._experiences[-keep_count:]
        logger.debug("Pruned experiences to %d", len(self._experiences))

    # ── Query ──────────────────────────────────────────────────────

    def query(self, experience_type: Optional[str] = None,
              outcome: Optional[str] = None,
              source: Optional[str] = None,
              tags: Optional[List[str]] = None,
              since: float = 0.0,
              until: float = 0.0,
              min_importance: float = 0.0,
              limit: int = 50) -> List[Experience]:
        """Query experiences with flexible filters.

        Args:
            experience_type: Filter by type
            outcome: Filter by outcome
            source: Filter by source component
            tags: Filter by tags (any match)
            since: Unix timestamp for start of window
            until: Unix timestamp for end of window
            min_importance: Minimum importance threshold
            limit: Maximum results

        Returns:
            Chronologically sorted (newest first) list of experiences
        """
        results = self._experiences

        if experience_type:
            results = [e for e in results if e.experience_type == experience_type]
        if outcome:
            results = [e for e in results if e.outcome == outcome]
        if source:
            results = [e for e in results if e.source == source]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if since:
            results = [e for e in results if e.timestamp >= since]
        if until:
            results = [e for e in results if e.timestamp <= until]
        if min_importance:
            results = [e for e in results if e.importance >= min_importance]

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_failures(self, experience_type: Optional[str] = None,
                     since: float = 0.0, limit: int = 20) -> List[Experience]:
        """Quick access to all failed experiences."""
        return self.query(
            experience_type=experience_type,
            outcome="failure",
            since=since,
            limit=limit,
        )

    def get_successes(self, experience_type: Optional[str] = None,
                      since: float = 0.0, limit: int = 20) -> List[Experience]:
        """Quick access to all successful experiences."""
        return self.query(
            experience_type=experience_type,
            outcome="success",
            since=since,
            limit=limit,
        )

    def count_by_type(self, since: float = 0.0) -> Dict[str, int]:
        """Count experiences grouped by type."""
        counts: Dict[str, int] = {}
        for exp in self._experiences:
            if since and exp.timestamp < since:
                continue
            counts[exp.experience_type] = counts.get(exp.experience_type, 0) + 1
        return counts

    def count_by_outcome(self, since: float = 0.0) -> Dict[str, int]:
        """Count experiences grouped by outcome."""
        counts: Dict[str, int] = {}
        for exp in self._experiences:
            if since and exp.timestamp < since:
                continue
            counts[exp.outcome] = counts.get(exp.outcome, 0) + 1
        return counts

    # ── Summaries ──────────────────────────────────────────────────

    def daily_summary(self) -> ExperienceSummary:
        """Generate a summary of today's experiences.

        Returns an ExperienceSummary with aggregated statistics.
        """
        now = time.time()
        day_start = now - 86400

        today_exps = [e for e in self._experiences if e.timestamp >= day_start]

        by_type: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        successes = 0
        failures = 0

        tag_counter: Dict[str, int] = {}
        total_importance = 0.0

        for exp in today_exps:
            by_type[exp.experience_type] = by_type.get(exp.experience_type, 0) + 1
            by_outcome[exp.outcome] = by_outcome.get(exp.outcome, 0) + 1
            if exp.outcome == "success":
                successes += 1
            elif exp.outcome == "failure":
                failures += 1
            total_importance += exp.importance
            for tag in exp.tags:
                tag_counter[tag] = tag_counter.get(tag, 0) + 1

        top_tags = sorted(tag_counter.items(), key=lambda x: -x[1])[:10]
        avg_importance = total_importance / max(1, len(today_exps))

        # Get key events (high importance)
        key_events = sorted(
            [e for e in today_exps if e.importance >= 0.7],
            key=lambda e: -e.timestamp,
        )[:5]

        return ExperienceSummary(
            period_start=day_start,
            period_end=now,
            total_count=len(today_exps),
            by_type=by_type,
            by_outcome=by_outcome,
            successes=successes,
            failures=failures,
            top_tags=top_tags,
            average_importance=round(avg_importance, 3),
            key_events=key_events,
        )

    def weekly_summary(self) -> ExperienceSummary:
        """Generate a summary of the last 7 days."""
        return self._period_summary(7 * 86400)

    def monthly_summary(self) -> ExperienceSummary:
        """Generate a summary of the last 30 days."""
        return self._period_summary(30 * 86400)

    def _period_summary(self, seconds: float) -> ExperienceSummary:
        """Generate a summary for a given period."""
        now = time.time()
        period_start = now - seconds

        period_exps = [e for e in self._experiences if e.timestamp >= period_start]

        return ExperienceSummary(
            period_start=period_start,
            period_end=now,
            total_count=len(period_exps),
            by_type=self.count_by_type(since=period_start),
            by_outcome=self.count_by_outcome(since=period_start),
            successes=sum(1 for e in period_exps if e.outcome == "success"),
            failures=sum(1 for e in period_exps if e.outcome == "failure"),
            top_tags=self._top_tags(period_exps, 10),
            average_importance=round(
                sum(e.importance for e in period_exps) / max(1, len(period_exps)), 3
            ),
            key_events=sorted(
                [e for e in period_exps if e.importance >= 0.7],
                key=lambda e: -e.timestamp,
            )[:5],
        )

    @staticmethod
    def _top_tags(experiences: List[Experience], n: int = 10) -> List[Tuple[str, int]]:
        tag_counts: Dict[str, int] = {}
        for exp in experiences:
            for tag in exp.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return sorted(tag_counts.items(), key=lambda x: -x[1])[:n]

    # ── Export ─────────────────────────────────────────────────────

    def export_json(self, filepath: str, limit: int = 1000) -> bool:
        """Export experiences to a JSON file."""
        try:
            export_path = Path(filepath)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            data = [vars(e) for e in self._experiences[-limit:]]
            export_path.write_text(
                json.dumps(data, indent=2, default=str)
            )
            logger.info("Exported %d experiences to %s", len(data), filepath)
            return True
        except Exception as e:
            logger.warning("Export failed: %s", e)
            return False

    def get_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get a timeline of recent experiences suitable for display."""
        since = time.time() - hours * 3600
        recent = [e for e in self._experiences if e.timestamp >= since]
        return [
            {
                "time": datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S"),
                "type": e.experience_type,
                "summary": e.summary,
                "outcome": e.outcome,
                "importance": e.importance,
            }
            for e in reversed(recent[-100:])
        ]

    # ── Consolidation ──────────────────────────────────────────────

    def find_consolidation_candidates(self,
                                      min_age_hours: float = 24,
                                      min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Find patterns of repeated experiences that could be consolidated.

        Returns a list of pattern groups where similar experiences occurred
        multiple times, suggesting they could be consolidated into a single
        long-term memory.
        """
        now = time.time()
        cutoff = now - min_age_hours * 3600

        # Group by type + outcome + first tag
        groups: Dict[str, List[Experience]] = {}
        for exp in self._experiences:
            if exp.timestamp > cutoff and not exp.consolidated:
                key = f"{exp.experience_type}:{exp.outcome}:{exp.tags[0] if exp.tags else 'none'}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(exp)

        candidates = []
        for key, group in groups.items():
            if len(group) >= min_occurrences:
                type_part, outcome_part, tag_part = key.split(":", 2)
                candidates.append({
                    "pattern": f"{len(group)}x {type_part} ({outcome_part})",
                    "experience_type": type_part,
                    "outcome": outcome_part,
                    "primary_tag": tag_part,
                    "count": len(group),
                    "example_summary": group[0].summary,
                    "experience_ids": [e.id for e in group],
                    "time_span_h": round(
                        (max(e.timestamp for e in group) -
                         min(e.timestamp for e in group)) / 3600, 1
                    ),
                })

        candidates.sort(key=lambda c: -c["count"])
        return candidates

    def mark_consolidated(self, experience_ids: List[str]) -> None:
        """Mark experiences as consolidated (summarized into long-term memory)."""
        id_set = set(experience_ids)
        for exp in self._experiences:
            if exp.id in id_set:
                exp.consolidated = True

    # ── EventBus integration ───────────────────────────────────────

    def _on_record_request(self, event: Event) -> None:
        """Handle external record requests via EventBus."""
        data = event.data
        self.record(
            experience_type=data.get("type", "system"),
            summary=data.get("summary", ""),
            outcome=data.get("outcome", "info"),
            tags=data.get("tags"),
            context=data.get("context"),
            source=event.source or "external",
            importance=data.get("importance", 0.5),
            emit_event=False,
        )

    def _on_summary_request(self, event: Event) -> None:
        """Handle summary requests via EventBus."""
        period = event.data.get("period", "daily")
        if period == "daily":
            summary = self.daily_summary()
        elif period == "weekly":
            summary = self.weekly_summary()
        else:
            summary = self.monthly_summary()

        self._bus.emit(Event("experience_summary", {
            "period": period,
            "total": summary.total_count,
            "successes": summary.successes,
            "failures": summary.failures,
            "top_tags": [t for t, _ in summary.top_tags[:5]],
            "key_events": [e.summary for e in summary.key_events],
        }, source="experience_engine"))

    # ── Query API ──────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Get a quick status summary of the engine."""
        now = time.time()
        today_count = sum(
            1 for e in self._experiences
            if e.timestamp >= now - 86400
        )
        return {
            "total_experiences": len(self._experiences),
            "total_recorded": self._total_recorded,
            "today_count": today_count,
            "auto_record": self._auto_record,
            "daily_counts": dict(self._daily_counts),
            "types": self.count_by_type(since=now - 86400 * 7),
            "success_rate": self._success_rate(),
        }

    def _success_rate(self) -> float:
        recent = [e for e in self._experiences[-200:]
                  if e.outcome in ("success", "failure")]
        if not recent:
            return 0.0
        successes = sum(1 for e in recent if e.outcome == "success")
        return round(successes / len(recent), 3)
