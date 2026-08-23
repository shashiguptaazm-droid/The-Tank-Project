#!/usr/bin/env python3
"""TankOS Agent Chat — complete AI coding assistant.

All 1,166 tools auto-selectable. Real camera via DFRobot USB serial + YOLO.
9 cloud providers rotating. Phi-3 local fallback. Never shows rate limit.

Usage:
    python3 -m tank_os.shell.terminal.agent_chat
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank_os.agent_chat")

# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TANK_WS_SRC = _PROJECT_ROOT / "tank_ws" / "src"
if str(_TANK_WS_SRC) not in sys.path:
    sys.path.insert(0, str(_TANK_WS_SRC))

_env_file = _PROJECT_ROOT / ".env.keys"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k not in os.environ:
                os.environ[k] = v

# ═══════════════════════════════════════════════════════════════════════════
#  Camera — DFRobot USB serial capture + REAL YOLO detection
# ═══════════════════════════════════════════════════════════════════════════

def _capture_frame() -> Optional[str]:
    """Capture JPEG from DFRobot camera via USB serial /dev/ttyACM0."""
    try:
        import serial as _serial
    except ImportError:
        return None

    port = "/dev/ttyACM0"
    if not Path(port).exists():
        return None

    try:
        s = _serial.Serial(port, 921600, timeout=5)
        time.sleep(0.5)
        # Double-drain buffer
        s.read(s.in_waiting)
        time.sleep(0.1)
        s.read(s.in_waiting)
        s.write(b"SNAP\n")
        header = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            c = s.read(1)
            if c:
                header += c
                if c == b"\n":
                    break
        h = header.decode("utf-8", errors="replace").strip()
        if not h.startswith("FRAME:"):
            s.close()
            return None
        parts = h.split(":")
        expected = int(parts[3])
        jpeg = b""
        dl = time.time() + 10
        while len(jpeg) < expected and time.time() < dl:
            chunk = s.read(min(expected - len(jpeg), 16384))
            if chunk:
                jpeg += chunk
                dl = time.time() + 2
        s.read(1)
        s.close()
        if len(jpeg) < 500:
            return None
        out = _PROJECT_ROOT / "data" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        path = out / "latest.jpg"
        path.write_bytes(jpeg)
        return str(path)
    except Exception as e:
        logger.debug("Camera capture failed: %s", e)
        return None


def _run_yolo(image_path: str) -> str:
    """Run YOLOv8 on a real captured image, return detection summary."""
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        results = model(image_path, verbose=False)
        objects = []
        for r in results:
            for box in r.boxes:
                name = r.names[int(box.cls[0])]
                conf = float(box.conf[0])
                cx = int((float(box.xyxy[0][0]) + float(box.xyxy[0][2])) / 2)
                cy = int((float(box.xyxy[0][1]) + float(box.xyxy[0][3])) / 2)
                objects.append(f"{name}({conf:.0%}) at ({cx},{cy})")
        if objects:
            return f"Real YOLO detections from camera: {', '.join(objects)}"
        return "No objects detected in camera frame"
    except ImportError:
        return "ultralytics not installed — run: pip install ultralytics"
    except Exception as e:
        return f"YOLO error: {e}"


def _camera_vision() -> str:
    """Capture frame + run REAL YOLO + face recognition. Returns description for LLM."""
    frame = _capture_frame()
    if frame is None:
        return "Camera not available — /dev/ttyACM0 not responding to SNAP"
    detections = _run_yolo(frame)

    # Face recognition on detected persons
    face_info = ""
    try:
        from tank_os.shell.terminal.face_db import FaceDB
        db = FaceDB()
        faces = db.recognize_in_frame(frame)
        if faces:
            parts = []
            unknown_count = 0
            for f in faces:
                if f["is_known"]:
                    parts.append(f'{f["name"]}({f["confidence"]:.0%}) at ({f["x"]},{f["y"]})')
                else:
                    unknown_count += 1
            if parts:
                face_info = f". Known faces: {', '.join(parts)}"
            if unknown_count > 0:
                face_info += f". {unknown_count} unknown person(s) detected"
    except Exception:
        pass

    return f"Captured {frame}. {detections}{face_info}"


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-provider LLM — all keys rotating, never fails silently
# ═══════════════════════════════════════════════════════════════════════════

_PROVIDER_DEFS = [
    ("groq_a",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "openai/gpt-oss-120b"),
    ("groq_b",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "openai/gpt-oss-20b"),
    ("groq_c",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "allam-2-7b"),
    ("openrouter","https://openrouter.ai/api/v1",     "OPENROUTER_API_KEY",    "openai/gpt-4o-mini"),
    ("mistral",   "https://api.mistral.ai/v1",        "MISTRAL_API_KEY",       "mistral-small-latest"),
    ("gemini",    "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "gemini-2.0-flash"),
    ("cohere",    "https://api.cohere.ai/v1",          "COHERE_API_KEY",        "command-r-plus"),
]

_local_llm = None


def _call_openai_shaped(base_url: str, api_key: str, model: str, messages: list) -> str:
    import httpx
    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": 1024, "temperature": 0.15},
        timeout=25.0,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate_limited")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(api_key: str, model: str, messages: list) -> str:
    import httpx
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    user = " ".join(m["content"] for m in messages if m["role"] == "user")
    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.15},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json=body, timeout=25.0,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate_limited")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_cohere(api_key: str, model: str, messages: list) -> str:
    import httpx
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    user = " ".join(m["content"] for m in messages if m["role"] == "user")
    body: Dict[str, Any] = {"model": model, "message": user, "max_tokens": 512}
    if system:
        body["preamble"] = system
        body["max_tokens"] = 1024
    resp = httpx.post(
        "https://api.cohere.ai/v1/chat",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body, timeout=25.0,
    )
    if resp.status_code == 429:
        raise RuntimeError("rate_limited")
    resp.raise_for_status()
    return resp.json()["text"].strip()


def _call_provider(name: str, messages: list) -> str:
    for pname, base, key_env, model in _PROVIDER_DEFS:
        if pname != name:
            continue
        api_key = os.environ.get(key_env, "")
        if not api_key or not model:
            raise RuntimeError(f"no_key:{name}")
        if "gemini" in pname:
            return _call_gemini(api_key, model, messages)
        if "cohere" in pname:
            return _call_cohere(api_key, model, messages)
        return _call_openai_shaped(base, api_key, model, messages)
    raise RuntimeError(f"unknown:{name}")


def _call_local_phi3(messages: list) -> str:
    global _local_llm
    try:
        import llama_cpp
    except ImportError:
        raise RuntimeError("llama-cpp-python not installed")
    model_path = _PROJECT_ROOT / "models/llm" / "phi-3-mini-4k-instruct-q4.gguf"
    if not model_path.exists():
        raise RuntimeError("Phi-3 not found")
    if _local_llm is None:
        print("\033[90m  Loading Phi-3 (~60s)...\033[0m", end="", flush=True)
        _local_llm = llama_cpp.Llama(model_path=str(model_path), n_ctx=4096, n_threads=4, verbose=False)
        print(" ready\033[0m")
    prompt = ""
    for m in messages:
        if m["role"] == "system":
            prompt += f"<|system|>\n{m['content']}\n"
        elif m["role"] == "user":
            prompt += f"<|user|>\n{m['content']}\n"
    prompt += "<|assistant|>\n"
    resp = _local_llm(prompt, max_tokens=1024, temperature=0.15, stop=["<|user|>", "<|system|>"])
    return resp["choices"][0]["text"].strip()


def _rotate_chat(messages: list) -> str:
    """Try all providers. Local Phi-3 final fallback. Never raise."""
    order = [p[0] for p in _PROVIDER_DEFS]
    last_err = None
    for name in order:
        try:
            return _call_provider(name, messages)
        except Exception as e:
            last_err = e
            logger.debug("Provider %s failed: %s", name, e)
            time.sleep(0.3)
    try:
        return _call_local_phi3(messages)
    except Exception as e:
        return f"All providers failed. Last error: {last_err}"


# ═══════════════════════════════════════════════════════════════════════════
#  Tool catalog
# ═══════════════════════════════════════════════════════════════════════════

def _load_tool_catalog(max_tools: int = 120) -> str:
    try:
        from tank_os.agent_framework.registry import ToolRegistry
        reg = ToolRegistry(scripts_dir=_PROJECT_ROOT / "scripts")
        reg.discover()
        tools = reg.list()
    except Exception:
        return "(no tools)"
    cats: Dict[str, list] = {}
    for t in tools[:400]:
        cats.setdefault(t.category, []).append(t)
    lines = []
    for cat, cat_tools in sorted(cats.items()):
        lines.append(f"\n[{cat}]")
        for t in cat_tools[:6]:
            desc = (t.description or "").strip()[:55]
            lines.append(f"  {t.name} — {desc}")
    lines.append(f"\n({len(tools)} tools total)")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Tool / shell execution
# ═══════════════════════════════════════════════════════════════════════════

def _invoke_tool(tool_name: str, args: Dict[str, Any]) -> str:
    try:
        from tank_os.agent_framework.registry import ToolRegistry
        from tank_os.agent_framework.invoker import ToolInvoker
        from tank_os.agent_framework.schemas import ToolCallRequest
        reg = ToolRegistry(scripts_dir=_PROJECT_ROOT / "scripts")
        reg.discover()
        tool_def = reg.get(tool_name)
        if tool_def is None:
            # Tool not registered — try to find a script that matches
            scripts_dir = _PROJECT_ROOT / "scripts"
            for cat_dir in scripts_dir.iterdir():
                if cat_dir.is_dir():
                    for script in cat_dir.glob("*.py"):
                        if tool_name.replace(".", "_") in script.name or tool_name.split(".")[-1] in script.name:
                            result = _run_shell(f"python3 {script} {' '.join(f'--{k} {v}' for k, v in args.items()) if args else ''}")
                            return result
            return f"Tool '{tool_name}' not found. Try using shell: {{\"action\":\"shell\",\"cmd\":\"<command>\"}}"
        invoker = ToolInvoker(reg)
        req = ToolCallRequest(tool_name=tool_name, args=args, timeout_s=30)
        resp = invoker.invoke(req)
        parts = []
        if resp.stdout:
            parts.append(resp.stdout.strip())
        if resp.stderr:
            parts.append(f"[stderr] {resp.stderr.strip()}")
        return "\n".join(parts) if parts else f"(status={resp.status}, exit={resp.exit_code})"
    except Exception as e:
        return f"Tool error: {e} — try shell instead"


def _run_shell(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        parts = []
        if r.stdout:
            parts.append(r.stdout.strip())
        if r.stderr:
            parts.append(f"[stderr] {r.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: {cmd}"
    except Exception as e:
        return f"ERROR: {e}"


# ═══════════════════════════════════════════════════════════════════════════
#  System prompt
# ═══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """You are TankOS Agent — an autonomous AI with FULL system access on a Jetson Orin Nano robot.
You can install packages, run commands, use tools, capture camera, read LiDAR, send SMS, make calls — anything.

