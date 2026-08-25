#!/usr/bin/env python3
"""TankOS Agent Chat — Professional AI coding assistant.

All 1,166 tools auto-selectable. Real camera via DFRobot USB serial + YOLO.
10 cloud providers rotating. Phi-3 local fallback. Never shows rate limit.

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
from dataclasses import dataclass, field
from datetime import datetime
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
#  Professional UI Helpers
# ═══════════════════════════════════════════════════════════════════════════

class Colors:
    """ANSI color codes for professional terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    
    # Foreground
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    
    # Bright
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


def _print_box(title: str, content: str, color: str = Colors.CYAN, width: int = 60):
    """Print a professional box with title and content."""
    print(f"\n{color}╔{'═' * (width - 2)}╗{Colors.RESET}")
    print(f"{color}║{Colors.RESET} {Colors.BOLD}{title}{Colors.RESET}{' ' * max(0, width - len(title) - 4)}{color}║{Colors.RESET}")
    print(f"{color}╠{'═' * (width - 2)}╣{Colors.RESET}")
    for line in content.split('\n'):
        print(f"{color}║{Colors.RESET} {line}{' ' * max(0, width - len(line) - 4)}{color}║{Colors.RESET}")
    print(f"{color}╚{'═' * (width - 2)}╝{Colors.RESET}")


def _print_status(label: str, value: str, color: str = Colors.GREEN):
    """Print a status line with label and value."""
    print(f"  {Colors.GRAY}├─{Colors.RESET} {Colors.BOLD}{label}:{Colors.RESET} {color}{value}{Colors.RESET}")


def _print_thinking(provider: str, model: str):
    """Print thinking indicator."""
    print(f"\n{Colors.YELLOW}  ⚡ Thinking...{Colors.RESET} {Colors.GRAY}({provider}/{model}){Colors.RESET}", end="", flush=True)


def _print_done(provider: str, elapsed: float):
    """Print done indicator."""
    print(f"\r{Colors.GREEN}  ✓ Done{Colors.RESET} {Colors.GRAY}({provider} in {elapsed:.1f}s){Colors.RESET}")


def _print_action(action: str, details: str):
    """Print action being taken."""
    icons = {
        "shell": "🔧",
        "tool": "⚙️",
        "camera": "📷",
        "modem": "📱",
        "opencode": "💻",
        "reply": "💬",
    }
    icon = icons.get(action, "▶")
    print(f"  {icon} {Colors.CYAN}{action.upper()}{Colors.RESET} {Colors.GRAY}{details[:80]}{Colors.RESET}")


def _print_result(text: str, prefix: str = "🤖"):
    """Print result with formatting."""
    print(f"\n  {prefix} {Colors.BRIGHT_GREEN}{text}{Colors.RESET}")


def _print_error(text: str):
    """Print error with formatting."""
    print(f"\n  {Colors.RED}✗ {text}{Colors.RESET}")


def _print_variables(variables: Dict[str, Any]):
    """Print current variables/state."""
    if variables:
        print(f"\n  {Colors.GRAY}┌─ Current State ──────────────────────────────────{Colors.RESET}")
        for k, v in variables.items():
            val = str(v)[:50]
            print(f"  {Colors.GRAY}│{Colors.RESET} {Colors.BOLD}{k}:{Colors.RESET} {Colors.CYAN}{val}{Colors.RESET}")
        print(f"  {Colors.GRAY}└─────────────────────────────────────────────────{Colors.RESET}")


# ═══════════════════════════════════════════════════════════════════════════
#  Camera — DFRobot USB serial capture + REAL YOLO detection
# ═══════════════════════════════════════════════════════════════════════════

