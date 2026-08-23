"""
vlm_bridge.py - Vision-Language AI (Features 181-190)
Local LLM inference, VLM, scene description, natural language commands
"""
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("tank.ai.vlm")

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


class VisionLanguageBridge:
    """Features 181-190: Vision-Language and generative AI bridge."""

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.llm = None
        self.local_model = None
        self.token_count = 0
        self.inference_times: List[float] = []
        self.scene_descriptions: List[str] = []
        self.command_history: List[Dict] = []
        if LLAMA_AVAILABLE and model_path:
            try:
                self.llm = Llama(model_path=model_path, n_ctx=2048, n_threads=4)
                logger.info(f"LLM loaded: {model_path}")
            except Exception as e:
                logger.error(f"LLM load failed: {e}")

    # 181. Local LLM inference
    def query_llm(self, prompt: str, max_tokens: int = 200) -> Dict[str, Any]:
        start = time.time()
        if self.llm:
            try:
                result = self.llm(prompt, max_tokens=max_tokens, stop=["</s>", "\n\n"])
                text = result["choices"][0]["text"]
                elapsed = (time.time() - start) * 1000
                self.inference_times.append(elapsed)
                self.token_count += len(text.split())
                return {"response": text.strip(), "latency_ms": round(elapsed, 1),
                        "tokens": len(text.split()), "method": "local_llm"}
            except Exception as e:
                return {"response": f"LLM error: {e}", "method": "error"}
        return {"response": "No local model loaded", "method": "fallback"}

    # 182. Vision-Language Model
    def describe_image(self, image_description: str, context: str = "") -> Dict[str, Any]:
        prompt = f"""Describe what the robot sees based on these detections:
{image_description}
{f'Context: {context}' if context else ''}

Describe concisely:"""
        return self.query_llm(prompt, max_tokens=100)

    # 183. Image question answering
    def answer_question(self, image_info: str, question: str) -> Dict[str, Any]:
        prompt = f"Based on what the robot sees: {image_info}\nQuestion: {question}\nAnswer:"
        return self.query_llm(prompt, max_tokens=150)

    # 184. Scene description
    def describe_scene(self, detections: List[Dict], depth_info: Dict = None,
                       lidar_info: Dict = None) -> str:
        det_text = ", ".join([f"{d.get('class', '?')} at {d.get('distance_est', '?')}m" for d in detections[:5]])
        prompt = f"The robot sees: {det_text}. Describe the scene briefly:"
        result = self.query_llm(prompt, max_tokens=80)
        desc = result.get("response", "Unable to describe scene")
        self.scene_descriptions.append(desc)
        return desc

    # 185-186. Natural language commands + Command-to-action parser
    def parse_natural_command(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        commands = []
        if any(w in text_lower for w in ["move forward", "go ahead", "advance"]):
            commands.append({"action": "move", "direction": "forward", "speed": 150})
        elif any(w in text_lower for w in ["move back", "reverse", "go back"]):
            commands.append({"action": "move", "direction": "backward", "speed": 150})
        elif any(w in text_lower for w in ["turn left", "go left"]):
            commands.append({"action": "turn", "direction": "left", "angle": 30})
        elif any(w in text_lower for w in ["turn right", "go right"]):
            commands.append({"action": "turn", "direction": "right", "angle": 30})
        elif any(w in text_lower for w in ["stop", "halt", "freeze"]):
            commands.append({"action": "stop"})
        elif any(w in text_lower for w in ["patrol", "patrol mode"]):
            commands.append({"action": "patrol", "mode": "start"})
        elif any(w in text_lower for w in ["go home", "return", "go back home"]):
            commands.append({"action": "return_home"})
        elif any(w in text_lower for w in ["take photo", "capture", "snapshot"]):
            commands.append({"action": "capture_image"})
        elif any(w in text_lower for w in ["what do you see", "describe", "look around"]):
            commands.append({"action": "describe_scene"})
        elif any(w in text_lower for w in ["where am i", "position", "location"]):
            commands.append({"action": "get_position"})
        elif any(w in text_lower for w in ["status", "how are you", "health"]):
            commands.append({"action": "get_status"})
        else:
            parsed = self.query_llm(f"Convert this robot command to JSON action: '{text}'\nJSON:", max_tokens=100)
            return {"raw": text, "llm_parsed": parsed.get("response", ""), "commands": []}
        self.command_history.append({"text": text, "commands": commands, "time": time.time()})
        return {"text": text, "commands": commands}

    # 187. Local AI assistant
    def chat(self, message: str) -> str:
        system = "You are TankOS AI, the brain of an autonomous robot. Be helpful and concise."
        prompt = f"System: {system}\nUser: {message}\nTankOS:"
        result = self.query_llm(prompt, max_tokens=200)
        return result.get("response", "I'm not sure how to respond.")

    # 188. Robot status explanation
    def explain_status(self, status: Dict[str, Any]) -> str:
        status_text = str(status)[:500]
        prompt = f"Explain this robot status to the operator: {status_text}\nExplanation:"
        result = self.query_llm(prompt, max_tokens=150)
        return result.get("response", "Status check completed.")

    # 189. Visual reasoning pipeline
    def visual_reasoning(self, detections: List[Dict], question: str) -> Dict[str, Any]:
        context = ", ".join([f"{d.get('class','?')}({d.get('confidence',0):.0%})" for d in detections[:8]])
        prompt = f"Objects detected: {context}\nQuestion: {question}\nReasoning and answer:"
        result = self.query_llm(prompt, max_tokens=200)
        return {"answer": result.get("response", ""), "context_objects": len(detections)}

    # 190. AI mission planner
    def plan_mission(self, goal: str, current_state: Dict) -> Dict[str, Any]:
        state_text = str(current_state)[:300]
        prompt = f"Robot state: {state_text}\nGoal: {goal}\nPlan 3 steps:"
        result = self.query_llm(prompt, max_tokens=200)
        return {"mission": goal, "plan": result.get("response", ""), "steps": []}

    def get_performance(self) -> Dict[str, Any]:
        avg_latency = sum(self.inference_times) / max(1, len(self.inference_times))
        return {
            "total_tokens": self.token_count,
            "inferences": len(self.inference_times),
            "avg_latency_ms": round(avg_latency, 1),
            "model_loaded": self.llm is not None,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "llm_loaded": self.llm is not None,
            "model_path": self.model_path,
            "scene_descriptions": len(self.scene_descriptions),
            "commands_parsed": len(self.command_history),
            "performance": self.get_performance(),
        }
