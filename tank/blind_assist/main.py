"""Blind-Assistance Module — Tank External Wearable for Visually Impaired Users.

This module runs on the Arduino UNO Q (QRB2210 + STM32U585) and coordinates
real-time AI vision assistance for blind users. It captures frames from an
ESP32-S3 CAM worn by the user, routes them to the Jetson AI brain or cloud AI
for analysis, and provides spoken feedback + visual alerts.

Architecture:
  ESP32 CAM → UNO Q → Tailscale/LTE → Jetson (YOLO + LLM + OCR) → UNO Q → Speaker + Screen

Usage:
  python3 -m tank.blind_assist.main --mode full     # All features
  python3 -m tank.blind_assist.main --mode vision-only  # Camera + AI only

APC-2026-RJ-75818 · Arduino Physical AI Challenge 2026 · Dr. Shashi Gupta
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("tank.blind_assist")

# ── Optional heavy imports (installed by setup_blind_assist.sh) ─────────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    np = None   # type: ignore
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class SceneResult:
    """Structured result from one frame analysis."""
    frame_id: int
    timestamp: float
    objects: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    obstacles: List[str] = field(default_factory=list)
    text_found: List[str] = field(default_factory=list)
    guidance: str = ""
    audio_text: str = ""
    raw_ai_response: str = ""
    latency_ms: float = 0.0
    source: str = "local"  # "local", "jetson", "cloud"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.frame_id,
            "objects": self.objects,
            "people": self.people,
            "obstacles": self.obstacles,
            "text": self.text_found,
            "guidance": self.guidance,
            "audio": self.audio_text,
            "latency_ms": self.latency_ms,
            "source": self.source,
        }

    def speakable(self) -> str:
        """Return a short, spoken-friendly summary."""
        parts = []
        if self.obstacles:
            parts.append("Obstacles: " + ", ".join(self.obstacles))
        if self.people:
            parts.append("People: " + ", ".join(self.people))
        if self.text_found:
            parts.append("Text: " + ", ".join(self.text_found))
        if self.guidance:
            parts.append(self.guidance)
        return ". ".join(parts) if parts else "Scene clear."


@dataclass
class EmergencyContact:
    name: str
    phone: str


# ── Voice Command Processor ─────────────────────────────────────────────────

class VoiceCommander:
    """Transcribes voice commands from USB microphone and dispatches actions."""

    COMMANDS = {
        "what's around me": "describe",
        "what is around me": "describe",
        "describe scene": "describe",
        "read that sign": "read_text",
        "read this": "read_text",
        "read the sign": "read_text",
        "who's that": "identify_person",
        "who is that": "identify_person",
        "find my keys": "find_object:keys",
        "find my phone": "find_object:phone",
        "find my wallet": "find_object:wallet",
        "take me to the door": "navigate:door",
        "take me to the stairs": "navigate:stairs",
        "call emergency": "emergency",
        "help": "emergency",
        "follow me": "locomotion:follow",
        "stop": "locomotion:stop",
        "battery status": "status:battery",
        "what time is it": "status:time",
        "system status": "status:system",
    }

    def __init__(self):
        self._whisper_loaded = False
        self._model = None
        self._command_callbacks: Dict[str, Callable] = {}

    def load_whisper(self):
        """Lazy-load Whisper for voice transcription."""
        if self._whisper_loaded:
            return
        try:
            import whisper
            self._model = whisper.load_model("base")
            self._whisper_loaded = True
            logger.info("Whisper base model loaded")
        except ImportError:
            logger.warning("Whisper not installed — voice commands disabled")
        except Exception as e:
            logger.error(f"Whisper load failed: {e}")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text using Whisper."""
        if not self._whisper_loaded:
            self.load_whisper()
        if self._model is None:
            return ""
        try:
            result = self._model.transcribe(audio_path, language="en")
            return result["text"].strip().lower()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def match_command(self, transcript: str) -> Optional[str]:
        """Match transcribed text to a known command."""
        t = transcript.lower().strip()
        for phrase, command in self.COMMANDS.items():
            if phrase in t:
                return command
        return None

    def register_callback(self, command: str, callback: Callable):
        """Register a callback for a specific command."""
        self._command_callbacks[command] = callback

    def dispatch(self, command: str):
        """Execute a matched command."""
        if command in self._command_callbacks:
            self._command_callbacks[command]()
        else:
            action = command.split(":")[0]
            if action in self._command_callbacks:
                self._command_callbacks[action](command)


