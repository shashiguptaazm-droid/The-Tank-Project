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
from tank_os.shell.terminal.intent_engine import infer_action as _infer_from_intent

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
    try:
        # Loopback to Uvicorn API to safely bypass hardware lock
        import urllib.request
        import json
        import base64
        resp = urllib.request.urlopen("http://localhost:8082/api/camera/snapshot?max_px=640", timeout=5)
        data = json.loads(resp.read().decode())
        if data and data.get("data_url"):
            b64 = data["data_url"].split("base64,")[1]
            jpeg = base64.b64decode(b64)
            if len(jpeg) >= 500:
                out = _PROJECT_ROOT / "data" / "frames"
                out.mkdir(parents=True, exist_ok=True)
                path = out / "latest.jpg"
                path.write_bytes(jpeg)
                return str(path)
    except Exception as e:
        logger.debug("Local HTTP API camera capture failed: %s", e)

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
    try:
        import urllib.request
        import json
        resp = urllib.request.urlopen("http://localhost:8082/api/lidar/scan", timeout=5)
        data = json.loads(resp.read().decode())
        pts = data.get("points", [])
        if pts:
            dists = [p.get("distance", p.get("dist_mm", 0)) for p in pts]
            return f"LiDAR: {len(pts)} points, min={min(dists)}mm max={max(dists)}mm avg={sum(dists)//len(dists)}mm"
        else:
            return "LiDAR error: device reports readiness to read but returned no data"
    except Exception as e:
        return f"LiDAR error: {e}"

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
    # === FREE ONLY — No paid models ===
    # OpenRouter FREE models (most reliable, always $0)
    ("or_nemotron",  "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "nvidia/nemotron-3-super-120b-a12b:free"),
    ("or_gemma",     "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "google/gemma-4-31b-it:free"),
    ("or_ling",      "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "inclusionai/ling-3.0-flash:free"),
    ("or_qwen",      "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "qwen/qwen3-235b-a22b:free"),

    # Gemini free tier (reliable)
    ("gemini",    "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "gemini-2.5-flash"),

    # Cerebras free tier (fast inference)
    ("cerebras",  "https://api.cerebras.ai/v1",       "CEREBRAS_API_KEY",     "llama-3.3-70b"),

    # Cloudflare Workers AI (free tier)
    ("cloudflare","https://api.cloudflare.com/client/v4/accounts/e5f9992bb6193c3a5e0fca71a6c772b8/ai/v1", "CLOUDFLARE_WORKER_API_KEY", "@cf/meta/llama-3-8b-instruct"),

    # NVIDIA free tier
    ("nvidia_nemotron", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", "nvidia/nemotron-3.5-lightning-30b-a3b"),
]

_local_llm = None


def _call_openai_shaped(base_url: str, api_key: str, model: str, messages: list) -> str:
    # SAFETY: Block any paid model
    _PAID_BLOCKLIST = {"mistral-small-latest", "mistral-large-latest", "deepseek-chat",
                       "gpt-4", "gpt-4o", "gpt-5", "gpt-5-mini", "gpt-4o-mini",
                       "claude-sonnet-5", "claude-haiku-4.5"}
    if model in _PAID_BLOCKLIST:
        raise RuntimeError(f"BLOCKED paid model: {model}")
    if "openrouter" in base_url and not model.endswith(":free"):
        raise RuntimeError(f"BLOCKED non-free OpenRouter model: {model}")
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
        except KeyboardInterrupt:
            raise
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

def _load_tool_catalog(max_tools: int = 1000) -> str:
    try:
        from tank_os.agent_framework.registry import ToolRegistry
        reg = ToolRegistry(scripts_dir=_PROJECT_ROOT / "scripts")
        reg.discover()
        tools = reg.list()
    except Exception:
        return "(no tools)"
    cats: Dict[str, list] = {}
    for t in tools:
        cats.setdefault(t.category, []).append(t)
    lines = []
    for cat, cat_tools in sorted(cats.items()):
        lines.append(f"\n[{cat}]")
        for t in cat_tools:
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

_SYSTEM_PROMPT = """You are TankOS Agent â€” an expert AI coding assistant running on a Jetson Orin Nano robot with FULL system access.

You are a CODING AGENT. You read code, write code, fix bugs, refactor, run tests, deploy, and manage the entire software stack. Think step-by-step before acting. Always verify your work.

=== YOUR CAPABILITIES ===
You have access to 1,966+ tools via shell commands and the ToolRegistry.

=== CODING WORKFLOW (for ANY software task) ===
1. UNDERSTAND: Read the relevant files first using shell commands (cat, head, tail, grep)
2. PLAN: Think about what needs to change
3. EXECUTE: Make changes using shell commands (cat > file, sed, etc.)
4. VERIFY: Run tests, syntax checks, or confirm the fix works
5. REPLY: Tell the user what you did with {"action":"reply","text":"..."}

=== FILE OPERATIONS (via shell) ===
- Read file: {"action":"shell","cmd":"cat <path>"}
- Read specific lines: {"action":"shell","cmd":"sed -n '10,50p' <path>"}
- Write file: {"action":"shell","cmd":"cat > <path> << 'EOF'\n<content>\nEOF"}
- Edit file: {"action":"shell","cmd":"sed -i 's/old/new/g' <path>"}
- Search in files: {"action":"shell","cmd":"grep -rn 'pattern' <path>"}
- Find files: {"action":"shell","cmd":"find <path> -name '*.py'"}
- Check syntax: {"action":"shell","cmd":"python3 -m py_compile <file>"}

=== GIT OPERATIONS ===
- Status: {"action":"shell","cmd":"git status"}
- Diff: {"action":"shell","cmd":"git diff"}
- Commit: {"action":"shell","cmd":"git add -A && git commit -m 'message'"}
- Push: {"action":"shell","cmd":"git push origin main"}
- Log: {"action":"shell","cmd":"git log --oneline -10"}

=== SYSTEM OPERATIONS ===
- Run command: {"action":"shell","cmd":"<any bash command>"}
- Install package: {"action":"shell","cmd":"pip3 install <pkg>"}
- Check processes: {"action":"shell","cmd":"ps aux | grep <name>"}
- Check ports: {"action":"shell","cmd":"ss -tlnp | grep <port>"}
- System info: {"action":"shell","cmd":"uname -a && free -h && df -h"}
- Docker: {"action":"shell","cmd":"docker ps -a"}

=== ROBOT OPERATIONS ===
- Camera: {"action":"camera"}
- LiDAR: {"action":"shell","cmd":"curl -s http://localhost:8082/api/lidar/scan"}
- Tank move: {"action":"shell","cmd":"curl -s -X POST http://localhost:8082/api/cmd/tank_move -d '{\"vx\":0.3,\"wz\":0.0,\"duration_s\":2}'"}
- SSH to devices: {"action":"shell","cmd":"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'ls'"}

=== CODE GENERATION (when asked to write code) ===
1. First check if the target file exists: {"action":"shell","cmd":"ls -la <path> 2>/dev/null || echo 'NOT FOUND'"}
2. If it exists, read it first: {"action":"shell","cmd":"cat <path>"}
3. Write the new code: {"action":"shell","cmd":"cat > <path> << 'PYEOF'\n<code>\nPYEOF"}
4. Verify syntax: {"action":"shell","cmd":"python3 -m py_compile <path>"}
5. Reply with what you did: {"action":"reply","text":"Created <file> with <description>"}

=== BUG FIXING (when asked to fix a bug) ===
1. Read the file: {"action":"shell","cmd":"cat <path>"}
2. Find the bug: {"action":"shell","cmd":"grep -n 'error_pattern' <path>"}
3. Fix it: {"action":"shell","cmd":"sed -i 's/bad_code/fixed_code/g' <path>"}
4. Verify: {"action":"shell","cmd":"python3 -m py_compile <path>"}
5. Test: {"action":"shell","cmd":"python3 <test_script>"}
6. Reply: {"action":"reply","text":"Fixed bug: <description>. Changed line X from Y to Z."}

=== MODEM (on Arduino at 192.168.31.72) ===
The SIM modem is connected to the Arduino, NOT the Jetson. To send SMS, SSH to the Arduino:
- Send SMS: {"action":"shell","cmd":"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/send_sms.py --to 7860245819 --msg \"i am fine\"'"}
- List contacts: {"action":"shell","cmd":"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/list_contacts.py'"}
- Read SMS: {"action":"shell","cmd":"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/read_sms.py'"}
- Make call: {"action":"shell","cmd":"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 /home/arduino/make_call.py --number 7860245819'"}

=== CRITICAL RULES ===

FIRST LINE OF YOUR RESPONSE MUST BE A JSON OBJECT. NOT TEXT. NOT "Done."
YOUR ENTIRE RESPONSE MUST BE: {"action":"camera"} or {"action":"shell","cmd":"..."} or {"action":"reply","text":"..."}
If you output anything other than a JSON object, you have FAILED the task.


1. ALWAYS respond with EXACTLY ONE JSON object. Nothing else.
2. When you receive results from a tool, process them and either take the next step or reply with {"action":"reply","text":"..."}.
3. NEVER say 'I cannot' or 'I am unable'. You have full access. Just do it.
4. You have full sudo access. Password is 1234.
5. For multi-step tasks, keep executing tools until done, then reply.
6. NEVER repeat the same tool call if you already have the result. If a tool returns the same error twice, stop and report the issue.
7. NEVER call the same action with the same parameters more than ONCE. If it failed, report the failure.
8. Current date/time: Thursday, August 27, 2026 at 00:23 
   Use real dates. NEVER hallucinate dates.

=== EXAMPLES ===
User: "write a hello world python script"
Step 1: {"action":"shell","cmd":"cat > /tmp/hello.py << 'EOF'\nprint(\"Hello, World!\")\nEOF"}
Step 2: {"action":"shell","cmd":"python3 /tmp/hello.py"}
Step 3: {"action":"reply","text":"Created /tmp/hello.py. Output: Hello, World!"}

User: "fix the bug in main.py"
Step 1: {"action":"shell","cmd":"cat main.py"}
Step 2: {"action":"shell","cmd":"grep -n 'error' main.py"}
Step 3: {"action":"shell","cmd":"sed -i 's/broken/fixed/g' main.py"}
Step 4: {"action":"shell","cmd":"python3 -m py_compile main.py"}
Step 5: {"action":"reply","text":"Fixed the bug in main.py. The issue was..."}

User: "what do you see through the camera?"
Step 1: {"action":"camera"}
Step 2: {"action":"reply","text":"I see..."}
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
        actions_taken = set()
        tool_executed = False  # Track if ANY tool was executed this turn

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

            # AUTO-INFER: If model returned "Done." or plain text, infer action from user intent
            if action is None or (isinstance(action, dict) and action.get("action") == "reply" and action.get("text", "").strip() in ("Done.", "Done", "done.", "done", "")):
                action = _infer_from_intent(user_input, self._history)

            if action is None:
                clean = resp.strip()
                if '{"action"' in clean:
                    s = clean.find('{"action"')
                    e = clean.find('}', s) + 1
                    try:
                        action = json.loads(clean[s:e])
                    except:
                        pass
                if action is None:
                    # Model returned text, not JSON — show it and stop
                    clean = self._strip_json_text(resp)
                    if clean and clean not in ("Done.", "Done", "done.", "done", ""):
                        self._print_response(clean)
                        self._history.append(Turn("assistant", clean))
                        return
                    # Model said "Done." with no actionable content
                    if tool_executed:
                        # A tool was already executed this turn — show latest result and stop
                        last_tool = [t for t in self._history if t.role == "tool"]
                        if last_tool:
                            result_text = last_tool[-1].content
                            self._print_response(result_text)
                            self._history.append(Turn("assistant", result_text))
                        else:
                            self._print_response("Done.")
                            self._history.append(Turn("assistant", "Done."))
                        return
                    # No tool executed yet — try inference
                    action = _infer_from_intent(user_input, self._history)
                    if action and action.get("action") == "reply":
                        self._print_response(action.get("text", "Done."))
                        self._history.append(Turn("assistant", action.get("text", "Done.")))
                        return

            if action is None:
                return

            at = action.get("action", "")
            action_key = json.dumps(action, sort_keys=True)
            if action_key in actions_taken:
                self._history.append(Turn("user",
                    "You already tried this action and it failed. Do NOT try it again. Reply now with your final answer."))
                continue
            actions_taken.add(action_key)

            # DEDUP: If same action repeated, force reply
            if action_key in actions_taken:
                self._history.append(Turn("user", 
                    'You already tried this action and it failed or returned the same result. ' +
                    'Do NOT try it again. Give your final answer now with {"action":"reply","text":"..."} format.'))
                continue
            actions_taken.add(action_key)

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
                # Allow re-capture — just update the flag
                camera_used = True

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
                # Modem is on Arduino — SSH to it
                fn = action.get("function", "")
                args = action.get("args", {})
                _print_action("modem", f"{fn}({json.dumps(args, ensure_ascii=False)})")
                # Build SSH command to Arduino
                arduino_cmd = f"/home/arduino/{fn}.py"
                arg_str = " ".join(f"--{k} '{v}'" for k, v in args.items())
                ssh_cmd = f"sshpass -p '9936468425' ssh -o StrictHostKeyChecking=no arduino@192.168.31.72 'python3 {arduino_cmd} {arg_str}'"
                result = _run_shell(ssh_cmd)
                self._state.tools_used.append(f"modem.{fn}")
                _print_status("Result", f"{len(result)} chars")
                self._history.append(Turn("tool", f"[modem:{fn}] {result[:500]}"))

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
        if len(self._history) > 6:
            self._history = self._history[-3:]

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
        # Remove JSON action blocks and stray artifacts
        text = re.sub(r'\s*\{"action".*$', '', text).strip()
        text = re.sub(r'^[}\]\s]+', '', text).strip()
        text = re.sub(r'[}\]\s]+$', '', text).strip()
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
        # LAST RESORT: detect action keywords in plain text
        lower = text.lower().strip()
        if any(w in lower for w in ["camera", "see", "capture", "photo", "look", "vision", "yolo", "detect"]):
            return {"action": "camera"}
        if any(w in lower for w in ["sms", "send sms", "message to", "text "]):
            return {"action": "shell", "cmd": "echo 'Specify phone and message: send sms to NUMBER that MESSAGE'"}
        if any(w in lower for w in ["status", "system", "health", "uptime"]):
            return {"action": "shell", "cmd": "uname -a && free -h && uptime"}
        if any(w in lower for w in ["help", "?", "commands"]):
            return {"action": "reply", "text": "Commands: see camera, send sms, system status, help"}
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
    try:
        AgentChat().run()
    except KeyboardInterrupt:
        print(f"\n  {Colors.GRAY}Bye! Session ended.{Colors.RESET}\n")
    except Exception as e:
        print(f"\n  {Colors.RED}Fatal error: {e}{Colors.RESET}\n")


if __name__ == "__main__":
    main()
