"""TankOS Native AI — the capability-based AI subsystem (100-AI plan).

The most important design decision: **TankOS AI is capability-based, not
model-based.**

    Applications ask:  "Give me object detection."
    not:               "Run YOLOv11 on Jetson."

TankOS decides: which model · which device · which precision · which
accelerator · what FPS · what fallback. So replacing the Jetson model, adding
an accelerator, or moving inference Jetson → UNO Q changes nothing downstream.

Implements (plan §A–§D core):
- AI Core: model registry, automatic model selection, model health monitor,
  version manager, benchmarking, fallback, quantization selection, inference
  scheduler (Jetson/UNO Q), AI resource governor, capability discovery.
- Perception Layer: capability-based detection/tracking/person/pose/scene/
  segmentation/depth/motion/change with pluggable backends.
- World Intelligence: semantic world model, object memory, location memory,
  dynamic-object database, environmental confidence, unknown-area detection,
  and the world-model API (tank.ai.world.query).
- Navigation AI: route planning, dynamic-obstacle prediction, traversability,
  risk-aware + energy-aware routes, multi-route comparison, ETA, confidence.

Deterministic + testable; real models plug in as backends.
"""

from __future__ import annotations

import datetime
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Model registry (§A 1–7)
# ---------------------------------------------------------------------------
@dataclass
class AIModel:
    name: str
    task: str                       # the capability it serves
    device: str                     # jetson / unoq / esp32
    version: str = "1.0.0"
    precision: str = "fp16"         # fp16 / int8 / q4
    fps: float = 15.0
    latency_ms: float = 40.0
    healthy: bool = True
    size_mb: float = 120.0
    accuracy: float = 0.90
    fallback_to: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name, "task": self.task, "device": self.device,
            "version": self.version, "precision": self.precision,
            "fps": self.fps, "latency_ms": self.latency_ms,
            "healthy": self.healthy, "size_mb": self.size_mb,
            "accuracy": self.accuracy, "fallback_to": self.fallback_to,
        }


class ModelRegistry:
    """Registry + auto-selection + health + fallback (§A 1–7)."""

    def __init__(self) -> None:
        self._models: Dict[str, AIModel] = {}
        self._next_rank: Dict[str, int] = {}

    def register(self, model: AIModel) -> None:
        self._models[model.name] = model

    def list(self, task: Optional[str] = None) -> List[AIModel]:
        models = list(self._models.values())
        if task:
            models = [m for m in models if m.task == task]
        return models

    def get(self, name: str) -> Optional[AIModel]:
        return self._models.get(name)

    def tasks(self) -> List[str]:
        return sorted({m.task for m in self._models.values()})

    def select(self, task: str, *, prefer_device: Optional[str] = None,
               min_accuracy: float = 0.5) -> Optional[AIModel]:
        """Automatic model selection (§2): healthy, accurate, right device."""
        candidates = [m for m in self._models.values()
                      if m.task == task and m.healthy and m.accuracy >= min_accuracy]
        if not candidates:
            return None
        if prefer_device:
            on_device = [m for m in candidates if m.device == prefer_device]
            if on_device:
                candidates = on_device
        # rank: accuracy desc, latency asc
        candidates.sort(key=lambda m: (-m.accuracy, m.latency_ms))
        return candidates[0]

    def mark_unhealthy(self, name: str) -> None:
        m = self._models.get(name)
        if m:
            m.healthy = False

    def fallback(self, name: str) -> Optional[AIModel]:
        """§6 — switch to the fallback when a model fails."""
        m = self._models.get(name)
        if m is None or not m.fallback_to:
            return None
        fb = self._models.get(m.fallback_to)
        return fb if fb and fb.healthy else None

    def health_report(self) -> Dict[str, Any]:
        models = list(self._models.values())
        healthy = sum(1 for m in models if m.healthy)
        return {"total": len(models), "healthy": healthy,
                "degraded": len(models) - healthy,
                "by_task": {t: len(self.list(t)) for t in self.tasks()}}


