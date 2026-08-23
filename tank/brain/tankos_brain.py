"""
TankOS Brain Storage System
=============================
Multi-tier memory architecture inspired by human cognition:
  Working Memory -> Episodic -> Semantic -> Procedural -> Spatial -> Evolution

Storage Tiers:
  Tier 0: RAM/VRAM (real-time, disposable)
  Tier 1: NVMe SSD (hot, recent)
  Tier 2: Large SSD (warm, historical)
  Tier 3: NAS/Archive (cold, raw)

Key Principle: Memory quality increases faster than storage consumption.
  100 GB raw -> 10 GB events -> 1 GB summaries -> 100 MB knowledge -> 10 MB policies
"""

from __future__ import annotations
import time
import json
import uuid
import hashlib
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("tank.brain")


class MemoryType(Enum):
    WORKING = "working"          # Current task context
    EPISODIC = "episodic"        # Mission/event history
    SEMANTIC = "semantic"        # Facts/knowledge
    PROCEDURAL = "procedural"    # Skills/behaviors
    SPATIAL = "spatial"          # Maps/world model
    EVOLUTION = "evolution"      # Experiments/improvements
    RAW = "raw"                  # Unprocessed sensor data


class StorageTier(Enum):
    REALTIME = 0   # RAM - current context
    HOT = 1        # NVMe - recent, frequently accessed
    WARM = 2       # SSD - historical, summaries
    COLD = 3       # NAS - archived, raw
    DELETED = 4    # Gone


@dataclass
class MemoryEntry:
    """A single memory entry."""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    memory_type: MemoryType = MemoryType.WORKING
    summary: str = ""
    content: dict = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    importance: float = 0.5
    source: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    storage_tier: StorageTier = StorageTier.REALTIME
    compressed: bool = False
    dedup_hash: str = ""


class ImportanceScorer:
    """Scores how important a memory entry is."""

    @staticmethod
    def score(event: dict) -> float:
        score = 0.0
        # Novelty
        if event.get("is_novel", False):
            score += 0.3
        # Task relevance
        if event.get("task_relevant", True):
            score += 0.2
        # Safety relevance
        if event.get("safety_relevant", False):
            score += 0.3
        # Anomaly
        if event.get("is_anomaly", False):
            score += 0.25
        # User significance
        if event.get("user_initiated", False):
            score += 0.15
        # Failure
        if event.get("status") == "error":
            score += 0.2
        # Success
        if event.get("status") == "success" and event.get("steps_count", 0) > 3:
            score += 0.1

        return min(1.0, score)


class WorkingMemory:
    """Tier 0: Real-time, volatile, fast access."""

    def __init__(self, max_size: int = 100):
        self._entries: list[dict] = []
        self._max_size = max_size
        self._current_task: dict = {}

    def update_context(self, key: str, value: Any):
        self._current_task[key] = value

    def get_context(self) -> dict:
        return dict(self._current_task)

    def add_event(self, event: dict):
        event["_timestamp"] = time.time()
        self._entries.append(event)
        if len(self._entries) > self._max_size:
            self._entries = self._entries[-self._max_size:]

    def get_recent(self, n: int = 10) -> list[dict]:
        return self._entries[-n:]

    def clear(self):
        self._entries.clear()
        self._current_task.clear()


class EpisodicMemory:
    """Tier 1: Mission/event history with temporal structure."""

    def __init__(self):
        self._episodes: list[dict] = []
        self._active_episode: Optional[dict] = None

    def start_episode(self, mission_id: str = None) -> dict:
        episode = {
            "episode_id": str(uuid.uuid4())[:8],
            "mission_id": mission_id,
            "start_time": time.time(),
            "events": [],
            "summary": "",
            "status": "active"
        }
        self._active_episode = episode
        return episode

    def add_event(self, event: dict):
        if self._active_episode:
            event["_ts"] = time.time()
            self._active_episode["events"].append(event)

    def close_episode(self, summary: str = "") -> Optional[dict]:
        if self._active_episode:
            self._active_episode["end_time"] = time.time()
            self._active_episode["status"] = "completed"
            self._active_episode["summary"] = summary
            self._active_episode["duration_s"] = (
                self._active_episode["end_time"] - self._active_episode["start_time"]
            )
            self._episodes.append(self._active_episode)
            closed = self._active_episode
            self._active_episode = None
            return closed
        return None

    def search(self, query: str = "", mission_id: str = None,
               limit: int = 10) -> list[dict]:
        results = self._episodes
        if mission_id:
            results = [e for e in results if e.get("mission_id") == mission_id]
        if query:
            q = query.lower()
            results = [e for e in results
                      if q in e.get("summary", "").lower() or
                         any(q in str(ev) for ev in e.get("events", []))]
        return results[-limit:]

    def get_stats(self) -> dict:
        total_events = sum(len(e.get("events", [])) for e in self._episodes)
        return {
            "total_episodes": len(self._episodes),
            "total_events": total_events,
            "active": self._active_episode is not None
        }


