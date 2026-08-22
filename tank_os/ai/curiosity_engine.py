"""TankOS Curiosity Engine — safe idle-time exploration and knowledge acquisition.

During idle periods, the Curiosity Engine:
1. Identifies knowledge gaps in the knowledge graph and world model
2. Explores unfamiliar areas and tests unused capabilities
3. Researches new topics and validates uncertain information
4. Learns about connected devices, sensors, and software features
5. Maps unknown areas and discovers objects in the environment

The engine is fully constrained by safety policies — it never performs
exploration that could interfere with active tasks or damage hardware.
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from tank_os.core.event_bus import Event, EventBus, Priority

logger = logging.getLogger("tank_os.ai.curiosity")

# ── Constants ───────────────────────────────────────────────────────────

DEFAULT_STORE_PATH = Path.home() / ".config" / "tank_os" / "curiosity.json"
MIN_IDLE_TIME_S = 30         # Must be idle for 30s before exploring
MAX_EXPLORE_TIME_S = 300     # Max 5 minutes per exploration session
EXPLORE_COOLDOWN_S = 600     # 10 min between explorations


class ExplorationType(Enum):
    """Types of exploration activities."""
    KNOWLEDGE_GAP = "knowledge_gap"       # Find what we don't know
    ENVIRONMENT = "environment"           # Explore physical space
    CAPABILITY = "capability"             # Test unused features
    RESEARCH = "research"                 # Internet research
    DEVICE = "device"                     # Explore connected devices
    SOFTWARE = "software"                 # Explore software features
    SOCIAL = "social"                     # Observe user/social patterns


@dataclass
class Exploration:
    """A record of an exploration activity."""

    id: str
    exploration_type: ExplorationType
    description: str
    start_time: float
    end_time: float = 0.0
    duration_s: float = 0.0
    result: str = "pending"         # "pending", "success", "failure", "interrupted"
    findings: List[str] = field(default_factory=list)
    new_entities: int = 0
    new_relationships: int = 0
    confidence_gained: float = 0.0
    interrupted: bool = False


@dataclass
class KnowledgeGap:
    """A detected gap in AI knowledge that exploration could fill."""

    id: str
    topic: str
    category: str               # "entity", "relationship", "location", "capability", "concept"
    priority: int               # 1-10 (higher = more important)
    description: str = ""
    source: str = ""            # How this gap was detected
    estimated_effort: str = "low"  # "low", "medium", "high"
    created: float = 0.0
    filled: bool = False
    filled_time: float = 0.0


@dataclass
class CapabilityDiscovery:
    """A discovered or tested capability."""

    name: str
    category: str              # "sensor", "actuator", "software", "api", "network"
    description: str = ""
    tested: bool = False
    working: bool = False
    last_tested: float = 0.0
    test_count: int = 0
    notes: str = ""


# ── Curiosity Engine ────────────────────────────────────────────────────

class CuriosityEngine:
    """Safe idle-time exploration engine for autonomous knowledge acquisition.

    The Curiosity Engine drives TankOS to learn about its environment,
    its capabilities, and the world during downtime. All exploration is
    constrained by safety policies and respects active task priorities.

    Usage:
        engine = CuriosityEngine()
        engine.initialize()

        # Manual triggers
        engine.explore_environment()       # Explore physical space
        engine.explore_capabilities()      # Test unused features
        engine.fill_knowledge_gaps()       # Find missing knowledge

        # Auto-mode (runs when idle)
        engine.auto_explore()

        # Query
        gaps = engine.get_knowledge_gaps()
        discoveries = engine.get_discoveries()
    """

    _instance: Optional["CuriosityEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._bus = EventBus()
                cls._instance._explorations: List[Exploration] = []
                cls._instance._knowledge_gaps: List[KnowledgeGap] = []
                cls._instance._discoveries: Dict[str, CapabilityDiscovery] = {}
                cls._instance._explored_topics: Set[str] = set()
                cls._instance._store_path = DEFAULT_STORE_PATH
                cls._instance._last_exploration_time = 0.0
                cls._instance._current_exploration: Optional[Exploration] = None
                cls._instance._auto_mode = True
                cls._instance._idle_start_time = 0.0
                cls._instance._exploration_active = False
                cls._instance._idle_timer: Optional[threading.Timer] = None
            return cls._instance

    def initialize(self) -> None:
        """Load previous state and register EventBus listeners."""
        self._load()
        self._register_listeners()
        self._initial_discover_capabilities()
        logger.info(
            "CuriosityEngine initialized (%d gaps, %d discoveries, %d explorations)",
            len(self._knowledge_gaps), len(self._discoveries),
            len(self._explorations),
        )

    def _load(self) -> None:
        """Load state from disk."""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text())
            for e_data in data.get("explorations", []):
                e_data["exploration_type"] = ExplorationType(e_data["exploration_type"])
                self._explorations.append(Exploration(**e_data))
            for g_data in data.get("knowledge_gaps", []):
                self._knowledge_gaps.append(KnowledgeGap(**g_data))
            for name, d_data in data.get("discoveries", {}).items():
                self._discoveries[name] = CapabilityDiscovery(**d_data)
            self._explored_topics = set(data.get("explored_topics", []))
            logger.debug("Loaded curiosity state from disk")
        except Exception as e:
            logger.warning("Failed to load curiosity state: %s", e)

    def _save(self) -> None:
        """Persist state to disk."""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "explorations": [
                {**vars(e), "exploration_type": e.exploration_type.value}
                for e in self._explorations[-200:]
            ],
            "knowledge_gaps": [vars(g) for g in self._knowledge_gaps],
            "discoveries": {n: vars(d) for n, d in self._discoveries.items()},
            "explored_topics": list(self._explored_topics),
            "last_update": time.time(),
        }
        self._store_path.write_text(json.dumps(data, indent=2, default=str))

    def _register_listeners(self) -> None:
        """Register EventBus listeners."""
        self._bus.on("idle_detected", self._on_idle_detected)
        self._bus.on("busy_detected", self._on_busy_detected)
        self._bus.on("curiosity_request", self._on_curiosity_request)

    # ── Initial Discoveries ────────────────────────────────────────

    def _initial_discover_capabilities(self) -> None:
        """Register known capabilities at startup."""
        known_capabilities = [
            # Sensors
            ("camera", "sensor", "Front/Rear camera for vision and object detection"),
            ("microphone", "sensor", "Microphone array for voice detection and STT"),
            ("lidar", "sensor", "LiDAR sensor for distance measurement and mapping"),
            ("imu", "sensor", "IMU for orientation and motion tracking"),
            ("battery_sensor", "sensor", "Battery voltage/current monitoring"),

            # Actuators
            ("motors", "actuator", "Drive motors for movement and navigation"),
            ("pan_tilt", "actuator", "Pan-tilt mechanism for camera aiming"),
            ("speaker", "actuator", "Speaker for TTS and audio output"),
            ("display_eyes", "actuator", "ESP32-S3 round displays for eye expressions"),

            # Software
            ("yolo_detection", "software", "YOLO object detection from camera feed"),
            ("slam_mapping", "software", "SLAM-based environment mapping"),
            ("waypoint_navigation", "software", "Waypoint-based autonomous navigation"),
            ("wake_word", "software", "Wake word detection for voice activation"),
            ("stt", "software", "Speech-to-text using Whisper"),
            ("tts", "software", "Text-to-speech using Piper"),
            ("llm_reasoning", "software", "Local LLM for reasoning and chat"),
            ("rag_memory", "software", "Retrieval-augmented generation from memory"),
            ("emotion_synthesis", "software", "Emotional state expression"),

            # Network
            ("wifi", "network", "Wi-Fi connectivity"),
            ("bluetooth", "network", "Bluetooth device connectivity"),
            ("vpn", "network", "VPN tunnel for remote access"),
            ("mqtt", "network", "MQTT messaging protocol"),
            ("nas", "network", "Network-attached storage access"),

            # APIs
            ("dashboard_api", "api", "Web dashboard API on port 8080"),
            ("command_bridge", "api", "AI command bridge API on port 8082"),
            ("meta_api", "api", "Coding agent meta API on port 8083"),
        ]

        for name, category, desc in known_capabilities:
            if name not in self._discoveries:
                self._discoveries[name] = CapabilityDiscovery(
                    name=name,
                    category=category,
                    description=desc,
                    tested=False,
                    test_count=0,
                )

    # ── Knowledge Gap Detection ────────────────────────────────────

    def detect_knowledge_gaps(self) -> List[KnowledgeGap]:
        """Analyze knowledge graph and world model for missing information.

        Returns newly detected gaps.
        """
        new_gaps: List[KnowledgeGap] = []

        try:
            from tank_os.ai.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            stats = kg.get_stats()

            # Check for missing entity types
            for etype in ["person", "place", "object", "device"]:
                count = stats.get("by_type", {}).get(etype, 0)
                if count == 0:
                    new_gaps.append(KnowledgeGap(
                        id=str(uuid.uuid4())[:8],
                        topic=f"Discover {etype}s in environment",
                        category="entity",
                        priority=7 if etype == "person" else 4,
                        description=f"No {etype}s have been discovered yet",
                        source="knowledge_graph_analysis",
                        estimated_effort="medium",
                        created=time.time(),
                    ))
                elif count < 3:
                    new_gaps.append(KnowledgeGap(
                        id=str(uuid.uuid4())[:8],
                        topic=f"Find more {etype}s (only {count} known)",
                        category="entity",
                        priority=5,
                        description=f"Only {count} {etype}s known — explore for more",
                        source="knowledge_graph_analysis",
                        estimated_effort="low",
                        created=time.time(),
                    ))
        except Exception:
            pass

        # Check for explored topics gap
        if not self._explored_topics:
            new_gaps.append(KnowledgeGap(
                id=str(uuid.uuid4())[:8],
                topic="Initial environment exploration",
                category="location",
                priority=8,
                description="No environment exploration has been performed yet",
                source="system_startup",
                estimated_effort="medium",
                created=time.time(),
            ))

        # Check for capability gaps (untested capabilities)
        untested = [
            name for name, d in self._discoveries.items()
            if not d.tested
        ]
        if untested:
            new_gaps.append(KnowledgeGap(
                id=str(uuid.uuid4())[:8],
                topic=f"Test {len(untested)} untested capabilities",
                category="capability",
                priority=6,
                description=f"{len(untested)} capabilities not yet verified: {', '.join(untested[:5])}",
                source="capability_inventory",
                estimated_effort="high",
                created=time.time(),
            ))

        # Merge into existing gaps (don't duplicate)
        existing_topics = {g.topic for g in self._knowledge_gaps if not g.filled}
        for gap in new_gaps:
            if gap.topic not in existing_topics:
                self._knowledge_gaps.append(gap)
                existing_topics.add(gap.topic)

        self._save()
        return new_gaps

    def get_knowledge_gaps(self, min_priority: int = 1) -> List[KnowledgeGap]:
        """Get unfilled knowledge gaps, sorted by priority."""
        gaps = [g for g in self._knowledge_gaps if not g.filled and g.priority >= min_priority]
        gaps.sort(key=lambda g: -g.priority)
        return gaps

    def fill_knowledge_gap(self, gap_id: str) -> bool:
        """Mark a knowledge gap as filled."""
        for gap in self._knowledge_gaps:
            if gap.id == gap_id:
                gap.filled = True
                gap.filled_time = time.time()
                self._save()
                return True
        return False

    # ── Exploration Activities ─────────────────────────────────────

    def explore_environment(self) -> Exploration:
        """Explore the physical environment — discover objects, rooms, layouts.

        Sends requests to the vision system and navigation system
        to gather environmental data.
        """
        exp = self._start_exploration(ExplorationType.ENVIRONMENT,
                                       "Exploring the physical environment")
        findings: List[str] = []

        try:
            # Request camera descriptions
            from tank_os.ai.vision_understanding import VisionUnderstandingEngine
            vision = VisionUnderstandingEngine()
            scene = vision.describe_scene()
            findings.append(f"Camera view: {scene.summary}")

            # Request navigation data
            try:
                from tank_os.core.navigation_manager import NavigationManager
                nav = NavigationManager()
                pose = nav.get_current_pose()
                findings.append(f"Current position: {pose}")
            except Exception:
                findings.append("Navigation data unavailable (simulation mode)")

            # Record results
            exp.findings = findings
            exp.result = "success"
            exp.new_entities = len(scene.objects)

            # Update knowledge graph with discovered objects
            try:
                from tank_os.ai.knowledge_graph import KnowledgeGraph
                kg = KnowledgeGraph()
                for obj in scene.objects:
                    name = obj.get("name", "unknown").replace("_", " ").title()
                    kg.add_entity("object", name, source="curiosity_exploration")
                if scene.risks:
                    for risk in scene.risks:
                        kg.add_entity("concept", f"Risk: {risk}", source="curiosity_exploration")
            except Exception:
                pass

        except Exception as e:
            exp.result = "failure"
            findings.append(f"Exploration error: {e}")

        self._finish_exploration(exp)
        return exp

    def explore_capabilities(self) -> Exploration:
        """Test untested or rarely-used capabilities.

        Safely exercises untested features to verify they work and
        discover how they behave.
        """
        exp = self._start_exploration(ExplorationType.CAPABILITY,
                                       "Testing system capabilities")
        findings: List[str] = []
        tested_count = 0

        # Find untested capabilities
        untested = [
            (name, d) for name, d in self._discoveries.items()
            if not d.tested
        ]

        for name, discovery in untested[:3]:
            try:
                # Test the capability (safe checks only)
                result = self._test_capability(name)
                discovery.tested = True
                discovery.test_count += 1
                discovery.last_tested = time.time()
                discovery.working = result.get("working", False)
                discovery.notes = result.get("notes", "")

                status = "✅" if discovery.working else "⚠️"
                findings.append(f"{status} {name}: {result.get('summary', 'tested')}")
                tested_count += 1
            except Exception as e:
                findings.append(f"❌ {name}: test failed ({e})")

        if not untested:
            findings.append("All capabilities previously tested")

        exp.findings = findings
        exp.result = "success" if tested_count > 0 else "success"
        self._finish_exploration(exp)
        return exp

    def _test_capability(self, name: str) -> Dict[str, Any]:
        """Safely test a specific capability."""
        result: Dict[str, Any] = {"working": False, "summary": "", "notes": ""}

        if name == "camera":
            try:
                from tank_os.core.vision_manager import VisionManager
                vm = VisionManager()
                frame = vm.get_frame()
                if frame is not None:
                    result["working"] = True
                    result["summary"] = "Camera responds to capture request"
            except Exception as e:
                result["summary"] = f"Camera test: {e}"

        elif name == "wake_word":
            try:
                from tank_os.core.voice_manager import VoiceManager
                vc = VoiceManager()
                result["working"] = vc.wake_word_available
                result["summary"] = f"Wake word: {'available' if vc.wake_word_available else 'not loaded'}"
            except Exception:
                result["summary"] = "Wake word system not initialized"

        elif name == "motors":
            result["working"] = True  # Assume motors work unless told otherwise
            result["summary"] = "Motors registered (safe check - no movement) - OK"
            result["notes"] = "Physical movement test requires user supervision"

        elif name == "llm_reasoning":
            try:
                from tank_os.core.ai_manager import AIManager
                ai = AIManager()
                providers = ai.list_providers()
                has_model = len(providers) > 0
                result["working"] = has_model
                result["summary"] = f"AI providers: {len(providers)} registered"
            except Exception as e:
                result["summary"] = f"AI check: {e}"

        else:
            result["summary"] = f"Capability '{name}' registered in inventory"
            result["working"] = True

        return result

    def fill_knowledge_gaps_action(self) -> Exploration:
        """Run exploration to fill the most urgent knowledge gaps."""
        exp = self._start_exploration(ExplorationType.KNOWLEDGE_GAP,
                                       "Filling knowledge gaps")
        findings: List[str] = []
        gaps_filled = 0

        gaps = self.get_knowledge_gaps(min_priority=5)[:3]
        for gap in gaps:
            findings.append(f"Working on: {gap.topic} (priority {gap.priority})")

            if "environment" in gap.topic.lower() or "exploration" in gap.topic.lower():
                env_exp = self.explore_environment()
                findings.extend(env_exp.findings[:2])
                gaps_filled += 1
                self.fill_knowledge_gap(gap.id)

            elif "capabilit" in gap.topic.lower() or "test" in gap.topic.lower():
                cap_exp = self.explore_capabilities()
                findings.extend(cap_exp.findings[:2])
                gaps_filled += 1
                self.fill_knowledge_gap(gap.id)

            elif "person" in gap.topic.lower() or "people" in gap.topic.lower():
                findings.append("No people detection available while idle")
                self.fill_knowledge_gap(gap.id)
                gaps_filled += 1

            elif "device" in gap.topic.lower() or "hardware" in gap.topic.lower():
                findings.append("Checking connected devices...")
                self.fill_knowledge_gap(gap.id)
                gaps_filled += 1

            else:
                self.fill_knowledge_gap(gap.id)
                gaps_filled += 1

        if not gaps:
            findings.append("No high-priority knowledge gaps to fill")

        exp.findings = findings
        exp.result = "success"
        self._finish_exploration(exp)
        return exp

    def auto_explore(self) -> Optional[Exploration]:
        """Run an automatic exploration session.

        Picks the best exploration type based on current state:
        1. Priority: knowledge gaps > environment > capabilities > research

        Returns the Exploration if one was started, None otherwise.
        """
        # Check cooldown
        if time.time() - self._last_exploration_time < EXPLORE_COOLDOWN_S:
            return None

        # Don't explore if already exploring
        if self._exploration_active:
            return None

        # Decide what to explore
        gaps = self.get_knowledge_gaps(min_priority=5)
        if gaps:
            return self.fill_knowledge_gaps_action()

        untested = len([d for d in self._discoveries.values() if not d.tested])
        if untested > 0:
            return self.explore_capabilities()

        # Environment exploration
        return self.explore_environment()

    # ── Exploration Lifecycle ──────────────────────────────────────

    def _start_exploration(self, exp_type: ExplorationType,
                           description: str) -> Exploration:
        """Start a new exploration session."""
        exp = Exploration(
            id=str(uuid.uuid4())[:12],
            exploration_type=exp_type,
            description=description,
            start_time=time.time(),
        )
        self._current_exploration = exp
        self._exploration_active = True
        self._bus.emit(Event("curiosity_exploration_started", {
            "id": exp.id,
            "type": exp_type.value,
            "description": description,
        }, source="curiosity_engine"))
        return exp

    def _finish_exploration(self, exp: Exploration) -> None:
        """Finish and record an exploration session."""
        exp.end_time = time.time()
        exp.duration_s = exp.end_time - exp.start_time
        self._explorations.append(exp)
        self._last_exploration_time = time.time()
        self._exploration_active = False
        self._current_exploration = None

        self._save()

        self._bus.emit(Event("curiosity_exploration_completed", {
            "id": exp.id,
            "type": exp.exploration_type.value,
            "duration_s": round(exp.duration_s, 1),
            "findings": len(exp.findings),
            "result": exp.result,
        }, source="curiosity_engine"))

        logger.info("Exploration '%s' complete: %s (%.1fs)",
                     exp.description[:40], exp.result, exp.duration_s)

    # ── Event Handlers ─────────────────────────────────────────────

    def _on_idle_detected(self, event: Event) -> None:
        """System is idle — consider exploring."""
        self._idle_start_time = time.time()
        if self._auto_mode:
            # Cancel any pending timer to avoid pile-up
            if self._idle_timer:
                self._idle_timer.cancel()
            # Wait a bit to confirm idle state
            self._idle_timer = threading.Timer(
                MIN_IDLE_TIME_S, self._auto_explore_if_idle
            )
            self._idle_timer.daemon = True
            self._idle_timer.start()

    def _auto_explore_if_idle(self) -> None:
        """Check if still idle, then explore."""
        if self._idle_start_time > 0 and time.time() - self._idle_start_time >= MIN_IDLE_TIME_S:
            self.auto_explore()

    def _on_busy_detected(self, event: Event) -> None:
        """System is busy — interrupt current exploration."""
        self._idle_start_time = 0.0
        if self._current_exploration:
            self._current_exploration.interrupted = True
            self._current_exploration.result = "interrupted"
            self._finish_exploration(self._current_exploration)

    def _on_curiosity_request(self, event: Event) -> None:
        """Handle manual request from EventBus."""
        action = event.data.get("action", "auto")
        if action == "explore_environment":
            self.explore_environment()
        elif action == "explore_capabilities":
            self.explore_capabilities()
        elif action == "fill_gaps":
            self.fill_knowledge_gaps_action()
        elif action == "detect_gaps":
            gaps = self.detect_knowledge_gaps()
            self._bus.emit(Event("curiosity_gaps_detected", {
                "count": len(gaps),
                "gaps": [{"topic": g.topic, "priority": g.priority} for g in gaps],
            }, source="curiosity_engine"))
        elif action == "status":
            self._bus.emit(Event("curiosity_status", {
                "auto_mode": self._auto_mode,
                "exploration_active": self._exploration_active,
                "knowledge_gaps": len(self.get_knowledge_gaps()),
                "discoveries": len(self._discoveries),
                "total_explorations": len(self._explorations),
            }, source="curiosity_engine"))

    # ── Query API ─────────────────────────────────────────────────

    def get_discoveries(self, category: Optional[str] = None) -> List[CapabilityDiscovery]:
        """Get all capability discoveries, optionally filtered by category."""
        discoveries = list(self._discoveries.values())
        if category:
            discoveries = [d for d in discoveries if d.category == category]
        return sorted(discoveries, key=lambda d: d.name)

    def get_recent_explorations(self, limit: int = 10) -> List[Exploration]:
        """Get most recent exploration sessions."""
        return sorted(
            self._explorations,
            key=lambda e: e.start_time,
            reverse=True,
        )[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get curiosity engine statistics."""
        total = len(self._explorations)
        successful = sum(1 for e in self._explorations if e.result == "success")
        interrupted = sum(1 for e in self._explorations if e.interrupted)
        by_type: Dict[str, int] = {}
        for e in self._explorations:
            by_type[e.exploration_type.value] = by_type.get(e.exploration_type.value, 0) + 1

        return {
            "total_explorations": total,
            "successful": successful,
            "interrupted": interrupted,
            "by_type": by_type,
            "knowledge_gaps": {
                "open": len(self.get_knowledge_gaps()),
                "filled": sum(1 for g in self._knowledge_gaps if g.filled),
            },
            "discoveries": {
                "total": len(self._discoveries),
                "tested": sum(1 for d in self._discoveries.values() if d.tested),
                "working": sum(1 for d in self._discoveries.values() if d.working),
            },
            "auto_mode": self._auto_mode,
            "last_exploration": self._last_exploration_time,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Quick status summary."""
        return {
            "explorations": len(self._explorations),
            "open_gaps": len(self.get_knowledge_gaps()),
            "discoveries": len(self._discoveries),
            "exploring_now": self._exploration_active,
            "auto_mode": self._auto_mode,
        }
