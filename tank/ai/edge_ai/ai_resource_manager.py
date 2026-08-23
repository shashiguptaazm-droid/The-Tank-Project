"""
ai_resource_manager.py - Advanced Edge-AI System (Features 191-200)
AI Resource Manager, model registry, workload scheduler, performance dashboard
"""
import time
import subprocess
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger("tank.ai.edge_ai")


class WorkloadPriority(Enum):
    CRITICAL = 0   # Safety, e-stop
    HIGH = 1       # Perception, obstacle avoidance
    MEDIUM = 2     # Navigation, tracking
    LOW = 3        # LLM, scene description
    BACKGROUND = 4 # Recording, logging


class AIModel:
    def __init__(self, name: str, model_type: str, path: str, precision: str = "fp16"):
        self.name = name
        self.model_type = model_type
        self.path = path
        self.precision = precision
        self.loaded = False
        self.version = "1.0"
        self.health = 1.0
        self.last_used = 0.0
        self.inference_count = 0
        self.total_latency_ms = 0.0

    def record_inference(self, latency_ms: float):
        self.inference_count += 1
        self.total_latency_ms += latency_ms
        self.last_used = time.time()

    def avg_latency(self) -> float:
        return self.total_latency_ms / max(1, self.inference_count)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "type": self.model_type, "precision": self.precision,
            "loaded": self.loaded, "version": self.version, "health": round(self.health, 2),
            "inferences": self.inference_count, "avg_latency_ms": round(self.avg_latency(), 1),
        }