# ── ESP32 Dual Screen Controller ────────────────────────────────────────────

class DualScreen:
    """Controls the ESP32 Dual Screen (2× GC9A01 Round LCDs + Speaker)."""

    EYE_EXPRESSIONS = {
        "neutral":   {"eyes": "neutral",   "color": "#4488ff"},
        "alert":     {"eyes": "alert",     "color": "#ff4444"},
        "happy":     {"eyes": "happy",     "color": "#44ff44"},
        "thinking":  {"eyes": "thinking",  "color": "#ffaa44"},
        "warning":   {"eyes": "warning",   "color": "#ff8800"},
        "emergency": {"eyes": "emergency", "color": "#ff0000"},
        "sleep":     {"eyes": "sleep",     "color": "#222244"},
    }

    def __init__(self, serial_port: str = "/dev/ttyUSB1"):
        self.serial_port = serial_port
        self._connected = False
        self._serial = None
        self._current_expression = "neutral"
        self._current_text = ""

    def connect(self) -> bool:
        """Open serial connection to ESP32 Dual Screen."""
        try:
            import serial
            self._serial = serial.Serial(self.serial_port, 115200, timeout=1)
            self._connected = True
            logger.info(f"Dual Screen connected on {self.serial_port}")
            return True
        except ImportError:
            logger.warning("pyserial not installed — screen output disabled")
            return False
        except Exception as e:
            logger.warning(f"Dual Screen not reachable: {e}")
            return False

    def set_expression(self, expression: str):
        """Set the eye expression (neutral, alert, happy, thinking, warning, emergency)."""
        if not self._connected or self._serial is None:
            return
        cfg = self.EYE_EXPRESSIONS.get(expression, self.EYE_EXPRESSIONS["neutral"])
        self._current_expression = expression
        self._send_json(cfg)

    def show_text(self, text: str, color: str = "#ffffff"):
        """Display scrolling text on both screens."""
        if not self._connected or self._serial is None:
            return
        self._current_text = text
        self._send_json({"text": text, "color": color})

    def speak(self, text: str):
        """Send text-to-speech command to ESP32 speaker."""
        if not self._connected or self._serial is None:
            return
        self._send_json({"speak": text})

    def alert_obstacle(self, direction: str, distance_m: float):
        """Show obstacle alert with direction and distance."""
        self.set_expression("warning")
        msg = f"{direction} obstacle, {distance_m:.1f} meters"
        self.show_text(msg, "#ff8800")
        self.speak(msg)
        # Auto-reset to neutral after 2 seconds
        threading.Timer(2.0, lambda: self.set_expression("neutral")).start()

    def emergency_alarm(self):
        """Activate emergency mode: red flash + loud alarm."""
        self.set_expression("emergency")
        self.show_text("EMERGENCY", "#ff0000")
        self.speak("Emergency activated. Help is on the way.")
        # Flash for 10 seconds
        def flash():
            for _ in range(20):
                self._send_json({"led": "on"})
                time.sleep(0.25)
                self._send_json({"led": "off"})
                time.sleep(0.25)
            self.set_expression("neutral")
        threading.Thread(target=flash, daemon=True).start()

    def _send_json(self, data: dict):
        """Send JSON command over serial."""
        if self._serial is None:
            return
        try:
            msg = json.dumps(data) + "\n"
            self._serial.write(msg.encode())
        except Exception as e:
            logger.debug(f"Screen write failed: {e}")

    def disconnect(self):
        if self._serial:
            self._serial.close()
        self._connected = False


# ── Emergency SMS ───────────────────────────────────────────────────────────