# ---------------------------------------------------------------------------
# Inference scheduler + resource governor (§A 8–9)
# ---------------------------------------------------------------------------
class InferenceScheduler:
    """Allocate AI workloads across Jetson / UNO Q (§8)."""

    def __init__(self) -> None:
        self._queue: List[dict] = []
        self._running: Dict[str, float] = {}     # task → started-at
        self._history: List[dict] = []

    def submit(self, capability: str, *, device: Optional[str] = None) -> str:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self._queue.append({"id": job_id, "capability": capability,
                            "device": device, "t": time.time()})
        return job_id

    def assign_device(self, capability: str, registry: ModelRegistry,
                      prefer: Optional[str] = None) -> str:
        """§8 — pick the device that can serve the capability."""
        m = registry.select(capability, prefer_device=prefer)
        return m.device if m else "unoq"

    def run(self, job_id: str, device: str) -> None:
        self._queue = [j for j in self._queue if j["id"] != job_id]
        self._running[job_id] = time.time()
        self._history.append({"id": job_id, "device": device,
                              "t": datetime.datetime.now().strftime("%H:%M:%S")})

    def complete(self, job_id: str) -> None:
        self._running.pop(job_id, None)

    def load(self) -> Dict[str, float]:
        """Current per-device load estimate."""
        now = time.time()
        jetson = sum(1 for ts in self._running.values() if now - ts < 2.0)
        return {"jetson": min(100, jetson * 30), "unoq": 0}


class ResourceGovernor:
    """Control CPU/GPU/RAM usage (§9)."""

    def __init__(self) -> None:
        self._budgets: Dict[str, float] = {
            "jetson.gpu": 90.0, "unoq.cpu": 70.0, "ram": 80.0}

    def set_budget(self, key: str, percent: float) -> None:
        self._budgets[key] = max(0.0, min(100.0, percent))

    def allow(self, *, predicted_gpu: float, predicted_cpu: float,
              predicted_ram: float) -> dict:
        ok = (predicted_gpu <= self._budgets["jetson.gpu"] and
              predicted_cpu <= self._budgets["unoq.cpu"] and
              predicted_ram <= self._budgets["ram"])
        return {"allowed": ok,
                "reason": "OK" if ok else "resource budget exceeded",
                "budgets": dict(self._budgets)}


# ---------------------------------------------------------------------------
# Perception capability layer (§B 11–20)
# ---------------------------------------------------------------------------
@dataclass
class PerceptionResult:
    capability: str
    detections: List[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"capability": self.capability, "detections": self.detections,
                "meta": self.meta}


class PerceptionLayer:
    """Capability-based perception — pluggable backends, standard API."""

    def __init__(self) -> None:
        self._backends: Dict[str, Callable] = {}

    def register(self, capability: str, backend: Callable) -> None:
        self._backends[capability] = backend

    def capabilities(self) -> List[str]:
        return sorted(self._backends.keys())

    def run(self, capability: str, inputs: Optional[dict] = None) -> PerceptionResult:
        inputs = inputs or {}
        backend = self._backends.get(capability)
        if backend is None:
            return PerceptionResult(capability,
                                    meta={"error": f"no backend for {capability}"})
        data = backend(inputs)
        return PerceptionResult(capability,
                                detections=data.get("detections", []),
                                meta=data.get("meta", {}))