CRITICAL RULES:
1. ALWAYS respond with EXACTLY ONE JSON object. Nothing else. No markdown. No explanation.
2. When you receive [camera results], [tool result], [shell result], or [modem result] in the conversation, you MUST describe those results with {"action":"reply","text":"..."}. NEVER request the same action again after receiving results.
3. You have full sudo access. Password is 1234. If pip/apt fails, use: echo '1234' | sudo -S <command>
4. NEVER say 'I cannot' or 'I am unable'. You have full access. Just do it.

ACTIONS (respond with exactly ONE):

To run ANY shell command:
{"action":"shell","cmd":"<bash command>"}

To use a registered tool:
{"action":"tool","tool":"<tool.name>","args":{}}

To capture from the DFRobot USB camera + YOLO detection:
{"action":"camera"}

To answer/describe results:
{"action":"reply","text":"<your answer>"}

MODEM ACTIONS (use {"action":"modem","function":"<fn>","args":{}}):
- Send SMS: {"action":"modem","function":"send_sms","args":{"message":"Hi!","to":"shashi"}}
- Read SMS: {"action":"modem","function":"get_sms_messages","args":{}}
- List contacts: {"action":"modem","function":"list_contacts","args":{}}
- Add contact: {"action":"modem","function":"add_contact","args":{"name":"mom","phone":"+919876543210"}}
- Make call: {"action":"modem","function":"call_number","args":{"number_or_name":"shashi"}}
- Hangup: {"action":"modem","function":"hangup_call","args":{}}
- Modem status: {"action":"modem","function":"get_modem_status","args":{}}