def _capture_frame() -> Optional[str]:
    """Capture JPEG from the camera — HTTP bridge or legacy USB serial."""
    cam_url = os.environ.get("TANK_CAM_URL", "").rstrip("/")
    if cam_url:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{cam_url}/snapshot.jpg", timeout=8) as resp:
                jpeg = resp.read()
            if len(jpeg) >= 500:
                out = _PROJECT_ROOT / "data" / "frames"
                out.mkdir(parents=True, exist_ok=True)
                path = out / "latest.jpg"
                path.write_bytes(jpeg)
                return str(path)
        except Exception as e:
            logger.debug("HTTP camera capture failed: %s", e)

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


def _capture_camera2() -> Optional[str]:
    """Capture from second camera (UNO Q ESP32-S3 CAM)."""
    unoq_urls = [
        os.environ.get("TANK_CAM2_URL", ""),                      # manual override
        "http://192.168.31.72:8083/snapshot.jpg",  # UNO Q TankOS Camera Server
        "http://100.84.235.7:8083/snapshot.jpg",   # UNO Q via Tailscale
        "http://192.168.31.145/snapshot.jpg",      # ESP32-S3 CAM direct
        "http://192.168.31.72:8081/frame.jpg",     # Motion streaming
    ]
    
    for url in unoq_urls:
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as resp:
                jpeg = resp.read()
            if len(jpeg) >= 500:  # Valid JPEG
                out = _PROJECT_ROOT / "data" / "frames"
                out.mkdir(parents=True, exist_ok=True)
                path = out / "camera2.jpg"
                path.write_bytes(jpeg)
                return str(path)
        except Exception:
            continue
    
    # Try local serial cameras
    for port in ["/dev/ttyACM1", "/dev/ttyACM2"]:
        if Path(port).exists():
            try:
                import serial as _serial
                s = _serial.Serial(port, 921600, timeout=5)
                time.sleep(0.5)
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
                if h.startswith("FRAME:"):
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
                    if len(jpeg) >= 500:
                        out = _PROJECT_ROOT / "data" / "frames"
                        out.mkdir(parents=True, exist_ok=True)
                        path = out / "camera2.jpg"
                        path.write_bytes(jpeg)
                        return str(path)
                s.close()
            except Exception:
                pass
    return None


def _read_lidar() -> str:
    """Read LiDAR distance data (aa55 protocol @ 115200, e.g. D300/Delta-2A).

    Frame: AA55 | speed | count | start_angle(2, deg*100) | end_angle(2,
    deg*100) | checksum(2) | count x distance(u16 LE, mm).
    Verified live on /dev/ttyUSB0 — 2026-08-25.
    """
    lidar_port = os.environ.get("TANK_LIDAR_PORT", "/dev/ttyUSB0")
    lidar_baud = int(os.environ.get("TANK_LIDAR_BAUD", "115200"))
    if not Path(lidar_port).exists():
        return f"LiDAR not connected ({lidar_port} not found)"

    try:
        import serial as _serial
        s = _serial.Serial(lidar_port, lidar_baud, timeout=0.1)
        time.sleep(0.2)
        s.reset_input_buffer()

        points = []  # (angle_deg, distance_mm)
        buf = b""
        deadline = time.time() + 2.0
        while time.time() < deadline:
            buf += s.read(4096)
        s.close()

        # Scan for aa55 headers and parse frames (10 + count*2 bytes)
        i = 0
        while True:
            idx = buf.find(b"\xaa\x55", i)
            if idx == -1 or idx + 10 > len(buf):
                break
            count = buf[idx + 3]
            frame_len = 10 + count * 2
            if count < 1 or count > 40 or idx + frame_len > len(buf):
                i = idx + 1
                continue
            frame = buf[idx:idx + frame_len]
            start_angle = int.from_bytes(frame[4:6], "little") / 100.0
            end_angle = int.from_bytes(frame[6:8], "little") / 100.0
            for j in range(count):
                off = 10 + j * 2
                dist = int.from_bytes(frame[off:off + 2], "little")
                if dist <= 0:
                    continue
                frac = j / max(count - 1, 1)
                angle = start_angle + (end_angle - start_angle) * frac
                if angle >= 360:
                    angle -= 360
                elif angle < 0:
                    angle += 360
                points.append((angle, dist))
            i = idx + frame_len

        if points:
            distances = [d for _, d in points]
            min_dist = min(distances)
            max_dist = max(distances)
            avg_dist = sum(distances) / len(distances)

            # Find closest obstacles (<1 m), bucketed by direction
            obstacles = []
            for a, d in sorted(points, key=lambda p: p[1]):
                if d >= 1000 or len(obstacles) >= 5:
                    continue
                direction = ("front" if a <= 45 or a >= 315 else
                             "right" if 45 < a <= 135 else
                             "back" if 135 < a <= 225 else "left")
                tag = f"{direction}({a:.0f}deg {d}mm)"
                if tag not in obstacles:
                    obstacles.append(tag)

            obstacle_str = ", ".join(obstacles) if obstacles else "none within 1m"
            return (f"LiDAR: {len(points)} points, min={min_dist}mm, "
                    f"max={max_dist}mm, avg={avg_dist:.0f}mm, "
                    f"obstacles: {obstacle_str}")
        else:
            return "LiDAR: No valid aa55 frames received"
    except Exception as e:
        return f"LiDAR error: {e}"