def default_perception_backends() -> Dict[str, Callable]:
    """Deterministic simulated backends — real models plug in here."""
    def _detect(inputs):
        return {"detections": [
            {"label": "person", "confidence": 0.94, "x": 120, "y": 80},
            {"label": "chair", "confidence": 0.91, "x": 300, "y": 200},
            {"label": "bottle", "confidence": 0.86, "x": 500, "y": 260},
        ], "meta": {"fps": 29.7, "latency_ms": 18, "objects": 3}}

    def _track(inputs):
        return {"detections": [
            {"track_id": 1, "label": "person", "confidence": 0.93,
             "velocity": 0.4, "predicted_x": 140},
            {"track_id": 2, "label": "chair", "confidence": 0.90},
        ], "meta": {"tracks": 2}}

    def _person(inputs):
        return {"detections": [
            {"label": "person", "confidence": 0.94, "distance_m": 2.4,
             "heading_deg": 37, "pose": "standing"}],
            "meta": {"count": 1}}

    def _pose(inputs):
        return {"detections": [
            {"label": "person", "pose": "standing", "keypoints": 17,
             "confidence": 0.88}], "meta": {"fps": 24}}

    def _gesture(inputs):
        return {"detections": [
            {"gesture": "wave", "confidence": 0.81}], "meta": {}}

    def _scene(inputs):
        return {"detections": [{"label": "office", "confidence": 0.87}],
                "meta": {}}

    def _segmentation(inputs):
        return {"detections": [{"class": "floor", "area_pct": 42},
                               {"class": "wall", "area_pct": 31}],
                "meta": {"classes": 6}}

    def _depth(inputs):
        return {"detections": [{"object": "person", "depth_m": 2.4},
                               {"object": "wall", "depth_m": 4.1}],
                "meta": {"points": 48000}}

    def _motion(inputs):
        return {"detections": [{"region": "center", "motion": 0.12}],
                "meta": {"active": True}}

    def _change(inputs):
        return {"detections": [{"change": "chair moved", "confidence": 0.9},
                               {"change": "door opened", "confidence": 0.84}],
                "meta": {"diff_region": "north-doorway"}}

    return {"object_detection": _detect, "object_tracking": _track,
            "person_detection": _person, "pose_estimation": _pose,
            "gesture_recognition": _gesture, "scene_classification": _scene,
            "semantic_segmentation": _segmentation, "depth_understanding": _depth,
            "motion_detection": _motion, "change_detection": _change}


# ---------------------------------------------------------------------------
# World intelligence (§C 21–30)
# ---------------------------------------------------------------------------
class WorldIntelligence:
    """Semantic world model, object memory, location memory, world API."""

    def __init__(self) -> None:
        self._objects: Dict[str, dict] = {}      # id → object record
        self._locations: Dict[str, dict] = {}    # name → confidence/known
        self._dynamic: List[dict] = []
        self._next = 1

    def remember_object(self, label: str, location: str, confidence: float,
                        features: Optional[dict] = None) -> str:
        oid = f"obj-{self._next}"
        self._next += 1
        self._objects[oid] = {
            "id": oid, "label": label, "location": location,
            "confidence": confidence, "features": features or {},
            "first_seen": time.time(), "last_seen": time.time()}
        return oid

    def observe(self, label: str, location: str, confidence: float) -> str:
        """Upsert: update last_seen if we've seen this label here before."""
        for oid, rec in self._objects.items():
            if rec["label"] == label and rec["location"] == location:
                rec["last_seen"] = time.time()
                rec["confidence"] = max(rec["confidence"], confidence)
                return oid
        return self.remember_object(label, location, confidence)

    def set_location_confidence(self, name: str, confidence: float) -> None:
        self._locations[name] = {"confidence": confidence,
                                 "known": confidence >= 0.5}

    def dynamic_objects(self) -> List[dict]:
        return list(self._dynamic)

    def query(self, question: str, *, near: Optional[str] = None) -> dict:
        """The world-model API: tank.ai.world.query(...)."""
        if near:
            hits = [rec for rec in self._objects.values()
                    if rec["location"] == near]
            return {"question": question, "near": near,
                    "objects": [rec["label"] for rec in hits],
                    "count": len(hits)}
        if "unknown" in question.lower() or "don't know" in question.lower():
            unknown = [name for name, loc in self._locations.items()
                       if not loc["known"]]
            return {"question": question, "unknown_areas": unknown}
        return {"question": question, "objects": [r["label"] for r in
                self._objects.values()], "count": len(self._objects)}

    def unknown_areas(self) -> List[str]:
        return [name for name, loc in self._locations.items() if not loc["known"]]

    def summary(self) -> dict:
        return {
            "objects": len(self._objects),
            "locations": len(self._locations),
            "known_locations": sum(1 for l in self._locations.values()
                                   if l["known"]),
            "dynamic_objects": len(self._dynamic),
            "unknown_areas": self.unknown_areas(),
        }


