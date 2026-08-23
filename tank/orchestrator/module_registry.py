"""
TankOS 300-Module Registry
============================
Universal callable capability registry. Every robot function is a typed module
that LLMs can discover, chain, execute, verify, and fall back on.

Architecture:
  LLM -> Module Router -> Capability Check -> Safety Gate -> Executor -> Result
"""

from __future__ import annotations
import json
import time
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("tank.module_registry")


class RiskLevel(Enum):
    READ = "read"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModuleCategory(Enum):
    PERCEPTION = "perception"
    OCR_LANGUAGE = "ocr_language"
    VOICE = "voice"
    HUMAN = "human"
    NAVIGATION = "navigation"
    SLAM_WORLD = "slam_world"
    MEMORY = "memory"
    AI_ORCHESTRATION = "ai_orchestration"
    TOOL_SYSTEM = "tool_system"
    HARDWARE_DEVICE = "hardware_device"
    ESP32_SENSOR = "esp32_sensor"
    ACTUATOR_ROBOT = "actuator_robot"
    POWER = "power"
    NETWORK = "network"
    GUI = "gui"
    EVOLUTION = "evolution"
    SAFETY_DIAG = "safety_diagnostics"
    GENERATIVE = "generative"


@dataclass
class ModuleSchema:
    """Schema for a single callable module."""
    name: str
    description: str
    category: ModuleCategory
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    requires: list[str] = field(default_factory=list)
    preferred_device: str = "jetson"
    risk: RiskLevel = RiskLevel.READ
    timeout_ms: int = 30000
    fallback: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    version: str = "1.0.0"

    def to_llm_tool(self) -> dict:
        """Convert to OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.input_schema,
                    "required": [
                        k for k, v in self.input_schema.items()
                        if not v.get("optional", False)
                    ]
                }
            }
        }


class ModuleRegistry:
    """Central registry for all 300 TankOS callable modules."""

    def __init__(self):
        self._modules: dict[str, ModuleSchema] = {}
        self._executors: dict[str, Callable] = {}
        self._health: dict[str, dict] = {}
        self._history: list[dict] = []
        self._register_all()
        logger.info(f"ModuleRegistry initialized with {len(self._modules)} modules")

    def _register_all(self):
        """Register all 300 modules across all categories."""
        self._register_perception()
        self._register_ocr_language()
        self._register_voice()
        self._register_human()
        self._register_navigation()
        self._register_slam_world()
        self._register_memory()
        self._register_ai_orchestration()
        self._register_tool_system()
        self._register_hardware_device()
        self._register_esp32_sensor()
        self._register_actuator_robot()
        self._register_power()
        self._register_network()
        self._register_gui()
        self._register_evolution()
        self._register_safety()
        self._register_generative()

    def _add(self, name: str, desc: str, cat: ModuleCategory,
             risk: RiskLevel = RiskLevel.READ, timeout: int = 30000,
             requires: list[str] | None = None, device: str = "jetson",
             input_schema: dict | None = None, fallback: list[str] | None = None,
             confirm: bool = False, **kwargs):
        """Helper to register a module."""
        schema = ModuleSchema(
            name=name, description=desc, category=cat,
            risk=risk, timeout_ms=timeout,
            requires=requires or [], preferred_device=device,
            input_schema=input_schema or {}, fallback=fallback or [],
            requires_confirmation=confirm
        )
        self._modules[name] = schema
        self._health[name] = {
            "success_count": 0, "fail_count": 0,
            "avg_latency_ms": 0, "last_used": None,
            "status": "healthy"
        }

    # ── 1-20: Perception ──
    def _register_perception(self):
        cat = ModuleCategory.PERCEPTION
        d = "jetson"
        self._add("vision.capture", "Capture image from active camera", cat, device=d,
                   input_schema={"camera_id": {"type": "string", "description": "Camera ID or 'auto'"}},
                   output_schema={"image": {"type": "string"}, "resolution": {"type": "string"}})
        self._add("vision.detect_objects", "Detect objects using YOLO TensorRT", cat, device=d,
                   input_schema={"confidence": {"type": "number", "description": "Min confidence 0-1", "optional": True}},
                   output_schema={"objects": {"type": "array"}})
        self._add("vision.track_objects", "Track multiple objects across frames", cat, RiskLevel.LOW, device=d)
        self._add("vision.detect_people", "Detect human persons in camera frame", cat, device=d)
        self._add("vision.count_people", "Count number of people visible", cat, device=d)
        self._add("vision.detect_motion", "Detect motion between frames", cat, device=d)
        self._add("vision.classify_scene", "Classify scene type (indoor/outdoor/etc)", cat, device=d)
        self._add("vision.segment_scene", "Semantic segmentation of scene", cat, device=d)
        self._add("vision.detect_faces", "Detect faces without identifying", cat, device=d)
        self._add("vision.detect_pose", "Estimate human body pose keypoints", cat, device=d)
        self._add("vision.detect_gesture", "Classify hand/body gestures", cat, device=d)
        self._add("vision.estimate_depth", "Estimate depth map from camera", cat, device=d)
        self._add("vision.detect_obstacles", "Detect navigation obstacles", cat, RiskLevel.MEDIUM, device=d)
        self._add("vision.detect_edges", "Edge detection for scene analysis", cat, device=d)
        self._add("vision.detect_anomalies", "Detect visual anomalies vs baseline", cat, device=d)
        self._add("vision.compare_images", "Compare two images for differences", cat, device=d)
        self._add("vision.detect_change", "Detect changes in environment", cat, device=d)
        self._add("vision.camera_health", "Check camera connection and status", cat, device=d)
        self._add("vision.camera_calibrate", "Calibrate camera intrinsics/extrinsics", cat, RiskLevel.LOW, device=d)
        self._add("vision.get_latest_frame", "Get most recent camera frame", cat, device=d)

    # ── 21-40: OCR / Language ──
    def _register_ocr_language(self):
        cat = ModuleCategory.OCR_LANGUAGE
        self._add("ocr.read", "Read text from image via OCR", cat)
        self._add("ocr.detect_language", "Detect language of text in image", cat)
        self._add("ocr.extract_numbers", "Extract numeric values from image", cat)
        self._add("ocr.extract_tables", "Extract table data from image", cat)
        self._add("ocr.extract_labels", "Extract labels/tags from image", cat)
        self._add("ocr.read_sign", "Read text from signs", cat)
        self._add("ocr.compare_documents", "Compare two document images", cat)
        self._add("language.detect", "Detect input language", cat)
        self._add("language.translate", "Translate between languages", cat)
        self._add("language.normalize", "Normalize text input", cat)
        self._add("language.summarize", "Summarize text content", cat)
        self._add("language.classify_intent", "Classify user intent from text", cat)
        self._add("language.extract_entities", "Extract named entities from text", cat)
        self._add("language.extract_command", "Extract robot command from text", cat, RiskLevel.LOW)
        self._add("language.detect_hinglish", "Detect Hinglish mixed language", cat)
        self._add("language.detect_indic_language", "Detect Indian language variant", cat)
        self._add("language.correct_text", "Correct grammar/spelling", cat)
        self._add("language.generate_response", "Generate natural language response", cat)
        self._add("language.format_response", "Format response for output channel", cat)
        self._add("language.redact_sensitive_data", "Redact PII from text", cat)

    # ── 41-60: Voice ──
    def _register_voice(self):
        cat = ModuleCategory.VOICE
        self._add("voice.listen", "Start listening for voice input", cat)
        self._add("voice.stop_listening", "Stop listening for voice", cat)
        self._add("voice.detect_speech", "Detect speech activity (VAD)", cat)
        self._add("voice.transcribe", "Transcribe speech to text (Whisper)", cat)
        self._add("voice.transcribe_stream", "Stream real-time transcription", cat)
        self._add("voice.detect_language", "Detect spoken language", cat)
        self._add("voice.detect_wake_word", "Detect TankOS wake word", cat)
        self._add("voice.detect_speaker", "Detect speaker identity", cat)
        self._add("voice.noise_reduce", "Apply noise reduction to audio", cat)
        self._add("voice.extract_command", "Extract command from speech", cat, RiskLevel.LOW)
        self._add("voice.speak", "Text-to-speech output", cat, device="uno_q")
        self._add("voice.speak_stream", "Stream TTS output", cat, device="uno_q")
        self._add("voice.set_language", "Set voice language", cat)
        self._add("voice.set_voice", "Select voice profile", cat)
        self._add("voice.set_speed", "Set speech speed", cat)
        self._add("voice.set_pitch", "Set speech pitch", cat)
        self._add("voice.set_volume", "Set output volume", cat)
        self._add("voice.interrupt", "Interrupt current speech", cat)
        self._add("voice.play_alert", "Play alert sound", cat, device="uno_q")
        self._add("voice.audio_health", "Check audio subsystem health", cat)

    # ── 61-80: Human Interaction ──
    def _register_human(self):
        cat = ModuleCategory.HUMAN
        d = "jetson"
        self._add("human.detect", "Detect humans in camera frame", cat, device=d)
        self._add("human.track", "Track detected humans over time", cat, device=d)
        self._add("human.get_position", "Get position of nearest human", cat, device=d)
        self._add("human.get_distance", "Get distance to nearest human", cat, device=d)
        self._add("human.get_count", "Get count of visible humans", cat, device=d)
        self._add("human.get_motion", "Get human motion vector", cat, device=d)
        self._add("human.detect_approach", "Detect human approaching robot", cat, device=d)
        self._add("human.detect_departure", "Detect human leaving", cat, device=d)
        self._add("human.detect_gesture", "Detect human gesture", cat, device=d)
        self._add("human.detect_wave", "Detect wave gesture", cat, device=d)
        self._add("human.detect_point", "Detect pointing gesture + direction", cat, device=d)
        self._add("human.detect_stop_gesture", "Detect stop hand gesture", cat, RiskLevel.HIGH, device=d)
        self._add("human.estimate_attention", "Estimate human attention direction", cat, device=d)
        self._add("human.detect_interaction", "Detect if human wants interaction", cat, device=d)
        self._add("human.start_interaction", "Start interaction session", cat, device=d)
        self._add("human.end_interaction", "End interaction session", cat, device=d)
        self._add("human.follow", "Follow a detected person", cat, RiskLevel.HIGH, device="jetson")
        self._add("human.escort", "Escort person to destination", cat, RiskLevel.HIGH, device="jetson")
        self._add("human.maintain_distance", "Maintain safe distance from human", cat, RiskLevel.MEDIUM, device="jetson")
        self._add("human.get_interaction_state", "Get current interaction state", cat, device=d)

    # ── 81-100: Navigation ──
    def _register_navigation(self):
        cat = ModuleCategory.NAVIGATION
        self._add("navigation.get_position", "Get current robot position", cat, device="jetson")
        self._add("navigation.get_heading", "Get current heading/bearing", cat, device="jetson")
        self._add("navigation.go_to", "Navigate to a known location", cat, RiskLevel.HIGH,
                  device="jetson", input_schema={"location": {"type": "string"}})
        self._add("navigation.go_home", "Navigate back to home/dock", cat, RiskLevel.HIGH, device="jetson")
        self._add("navigation.stop", "Stop navigation immediately", cat, RiskLevel.HIGH, device="jetson")
        self._add("navigation.pause", "Pause current navigation", cat, RiskLevel.MEDIUM, device="jetson")
        self._add("navigation.resume", "Resume paused navigation", cat, RiskLevel.MEDIUM, device="jetson")
        self._add("navigation.rotate", "Rotate robot in place", cat, RiskLevel.MEDIUM, device="jetson",
                  input_schema={"degrees": {"type": "number"}, "direction": {"type": "string"}})
        self._add("navigation.follow_route", "Follow a predefined route", cat, RiskLevel.HIGH, device="jetson")
        self._add("navigation.follow_person", "Follow a detected person", cat, RiskLevel.HIGH, device="jetson")
        self._add("navigation.avoid_obstacle", "Trigger obstacle avoidance", cat, RiskLevel.HIGH, device="jetson")
        self._add("navigation.plan_path", "Plan path between two points", cat, device="jetson")
        self._add("navigation.replan", "Replan current navigation", cat, device="jetson")
        self._add("navigation.localize", "Determine current position", cat, device="jetson")
        self._add("navigation.build_map", "Build/update environment map", cat, device="jetson")
        self._add("navigation.update_map", "Update existing map with new data", cat, device="jetson")
        self._add("navigation.save_map", "Save current map to storage", cat, device="jetson")
        self._add("navigation.load_map", "Load a saved map", cat, device="jetson")
        self._add("navigation.get_route", "Get current planned route", cat, device="jetson")
        self._add("navigation.estimate_arrival", "Estimate time to destination", cat, device="jetson")

    # ── 101-120: SLAM / World Model ──
    def _register_slam_world(self):
        cat = ModuleCategory.SLAM_WORLD
        self._add("slam.start", "Start SLAM mapping", cat, RiskLevel.MEDIUM, device="jetson")
        self._add("slam.stop", "Stop SLAM mapping", cat, device="jetson")
        self._add("slam.reset", "Reset SLAM state", cat, RiskLevel.HIGH, device="jetson")
        self._add("slam.get_pose", "Get SLAM pose estimate", cat, device="jetson")
        self._add("slam.get_map", "Get current SLAM map", cat, device="jetson")
        self._add("slam.add_landmark", "Add landmark to map", cat, device="jetson")
        self._add("slam.remove_landmark", "Remove landmark from map", cat, device="jetson")
        self._add("slam.localize", "Localize on existing map", cat, device="jetson")
        self._add("slam.relocalize", "Force relocalization", cat, device="jetson")
        self._add("slam.detect_loop_closure", "Detect loop closure event", cat, device="jetson")
        self._add("world.get_state", "Get current world model state", cat, device="jetson")
        self._add("world.update", "Update world model with new data", cat, device="jetson")
        self._add("world.get_object", "Get info about a specific object", cat, device="jetson")
        self._add("world.find_object", "Find an object in world model", cat, device="jetson")
        self._add("world.add_object", "Add object to world model", cat, device="jetson")
        self._add("world.remove_object", "Remove object from world model", cat, device="jetson")
        self._add("world.update_object", "Update object properties", cat, device="jetson")
        self._add("world.get_room", "Get room information", cat, device="jetson")
        self._add("world.get_people", "Get all tracked people", cat, device="jetson")
        self._add("world.get_nearby_entities", "Get nearby entities within range", cat, device="jetson")

    # ── 121-140: Memory ──
    def _register_memory(self):
        cat = ModuleCategory.MEMORY
        self._add("memory.store", "Store a memory entry", cat, device="jetson")
        self._add("memory.retrieve", "Retrieve memory by query", cat, device="jetson")
        self._add("memory.search", "Search memory by keywords", cat, device="jetson")
        self._add("memory.semantic_search", "Semantic vector search", cat, device="jetson")
        self._add("memory.episodic_search", "Search episodic memory", cat, device="jetson")
        self._add("memory.procedural_search", "Search procedural memory", cat, device="jetson")
        self._add("memory.spatial_search", "Search spatial memory", cat, device="jetson")
        self._add("memory.summarize", "Summarize memory contents", cat, device="jetson")
        self._add("memory.compress", "Compress memory entries", cat, device="jetson")
        self._add("memory.deduplicate", "Remove duplicate memories", cat, device="jetson")
        self._add("memory.tag", "Tag a memory entry", cat, device="jetson")
        self._add("memory.update", "Update an existing memory", cat, device="jetson")
        self._add("memory.delete", "Delete a memory entry", cat, RiskLevel.MEDIUM, device="jetson")
        self._add("memory.archive", "Archive old memories", cat, device="jetson")
        self._add("memory.restore", "Restore archived memory", cat, device="jetson")
        self._add("memory.get_recent", "Get recent memories", cat, device="jetson")
        self._add("memory.get_context", "Get context for current task", cat, device="jetson")
        self._add("memory.create_episode", "Create new episodic memory", cat, device="jetson")
        self._add("memory.close_episode", "Close and summarize episode", cat, device="jetson")
        self._add("memory.health", "Check memory system health", cat, device="jetson")

    # ── 141-160: AI Orchestration ──
    def _register_ai_orchestration(self):
        cat = ModuleCategory.AI_ORCHESTRATION
        self._add("ai.ask", "Ask any AI provider a question", cat, device="jetson")
        self._add("ai.reason", "Complex reasoning with best model", cat, device="jetson")
        self._add("ai.plan", "Generate an action plan", cat, device="jetson")
        self._add("ai.summarize", "Summarize content using AI", cat, device="jetson")
        self._add("ai.classify", "Classify input using AI", cat, device="jetson")
        self._add("ai.extract", "Extract structured data using AI", cat, device="jetson")
        self._add("ai.compare", "Compare items using AI", cat, device="jetson")
        self._add("ai.generate", "Generate content using AI", cat, device="jetson")
        self._add("ai.explain", "Explain something using AI", cat, device="jetson")
        self._add("ai.critique", "Critique/review using AI", cat, device="jetson")
        self._add("ai.verify", "Verify a claim using AI", cat, device="jetson")
        self._add("ai.route_model", "Route to best model for task", cat, device="jetson")
        self._add("ai.select_provider", "Select best AI provider", cat, device="jetson")
        self._add("ai.select_local_model", "Select best local model", cat, device="jetson")
        self._add("ai.estimate_cost", "Estimate AI task cost", cat, device="jetson")
        self._add("ai.estimate_latency", "Estimate AI task latency", cat, device="jetson")
        self._add("ai.get_model_health", "Get health of AI models", cat, device="jetson")
        self._add("ai.fallback", "Trigger AI fallback chain", cat, device="jetson")
        self._add("ai.cancel", "Cancel running AI task", cat, device="jetson")
        self._add("ai.get_usage", "Get AI usage statistics", cat, device="jetson")

    # ── 161-180: Tool System ──
    def _register_tool_system(self):
        cat = ModuleCategory.TOOL_SYSTEM
        self._add("tool.list", "List all available modules", cat, RiskLevel.READ)
        self._add("tool.search", "Search modules by keyword", cat, RiskLevel.READ)
        self._add("tool.describe", "Get detailed module description", cat, RiskLevel.READ)
        self._add("tool.validate", "Validate arguments for a module", cat, RiskLevel.READ)
        self._add("tool.execute", "Execute a module by name", cat, RiskLevel.MEDIUM)
        self._add("tool.cancel", "Cancel a running tool", cat, RiskLevel.MEDIUM)
        self._add("tool.retry", "Retry a failed tool execution", cat, RiskLevel.LOW)
        self._add("tool.parallel", "Execute multiple tools in parallel", cat, RiskLevel.MEDIUM)
        self._add("tool.sequence", "Execute tools in sequence", cat, RiskLevel.MEDIUM)
        self._add("tool.chain", "Chain tools with output piping", cat, RiskLevel.MEDIUM)
        self._add("tool.check_permission", "Check if action is permitted", cat, RiskLevel.READ)
        self._add("tool.check_requirements", "Check tool requirements met", cat, RiskLevel.READ)
        self._add("tool.find_fallback", "Find fallback for failed tool", cat, RiskLevel.READ)
        self._add("tool.get_status", "Get tool execution status", cat, RiskLevel.READ)
        self._add("tool.get_history", "Get tool execution history", cat, RiskLevel.READ)
        self._add("tool.register", "Register a new tool at runtime", cat, RiskLevel.HIGH)
        self._add("tool.unregister", "Unregister a tool", cat, RiskLevel.HIGH)
        self._add("tool.version", "Get tool version info", cat, RiskLevel.READ)
        self._add("tool.benchmark", "Benchmark a tool's performance", cat, RiskLevel.LOW)
        self._add("tool.simulate", "Simulate tool without execution", cat, RiskLevel.READ)

    # ── 181-200: Hardware / Device ──
    def _register_hardware_device(self):
        cat = ModuleCategory.HARDWARE_DEVICE
        self._add("device.list", "List all connected devices", cat, device="uno_q")
        self._add("device.discover", "Discover new devices", cat, device="uno_q")
        self._add("device.identify", "Identify a specific device", cat, device="uno_q")
        self._add("device.get_info", "Get device information", cat, device="uno_q")
        self._add("device.get_health", "Get device health status", cat, device="uno_q")
        self._add("device.get_temperature", "Get device temperature", cat, device="uno_q")
        self._add("device.get_power", "Get device power state", cat, device="uno_q")
        self._add("device.get_capabilities", "Get device capabilities", cat, device="uno_q")
        self._add("device.enable", "Enable a device", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("device.disable", "Disable a device", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("device.restart", "Restart a device/service", cat, RiskLevel.HIGH, device="uno_q")
        self._add("device.shutdown", "Shutdown a device", cat, RiskLevel.CRITICAL, device="uno_q")
        self._add("device.reset", "Reset a device to defaults", cat, RiskLevel.CRITICAL, device="uno_q")
        self._add("device.ping", "Ping a device for connectivity", cat, device="uno_q")
        self._add("device.get_latency", "Measure device latency", cat, device="uno_q")
        self._add("device.get_uptime", "Get device uptime", cat, device="uno_q")
        self._add("device.get_firmware", "Get device firmware version", cat, device="uno_q")
        self._add("device.update_firmware", "Update device firmware", cat, RiskLevel.CRITICAL, device="uno_q")
        self._add("device.calibrate", "Calibrate device", cat, RiskLevel.HIGH, device="uno_q")
        self._add("device.self_test", "Run device self-test", cat, RiskLevel.LOW, device="uno_q")

    # ── 201-220: ESP32 / Sensor Bus ──
    def _register_esp32_sensor(self):
        cat = ModuleCategory.ESP32_SENSOR
        self._add("sensor.list", "List all sensors", cat, device="esp32")
        self._add("sensor.read", "Read a specific sensor", cat, device="esp32")
        self._add("sensor.read_batch", "Read multiple sensors at once", cat, device="esp32")
        self._add("sensor.stream", "Start streaming sensor data", cat, device="esp32")
        self._add("sensor.stop_stream", "Stop streaming sensor data", cat, device="esp32")
        self._add("sensor.calibrate", "Calibrate a sensor", cat, RiskLevel.MEDIUM, device="esp32")
        self._add("sensor.health", "Check sensor health", cat, device="esp32")
        self._add("imu.read", "Read IMU orientation", cat, device="esp32")
        self._add("imu.orientation", "Get current orientation (Euler/quaternion)", cat, device="esp32")
        self._add("imu.motion", "Get motion/acceleration data", cat, device="esp32")
        self._add("imu.detect_collision", "Detect collision event", cat, RiskLevel.HIGH, device="esp32")
        self._add("imu.detect_tilt", "Detect tilt beyond threshold", cat, RiskLevel.MEDIUM, device="esp32")
        self._add("thermal.read", "Read thermal sensor array", cat, device="esp32")
        self._add("thermal.hotspots", "Detect thermal hotspots", cat, device="esp32")
        self._add("battery.read", "Read battery voltage/current", cat, device="esp32")
        self._add("battery.estimate_runtime", "Estimate remaining runtime", cat, device="esp32")
        self._add("encoder.read", "Read wheel encoders", cat, device="esp32")
        self._add("distance.read", "Read ultrasonic distance", cat, device="esp32")
        self._add("gpio.status", "Read GPIO pin states", cat, device="esp32")
        self._add("gpio.safe_state", "Set GPIO to safe state", cat, RiskLevel.HIGH, device="esp32")

    # ── 221-240: Actuators / Robot ──
    def _register_actuator_robot(self):
        cat = ModuleCategory.ACTUATOR_ROBOT
        self._add("robot.status", "Get overall robot status", cat, device="uno_q")
        self._add("robot.start", "Start robot operations", cat, RiskLevel.HIGH, device="uno_q")
        self._add("robot.stop", "Stop all robot operations", cat, RiskLevel.HIGH, device="uno_q")
        self._add("robot.pause", "Pause robot operations", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("robot.resume", "Resume robot operations", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("robot.set_mode", "Set robot operating mode", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("robot.get_mode", "Get current operating mode", cat, device="uno_q")
        self._add("motor.set_speed", "Set motor speed", cat, RiskLevel.HIGH, device="esp32",
                  input_schema={"left": {"type": "integer"}, "right": {"type": "integer"}})
        self._add("motor.stop", "Stop all motors", cat, RiskLevel.HIGH, device="esp32")
        self._add("motor.get_status", "Get motor status", cat, device="esp32")
        self._add("servo.set_angle", "Set servo angle", cat, RiskLevel.HIGH, device="esp32",
                  input_schema={"channel": {"type": "integer"}, "angle": {"type": "number"}})
        self._add("servo.get_angle", "Get current servo angle", cat, device="esp32")
        self._add("servo.move", "Move servo to position", cat, RiskLevel.HIGH, device="esp32")
        self._add("servo.stop", "Stop servo movement", cat, device="esp32")
        self._add("arm.home", "Home the robotic arm", cat, RiskLevel.HIGH, device="esp32")
        self._add("arm.move", "Move arm to position", cat, RiskLevel.HIGH, device="esp32")
        self._add("arm.stop", "Stop arm movement", cat, RiskLevel.HIGH, device="esp32")
        self._add("actuator.test", "Test actuator subsystem", cat, RiskLevel.LOW, device="esp32")
        self._add("actuator.emergency_stop", "Emergency stop all actuators", cat, RiskLevel.CRITICAL, device="esp32")
        self._add("actuator.safe_state", "Set all actuators to safe state", cat, RiskLevel.CRITICAL, device="esp32")

    # ── 241-255: Power ──
    def _register_power(self):
        cat = ModuleCategory.POWER
        self._add("power.get_status", "Get overall power status", cat, device="uno_q")
        self._add("power.get_voltage", "Get battery voltage", cat, device="uno_q")
        self._add("power.get_current", "Get current draw", cat, device="uno_q")
        self._add("power.get_consumption", "Get power consumption rate", cat, device="uno_q")
        self._add("power.get_battery", "Get battery percentage", cat, device="uno_q")
        self._add("power.estimate_runtime", "Estimate remaining runtime", cat, device="uno_q")
        self._add("power.set_budget", "Set power budget per subsystem", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("power.get_budget", "Get current power budget", cat, device="uno_q")
        self._add("power.detect_charging", "Detect if charging", cat, device="uno_q")
        self._add("power.detect_overload", "Detect power overload", cat, RiskLevel.HIGH, device="uno_q")
        self._add("power.detect_thermal_issue", "Detect thermal power issue", cat, RiskLevel.HIGH, device="uno_q")
        self._add("power.optimize", "Optimize power usage", cat, device="uno_q")
        self._add("power.low_power_mode", "Enable low power mode", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("power.shutdown_nonessential", "Shutdown non-essential services", cat, RiskLevel.HIGH, device="uno_q")
        self._add("power.restore_services", "Restore shutdown services", cat, device="uno_q")

    # ── 256-270: Network ──
    def _register_network(self):
        cat = ModuleCategory.NETWORK
        self._add("network.status", "Get network status", cat, device="uno_q")
        self._add("network.scan", "Scan for devices on network", cat, device="uno_q")
        self._add("network.discover_devices", "Discover network devices", cat, device="uno_q")
        self._add("network.get_topology", "Get network topology map", cat, device="uno_q")
        self._add("network.ping", "Ping a network address", cat, device="uno_q")
        self._add("network.bandwidth", "Measure bandwidth", cat, device="uno_q")
        self._add("network.latency", "Measure network latency", cat, device="uno_q")
        self._add("network.packet_loss", "Measure packet loss", cat, device="uno_q")
        self._add("network.select_route", "Select best network route", cat, device="uno_q")
        self._add("network.failover", "Trigger network failover", cat, RiskLevel.MEDIUM, device="uno_q")
        self._add("network.restore", "Restore primary network", cat, device="uno_q")
        self._add("network.publish", "Publish to network topic", cat, device="uno_q")
        self._add("network.subscribe", "Subscribe to network topic", cat, device="uno_q")
        self._add("network.send", "Send message to device", cat, device="uno_q")
        self._add("network.broadcast", "Broadcast message to all devices", cat, device="uno_q")

    # ── 271-280: GUI / Android TV ──
    def _register_gui(self):
        cat = ModuleCategory.GUI
        self._add("ui.show_dashboard", "Show main dashboard", cat, device="uno_q")
        self._add("ui.show_camera", "Show camera view", cat, device="uno_q")
        self._add("ui.show_map", "Show navigation map", cat, device="uno_q")
        self._add("ui.show_mission", "Show mission screen", cat, device="uno_q")
        self._add("ui.show_ai", "Show AI brain dashboard", cat, device="uno_q")
        self._add("ui.show_devices", "Show device manager", cat, device="uno_q")
        self._add("ui.show_network", "Show network status", cat, device="uno_q")
        self._add("ui.show_memory", "Show memory system", cat, device="uno_q")
        self._add("ui.show_evolution", "Show evolution dashboard", cat, device="uno_q")
        self._add("ui.show_diagnostics", "Show system diagnostics", cat, device="uno_q")

    # ── 281-290: Evolution ──
    def _register_evolution(self):
        cat = ModuleCategory.EVOLUTION
        self._add("evolution.observe", "Observe system for improvement areas", cat, device="jetson")
        self._add("evolution.detect_failure", "Detect failure patterns", cat, device="jetson")
        self._add("evolution.create_hypothesis", "Generate improvement hypothesis", cat, device="jetson")
        self._add("evolution.create_experiment", "Create evolution experiment", cat, device="jetson")
        self._add("evolution.run_experiment", "Run experiment in sandbox", cat, RiskLevel.HIGH, device="jetson")
        self._add("evolution.benchmark", "Benchmark against baseline", cat, device="jetson")
        self._add("evolution.compare", "Compare candidate vs baseline", cat, device="jetson")
        self._add("evolution.approve", "Approve evolution candidate", cat, RiskLevel.CRITICAL, device="jetson")
        self._add("evolution.rollback", "Rollback to previous version", cat, RiskLevel.HIGH, device="jetson")
        self._add("evolution.record", "Record evolution experiment result", cat, device="jetson")

    # ── 291-300: Safety / Diagnostics ──
    def _register_safety(self):
        cat = ModuleCategory.SAFETY_DIAG
        self._add("safety.check", "Run safety check on proposed action", cat, RiskLevel.READ, device="uno_q")
        self._add("safety.stop", "Emergency stop", cat, RiskLevel.CRITICAL, device="uno_q")
        self._add("safety.get_state", "Get safety subsystem state", cat, device="uno_q")
        self._add("safety.set_mode", "Set safety mode", cat, RiskLevel.HIGH, device="uno_q")
        self._add("safety.validate_action", "Validate action against safety rules", cat, RiskLevel.READ, device="uno_q")
        self._add("diagnostics.run", "Run full diagnostics", cat, device="uno_q")
        self._add("diagnostics.get_errors", "Get current errors", cat, device="uno_q")
        self._add("diagnostics.get_logs", "Get system logs", cat, device="uno_q")
        self._add("diagnostics.create_report", "Create diagnostics report", cat, device="uno_q")
        self._add("diagnostics.export", "Export diagnostics data", cat, device="uno_q")

    # ── Generative AI modules ──
    def _register_generative(self):
        cat = ModuleCategory.GENERATIVE
        # Text generation (150.1-150.20)
        self._add("gen.text.generate", "Generate general text", cat)
        self._add("gen.text.report", "Generate mission/incident report", cat)
        self._add("gen.text.document", "Generate structured document", cat)
        self._add("gen.text.code", "Generate code in any language", cat)
        self._add("gen.text.summary", "Generate summary from content", cat)
        # Code generation (150.21-150.50)
        self._add("gen.code.python", "Generate Python code", cat)
        self._add("gen.code.arduino", "Generate Arduino/ESP32 firmware", cat)
        self._add("gen.code.ros2", "Generate ROS2 node/launch", cat)
        self._add("gen.code.test", "Generate unit/integration tests", cat)
        self._add("gen.code.docker", "Generate Docker/docker-compose", cat)
        self._add("gen.code.api", "Generate REST/WebSocket API", cat)
        # Robot behavior (150.51-150.70)
        self._add("gen.robot.mission", "Generate robot mission plan", cat, RiskLevel.HIGH,
                  requires=["navigation", "perception"])
        self._add("gen.robot.patrol", "Generate patrol route plan", cat, RiskLevel.HIGH)
        self._add("gen.robot.behavior", "Generate behavior tree", cat, RiskLevel.HIGH)
        self._add("gen.robot.recovery", "Generate recovery behavior", cat, RiskLevel.HIGH)
        # Image generation (150.71-150.90)
        self._add("gen.image.generate", "Generate image from prompt", cat)
        self._add("gen.image.infographic", "Generate infographic SVG", cat)
        self._add("gen.image.thumbnail", "Generate thumbnail", cat)
        # Voice generation (150.106-150.120)
        self._add("gen.voice.speak", "Generate speech output", cat, device="uno_q")
        self._add("gen.voice.announce", "Generate announcement", cat, device="uno_q")
        # GUI generation (150.121-150.140)
        self._add("gen.ui.dashboard", "Generate dashboard from NL description", cat)
        self._add("gen.ui.widget", "Generate UI widget", cat)
        self._add("gen.ui.layout", "Generate custom layout", cat)
        # Self-evolution generation (150.141-150.150)
        self._add("gen.evolution.plugin", "Generate new plugin", cat, RiskLevel.HIGH)
        self._add("gen.evolution.node", "Generate new ROS2 node", cat, RiskLevel.HIGH)
        self._add("gen.evolution.tool", "Generate new tool module", cat, RiskLevel.HIGH)
        self._add("gen.evolution.test", "Generate tests for module", cat)

    # ═══════════════════════════════════════
    #  PUBLIC API
    # ═══════════════════════════════════════

    def get_module(self, name: str) -> Optional[ModuleSchema]:
        return self._modules.get(name)

    def list_modules(self, category: ModuleCategory | None = None) -> list[ModuleSchema]:
        if category:
            return [m for m in self._modules.values() if m.category == category]
        return list(self._modules.values())

    def search(self, query: str) -> list[ModuleSchema]:
        q = query.lower()
        return [m for m in self._modules.values()
                if q in m.name.lower() or q in m.description.lower()]

    def get_llm_tools(self, category: ModuleCategory | None = None) -> list[dict]:
        """Get all modules formatted as OpenAI-compatible tool schemas."""
        modules = self.list_modules(category)
        return [m.to_llm_tool() for m in modules]

    def get_count(self) -> int:
        return len(self._modules)

    def get_categories(self) -> dict[str, int]:
        counts = {}
        for m in self._modules.values():
            cat = m.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def register_executor(self, module_name: str, executor: Callable):
        """Register a callable executor for a module."""
        self._executors[module_name] = executor

    def execute(self, module_name: str, args: dict) -> dict:
        """Execute a module with arguments."""
        module = self._modules.get(module_name)
        if not module:
            return {"error": f"Module '{module_name}' not found", "status": "error"}

        # Check health
        health = self._health.get(module_name, {})
        if health.get("status") == "failed":
            # Try fallback
            for fb in module.fallback:
                if fb in self._executors:
                    return self.execute(fb, args)
            return {"error": f"Module '{module_name}' failed, no fallback", "status": "error"}

        executor = self._executors.get(module_name)
        if not executor:
            # Return simulated result for demo
            return {
                "module": module_name,
                "status": "simulated",
                "message": f"Module '{module_name}' registered but no executor attached",
                "args": args,
                "timestamp": time.time()
            }

        start = time.time()
        try:
            result = executor(**args)
            elapsed_ms = (time.time() - start) * 1000
            health["success_count"] = health.get("success_count", 0) + 1
            health["avg_latency_ms"] = (
                health.get("avg_latency_ms", 0) * 0.9 + elapsed_ms * 0.1
            )
            health["last_used"] = time.time()
            health["status"] = "healthy"

            entry = {
                "module": module_name,
                "status": "success",
                "result": result,
                "latency_ms": round(elapsed_ms, 1),
                "timestamp": time.time()
            }
            self._history.append(entry)
            return entry
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            health["fail_count"] = health.get("fail_count", 0) + 1
            health["status"] = "degraded" if health["fail_count"] < 5 else "failed"
            return {
                "module": module_name,
                "status": "error",
                "error": str(e),
                "latency_ms": round(elapsed_ms, 1),
                "timestamp": time.time()
            }

    def get_health(self, module_name: str) -> dict:
        return self._health.get(module_name, {})

    def get_stats(self) -> dict:
        total_success = sum(h.get("success_count", 0) for h in self._health.values())
        total_fail = sum(h.get("fail_count", 0) for h in self._health.values())
        return {
            "total_modules": self.get_count(),
            "categories": self.get_categories(),
            "total_executions": total_success + total_fail,
            "total_success": total_success,
            "total_failures": total_fail,
            "success_rate": round(total_success / max(1, total_success + total_fail) * 100, 1),
        }


# Global singleton
REGISTRY = ModuleRegistry()