class SemanticMemory:
    """Tier 2: Facts, knowledge, learned information."""

    def __init__(self):
        self._facts: dict[str, dict] = {}
        self._knowledge_base: list[dict] = []

    def store_fact(self, key: str, value: Any, confidence: float = 0.8,
                   source: str = ""):
        self._facts[key] = {
            "value": value,
            "confidence": confidence,
            "source": source,
            "created": time.time(),
            "updated": time.time()
        }

    def get_fact(self, key: str) -> Optional[Any]:
        fact = self._facts.get(key)
        return fact["value"] if fact else None

    def add_knowledge(self, topic: str, content: str, tags: list[str] = None):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "topic": topic,
            "content": content,
            "tags": tags or [],
            "importance": ImportanceScorer.score({"task_relevant": True}),
            "created": time.time()
        }
        self._knowledge_base.append(entry)

    def search_knowledge(self, query: str, limit: int = 5) -> list[dict]:
        q = query.lower()
        results = [k for k in self._knowledge_base
                  if q in k.get("topic", "").lower() or
                     q in k.get("content", "").lower() or
                     any(q in t for t in k.get("tags", []))]
        return sorted(results, key=lambda x: x.get("importance", 0),
                     reverse=True)[:limit]

    def get_stats(self) -> dict:
        return {
            "facts": len(self._facts),
            "knowledge_entries": len(self._knowledge_base)
        }


class ProceduralMemory:
    """Skills, behaviors, learned procedures."""

    def __init__(self):
        self._skills: dict[str, dict] = {}

    def store_skill(self, name: str, steps: list[dict],
                    success_rate: float = 1.0, context: str = ""):
        if name in self._skills:
            # Update existing
            old = self._skills[name]
            old["success_rate"] = (old["success_rate"] * 0.8 + success_rate * 0.2)
            old["usage_count"] = old.get("usage_count", 0) + 1
            old["last_used"] = time.time()
        else:
            self._skills[name] = {
                "steps": steps,
                "success_rate": success_rate,
                "context": context,
                "usage_count": 1,
                "created": time.time(),
                "last_used": time.time()
            }

    def get_skill(self, name: str) -> Optional[dict]:
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        return [{"name": k, **v} for k, v in self._skills.items()]

    def get_stats(self) -> dict:
        return {"total_skills": len(self._skills)}


class SpatialMemory:
    """Maps, locations, routes, spatial knowledge."""

    def __init__(self):
        self._rooms: dict[str, dict] = {}
        self._landmarks: list[dict] = []
        self._routes: list[dict] = []
        self._occupancy_grid: list[list[int]] = []

    def add_room(self, name: str, bounds: dict, properties: dict = None):
        self._rooms[name] = {
            "bounds": bounds,
            "properties": properties or {},
            "last_observed": time.time()
        }

    def add_landmark(self, name: str, position: dict, description: str = ""):
        self._landmarks.append({
            "name": name, "position": position,
            "description": description, "timestamp": time.time()
        })

    def add_route(self, name: str, waypoints: list[dict], distance: float = 0):
        self._routes.append({
            "name": name, "waypoints": waypoints,
            "distance": distance, "created": time.time()
        })

    def get_room(self, name: str) -> Optional[dict]:
        return self._rooms.get(name)

    def find_landmark(self, query: str) -> list[dict]:
        return [l for l in self._landmarks
               if query.lower() in l.get("name", "").lower() or
                  query.lower() in l.get("description", "").lower()]

    def get_stats(self) -> dict:
        return {
            "rooms": len(self._rooms),
            "landmarks": len(self._landmarks),
            "routes": len(self._routes)
        }