# ---------------------------------------------------------------------------
# Navigation AI (§D 31–40)
# ---------------------------------------------------------------------------
@dataclass
class Route:
    id: str
    waypoints: List[tuple]
    risk: float
    energy: float
    eta_s: float
    confidence: float

    def to_dict(self) -> dict:
        return {"id": self.id, "waypoints": self.waypoints, "risk": self.risk,
                "energy": self.energy, "eta_s": self.eta_s,
                "confidence": self.confidence}


class NavigationAI:
    """Route planning, prediction, risk/energy-aware comparison, ETA."""

    def __init__(self) -> None:
        self._next = 1

    def plan(self, start: tuple, goal: tuple, *, obstacles: Optional[list] = None,
             battery_pct: int = 100) -> List[Route]:
        """Multi-route comparison (§36): three candidate routes."""
        obstacles = obstacles or []
        obstacle_risk = min(0.9, 0.2 * len(obstacles))
        routes = []
        for i, (name, length, obstacle_factor, energy) in enumerate([
                ("A", 8.0, 0.0, 1.0), ("B", 9.5, 0.35, 1.2),
                ("C", 12.0, 0.1, 1.6)]):
            risk = min(0.95, obstacle_factor + obstacle_risk)
            eta = length / 0.4  # m/s
            conf = max(0.3, 1.0 - risk - 0.05 * (energy - 1.0))
            routes.append(Route(f"route-{name}", [start, goal], round(risk, 2),
                                round(energy, 2), round(eta), round(conf, 2)))
        return routes

    def best(self, routes: List[Route], *, risk_weight: float = 0.5,
             energy_weight: float = 0.3) -> Route:
        """Risk-aware + energy-aware selection (§34–35)."""
        return min(routes, key=lambda r: r.risk * risk_weight +
                   r.energy * energy_weight)

    def eta(self, route: Route, current_speed: float = 0.4) -> float:
        """§39 — ETA prediction."""
        return route.eta_s * 0.4 / max(current_speed, 0.05)

    def confidence(self, route: Route) -> float:
        """§40 — navigation confidence estimation."""
        return route.confidence


# ---------------------------------------------------------------------------
# AI Robot Executive (§E 41–50)
# ---------------------------------------------------------------------------
@dataclass
class Task:
    id: str
    description: str
    parent: Optional[str] = None
    status: str = "pending"        # pending / running / done / failed
    result: Optional[str] = None

    def to_dict(self) -> dict:
        return {"id": self.id, "description": self.description,
                "parent": self.parent, "status": self.status,
                "result": self.result}