class AIResourceManager:
    """Features 191-200: AI Resource Manager for Jetson Orin Nano Super."""

    def __init__(self):
        self.models: Dict[str, AIModel] = {}
        self.workloads: List[Dict] = []
        self.scheduled: List[str] = []
        self.gpu_overloaded = False
        self.gpu_temp = 0.0
        self.gpu_util = 0.0
        self.ram_util = 0.0
        self.power_budget_w = 15.0
        self.thermal_threshold = 83.0
        self.versions: Dict[str, List[str]] = {}
        self.rollback_log: List[Dict] = []
        self.perception_fps = 0.0
        self.llm_tokens_per_sec = 0.0
        self.performance_history: List[Dict] = []

    # 191. AI model registry
    def register_model(self, name: str, model_type: str, path: str, precision: str = "fp16") -> AIModel:
        model = AIModel(name, model_type, path, precision)
        self.models[name] = model
        if name not in self.versions:
            self.versions[name] = []
        self.versions[name].append(model.version)
        return model

    def get_model(self, name: str) -> Optional[AIModel]:
        return self.models.get(name)

    # 192. Automatic model selection
    def select_model(self, task: str, constraints: Dict[str, Any] = None) -> Optional[str]:
        candidates = []
        for name, model in self.models.items():
            if task in model.model_type or model.model_type in task:
                score = model.health * 10 - model.avg_latency() * 0.1
                if model.loaded:
                    score += 5
                candidates.append((name, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0] if candidates else None

    # 193-194. Model versioning + Rollback
    def update_model_version(self, name: str, new_version: str):
        if name in self.versions:
            self.versions[name].append(new_version)
        else:
            self.versions[name] = [new_version]
        if name in self.models:
            self.models[name].version = new_version

    def rollback_model(self, name: str) -> bool:
        if name in self.versions and len(self.versions[name]) > 1:
            self.versions[name].pop()
            old_version = self.versions[name][-1]
            if name in self.models:
                self.models[name].version = old_version
            self.rollback_log.append({"model": name, "to_version": old_version, "time": time.time()})
            logger.info(f"Model {name} rolled back to {old_version}")
            return True
        return False

    # 195. Model health monitoring
    def check_model_health(self, name: str) -> float:
        model = self.models.get(name)
        if not model:
            return 0.0
        recency = max(0, 1.0 - (time.time() - model.last_used) / 300) if model.last_used > 0 else 0.5
        latency_score = max(0, 1.0 - model.avg_latency() / 100)
        model.health = 0.5 * recency + 0.5 * latency_score
        return model.health

    # 196-197. AI confidence aggregation + disagreement detection
    def aggregate_confidence(self, model_confidences: Dict[str, float]) -> Dict[str, Any]:
        if not model_confidences:
            return {"aggregated": 0, "count": 0}
        values = list(model_confidences.values())
        import numpy as np
        mean_conf = float(np.mean(values))
        std_conf = float(np.std(values))
        return {"aggregated": round(mean_conf, 3), "std": round(std_conf, 3),
                "count": len(values), "disagreement": std_conf > 0.3}

    def detect_ai_disagreement(self, model_outputs: Dict[str, Any]) -> Dict[str, Any]:
        if len(model_outputs) < 2:
            return {"disagreement": False}
        labels = [o.get("label", "") for o in model_outputs.values()]
        unique = set(labels)
        return {"disagreement": len(unique) > 1, "labels": list(unique),
                "confidence_range": [o.get("confidence", 0) for o in model_outputs.values()]}

    # 198. AI workload scheduler
    def schedule_workload(self, name: str, priority: WorkloadPriority, estimated_gpu: float,
                          estimated_ram: float) -> Dict[str, Any]:
        workload = {
            "name": name, "priority": priority.value,
            "gpu": estimated_gpu, "ram": estimated_ram,
            "scheduled_at": time.time(),
        }
        self.workloads.append(workload)
        self.workloads.sort(key=lambda w: w["priority"])
        self._rebalance()
        return {"scheduled": name, "priority": priority.name, "total_workloads": len(self.workloads)}

    def _rebalance(self):
        stats = self._read_gpu_stats()
        self.gpu_util = stats.get("gpu_util", 0)
        self.gpu_temp = stats.get("gpu_temp", 0)
        self.ram_util = stats.get("ram_pct", 0)
        self.gpu_overloaded = self.gpu_util > 85 or self.gpu_temp > self.thermal_threshold
        if self.gpu_overloaded:
            for w in self.workloads:
                if w["priority"] >= WorkloadPriority.LOW.value:
                    logger.warning(f"Throttling workload: {w['name']} (GPU overloaded)")
            self.scheduled = [w["name"] for w in self.workloads if w["priority"] < WorkloadPriority.LOW.value]
        else:
            self.scheduled = [w["name"] for w in self.workloads]

    # 199. AI performance dashboard
    def get_dashboard(self) -> Dict[str, Any]:
        stats = self._read_gpu_stats()
        return {
            "gpu": {
                "utilization": stats.get("gpu_util", 0),
                "temperature": stats.get("gpu_temp", 0),
                "memory_used": stats.get("gpu_mem_used", 0),
                "memory_total": stats.get("gpu_mem_total", 0),
                "overloaded": self.gpu_overloaded,
            },
            "models": {name: m.to_dict() for name, m in self.models.items()},
            "workloads": {
                "total": len(self.workloads),
                "active": len(self.scheduled),
                "names": self.scheduled,
            },
            "performance": {
                "perception_fps": self.perception_fps,
                "llm_tokens_per_sec": self.llm_tokens_per_sec,
            },
            "versions": {k: v[-3:] for k, v in self.versions.items()},
        }

    # 200. Autonomous AI orchestration
    def orchestrate(self, camera_frame=None, detections=None, sensor_data=None,
                    user_command=None) -> Dict[str, Any]:
        pipeline = {
            "camera": bool(camera_frame is not None),
            "detection": bool(detections),
            "tracking": False,
            "depth": False,
            "sensor_fusion": bool(sensor_data),
            "navigation": False,
            "risk_assessment": False,
            "mission_planning": bool(user_command),
            "safety_check": True,
            "motor_command": False,
        }
        if camera_frame:
            self.schedule_workload("perception", WorkloadPriority.HIGH, 30, 500)
            pipeline["detection"] = True
        if detections:
            self.schedule_workload("tracking", WorkloadPriority.HIGH, 15, 200)
            pipeline["tracking"] = True
        if sensor_data:
            self.schedule_workload("fusion", WorkloadPriority.HIGH, 5, 100)
            pipeline["sensor_fusion"] = True
        if user_command:
            self.schedule_workload("planning", WorkloadPriority.MEDIUM, 20, 300)
            pipeline["mission_planning"] = True
        pipeline["safety_check"] = True
        return {"pipeline": pipeline, "active_workloads": len(self.scheduled)}

    def _read_gpu_stats(self) -> Dict[str, float]:
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                timeout=3, text=True
            ).strip()
            parts = out.split(", ")
            return {"gpu_temp": float(parts[0]), "gpu_util": float(parts[1]),
                    "gpu_mem_used": int(parts[2]), "gpu_mem_total": int(parts[3])}
        except Exception:
            pass
        try:
            out = subprocess.check_output(["free", "-m"], timeout=3, text=True)
            for line in out.split("\n"):
                if "Mem:" in line:
                    parts = line.split()
                    total = int(parts[1])
                    used = int(parts[2])
                    return {"ram_pct": round(used / total * 100, 1)}
        except Exception:
            pass
        return {}

    def get_status(self) -> Dict[str, Any]:
        return {
            "models_registered": len(self.models),
            "models_loaded": sum(1 for m in self.models.values() if m.loaded),
            "workloads_total": len(self.workloads),
            "workloads_active": len(self.scheduled),
            "gpu_overloaded": self.gpu_overloaded,
            "versions_tracked": len(self.versions),
            "rollbacks": len(self.rollback_log),
        }