Saved contacts: Shashi (+917860245819), Owner (+917860245819)
To save a new contact: use add_contact above.

TORRENT/DOWNLOAD (use {"action":"shell","cmd":"python3 /home/shashi/The-Tank-Project/tank_os/shell/terminal/torrent_tool.py <command> <args>"}):
- Search: search "query" — find torrents
- Download: download <url_or_magnet> — start download on VPS
- List: list active|waiting|stopped|all — show downloads
- Status: status — global aria2 stats
- Pause/Resume/Delete: pause/resume/delete <gid>
Torrent downloads go to VPS aria2 (100.71.127.19:6800)
Web UI: http://100.71.127.19:8082/

EXAMPLES:
- Send SMS: use modem tool above with send_sms('Hi mom!', to='mom')
- Install packages: {"action":"shell","cmd":"pip install mediapipe"}
- With sudo: {"action":"shell","cmd":"echo '1234' | sudo -S apt install -y mediapipe"}
- Run python: {"action":"shell","cmd":"python3 -c 'print(1+1)'"}
- Check devices: {"action":"shell","cmd":"ls /dev/ttyACM* /dev/ttyUSB*"}
- Camera see: {"action":"camera"}
- System info: {"action":"shell","cmd":"uname -a && free -h && df -h"}
- Search torrents: {"action":"shell","cmd":"python3 /home/shashi/The-Tank-Project/tank_os/shell/terminal/torrent_tool.py search 'ubuntu 24.04'"}
- Download torrent: {"action":"shell","cmd":"python3 /home/shashi/The-Tank-Project/tank_os/shell/terminal/torrent_tool.py download 'magnet:?xt=...'"}
- List downloads: {"action":"shell","cmd":"python3 /home/shashi/The-Tank-Project/tank_os/shell/terminal/torrent_tool.py list all"}
- After seeing results: {"action":"reply","text":"The system shows..."}
"""


# ═══════════════════════════════════════════════════════════════════════════
#  Agent REPL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Turn:
    role: str
    content: str


class AgentChat:
    MAX_ROUNDS = 5

    def __init__(self):
        self._catalog = _load_tool_catalog()
        self._system = _SYSTEM_PROMPT + "\n\nAVAILABLE TOOLS:\n" + self._catalog
        self._history: List[Turn] = []

    def run(self):
        self._banner()
        while True:
            try:
                user = input("\033[1;36mtank\033[0m> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\033[90mBye\033[0m")
                break
            if not user:
                continue
            if user.lower() in ("exit", "quit", "q"):
                break
            if user.lower() == "clear":
                self._history.clear()
                continue
            self._handle(user)

    def _handle(self, user_input: str):
        self._history.append(Turn("user", user_input))
        camera_used = False  # track camera captures per turn

        for round_num in range(self.MAX_ROUNDS):
            resp = self._llm()
            if not resp:
                print("\033[33m  LLM unavailable — retrying...\033[0m")
                resp = self._llm()
                if not resp:
                    print("\033[31m  All providers down\033[0m")
                    return
            if resp.startswith("All providers"):
                print(f"\033[31m  {resp}\033[0m")
                return

            action = self._parse(resp)

            if action is None:
                # Plain text reply — but check if it contains hidden JSON
                clean = resp.strip()
                # Try harder to extract JSON from text
                if '{"action"' in clean:
                    s = clean.find('{"action"')
                    e = clean.find('}', s) + 1
                    try:
                        action = json.loads(clean[s:e])
                    except:
                        pass
                if action is None and clean:
                    clean = self._strip_json_text(clean)
                    print(f"\n\033[1;32m🤖\033[0m {clean}")
                    self._history.append(Turn("assistant", clean))
                    return

            if action is None:
                return

            at = action.get("action", "")

            if at == "reply":
                text = action.get("text", "")
                print(f"\n\033[1;32m🤖\033[0m {text}")
                self._history.append(Turn("assistant", text))
                # Trim history: keep only last 4 turns (user + assistant) to prevent repetition
                if len(self._history) > 8:
                    self._history = self._history[-4:]
                return

            elif at == "camera" and not camera_used:
                camera_used = True
                print("\033[90m  Capturing from DFRobot camera + YOLO...\033[0m", end="", flush=True)
                result = _camera_vision()
                print(" done")
                self._history.append(Turn("tool", f"[camera] {result}"))

                # Check for unknown faces — prompt enrollment
                if "unknown person" in result.lower():
                    try:
                        from tank_os.shell.terminal.face_db import FaceDB
                        db = FaceDB()
                        frame = _PROJECT_ROOT / "data" / "frames" / "latest.jpg"
                        if frame.exists():
                            faces = db.recognize_in_frame(str(frame))
                            unknowns = [f for f in faces if not f["is_known"]]
                            if unknowns:
                                print(f"\n\033[1;33m  I see {len(unknowns)} unknown person(s).\033[0m")
                                name = input("\033[1;33m  What is their name? (or press Enter to skip): \033[0m").strip()
                                if name:
                                    db.enroll(str(frame), name)
                                    print(f"\033[32m  Saved {name} to face database\033[0m")
                                    self._history.append(Turn("tool", f"[face] Enrolled new face: {name}"))
                    except Exception as e:
                        logger.debug("Face enrollment error: %s", e)

                # Continue loop — LLM will describe what it sees

            elif at == "camera" and camera_used:
                # Already captured — force LLM to describe instead of capturing again
                # Find the previous camera result in history
                last_camera = ""
                for t in reversed(self._history):
                    if t.role == "tool" and "[camera]" in t.content:
                        last_camera = t.content
                        break
                self._history.append(Turn("user", f"STOP. Camera already captured. DO NOT capture again. Here are the results: {last_camera}\nDescribe what you see. Reply with {{\"action\":\"reply\",\"text\":\"...\"}} format."))
                continue

            elif at == "tool":
                tn = action.get("tool", "")
                args = action.get("args", {})
                print(f"\033[90m  {tn}({json.dumps(args, ensure_ascii=False)})\033[0m", end="", flush=True)
                result = _invoke_tool(tn, args)
                print(f" -> {len(result)} chars")
                self._history.append(Turn("tool", f"[tool:{tn}] {result[:500]}"))

            elif at == "shell":
                cmd = action.get("cmd", "")
                print(f"\033[90m  $ {cmd}\033[0m", end="", flush=True)
                result = _run_shell(cmd)
                print(f" -> {len(result)} chars")
                self._history.append(Turn("tool", f"[shell] {result[:500]}"))

            elif at == "modem":
                # Direct modem action: send_sms, call, contacts, etc.
                fn = action.get("function", "")
                args = action.get("args", {})
                print(f"\033[90m  modem.{fn}({json.dumps(args, ensure_ascii=False)})\033[0m", end="", flush=True)
                try:
                    import importlib
                    modem_mod = importlib.import_module("tank_os.shell.terminal.modem_tools")
                    fn_obj = getattr(modem_mod, fn, None)
                    if fn_obj is None:
                        result = f"Unknown modem function: {fn}. Available: send_sms, get_sms_messages, list_contacts, add_contact, call_number, hangup_call, get_modem_status"
                    else:
                        result = fn_obj(**args)
                except Exception as e:
                    result = f"Modem error: {e}"
                print(f" -> {len(result)} chars")
                self._history.append(Turn("tool", f"[modem] {result[:500]}"))

            else:
                # Unknown action — strip any JSON and show clean text
                clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
                clean = self._strip_json_text(clean)
                print(f"\n\033[1;32m🤖\033[0m {clean}")
                self._history.append(Turn("assistant", clean))
                return

        # Max rounds — force a text reply
        self._history.append(Turn("user", "Stop using tools. Give your final answer as plain text describing what was found. Use {\"action\":\"reply\",\"text\":\"...\"} format."))
        final = self._llm()
        if final:
            clean = self._strip_json_text(final)
            print(f"\n\033[1;32m🤖\033[0m {clean}")
        # Trim history after max rounds
        if len(self._history) > 8:
            self._history = self._history[-4:]

    def _llm(self) -> Optional[str]:
        msgs = [{"role": "system", "content": self._system}]
        # Only keep last 6 turns to avoid context overflow
        recent = self._history[-6:]
        parts = []
        for t in recent:
            if t.role == "user":
                parts.append(f"User: {t.content}")
            elif t.role == "tool":
                # Truncate tool results aggressively to save context
                truncated = t.content[:500]
                parts.append(truncated)
            elif t.role == "assistant":
                parts.append(f"Assistant: {t.content}")
        msgs.append({"role": "user", "content": "\n\n".join(parts)})
        try:
            return _rotate_chat(msgs)
        except Exception as e:
            return None

    @staticmethod
    def _strip_json_text(text: str) -> str:
        """Extract human-readable text from LLM response that might contain JSON."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # If it's pure JSON with a text field, extract it
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "text" in obj:
                return obj["text"]
        except:
            pass
        # Try to find reply JSON embedded in text
        for pattern in [r'\{"action"\s*:\s*"reply"\s*,\s*"text"\s*:\s*"([^"]+)"\}',
                       r'"text"\s*:\s*"([^"]+)"']:
            m = re.search(pattern, text)
            if m:
                return m.group(1).replace("\\n", "").replace("\\t", " ")
        # Remove raw JSON from the end of text
        text = re.sub(r'\s*\{"action".*$', '', text).strip()
        return text if text else "Done."

    @staticmethod
    def _parse(text: str) -> Optional[Dict]:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _banner(self):
        print()
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║      TankOS Agent Chat                         ║")
        print("  ║      Talk naturally — auto tool selection       ║")
        print(f"  ║      {len(_PROVIDER_DEFS)} cloud providers + Phi-3 local       ║")
        print("  ║      Real DFRobot USB camera + YOLO             ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()
        print('  Try: "what do you see through the camera?"')
        print('  Try: "what is the system status?"')
        print('  Try: "show me the USB devices"')
        print('  Type exit to quit.\n')


def main():
    AgentChat().run()


if __name__ == "__main__":
    main()