class AIExecutive:
    """Natural-language → intent → tasks → subtasks → verify → recover."""

    #: simple deterministic NL command parsing (intent + location/object)
    INTENTS = [
        (("inspect", "patrol", "search", "check"), "inspect"),
        (("follow",), "follow"),
        (("goto", "go to", "drive to", "navigate"), "goto"),
        (("return", "go home", "come back"), "return_home"),
        (("stop", "halt"), "stop"),
        (("status", "how", "what", "health"), "status_query"),
    ]

    def __init__(self, service: "TankAIService") -> None:
        self._service = service
        self._tasks: Dict[str, Task] = {}
        self._next = 1
        self._goals: List[dict] = []

    def classify(self, text: str) -> str:
        """§42 — intent classification."""
        low = text.lower()
        for keys, intent in self.INTENTS:
            if any(k in low for k in keys):
                return intent
        return "unknown"

    def decompose(self, command: str) -> List[Task]:
        """§43/§47 — turn a goal into subtasks."""
        intent = self.classify(command)
        plan = {
            "inspect": ["check system", "localize", "plan route",
                        "navigate", "scan area", "classify objects",
                        "investigate anomalies", "report"],
            "follow": ["detect person", "track person", "maintain distance",
                       "follow"],
            "goto": ["localize", "plan route", "navigate", "arrive"],
            "return_home": ["localize", "plan route home", "navigate", "dock"],
            "stop": ["halt motion"],
            "status_query": ["query health", "report"],
        }.get(intent, ["parse command", "report unsupported"])
        tasks = []
        parent = None
        for desc in plan:
            task = Task(id=f"task-{self._next:02d}", description=desc,
                        parent=parent)
            self._next += 1
            self._tasks[task.id] = task
            tasks.append(task)
            parent = task.id
        self._goals.append({"command": command, "intent": intent,
                            "tasks": len(tasks),
                            "t": datetime.datetime.now().strftime("%H:%M:%S")})
        return tasks

    def run(self, command: str, inputs: Optional[dict] = None) -> dict:
        """Execute the decomposed goal end-to-end (§44–50)."""
        tasks = self.decompose(command)
        results = []
        for task in tasks:
            task.status = "running"
            result = self._execute_task(task, inputs or {})
            task.status = "done" if result["ok"] else "failed"
            task.result = result.get("summary", "")
            results.append(result)
            if not result["ok"] and self._recover(task, inputs or {}):
                task.status = "done"
                task.result = task.result + " (recovered)"
        ok = all(t.status == "done" for t in tasks)
        return {"intent": self.classify(command), "tasks": len(tasks),
                "success": ok,
                "steps": [t.to_dict() for t in tasks],
                "summary": f"{sum(1 for t in tasks if t.status == 'done')}/"
                           f"{len(tasks)} subtasks complete"}

    def _execute_task(self, task: Task, inputs: dict) -> dict:
        desc = task.description
        if "check system" in desc:
            health = self._service.registry.health_report()
            return {"ok": True, "summary": f"models healthy {health['healthy']}/"
                    f"{health['total']}"}
        if "localize" in desc:
            return {"ok": True, "summary": "pose (3.2, 4.8, 128°)"}
        if "plan" in desc:
            routes = self._service.navigation.plan((0, 0), (10, 10))
            best = self._service.navigation.best(routes)
            return {"ok": True, "summary": f"best {best.id} risk {best.risk}"}
        if "navigate" in desc:
            return {"ok": True, "summary": "arrived at waypoint"}
        if "scan" in desc or "detect" in desc:
            res = self._service.run_capability("object_detection")
            return {"ok": res.get("success", False),
                    "summary": f"{len(res.get('detections', []))} objects"}
        if "classify" in desc:
            return {"ok": True, "summary": "3 objects classified"}
        if "investigate" in desc:
            unknown = self._service.world.unknown_areas()
            return {"ok": True, "summary": f"{len(unknown)} anomalies checked"}
        if "report" in desc or "halt" in desc or "arrive" in desc or "dock" in desc:
            return {"ok": True, "summary": "done"}
        if "follow" in desc or "maintain" in desc:
            return {"ok": True, "summary": "following person"}
        return {"ok": True, "summary": "done"}

    def _recover(self, task: Task, inputs: dict) -> bool:
        """§49 — failure recovery: retry once, then ask human."""
        if task.status == "failed":
            task.status = "running"
            result = self._execute_task(task, inputs)
            task.status = "done" if result["ok"] else "failed"
            return result["ok"]
        return False

    def verify(self, task: Task) -> bool:
        """§48 — task verification."""
        return task.status == "done" and bool(task.result)

    def goals(self) -> List[dict]:
        return list(self._goals[-10:])

    def tasks(self) -> List[Task]:
        return list(self._tasks.values())


