"""TankOS Companion Agent — emotion, personality, dialogue, social interaction, empathy."""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from tank_os.core.agents.base_agent import BaseAgent, AgentResult
from tank_os.core.emotion_manager import EmotionManager


class CompanionAgent(BaseAgent):
    name = "companion"
    description = "Emotion, personality, dialogue, social interaction, empathy"

    def __init__(self) -> None:
        super().__init__()
        self._emotion = EmotionManager()
        self._capabilities = ["chat", "express_emotion", "check_mood",
                              "greet", "respond", "empathize"]
        self._greeting_count = 0

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        p = params or {}
        if task == "chat":
            message = p.get("message", "")
            emotion = self._emotion.current
            if "sad" in message.lower() or "help" in message.lower():
                self._emotion.set_emotion("compassion", 0.6, -0.2, 0.7)
            elif "thank" in message.lower():
                self._emotion.set_emotion("gratitude", 0.85, 0.3, 0.6)
            elif "happy" in message.lower() or "great" in message.lower():
                self._emotion.set_emotion("joy", 0.95, 0.6, 0.8)
            return AgentResult(success=True, data={
                "reply": f"({emotion['name']}) I received your message",
                "emotion": emotion["name"],
            })
        elif task == "express_emotion":
            em = p.get("emotion", "neutral")
            val = p.get("valence", 0.0)
            aro = p.get("arousal", 0.0)
            self._emotion.set_emotion(em, val, aro, 0.7)
            return AgentResult(success=True, data={"emotion": em, "state": self._emotion.current})
        elif task == "check_mood":
            return AgentResult(success=True, data=self._emotion.current)
        elif task == "greet":
            self._greeting_count += 1
            self._emotion.set_emotion("joy", 0.9, 0.5, 0.7)
            name = p.get("name", "friend")
            return AgentResult(success=True, data={
                "greeting": f"Hello {name}! (greeting #{self._greeting_count})",
                "emotion": "joy",
            })
        elif task == "empathize":
            feeling = p.get("feeling", "unknown")
            self._emotion.set_emotion("compassion", 0.5, -0.1, 0.6)
            return AgentResult(success=True, data={
                "response": f"I understand you're feeling {feeling}. I'm here for you.",
                "emotion": "compassion",
            })
        return AgentResult(success=False, error=f"Unknown task: {task}")