def _camera_vision() -> str:
    """Capture from all cameras + LiDAR + run REAL YOLO + face recognition."""
    results = []
    
    # Camera 1: DFRobot
    frame1 = _capture_frame()
    if frame1:
        detections1 = _run_yolo(frame1)
        results.append(f"Camera 1: {detections1}")
        
        # Face recognition
        try:
            from tank_os.shell.terminal.face_db import FaceDB
            db = FaceDB()
            faces = db.recognize_in_frame(frame1)
            if faces:
                parts = []
                unknown_count = 0
                for f in faces:
                    if f["is_known"]:
                        parts.append(f'{f["name"]}({f["confidence"]:.0%})')
                    else:
                        unknown_count += 1
                if parts:
                    results.append(f"Known faces: {', '.join(parts)}")
                if unknown_count > 0:
                    results.append(f"{unknown_count} unknown person(s)")
        except Exception:
            pass
    else:
        results.append("Camera 1: Not available")
    
    # Camera 2 (if available)
    frame2 = _capture_camera2()
    if frame2:
        detections2 = _run_yolo(frame2)
        results.append(f"Camera 2: {detections2}")
    
    # LiDAR
    lidar_result = _read_lidar()
    results.append(lidar_result)
    
    return ". ".join(results)


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-provider LLM
# ═══════════════════════════════════════════════════════════════════════════