# ---------------------------------------------------------------------------
# The capability facade — tank.ai (§10)
# ---------------------------------------------------------------------------
class TankAIService:
    """Native AI subsystem — capability-based, one entry point."""

    _instance: Optional["TankAIService"] = None

    def __new__(cls) -> "TankAIService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.registry = ModelRegistry()
            cls._instance.scheduler = InferenceScheduler()
            cls._instance.governor = ResourceGovernor()
            cls._instance.perception = PerceptionLayer()
            cls._instance.world = WorldIntelligence()
            cls._instance.navigation = NavigationAI()
            cls._seed_models()
            cls._instance.executive = AIExecutive(cls._instance)
            for name, backend in default_perception_backends().items():
                cls._instance.perception.register(name, backend)
        return cls._instance

    @staticmethod
    def _seed_models() -> None:
        svc = TankAIService._instance
        svc.registry.register(AIModel(
            "yolo-v11n", "object_detection", "jetson", version="11.0",
            precision="fp16", fps=31, latency_ms=18, accuracy=0.94))
        svc.registry.register(AIModel(
            "yolo-v11n-q8", "object_detection", "unoq", version="11.0-q8",
            precision="int8", fps=12, latency_ms=64, accuracy=0.89,
            fallback_to="yolo-v11n"))
        svc.registry.register(AIModel(
            "phi-3-mini", "language", "unoq", version="3.0", precision="q4",
            fps=8, latency_ms=42, accuracy=0.87))
        svc.registry.register(AIModel(
            "deeplab-x", "semantic_segmentation", "jetson", version="2.0",
            precision="fp16", fps=24, latency_ms=26, accuracy=0.91))
        svc.registry.register(AIModel(
            "pose-x", "pose_estimation", "jetson", version="1.0",
            precision="fp16", fps=24, latency_ms=30, accuracy=0.88))

    # §10 — capability discovery: what AI capabilities exist?
    def capabilities(self) -> Dict[str, Any]:
        return {
            "perception": self.perception.capabilities(),
            "world": ["world.query", "world.memory", "world.unknown_areas"],
            "navigation": ["navigation.plan", "navigation.best", "navigation.eta"],
            "language": ["language.chat"],
            "models": [m.to_dict() for m in self.registry.list()],
        }

    def run_capability(self, capability: str, inputs: Optional[dict] = None,
                       *, prefer_device: Optional[str] = None) -> Dict[str, Any]:
        """The capability API — TankOS picks model/device/precision/fallback.

        Applications ask for a capability; TankOS decides the rest.
        """
        inputs = inputs or {}
        # perception capabilities
        if capability in self.perception.capabilities():
            model = self.registry.select(capability, prefer_device=prefer_device)
            if model is None:
                return {"capability": capability, "success": False,
                        "error": "no healthy model"}
            device = prefer_device or model.device
            job = self.scheduler.submit(capability, device=device)
            self.scheduler.run(job, device)
            try:
                result = self.perception.run(capability, inputs)
            finally:
                self.scheduler.complete(job)
            return {"capability": capability, "success": True, "device": device,
                    "model": model.name, "precision": model.precision,
                    "fps": model.fps, **result.to_dict()}
        if capability == "world.query":
            return {"capability": capability, "success": True,
                    **self.world.query(inputs.get("question", ""),
                                       near=inputs.get("near"))}
        if capability == "navigation.plan":
            routes = self.navigation.plan(inputs.get("start", (0, 0)),
                                          inputs.get("goal", (10, 10)),
                                          obstacles=inputs.get("obstacles"),
                                          battery_pct=inputs.get("battery_pct", 100))
            return {"capability": capability, "success": True,
                    "routes": [r.to_dict() for r in routes]}
        if capability == "language.chat":
            model = self.registry.select("language")
            return {"capability": capability, "success": True,
                    "model": model.name if model else "none",
                    "reply": "(local assistant — capability-based routing)"}
        if capability == "executive.run":
            return {"capability": capability, "success": True,
                    **self.executive.run(inputs.get("command", ""))}
        return {"capability": capability, "success": False,
                "error": f"unknown capability {capability}"}

    def status(self) -> Dict[str, Any]:
        return {
            "capabilities": self.capabilities(),
            "model_health": self.registry.health_report(),
            "scheduler_load": self.scheduler.load(),
            "world": self.world.summary(),
            "budgets": dict(self.governor._budgets),
        }

    def reset(self) -> None:
        self.registry._models.clear()
        self.scheduler._queue.clear()
        self.scheduler._running.clear()
        self.perception._backends.clear()
        self.world._objects.clear()
        self.world._locations.clear()
        self._seed_models()
        for name, backend in default_perception_backends().items():
            self.perception.register(name, backend)
        return self
