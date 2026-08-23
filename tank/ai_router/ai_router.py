"""
TankOS AI Selection Router
===========================
Policy-driven router that selects the best model/provider/device for each task
based on capability, quality, latency, cost, privacy, power, network, and health.

Flow: Task -> Requirements -> Filter -> Score -> Select -> Execute -> Verify
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("tank.ai_router")


@dataclass
class TaskProfile:
    """Structured task with requirements."""
    task_type: str = "general"
    requires_vision: bool = False
    requires_reasoning: bool = False
    requires_code: bool = False
    requires_voice: bool = False
    requires_local: bool = False
    latency_requirement: str = "medium"  # low, medium, high
    privacy_requirement: str = "normal"  # public, normal, private, sensitive
    complexity: str = "medium"  # low, medium, high
    language: str = "en"


# Task weight profiles
TASK_WEIGHTS = {
    "emergency_robotics": {
        "safety": 0.30, "latency": 0.25, "reliability": 0.25,
        "quality": 0.15, "cost": 0.05
    },
    "navigation": {
        "latency": 0.30, "reliability": 0.25, "safety": 0.20,
        "quality": 0.15, "cost": 0.10
    },
    "conversation": {
        "quality": 0.30, "latency": 0.25, "reliability": 0.20,
        "cost": 0.15, "privacy": 0.10
    },
    "coding": {
        "quality": 0.35, "reasoning": 0.25, "context": 0.15,
        "latency": 0.10, "reliability": 0.10, "cost": 0.05
    },
    "vision": {
        "quality": 0.30, "latency": 0.25, "reliability": 0.20,
        "privacy": 0.15, "cost": 0.10
    },
    "offline_mode": {
        "locality": 0.35, "latency": 0.25, "reliability": 0.20,
        "quality": 0.15, "power": 0.05
    },
    "multilingual": {
        "quality": 0.25, "language_fit": 0.30, "reliability": 0.20,
        "latency": 0.15, "cost": 0.10
    },
}


class AISelectionRouter:
    """Selects the best AI provider for each task using policy-driven scoring."""

    def __init__(self, provider_registry=None):
        self._registry = provider_registry
        self._battery_percent = 100.0
        self._gpu_load = 0.0
        self._network_latency_ms = 50.0
        self._network_available = True
        self._task_history: list[dict] = []

    def set_registry(self, registry):
        self._registry = registry

    def update_context(self, battery: float = None, gpu_load: float = None,
                       network_latency: float = None, network_available: bool = None):
        if battery is not None:
            self._battery_percent = battery
        if gpu_load is not None:
            self._gpu_load = gpu_load
        if network_latency is not None:
            self._network_latency_ms = network_latency
        if network_available is not None:
            self._network_available = network_available

    def classify_task(self, text: str, intent: str = None) -> TaskProfile:
        """Classify a request into a task profile."""
        t = text.lower()
        profile = TaskProfile()

        if not intent:
            if any(w in t for w in ["stop", "emergency", "help"]):
                intent = "emergency_robotics"
            elif any(w in t for w in ["go to", "move", "navigate", "patrol"]):
                intent = "navigation"
            elif any(w in t for w in ["what", "see", "detect", "look", "who"]):
                intent = "vision"
            elif any(w in t for w in ["code", "write", "generate", "build"]):
                intent = "coding"
            elif any(w in t for w in ["translate", "hindi", "gujarati"]):
                intent = "multilingual"
            else:
                intent = "conversation"

        profile.task_type = intent
        profile.requires_vision = intent in ("vision",)
        profile.requires_reasoning = intent in ("coding", "conversation")
        profile.requires_code = intent == "coding"
        profile.requires_voice = any(w in t for w in ["speak", "voice", "listen"])
        profile.requires_local = not self._network_available or any(
            w in t for w in ["offline", "local only"])
        profile.privacy_requirement = "private" if any(
            w in t for w in ["private", "secret", "personal"]) else "normal"

        # Check for Indian languages
        hi_chars = set("अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")
        if any(c in text for c in hi_chars) or any(w in t for w in ["hindi", "gujarati"]):
            profile.language = "hi"
            profile.task_type = "multilingual"

        return profile

    def select_model(self, task: TaskProfile) -> dict:
        """Select the best AI model for a task. Returns selection info."""
        if not self._registry:
            return {"selected": "fallback_rule_based", "confidence": 0.3}

        # Determine required capability
        from tank.ai.providers.provider_registry import AICapability
        cap_map = {
            "vision": AICapability.VLM,
            "conversation": AICapability.LLM_TEXT,
            "coding": AICapability.CODING,
            "navigation": AICapability.ROBOTICS,
            "multilingual": AICapability.TRANSLATION,
            "emergency_robotics": AICapability.LLM_TEXT,
        }
        capability = cap_map.get(task.task_type, AICapability.LLM_TEXT)

        # Get candidates
        candidates = self._registry.find_capable(capability)

        # Apply hard constraints (eliminate impossible candidates)
        candidates = self._apply_constraints(candidates, task)

        if not candidates:
            # Fallback to local models
            candidates = [c for c in self._registry.find_capable(capability)
                         if not c.requires_network]
            if not candidates:
                return {"selected": "rule_based_fallback", "confidence": 0.2,
                        "reason": "no_capable_provider"}

        # Score candidates
        weights = TASK_WEIGHTS.get(task.task_type, TASK_WEIGHTS["conversation"])
        scored = []
        for c in candidates:
            score = self._score_candidate(c, task, weights)
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best = scored[0] if scored else (0, None)
        alternatives = [{"name": s.display_name, "score": round(sc, 1)}
                       for sc, s in scored[1:4]]

        return {
            "selected": best.name if best else "none",
            "display_name": best.display_name if best else "None",
            "score": round(best_score, 1),
            "model": best.models[0] if best and best.models else "default",
            "alternatives": alternatives,
            "reason": self._explain_selection(best, task, best_score),
            "latency_ms": best.latency_ms if best else 0,
            "free": best.free_tier if best else False,
            "local": not (best.requires_network if best else True),
            "privacy": best.privacy_level if best else "unknown",
        }

    def _apply_constraints(self, candidates, task: TaskProfile) -> list:
        filtered = []
        for c in candidates:
            # Network check
            if task.requires_local and c.requires_network:
                continue
            if not self._network_available and c.requires_network:
                continue

            # Privacy check
            if task.privacy_requirement in ("private", "sensitive"):
                if c.privacy_level == "cloud":
                    continue

            # Battery check
            if self._battery_percent < 20 and not c.free_tier:
                continue

            # Language check
            if task.language != "en" and task.language not in c.languages:
                if task.task_type != "multilingual":
                    continue

            filtered.append(c)
        return filtered

    def _score_candidate(self, provider, task: TaskProfile, weights: dict) -> float:
        """Score a candidate provider for a task."""
        # Capability match
        cap_score = 80  # Already filtered to capable providers
        if provider.supports_tools:
            cap_score += 10
        if task.requires_vision and provider.supports_vision:
            cap_score += 10

        # Quality (based on provider priority)
        quality = provider.priority

        # Latency
        latency_score = max(0, 100 - provider.latency_ms / 50)

        # Reliability
        health = self._registry.get_health(provider.name) if self._registry else None
        reliability = 80
        if health:
            reliability = max(20, 100 - health.fail_count * 10)

        # Cost
        cost_score = 100 if provider.free_tier else max(0,
            100 - provider.cost_per_1k_tokens * 500)

        # Privacy
        privacy = {"local": 100, "hybrid": 70, "cloud": 40}.get(
            provider.privacy_level, 50)

        # Hardware fit (prefer local if low battery)
        hw_fit = 80
        if self._battery_percent < 30 and not provider.requires_network:
            hw_fit = 100
        if self._gpu_load > 90 and provider.privacy_level == "local":
            hw_fit = 40

        # Network fit
        network_fit = 90 if not provider.requires_network else (
            80 if self._network_latency_ms < 100 else 50)

        # Weighted sum
        score = (
            cap_score * weights.get("quality", 0.25) +
            quality * weights.get("quality", 0.25) +
            latency_score * weights.get("latency", 0.25) +
            reliability * weights.get("reliability", 0.20) +
            cost_score * weights.get("cost", 0.10) +
            privacy * weights.get("privacy", 0.10) +
            hw_fit * 0.10 +
            network_fit * 0.05
        )

        return round(max(0, min(100, score)), 1)

    def _explain_selection(self, provider, task: TaskProfile, score: float) -> str:
        reasons = []
        if provider and not provider.requires_network:
            reasons.append("local")
        if provider and provider.free_tier:
            reasons.append("free")
        if provider and provider.latency_ms < 500:
            reasons.append("fast")
        if task.privacy_requirement in ("private", "sensitive"):
            reasons.append("private")
        if self._battery_percent < 30:
            reasons.append("low_battery_local")
        if not reasons:
            reasons.append("best_score")
        return " + ".join(reasons)

    def record_task(self, task: TaskProfile, selection: dict, success: bool):
        self._task_history.append({
            "task": task.task_type,
            "selected": selection.get("selected"),
            "score": selection.get("score"),
            "success": success,
            "timestamp": time.time()
        })

    def get_status(self) -> dict:
        return {
            "battery": self._battery_percent,
            "gpu_load": self._gpu_load,
            "network_latency_ms": self._network_latency_ms,
            "network_available": self._network_available,
            "tasks_processed": len(self._task_history),
            "recent_tasks": self._task_history[-5:] if self._task_history else []
        }


# Global singleton
AI_ROUTER = AISelectionRouter()