_PROVIDER_DEFS = [
    # PRIMARY — fast, reliable
    ("groq_a",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "openai/gpt-oss-120b"),
    ("groq_b",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "openai/gpt-oss-20b"),
    ("groq_c",    "https://api.groq.com/openai/v1",  "GROQ_API_KEY",          "allam-2-7b"),
    ("mistral",   "https://api.mistral.ai/v1",        "MISTRAL_API_KEY",       "mistral-small-latest"),
    ("nvidia_nemotron_light", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", "nvidia/nemotron-3.5-lightning-30b-a3b"),
    ("nvidia_vision", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY_3",  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"),
    # FALLBACK
    ("nvidia_ultra", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY_2",   "nvidia/nemotron-3-ultra-550b-a55b"),
    ("gemini",    "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "gemini-2.5-flash"),
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
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if "nvidia" in base_url.lower() or "nemotron" in model.lower():
        content = _extract_nvidia_answer(content)
    return content


def _extract_nvidia_answer(text: str) -> str:
    """Extract final answer from NVIDIA thinking models."""
    lines = text.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        if line.startswith("Let me") or line.startswith("I'll") or line.startswith("Actually"):
            continue
        if line.startswith("-") and "output" in line.lower():
            continue
        if "--" in line and len(line) < 50:
            continue
        return line
    return lines[-1].strip() if lines else text


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


def _call_provider(name: str, messages: list) -> str:
    for pname, base, key_env, model in _PROVIDER_DEFS:
        if pname != name:
            continue
        api_key = os.environ.get(key_env, "")
        if not api_key or not model:
            raise RuntimeError(f"no_key:{name}")
        if "gemini" in pname:
            return _call_gemini(api_key, model, messages)
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
        print(f"\n  {Colors.YELLOW}⏳ Loading Phi-3 (~60s)...{Colors.RESET}", end="", flush=True)
        _local_llm = llama_cpp.Llama(model_path=str(model_path), n_ctx=4096, n_threads=4, verbose=False)
        print(f" {Colors.GREEN}ready{Colors.RESET}")
    prompt = ""
    for m in messages:
        if m["role"] == "system":
            prompt += f"<|system|>\n{m['content']}\n"
        elif m["role"] == "user":
            prompt += f"<|user|>\n{m['content']}\n"
    prompt += "<|assistant|>\n"
    resp = _local_llm(prompt, max_tokens=1024, temperature=0.15, stop=["<|user|>", "<|system|>"])
    return resp["choices"][0]["text"].strip()


def _rotate_chat(messages: list, show_thinking: bool = True) -> tuple:
    """Try all providers. Returns (response, provider_name, elapsed)."""
    order = [p[0] for p in _PROVIDER_DEFS]
    last_err = None
    for name in order:
        try:
            provider_info = next((p for p in _PROVIDER_DEFS if p[0] == name), None)
            if provider_info and show_thinking:
                model_short = provider_info[3].split("/")[-1][:20]
                _print_thinking(provider_info[0], model_short)
            
            start = time.time()
            result = _call_provider(name, messages)
            elapsed = time.time() - start
            
            if provider_info and show_thinking:
                _print_done(provider_info[0], elapsed)
            
            return result, name, elapsed
        except Exception as e:
            last_err = e
            logger.debug("Provider %s failed: %s", name, e)
            time.sleep(0.3)
    try:
        return _call_local_phi3(messages), "phi3-local", 0.0
    except Exception as e:
        return f"All providers failed. Last error: {last_err}", "none", 0.0


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
#  OpenCode integration
# ═══════════════════════════════════════════════════════════════════════════

def _run_opencode(task: str, timeout: int = 120) -> str:
    """Run OpenCode for development tasks."""
    opencode_path = None
    possible_paths = [
        "/home/shashi/.opencode/bin/opencode",
        "/usr/local/bin/opencode",
        "/usr/bin/opencode",
    ]
    for p in possible_paths:
        if Path(p).exists():
            opencode_path = p
            break
    
    if opencode_path is None:
        try:
            result = subprocess.run(["which", "opencode"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                opencode_path = result.stdout.strip()
        except Exception:
            pass
    
    if opencode_path is None:
        return "OpenCode not installed. Run: curl -fsSL https://opencode.ai/install | bash"
    
    try:
        result = subprocess.run(
            [opencode_path, "run", task],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)}
        )
        output = []
        if result.stdout:
            output.append(result.stdout.strip())
        if result.stderr:
            output.append(f"[stderr] {result.stderr.strip()[:500]}")
        return "\n".join(output) if output else "OpenCode completed with no output"
    except subprocess.TimeoutExpired:
        return f"OpenCode timed out after {timeout}s"
    except Exception as e:
        return f"OpenCode error: {e}"


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
            scripts_dir = _PROJECT_ROOT / "scripts"
            for cat_dir in scripts_dir.iterdir():
                if cat_dir.is_dir():
                    for script in cat_dir.glob("*.py"):
                        if tool_name.replace(".", "_") in script.name or tool_name.split(".")[-1] in script.name:
                            result = _run_shell(f"python3 {script} {' '.join(f'--{k} {v}' for k, v in args.items()) if args else ''}")
                            return result
            return f"Tool '{tool_name}' not found"
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
        return f"Tool error: {e}"


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
- Make call: {"action":"modem","function":"call_number","args":{"number_or_name":"shashi"}}

OPENCODE DEVELOPMENT (use {"action":"opencode","task":"<description>"}):
For ANY coding, development, debugging, or software engineering task:
- Write code: {"action":"opencode","task":"Write a Python function to sort a list using quicksort"}
- Debug code: {"action":"opencode","task":"Fix the bug in main.py where the API returns 500"}
- Refactor: {"action":"opencode","task":"Refactor the authentication module to use JWT tokens"}

EXAMPLES:
- Camera see: {"action":"camera"}
- System info: {"action":"shell","cmd":"uname -a && free -h && df -h"}
- Write code: {"action":"opencode","task":"Write a Python function to calculate fibonacci numbers"}
- After seeing results: {"action":"reply","text":"The system shows..."}
"""


# ═══════════════════════════════════════════════════════════════════════════
#  Agent REPL — Professional UI
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Turn:
    role: str
    content: str


@dataclass
class SessionState:
    """Track session state for display."""
    turn_count: int = 0
    provider_used: str = ""
    last_response_time: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    total_tokens: int = 0


class AgentChat:
    MAX_ROUNDS = 5

    def __init__(self):
        self._catalog = _load_tool_catalog()
        self._system = _SYSTEM_PROMPT + "\n\nAVAILABLE TOOLS:\n" + self._catalog
        self._history: List[Turn] = []
        self._state = SessionState()

    def run(self):
        self._banner()
        while True:
            try:
                user = input(f"\n{Colors.BRIGHT_CYAN}tank{Colors.RESET}{Colors.DIM}>{Colors.RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Colors.GRAY}  Bye! Session ended.{Colors.RESET}\n")
                break
            if not user:
                continue
            if user.lower() in ("exit", "quit", "q"):
                print(f"\n{Colors.GRAY}  Bye! Session ended.{Colors.RESET}\n")
                break
            if user.lower() == "clear":
                self._history.clear()
                self._state = SessionState()
                print(f"\n{Colors.GREEN}  ✓ History cleared{Colors.RESET}")
                continue
            if user.lower() == "status":
                self._show_status()
                continue
            if user.lower() == "help":
                self._show_help()
                continue
            self._handle(user)

    def _handle(self, user_input: str):
        self._state.turn_count += 1
        self._history.append(Turn("user", user_input))
        camera_used = False

        # Show what we're doing
        print(f"\n{Colors.GRAY}  ┌─ Processing turn {self._state.turn_count} ──────────────────────────{Colors.RESET}")

        for round_num in range(self.MAX_ROUNDS):
            resp, provider, elapsed = self._llm_with_provider()
            self._state.provider_used = provider
            self._state.last_response_time = elapsed
            
            if not resp:
                print(f"\n{Colors.YELLOW}  ⚠ LLM unavailable — retrying...{Colors.RESET}")
                resp, provider, elapsed = self._llm_with_provider()
                if not resp:
                    _print_error("All providers down")
                    return
            if resp.startswith("All providers"):
                _print_error(resp)
                return

            action = self._parse(resp)

            if action is None:
                clean = resp.strip()
                if '{"action"' in clean:
                    s = clean.find('{"action"')
                    e = clean.find('}', s) + 1
                    try:
                        action = json.loads(clean[s:e])
                    except:
                        pass
                if action is None and clean:
                    clean = self._strip_json_text(clean)
                    self._print_response(clean)
                    self._history.append(Turn("assistant", clean))
                    return

            if action is None:
                return

            at = action.get("action", "")

            if at == "reply":
                text = action.get("text", "")
                self._print_response(text)
                self._history.append(Turn("assistant", text))
                if len(self._history) > 8:
                    self._history = self._history[-4:]
                return

            elif at == "camera" and not camera_used:
                camera_used = True
                _print_action("camera", "Capturing from DFRobot camera + YOLO")
                result = _camera_vision()
                self._state.tools_used.append("camera")
                self._history.append(Turn("tool", f"[camera] {result}"))
                _print_status("Detections", result[:100])

            elif at == "camera" and camera_used:
                last_camera = ""
                for t in reversed(self._history):
                    if t.role == "tool" and "[camera]" in t.content:
                        last_camera = t.content
                        break
                self._history.append(Turn("user", f"STOP. Camera already captured. Here are the results: {last_camera}\nDescribe what you see. Reply with {{\"action\":\"reply\",\"text\":\"...\"}} format."))
                continue

            elif at == "tool":
                tn = action.get("tool", "")
                args = action.get("args", {})
                _print_action("tool", f"{tn}({json.dumps(args, ensure_ascii=False)})")
                result = _invoke_tool(tn, args)
                self._state.tools_used.append(tn)
                _print_status("Result", f"{len(result)} chars")
                self._history.append(Turn("tool", f"[tool:{tn}] {result[:500]}"))

            elif at == "shell":
                cmd = action.get("cmd", "")
                _print_action("shell", cmd)
                result = _run_shell(cmd)
                self._state.tools_used.append("shell")
                _print_status("Output", f"{len(result)} chars")
                self._history.append(Turn("tool", f"[shell] {result[:500]}"))

            elif at == "modem":
                fn = action.get("function", "")
                args = action.get("args", {})
                _print_action("modem", f"{fn}({json.dumps(args, ensure_ascii=False)})")
                try:
                    import importlib
                    modem_mod = importlib.import_module("tank_os.shell.terminal.modem_tools")
                    fn_obj = getattr(modem_mod, fn, None)
                    if fn_obj is None:
                        result = f"Unknown modem function: {fn}"
                    else:
                        result = fn_obj(**args)
                except Exception as e:
                    result = f"Modem error: {e}"
                self._state.tools_used.append(f"modem.{fn}")
                _print_status("Result", f"{len(result)} chars")
                self._history.append(Turn("tool", f"[modem] {result[:500]}"))

            elif at == "opencode":
                task = action.get("task", "")
                if not task:
                    result = "No task specified for OpenCode"
                else:
                    _print_action("opencode", task[:80])
                    result = _run_opencode(task)
                    self._state.tools_used.append("opencode")
                self._history.append(Turn("tool", f"[opencode] {result[:500]}"))

            else:
                clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
                clean = self._strip_json_text(clean)
                self._print_response(clean)
                self._history.append(Turn("assistant", clean))
                return

        # Max rounds
        self._history.append(Turn("user", 'Stop using tools. Give your final answer as plain text. Use {"action":"reply","text":"..."} format.'))
        final = self._llm()
        if final:
            clean = self._strip_json_text(final)
            self._print_response(clean)
        if len(self._history) > 8:
            self._history = self._history[-4:]

    def _print_response(self, text: str):
        """Print response with professional formatting."""
        print(f"\n  {Colors.BRIGHT_GREEN}🤖 TankOS:{Colors.RESET}")
        # Word wrap response
        words = text.split()
        line = "    "
        for word in words:
            if len(line) + len(word) + 1 > 70:
                print(line)
                line = "    " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
        print(f"\n  {Colors.GRAY}└─────────────────────────────────────────────────{Colors.RESET}")

    def _llm_with_provider(self) -> tuple:
        """Call LLM and return (response, provider, elapsed)."""
        msgs = [{"role": "system", "content": self._system}]
        recent = self._history[-6:]
        parts = []
        for t in recent:
            if t.role == "user":
                parts.append(f"User: {t.content}")
            elif t.role == "tool":
                truncated = t.content[:500]
                parts.append(truncated)
            elif t.role == "assistant":
                parts.append(f"Assistant: {t.content}")
        msgs.append({"role": "user", "content": "\n\n".join(parts)})
        try:
            return _rotate_chat(msgs)
        except Exception as e:
            return None, "none", 0.0

    def _llm(self) -> Optional[str]:
        resp, _, _ = self._llm_with_provider()
        return resp

    def _show_status(self):
        """Show session status."""
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Session Status{Colors.RESET}")
        print(f"{Colors.CYAN}╠══════════════════════════════════════════════════╣{Colors.RESET}")
        _print_status("Turns", str(self._state.turn_count))
        _print_status("Provider", self._state.provider_used or "none")
        _print_status("Last Response", f"{self._state.last_response_time:.1f}s")
        _print_status("Tools Used", ", ".join(set(self._state.tools_used)) or "none")
        _print_status("History", f"{len(self._history)} messages")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════╝{Colors.RESET}")

    def _show_help(self):
        """Show help."""
        print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}TankOS Agent Chat — Commands{Colors.RESET}")
        print(f"{Colors.CYAN}╠══════════════════════════════════════════════════╣{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Natural Language:{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}   \"what do you see through the camera?\"")
        print(f"{Colors.CYAN}║{Colors.RESET}   \"what is the system status?\"")
        print(f"{Colors.CYAN}║{Colors.RESET}   \"write a Python function to sort a list\"")
        print(f"{Colors.CYAN}║{Colors.RESET}   \"send an SMS to Shashi\"")
        print(f"{Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET} {Colors.BOLD}Commands:{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}   {Colors.GREEN}status{Colors.RESET}  — Show session info")
        print(f"{Colors.CYAN}║{Colors.RESET}   {Colors.GREEN}help{Colors.RESET}    — Show this help")
        print(f"{Colors.CYAN}║{Colors.RESET}   {Colors.GREEN}clear{Colors.RESET}   — Clear history")
        print(f"{Colors.CYAN}║{Colors.RESET}   {Colors.GREEN}exit{Colors.RESET}    — Quit")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════╝{Colors.RESET}")

    @staticmethod
    def _strip_json_text(text: str) -> str:
        """Extract human-readable text from LLM response."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "text" in obj:
                return obj["text"]
        except:
            pass
        for pattern in [r'\{"action"\s*:\s*"reply"\s*,\s*"text"\s*:\s*"([^"]+)"\}',
                       r'"text"\s*:\s*"([^"]+)"']:
            m = re.search(pattern, text)
            if m:
                return m.group(1).replace("\\n", "").replace("\\t", " ")
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
        """Professional banner with full status."""
        # Get provider count
        configured = sum(1 for _, _, key, _ in _PROVIDER_DEFS if os.environ.get(key))
        
        print()
        print(f"  {Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.BOLD}🤖  TankOS Agent Chat{Colors.RESET}                                 {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.DIM}Autonomous AI Robotics Operating System{Colors.RESET}              {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}╠═══════════════════════════════════════════════════════════╣{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.GREEN}●{Colors.RESET} {configured} cloud providers + Phi-3 local fallback       {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.GREEN}●{Colors.RESET} Real DFRobot USB camera + YOLO detection           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.GREEN}●{Colors.RESET} OpenCode for development tasks                    {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.GREEN}●{Colors.RESET} 1,166+ callable robot modules                      {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}╠═══════════════════════════════════════════════════════════╣{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.BOLD}Quick Start:{Colors.RESET}                                         {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.CYAN}\"what do you see through the camera?\"{Colors.RESET}              {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.CYAN}\"what is the system status?\"{Colors.RESET}                      {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.CYAN}\"write a Python function to sort a list\"{Colors.RESET}            {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}   {Colors.CYAN}\"help\"{Colors.RESET} for all commands                             {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}║{Colors.RESET}                                                           {Colors.BRIGHT_CYAN}║{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}╚═══════════════════════════════════════════════════════════╝{Colors.RESET}")
        print()


def main():
    AgentChat().run()


if __name__ == "__main__":
    main()
