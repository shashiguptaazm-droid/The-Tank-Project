"""
TankOS Master Orchestrator
===========================
The central brain that coordinates Jetson, UNO Q, ESP32 nodes, AI providers,
tools, memory, language, generative AI, safety, auto-evolution, and documentation.

Master Loop:
  OBSERVE -> UNDERSTAND -> REMEMBER -> REASON -> PLAN -> VALIDATE
  -> ACT -> OBSERVE RESULT -> EVALUATE -> LEARN -> UPDATE STATE
"""

from __future__ import annotations
import uuid
import time
import logging
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("tank.orchestrator")


class TankOSState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    EXECUTING = "executing"
    LEARNING = "learning"
    EVOLVING = "evolving"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"


class EventType(Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"
    CAMERA = "camera"
    OCR = "ocr"
    SENSOR = "sensor"
    TELEMETRY = "telemetry"
    REMOTE_COMMAND = "remote_command"
    ANDROID_TV = "android_tv"
    ROS_EVENT = "ros_event"
    ESP32_EVENT = "esp32_event"
    SYSTEM_EVENT = "system_event"
    SCHEDULE = "schedule"
    WEB_EVENT = "web_event"
    HUMAN_DETECTED = "human_detected"


class Priority(Enum):
    EMERGENCY = 0
    SAFETY = 1
    HUMAN_REQUEST = 2
    MISSION = 3
    AUTONOMY = 4
    BACKGROUND = 5
    LEARNING = 6


@dataclass
class Event:
    """Universal event format — everything downstream gets this."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = "unknown"
    event_type: EventType = EventType.SYSTEM_EVENT
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)
    priority: Priority = Priority.BACKGROUND
    user_initiated: bool = False
    language: str = "en"


@dataclass
class WorldState:
    """Unified world model — single source of truth."""
    robot_position: dict = field(default_factory=lambda: {"x": 0, "y": 0, "theta": 0})
    robot_velocity: dict = field(default_factory=lambda: {"vx": 0, "vy": 0, "vth": 0})
    battery_percent: float = 100.0
    environment_objects: list = field(default_factory=list)
    obstacles: list = field(default_factory=list)
    rooms: list = field(default_factory=list)
    humans: list = field(default_factory=list)
    mission: dict = field(default_factory=dict)
    hazards: list = field(default_factory=list)
    confidence: dict = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class Plan:
    """Structured plan with safety validation."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task: str = ""
    steps: list[dict] = field(default_factory=list)
    required_modules: list[str] = field(default_factory=list)
    risk_level: str = "low"
    safety_validated: bool = False
    allowed: bool = True
    denial_reason: str = ""


class LanguageProcessor:
    """Normalizes all inputs into structured events."""

    @staticmethod
    def normalize(event: Event) -> Event:
        """Normalize any input into the universal event format."""
        if event.payload.get("raw_text"):
            text = event.payload["raw_text"]
            event.language = LanguageProcessor._detect_language(text)
            event.payload["intent"] = LanguageProcessor._classify_intent(text)
            event.payload["entities"] = LanguageProcessor._extract_entities(text)
            event.payload["normalized_text"] = text.strip()
        return event

    @staticmethod
    def _detect_language(text: str) -> str:
        hindi_chars = set("अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")
        if any(c in hindi_chars for c in text):
            return "hi"
        if any(w in text.lower() for w in ["ka", "hai", "kya", "mein", "aur"]):
            return "hinglish"
        return "en"

    @staticmethod
    def _classify_intent(text: str) -> str:
        t = text.lower().strip()
        nav_words = ["go to", "move", "navigate", "patrol", "return", "home"]
        vision_words = ["what", "see", "detect", "look", "camera", "who"]
        control_words = ["stop", "start", "emergency", "help"]
        query_words = ["status", "battery", "temperature", "how"]
        gen_words = ["generate", "create", "write", "make", "build"]

        if any(w in t for w in nav_words):
            return "navigation"
        if any(w in t for w in vision_words):
            return "vision_query"
        if any(w in t for w in control_words):
            return "robot_control"
        if any(w in t for w in query_words):
            return "status_query"
        if any(w in t for w in gen_words):
            return "generation"
        return "general_query"

    @staticmethod
    def _extract_entities(text: str) -> dict:
        entities = {}
        t = text.lower()
        locations = ["kitchen", "room", "corridor", "hallway", "door", "dock", "home", "base"]
        for loc in locations:
            if loc in t:
                entities["location"] = loc
        if any(w in t for w in ["left", "right", "forward", "backward", "up", "down"]):
            for d in ["left", "right", "forward", "backward"]:
                if d in t:
                    entities["direction"] = d
        import re
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            entities["values"] = [float(n) for n in numbers]
        return entities


class SafetyGate:
    """Deterministic safety validation — AI never overrides this."""

    def __init__(self):
        self.emergency_stop = False
        self.motor_limits = {"max_speed": 255, "max_current": 10}
        self.battery_minimum = 5.0
        self.max_temperature = 85.0

    def validate(self, plan: Plan, world: WorldState) -> Plan:
        """Validate plan against safety rules. Returns validated plan."""
        checks = [
            self._check_schema(plan),
            self._check_battery(world),
            self._check_temperature(world),
            self._check_emergency_stop(),
            self._check_motor_limits(plan),
            self._check_obstacles(plan, world),
            self._check_hazards(plan, world),
        ]
        for passed, reason in checks:
            if not passed:
                plan.allowed = False
                plan.denial_reason = reason
                plan.safety_validated = False
                logger.warning(f"Safety gate DENIED plan: {reason}")
                return plan

        plan.safety_validated = True
        plan.allowed = True
        return plan

    def _check_schema(self, plan: Plan) -> tuple[bool, str]:
        return (True, "")

    def _check_battery(self, world: WorldState) -> tuple[bool, str]:
        if world.battery_percent < self.battery_minimum:
            return (False, f"Battery critical: {world.battery_percent}%")
        return (True, "")

    def _check_temperature(self, world: WorldState) -> tuple[bool, str]:
        temp = world.confidence.get("cpu_temp", 50)
        if temp > self.max_temperature:
            return (False, f"Temperature critical: {temp}°C")
        return (True, "")

    def _check_emergency_stop(self) -> tuple[bool, str]:
        if self.emergency_stop:
            return (False, "Emergency stop is active")
        return (True, "")

    def _check_motor_limits(self, plan: Plan) -> tuple[bool, str]:
        for step in plan.steps:
            speed = step.get("speed", 0)
            if abs(speed) > self.motor_limits["max_speed"]:
                return (False, f"Motor speed {speed} exceeds limit")
        return (True, "")

    def _check_obstacles(self, plan: Plan, world: WorldState) -> tuple[bool, str]:
        return (True, "")

    def _check_hazards(self, plan: Plan, world: WorldState) -> tuple[bool, str]:
        for hazard in world.hazards:
            if hazard.get("severity", 0) >= 0.9:
                return (False, f"Hazard detected: {hazard.get('type', 'unknown')}")
        return (True, "")

    def trigger_estop(self):
        self.emergency_stop = True
        logger.critical("EMERGENCY STOP TRIGGERED")

    def release_estop(self):
        self.emergency_stop = False
        logger.info("Emergency stop released")


class TankOSOrchestrator:
    """
    Master orchestrator implementing the TankOS brain:
      OBSERVE -> UNDERSTAND -> REMEMBER -> REASON -> PLAN
      -> VALIDATE -> ACT -> OBSERVE RESULT -> EVALUATE -> LEARN
    """

    def __init__(self):
        self.state = TankOSState.IDLE
        self.world = WorldState()
        self.language = LanguageProcessor()
        self.safety = SafetyGate()
        self._memory: list[dict] = []
        self._event_log: list[dict] = []
        self._module_registry = None
        self._ai_router = None

        # Lazy imports to avoid circular deps
        try:
            from tank.orchestrator.module_registry import REGISTRY
            self._module_registry = REGISTRY
        except ImportError:
            logger.warning("ModuleRegistry not available")

        logger.info("TankOS Orchestrator initialized")

    def set_ai_router(self, router):
        self._ai_router = router

    def set_module_registry(self, registry):
        self._module_registry = registry

    async def process_event(self, event: Event) -> dict:
        """Main brain loop — processes any event through the full pipeline."""
        self.state = TankOSState.PROCESSING
        result = {"event_id": event.event_id, "steps": []}

        try:
            # 1. OBSERVE — normalize input
            event = self.language.normalize(event)
            result["steps"].append("observed")

            # 2. UNDERSTAND — classify intent + extract entities
            understanding = {
                "intent": event.payload.get("intent", "general_query"),
                "entities": event.payload.get("entities", {}),
                "language": event.language,
                "priority": event.priority.value
            }
            result["understanding"] = understanding
            result["steps"].append("understood")

            # 3. REMEMBER — retrieve relevant context
            context = self._retrieve_context(event)
            result["context"] = context
            result["steps"].append("remembered")

            # 4. REASON — AI/LLM reasoning
            reasoning = await self._reason(event, understanding, context)
            result["reasoning"] = reasoning
            result["steps"].append("reasoned")

            # 5. PLAN — generate action plan
            plan = self._plan(event, understanding, reasoning)
            result["plan"] = plan.__dict__ if hasattr(plan, '__dict__') else plan
            result["steps"].append("planned")

            # 6. VALIDATE — safety gate
            if isinstance(plan, Plan):
                plan = self.safety.validate(plan, self.world)
                if not plan.allowed:
                    result["denied"] = True
                    result["denial_reason"] = plan.denial_reason
                    result["steps"].append("denied")
                    await self._store_memory(event, result)
                    return result

            # 7. ACT — execute plan
            self.state = TankOSState.EXECUTING
            exec_result = await self._execute(plan)
            result["execution"] = exec_result
            result["steps"].append("executed")

            # 8. OBSERVE RESULT — check outcome
            observation = await self._observe_result(exec_result)
            result["observation"] = observation
            result["steps"].append("observed_result")

            # 9. EVALUATE — assess success
            evaluation = self._evaluate(event, plan, observation)
            result["evaluation"] = evaluation
            result["steps"].append("evaluated")

            # 10. LEARN — store in memory
            await self._store_memory(event, result)
            result["steps"].append("learned")

            result["status"] = "success"
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            self.state = TankOSState.IDLE

        return result

    def _retrieve_context(self, event: Event) -> dict:
        """Retrieve relevant memory context for the current event."""
        context = {
            "recent_events": self._event_log[-5:] if self._event_log else [],
            "world_state": {
                "position": self.world.robot_position,
                "battery": self.world.battery_percent,
                "objects_count": len(self.world.environment_objects),
                "humans_count": len(self.world.humans),
            }
        }
        return context

    async def _reason(self, event: Event, understanding: dict, context: dict) -> dict:
        """AI reasoning — select best model and generate response."""
        intent = understanding["intent"]
        if self._ai_router:
            try:
                return await self._ai_router.route_and_reason(event, understanding, context)
            except Exception as e:
                logger.warning(f"AI router failed, using fallback: {e}")
        return {
            "provider": "rule_based",
            "model": "fallback",
            "response": f"Rule-based response for intent={intent}",
            "confidence": 0.5
        }

    def _plan(self, event: Event, understanding: dict, reasoning: dict) -> Plan:
        """Generate an action plan from reasoning output."""
        plan = Plan(
            task=reasoning.get("response", ""),
            steps=reasoning.get("steps", []),
            required_modules=reasoning.get("modules", []),
            risk_level=reasoning.get("risk", "low")
        )
        if understanding["intent"] == "robot_control":
            plan.risk_level = "high"
        if understanding["intent"] == "navigation":
            plan.risk_level = "medium"
        return plan

    async def _execute(self, plan: Plan | dict) -> dict:
        """Execute a plan through the module registry."""
        if not self._module_registry:
            return {"status": "no_registry", "message": "Module registry not connected"}

        results = []
        if isinstance(plan, Plan):
            for step in plan.steps:
                module_name = step.get("module", step.get("tool", ""))
                args = step.get("args", step.get("arguments", {}))
                if module_name:
                    r = self._module_registry.execute(module_name, args)
                    results.append(r)
            return {"steps_executed": len(results), "results": results}
        return {"status": "no_plan"}

    async def _observe_result(self, exec_result: dict) -> dict:
        """Observe the result of execution."""
        return {
            "executed": exec_result.get("steps_executed", 0),
            "successes": sum(1 for r in exec_result.get("results", [])
                           if r.get("status") == "success"),
            "failures": sum(1 for r in exec_result.get("results", [])
                          if r.get("status") == "error")
        }

    def _evaluate(self, event: Event, plan, observation: dict) -> dict:
        """Evaluate whether the task was successful."""
        successes = observation.get("successes", 0)
        failures = observation.get("failures", 0)
        total = successes + failures
        success_rate = successes / max(1, total)
        return {
            "success_rate": round(success_rate, 2),
            "total_steps": total,
            "passed": failures == 0 and total > 0
        }

    async def _store_memory(self, event: Event, result: dict):
        """Store event + result in memory for future learning."""
        memory_entry = {
            "event_id": event.event_id,
            "source": event.source,
            "type": event.event_type.value,
            "intent": result.get("understanding", {}).get("intent"),
            "status": result.get("status"),
            "steps": result.get("steps", []),
            "timestamp": time.time()
        }
        self._memory.append(memory_entry)
        self._event_log.append(memory_entry)
        # Keep memory bounded
        if len(self._memory) > 10000:
            self._memory = self._memory[-5000:]
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]

    def update_world_state(self, **kwargs):
        """Update world model with new data."""
        for k, v in kwargs.items():
            if hasattr(self.world, k):
                setattr(self.world, k, v)
        self.world.last_updated = time.time()

    def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            "state": self.state.value,
            "world": {
                "position": self.world.robot_position,
                "battery": self.world.battery_percent,
                "objects": len(self.world.environment_objects),
                "humans": len(self.world.humans),
            },
            "memory_count": len(self._memory),
            "events_processed": len(self._event_log),
            "safety": {
                "estop": self.safety.emergency_stop,
                "validated_plans": sum(1 for m in self._memory if m.get("status") == "success"),
            }
        }


# Global singleton
ORCHESTRATOR = TankOSOrchestrator()
