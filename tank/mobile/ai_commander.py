"""
ai_commander.py - AI-Powered SMS/Command Processor
Processes incoming messages with local LLM + cloud AI fallback
Generates intelligent responses, alerts, and autonomous actions
"""
import json
import time
import logging
import subprocess
import os
from datetime import datetime

logger = logging.getLogger("tank.ai_commander")

LOCAL_MODELS = {
    "phi3": os.path.expanduser("~/models/phi-3-mini-4k-instruct-Q4_K_M.gguf"),
    "tinyllama": os.path.expanduser("~/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"),
}

TANK_SYSTEM_PROMPT = """You are TankOS AI — the brain of an autonomous AI tracked robot called "The Tank".
You are connected to the user via SMS/Telegram. Keep responses SHORT (under 160 chars for SMS).
You have: camera vision, LiDAR, IMU, 4G LTE, motors, servos, AI models.
Commands you understand: STATUS, CAMERA, MOVE, STOP, SCAN, WHERE, HELP
Always be helpful, concise, and technically accurate."""


class AICommander:
    def __init__(self):
        self.local_model = None
        self.lslm_loaded = False
        self.conversation_history = []
        self.commands_registered = {
            "STATUS": self.cmd_status,
            "HELP": self.cmd_help,
            "WHERE": self.cmd_location,
            "CAMERA": self.cmd_camera,
            "SCAN": self.cmd_scan,
            "MOVE": self.cmd_move,
            "STOP": self.cmd_stop,
            "BATTERY": self.cmd_battery,
            "ALERTS": self.cmd_alerts,
            "AI": self.cmd_ai,
        }
        self.alerts = []
        self.last_camera_frame = None
        self.robot_state = {
            "position": {"lat": 0.0, "lon": 0.0},
            "motors": {"left": 0, "right": 0},
            "sensors": {},
            "mode": "standby",
            "uptime": 0,
            "alerts_count": 0,
        }

    def load_local_model(self, model_name="phi3"):
        model_path = LOCAL_MODELS.get(model_name)
        if not model_path or not os.path.exists(model_path):
            logger.warning(f"Local model {model_name} not found")
            return False
        try:
            from llama_cpp import Llama
            self.local_model = Llama(model_path=model_path, n_ctx=2048, n_threads=4)
            self.lslm_loaded = True
            logger.info(f"Loaded local model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def process_message(self, phone, message, context=None):
        """Process incoming SMS and return AI response"""
        msg_upper = message.strip().upper()
        for cmd_key, cmd_func in self.commands_registered.items():
            if msg_upper.startswith(cmd_key) or msg_upper == cmd_key:
                args = message.strip()[len(cmd_key):].strip()
                return cmd_func(phone, args, context)

        return self._ai_respond(message, context)

    def _ai_respond(self, message, context=None):
        """Use local LLM or cloud AI to respond"""
        if self.lslm_loaded and self.local_model:
            try:
                history = self.conversation_history[-6:]
                messages = [{"role": "system", "content": TANK_SYSTEM_PROMPT}]
                for h in history:
                    messages.append(h)
                messages.append({"role": "user", "content": message})

                response = self.local_model.create_chat_completion(
                    messages=messages,
                    max_tokens=150,
                    temperature=0.7,
                )
                reply = response["choices"][0]["message"]["content"][:160]
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
            except Exception as e:
                logger.error(f"Local LLM error: {e}")

        return self._cloud_respond(message)

    def _cloud_respond(self, message):
        """Cloud AI fallback via OpenRouter"""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return f"TankOS: Received '{message}'. Reply HELP for commands."

        try:
            import urllib.request
            data = json.dumps({
                "model": "google/gemma-2-2b-it",
                "messages": [
                    {"role": "system", "content": TANK_SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 150,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"][:160]
        except Exception as e:
            logger.error(f"Cloud AI error: {e}")
            return f"TankOS AI: Processing error. Reply HELP for commands."

    # === COMMAND HANDLERS ===

    def cmd_status(self, phone, args, ctx):
        s = self.robot_state
        return (
            f"Tank Status: Mode={s['mode']} "
            f"MotorL={s['motors']['left']} MotorR={s['motors']['right']} "
            f"Alerts={s['alerts_count']}"
        )

    def cmd_help(self, phone, args, ctx):
        return (
            "TankOS Commands:\n"
            "STATUS - Robot status\n"
            "CAMERA - Get vision\n"
            "SCAN - LiDAR scan\n"
            "WHERE - Position\n"
            "MOVE L/R/F/B - Move\n"
            "STOP - E-stop\n"
            "BATTERY - Power\n"
            "ALERTS - Recent alerts\n"
            "AI <msg> - Chat with AI\n"
            "Any text = AI chat"
        )

    def cmd_location(self, phone, args, ctx):
        pos = self.robot_state["position"]
        return f"Position: {pos['lat']:.6f}, {pos['lon']:.6f}"

    def cmd_camera(self, phone, args, ctx):
        return "Camera: Capturing frame... Check dashboard for live feed."

    def cmd_scan(self, phone, args, ctx):
        return "LiDAR: Scanning environment... Dashboard shows map."

    def cmd_move(self, phone, args, ctx):
        direction = args.upper().strip() if args else "F"
        dir_map = {"F": "Forward", "B": "Backward", "L": "Left", "R": "Right"}
        dir_name = dir_map.get(direction, "Forward")
        self.robot_state["mode"] = "moving"
        return f"Moving {dir_name}"

    def cmd_stop(self, phone, args, ctx):
        self.robot_state["motors"] = {"left": 0, "right": 0}
        self.robot_state["mode"] = "stopped"
        return "E-STOP: All motors stopped."

    def cmd_battery(self, phone, args, ctx):
        return "Battery: Checking power systems... See dashboard for details."

    def cmd_alerts(self, phone, args, ctx):
        if not self.alerts:
            return "No alerts. All systems nominal."
        recent = self.alerts[-3:]
        lines = [f"[{a['time']}] {a['message']}" for a in recent]
        return "\n".join(lines)[:160]

    def cmd_ai(self, phone, args, ctx):
        if args:
            return self._ai_respond(args, ctx)
        return "Usage: AI <your question>"

    def add_alert(self, alert_type, message, data=None):
        alert = {
            "type": alert_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.alerts.append(alert)
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        self.robot_state["alerts_count"] = len(self.alerts)
        return alert

    def get_full_status(self):
        return {
            "robot_state": self.robot_state,
            "alerts": self.alerts[-10:],
            "conversation": self.conversation_history[-6:],
            "model_loaded": self.lslm_loaded,
        }