class EvolutionMemory:
    """Evolution experiments, failures, improvements."""

    def __init__(self):
        self._experiments: list[dict] = []
        self._lessons: list[dict] = []

    def record_experiment(self, experiment: dict):
        experiment["_id"] = str(uuid.uuid4())[:8]
        experiment["_timestamp"] = time.time()
        self._experiments.append(experiment)

    def record_failure(self, failure: dict):
        failure["_id"] = str(uuid.uuid4())[:8]
        failure["_timestamp"] = time.time()
        self._lessons.append({
            "type": "failure",
            **failure
        })

    def record_lesson(self, lesson: dict):
        lesson["_id"] = str(uuid.uuid4())[:8]
        lesson["_timestamp"] = time.time()
        self._lessons.append(lesson)

    def get_experiments(self, status: str = None) -> list[dict]:
        if status:
            return [e for e in self._experiments if e.get("result") == status]
        return self._experiments

    def get_lessons(self, limit: int = 20) -> list[dict]:
        return self._lessons[-limit:]

    def get_stats(self) -> dict:
        return {
            "experiments": len(self._experiments),
            "accepted": sum(1 for e in self._experiments if e.get("result") == "accepted"),
            "rejected": sum(1 for e in self._experiments if e.get("result") == "rejected"),
            "lessons": len(self._lessons)
        }


class TankOSBrain:
    """
    Unified brain storage system.
    Coordinates all memory types with importance-based storage tiering.
    """

    def __init__(self):
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.spatial = SpatialMemory()
        self.evolution = EvolutionMemory()
        self._scorer = ImportanceScorer()
        self._total_stored = 0
        self._total_compressed = 0

    def observe(self, event: dict) -> MemoryEntry:
        """Observe an event and store in appropriate memory."""
        importance = self._scorer.score(event)

        entry = MemoryEntry(
            memory_type=self._determine_type(event),
            summary=event.get("summary", str(event)[:200]),
            content=event,
            importance=importance,
            source=event.get("source", "unknown"),
            tags=event.get("tags", []),
            storage_tier=self._determine_tier(importance)
        )

        # Always add to working memory
        self.working.add_event(event)

        # Add to episodic if significant
        if importance > 0.3:
            self.episodic.add_event(event)

        # Add to semantic if it's a fact
        if event.get("type") == "fact":
            self.semantic.store_fact(
                event.get("key", str(time.time())),
                event.get("value"),
                confidence=event.get("confidence", 0.8)
            )

        # Add to procedural if it's a skill
        if event.get("type") == "skill":
            self.procedural.store_skill(
                event.get("name", "unknown"),
                event.get("steps", [])
            )

        # Add to evolution if it's an experiment
        if event.get("type") == "experiment":
            self.evolution.record_experiment(event)

        self._total_stored += 1
        return entry

    def retrieve(self, query: str, context: dict = None) -> dict:
        """Retrieve relevant memories for a query."""
        results = {
            "working": self.working.get_recent(5),
            "episodic": self.episodic.search(query, limit=3),
            "semantic": self.semantic.search_knowledge(query, limit=3),
            "procedural": [],
            "spatial": [],
            "evolution": []
        }

        # Search procedural memory for matching skills
        for skill in self.procedural.list_skills():
            if query.lower() in skill["name"].lower():
                results["procedural"].append(skill)

        # Search spatial memory
        results["spatial"] = self.spatial.find_landmark(query)

        # Search evolution for lessons
        results["evolution"] = self.evolution.get_lessons(5)

        return results

    def store_knowledge(self, topic: str, content: str, tags: list[str] = None):
        """Store knowledge in semantic memory."""
        self.semantic.add_knowledge(topic, content, tags)

    def _determine_type(self, event: dict) -> MemoryType:
        t = event.get("type", "")
        type_map = {
            "fact": MemoryType.SEMANTIC,
            "skill": MemoryType.PROCEDURAL,
            "map": MemoryType.SPATIAL,
            "experiment": MemoryType.EVOLUTION,
            "mission": MemoryType.EPISODIC,
        }
        return type_map.get(t, MemoryType.WORKING)

    def _determine_tier(self, importance: float) -> StorageTier:
        if importance >= 0.8:
            return StorageTier.HOT
        elif importance >= 0.4:
            return StorageTier.WARM
        else:
            return StorageTier.REALTIME

    def get_stats(self) -> dict:
        return {
            "total_stored": self._total_stored,
            "working": {"events": len(self.working._entries)},
            "episodic": self.episodic.get_stats(),
            "semantic": self.semantic.get_stats(),
            "procedural": self.procedural.get_stats(),
            "spatial": self.spatial.get_stats(),
            "evolution": self.evolution.get_stats(),
        }


# Global singleton
BRAIN = TankOSBrain()