class EmergencySystem:
    """Triple-tap E-STOP → SMS with GPS coordinates."""

    CONTACTS_PATH = os.path.expanduser("~/.blind_assist_contacts")

    def __init__(self):
        self._contacts: List[EmergencyContact] = []
        self._tap_count = 0
        self._last_tap = 0.0
        self._enabled = True
        self._load_contacts()

    def _load_contacts(self):
        """Parse emergency contacts file."""
        self._contacts = []
        if not os.path.exists(self.CONTACTS_PATH):
            logger.warning(f"No contacts file at {self.CONTACTS_PATH}")
            return
        with open(self.CONTACTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("#")[0].strip().split(maxsplit=1)
                phone = parts[0].replace("-", "").replace(" ", "")
                name = parts[1] if len(parts) > 1 else "Contact"
                self._contacts.append(EmergencyContact(name=name, phone=phone))
        logger.info(f"Loaded {len(self._contacts)} emergency contacts")

    def tap(self) -> bool:
        """Register an E-STOP tap. Returns True if triple-tap trigger fires."""
        now = time.time()
        if now - self._last_tap > 2.0:
            self._tap_count = 0
        self._tap_count += 1
        self._last_tap = now

        if self._tap_count >= 3:
            self._tap_count = 0
            self._trigger()
            return True
        return False

    def _trigger(self):
        """Send emergency SMS to all contacts."""
        logger.warning("🚨 EMERGENCY TRIGGERED — Sending SMS alerts")
        gps = self._get_location()
        message = f"🚨 EMERGENCY: Blind user needs help. GPS: {gps}"

        for contact in self._contacts:
            self._send_sms(contact.phone, message)

        # Also send via LTE modem if available
        self._send_modem_sms(message)

    def _send_sms(self, phone: str, message: str):
        """Attempt to send SMS via multiple methods."""
        # Method 1: mmcli
        try:
            modem_id = subprocess.check_output(
                "mmcli -L | head -1 | grep -oP '/Modem/\\K[0-9]+'",
                shell=True, text=True, timeout=5
            ).strip()
            if modem_id:
                subprocess.run([
                    "mmcli", "-m", modem_id,
                    "--messaging-create-sms",
                    f"number={phone}",
                    f"text={message}"
                ], timeout=10, capture_output=True)
                logger.info(f"SMS sent to {phone} via LTE modem")
                return
        except Exception as e:
            logger.debug(f"mmcli SMS failed: {e}")

        # Method 2: Python SMS library (future)
        logger.warning(f"Could not send SMS to {phone}")

    def _send_modem_sms(self, message: str):
        """Send SMS via AT commands to Quectel modem."""
        try:
            ports = ["/dev/ttyUSB2", "/dev/ttyUSB3"]
            for port in ports:
                if os.path.exists(port):
                    with open(port, "w") as f:
                        f.write("AT+CMGF=1\r\n")
                        f.write(f'AT+CMGS="{self._contacts[0].phone}"\r\n')
                        f.write(f"{message}\x1A\r\n")
                    logger.info(f"Emergency SMS sent via {port}")
                    return
        except Exception as e:
            logger.error(f"Modem SMS failed: {e}")

    def _get_location(self) -> str:
        """Try to get GPS coordinates from LTE modem or fallback."""
        try:
            # Try mmcli GPS
            output = subprocess.check_output(
                "mmcli -m 0 --location-get 2>/dev/null | grep -E 'gps|utc'",
                shell=True, text=True, timeout=5
            ).strip()
            if output:
                return output
        except Exception:
            pass
        return "GPS unavailable (check LTE modem)"


# ── AI Inference Client ─────────────────────────────────────────────────────

class AIInferenceClient:
    """Routes frames to Jetson (primary) or cloud (fallback) for AI analysis."""

    BLIND_ASSIST_PROMPT = (
        "You are assisting a blind person. Describe what you see in this image. "
        "Focus on: obstacles (stairs, poles, vehicles), people (known/unknown), "
        "text (signs, door numbers), and actionable guidance for safe navigation. "
        "Keep it concise — the output will be spoken aloud. "
        "Format: [OBSTACLES] ... [PEOPLE] ... [TEXT] ... [GUIDANCE] ... "
        "If nothing dangerous, say 'Path is clear.'"
    )

    def __init__(
        self,
        jetson_api: str = "http://100.122.31.46:8085",
        vps_api: str = "http://100.71.127.19:8888",
    ):
        self.jetson_api = jetson_api
        self.vps_api = vps_api
        self._local_model: Optional[Any] = None
        self._use_local = False

    def load_local_model(self):
        """Try to load a local Phi-3/TinyLlama for offline inference."""
        try:
            # Fallback: use YOLO + rule-based description (no LLM needed)
            self._use_local = True
            logger.info("Local inference mode active (YOLO + rules)")
        except Exception:
            logger.info("No local model available — using Jetson/cloud")

    def analyze_frame(self, jpeg_bytes: bytes) -> Tuple[str, str]:
        """Send frame to AI and return (raw_response, speakable_summary)."""
        t0 = time.time()

        # Try Jetson first
        try:
            result = self._send_to_jetson(jpeg_bytes)
            if result:
                return result, self._summarize(result)
        except Exception as e:
            logger.debug(f"Jetson inference failed: {e}")

        # Fallback to VPS cloud
        try:
            result = self._send_to_vps(jpeg_bytes)
            if result:
                return result, self._summarize(result)
        except Exception as e:
            logger.debug(f"VPS inference failed: {e}")

        # Last resort: local YOLO-only analysis
        if self._use_local:
            result = self._local_analysis(jpeg_bytes)
            return result, result

        return "AI analysis unavailable.", "Analysis unavailable."

    def _send_to_jetson(self, jpeg_bytes: bytes) -> Optional[str]:
        """POST image to Jetson for AI analysis."""
        url = f"{self.jetson_api}/api/vision/analyze"
        req = urllib.request.Request(
            url, data=jpeg_bytes,
            headers={
                "Content-Type": "image/jpeg",
                "X-Prompt": self.BLIND_ASSIST_PROMPT,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("analysis", data.get("response", ""))

    def _send_to_vps(self, jpeg_bytes: bytes) -> Optional[str]:
        """POST image to VPS cloud AI (fallback)."""
        import base64
        b64 = base64.b64encode(jpeg_bytes).decode()
        payload = json.dumps({
            "image": b64,
            "prompt": self.BLIND_ASSIST_PROMPT,
            "source": "blind_assist_wearable",
        }).encode()
        req = urllib.request.Request(
            f"{self.vps_api}/api/vision/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("analysis", data.get("response", ""))

    def _local_analysis(self, jpeg_bytes: bytes) -> str:
        """Local YOLO-only analysis (no LLM needed)."""
        if not CV2_AVAILABLE or not YOLO_AVAILABLE:
            return "Local analysis offline."

        buf = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            return "Could not process image."

        model = YOLO("yolov8n.pt")
        results = model(frame, verbose=False)

        objects = []
        for r in results:
            for box in r.boxes:
                name = r.names[int(box.cls[0])]
                conf = float(box.conf[0])
                if conf > 0.5:
                    objects.append(f"{name} ({conf:.0%})")

        if not objects:
            return "No objects detected. Path appears clear."
        return "Detected: " + ", ".join(objects)

    def _summarize(self, raw: str) -> str:
        """Extract a short speakable summary from AI response."""
        # Take first 200 chars, stop at a sentence boundary
        short = raw[:200]
        for end in [". ", "! ", "? ", "\n"]:
            if end in short:
                short = short[:short.rindex(end) + 1]
                break
        return short


# ── Main BlindAssist Class ──────────────────────────────────────────────────

class BlindAssist:
    """Main coordinator for the blind-assistance wearable module.

    Orchestrates: camera → AI analysis → screen/speaker feedback → emergency.
    """

    def __init__(
        self,
        esp32cam_host: str = "192.168.31.145",
        mode: str = "vision-only",
        jetson_api: str = "http://100.122.31.46:8085",
        vps_api: str = "http://100.71.127.19:8888",
        interval_s: float = 2.0,
    ):
        self.esp32cam_host = esp32cam_host
        self.mode = mode
        self.interval_s = interval_s
        self._running = False
        self._frame_count = 0
        self._results: List[SceneResult] = []

        # Subsystems
        self.screen = DualScreen()
        self.voice = VoiceCommander()
        self.emergency = EmergencySystem()
        self.ai = AIInferenceClient(jetson_api=jetson_api, vps_api=vps_api)

        # Callbacks
        self.on_result: Optional[Callable[[SceneResult], None]] = None

    def start(self):
        """Start the blind-assistance system."""
        logger.info(f"🦯 Starting BlindAssist in {self.mode} mode")
        logger.info(f"   Camera: {self.esp32cam_host}")
        logger.info(f"   Jetson: {self.ai.jetson_api}")

        # Connect peripherals
        self.screen.connect()
        self.ai.load_local_model()

        self._running = True

        # Main loop
        try:
            while self._running:
                self._loop()
                time.sleep(self.interval_s)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the system gracefully."""
        logger.info("Stopping BlindAssist...")
        self._running = False
        self.screen.set_expression("sleep")
        self.screen.disconnect()

    def process_one_frame(self) -> SceneResult:
        """Process a single frame: capture → analyze → return result."""
        t0 = time.time()

        # 1. Capture frame from ESP32-S3 CAM
        jpeg_bytes = self._capture_frame()
        if not jpeg_bytes:
            return SceneResult(
                frame_id=self._frame_count,
                timestamp=t0,
                guidance="Camera not available. Check ESP32 connection.",
                audio_text="Camera not available.",
                latency_ms=(time.time() - t0) * 1000,
            )

        # 2. AI analysis
        raw_response, summary = self.ai.analyze_frame(jpeg_bytes)

        # 3. Build result
        result = SceneResult(
            frame_id=self._frame_count,
            timestamp=t0,
            raw_ai_response=raw_response,
            guidance=summary,
            audio_text=summary,
            latency_ms=(time.time() - t0) * 1000,
            source="jetson" if raw_response else "local",
        )

        self._results.append(result)
        if len(self._results) > 100:
            self._results = self._results[-50:]

        return result

    def _loop(self):
        """Main processing loop."""
        result = self.process_one_frame()

        # Update screen and speaker
        if result.obstacles:
            nearest = result.obstacles[0] if result.obstacles else ""
            self.screen.alert_obstacle(nearest, 2.0)
        else:
            self.screen.set_expression("neutral")

        if result.guidance:
            self.screen.show_text(result.guidance[:50])
            self.screen.speak(result.audio_text)

        if self.on_result:
            self.on_result(result)

    def _capture_frame(self) -> Optional[bytes]:
        """Capture JPEG frame from ESP32-S3 CAM."""
        url = f"http://{self.esp32cam_host}/capture"
        try:
            req = urllib.request.urlopen(url, timeout=5)
            data = req.read()
            if len(data) > 100:
                self._frame_count += 1
                return data
        except Exception as e:
            logger.debug(f"Frame capture failed: {e}")
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "running": self._running,
            "frames": self._frame_count,
            "camera": self.esp32cam_host,
            "results_count": len(self._results),
            "last_latency_ms": self._results[-1].latency_ms if self._results else 0,
        }


# ── CLI Entry Point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🦯 Tank Blind-Assistance Module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m tank.blind_assist.main --mode full
  python3 -m tank.blind_assist.main --mode vision-only --camera 192.168.1.100
  python3 -m tank.blind_assist.main --mode emergency
        """,
    )
    parser.add_argument("--mode", choices=["full", "vision-only", "nav-only", "read-only", "emergency"],
                        default="vision-only", help="Operating mode")
    parser.add_argument("--camera", default="192.168.31.145", help="ESP32-S3 CAM IP address")
    parser.add_argument("--jetson", default="http://100.122.31.46:8085", help="Jetson API URL")
    parser.add_argument("--vps", default="http://100.71.127.19:8888", help="VPS fallback API URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Frame interval in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )

    assist = BlindAssist(
        esp32cam_host=args.camera,
        mode=args.mode,
        jetson_api=args.jetson,
        vps_api=args.vps,
        interval_s=args.interval,
    )

    print("🦯 Tank Blind-Assistance Module")
    print(f"   Mode: {args.mode}")
    print(f"   Camera: {args.camera}")
    print("   Press Ctrl+C to stop")
    print()

    assist.start()


if __name__ == "__main__":
    main()