"""
TankOS Preload Manifest — Complete Offline Dependency Registry.

Defines every dependency required for a fully offline TankOS installation.
Each entry includes category, name, description, source URL, expected
checksum, size, install path, and install method.

To regenerate checksums after updating a dependency::

    python3 -c "import hashlib; print(hashlib.sha256(open('file.bin','rb').read()).hexdigest())"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PreloadItem:
    """A single downloadable dependency."""
    id: str                          # Unique identifier (e.g. "whisper-tiny")
    category: str                    # Category group
    name: str                        # Human-readable name
    description: str                 # Description
    url: str                         # Download URL
    filename: str                    # Local filename after download
    install_path: str                # Where to install/extract
    size_mb: float = 0.0            # Approximate size in MB
    sha256: str = ""                 # SHA-256 checksum (hex)
    required: bool = True            # Is this required for basic operation?
    install_method: str = "copy"     # "copy", "extract", "pip", "apt", "git", "symlink"
    extract: bool = False            # Whether to extract (tar.gz, zip)
    version: str = ""                # Version string if applicable
    verify_only: bool = False        # Skip download, verify only (for apt/pip)
    package_name: str = ""           # Pip/apt package name for verification (if different from id)


# ── Helper: build default install paths ──────────────────────────────

BASE = os.environ.get("TANKOS_DATA_DIR", "/var/lib/tank_os")
MODELS_DIR = f"{BASE}/models"
SPEECH_DIR = f"{MODELS_DIR}/speech"
VISION_DIR = f"{MODELS_DIR}/vision"
LLM_DIR = f"{MODELS_DIR}/llm"
NAV_DIR = f"{MODELS_DIR}/navigation"
ASSETS_DIR = f"{BASE}/assets"
CACHE_DIR = f"{BASE}/cache"


# ── Complete Manifest ────────────────────────────────────────────────

MANIFEST: Dict[str, PreloadItem] = {}


def _register(item: PreloadItem) -> None:
    MANIFEST[item.id] = item


# ═══════════════════════════════════════════════════════════════════════
# Section 1: AI Runtime Libraries
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="llama-cpp-python",
    category="ai-runtime",
    name="llama.cpp (Python bindings)",
    description="GGUF model inference engine for local LLMs",
    url="https://github.com/abetlen/llama-cpp-python/releases/download/v0.2.90/llama_cpp_python-0.2.90-cp312-cp312-linux_aarch64.whl",
    filename="llama_cpp_python.whl",
    install_path=f"{BASE}/wheels",
    size_mb=45.0,
    install_method="pip",
    required=False,
))

_register(PreloadItem(
    id="onnxruntime",
    category="ai-runtime",
    name="ONNX Runtime",
    description="Cross-platform ML inference engine — install via pip (pip install onnxruntime)",
    url="",
    filename="",
    install_path="",
    size_mb=80.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="onnxruntime",
))

_register(PreloadItem(
    id="sentence-transformers",
    category="ai-runtime",
    name="Sentence Transformers",
    description="Text embedding models for semantic search",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="sentence-transformers",
))

_register(PreloadItem(
    id="faiss-cpu",
    category="ai-runtime",
    name="FAISS (CPU)",
    description="Vector similarity search library — install via pip (pip install faiss-cpu)",
    url="",
    filename="",
    install_path="",
    size_mb=25.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="faiss-cpu",
))

_register(PreloadItem(
    id="numpy-scipy",
    category="ai-runtime",
    name="NumPy + SciPy",
    description="Scientific computing libraries",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=True,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Local LLM Models
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="llm-primary",
    category="llm",
    name="Primary LLM (GGUF)",
    description="Main conversational AI model — Microsoft Phi-3 Mini 4K Instruct (2.3B params)",
    url="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
    filename="Phi-3-mini-4k-instruct-q4.gguf",
    install_path=f"{LLM_DIR}",
    size_mb=2200.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="llm-fallback",
    category="llm",
    name="Fallback LLM (GGUF)",
    description="Lightweight model for when primary is too slow — TinyLlama 1.1B Chat",
    url="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    filename="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    install_path=f"{LLM_DIR}",
    size_mb=670.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="llm-code",
    category="llm",
    name="Code Generation LLM (optional)",
    description="Specialized model for code generation tasks — Qwen2.5 Coder 1.5B",
    url="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    filename="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    install_path=f"{LLM_DIR}",
    size_mb=980.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="llm-vision",
    category="llm",
    name="Vision-Language Model (optional)",
    description="Multimodal model for image understanding — Qwen2-VL-7B Q4_K_M",
    url="https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
    filename="Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
    install_path=f"{LLM_DIR}",
    size_mb=4400.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="llm-vision-mmproj",
    category="llm",
    name="Vision-Language MMProj (companion)",
    description="Multimodal projector file required for Qwen2-VL vision understanding",
    url="https://huggingface.co/bartowski/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f16.gguf",
    filename="mmproj-Qwen2-VL-7B-Instruct-f16.gguf",
    install_path=f"{LLM_DIR}",
    size_mb=75.0,
    sha256="",
    required=False,
    install_method="copy",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Speech AI Models
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="whisper-tiny",
    category="speech",
    name="Whisper Tiny",
    description="Lightweight speech recognition model — install via openai-whisper pip package",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=True,
    install_method="pip",
    verify_only=True,
    package_name="openai-whisper",
))

_register(PreloadItem(
    id="whisper-base",
    category="speech",
    name="Whisper Base",
    description="Balanced speech recognition model — install via openai-whisper pip package",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=False,
    install_method="pip",
    verify_only=True,
    package_name="openai-whisper",
))

_register(PreloadItem(
    id="piper-tts",
    category="speech",
    name="Piper TTS Engine",
    description="Fast, local text-to-speech engine — install via pip (repo moved to OHF-Voice/piper1-gpl)",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=False,
    install_method="pip",
    verify_only=True,
    package_name="piper-tts",
))

_register(PreloadItem(
    id="piper-voice-en-us",
    category="speech",
    name="Piper English Voice (US)",
    description="High-quality US English TTS voice",
    url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
    filename="en_US-amy-medium.onnx",
    install_path=f"{SPEECH_DIR}/piper/voices",
    size_mb=40.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="openwakeword",
    category="speech",
    name="openWakeWord",
    description="Wake word detection engine — install via pip (models managed internally)",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=False,
    install_method="pip",
    verify_only=True,
    package_name="openwakeword",
))

_register(PreloadItem(
    id="wakeword-hey-tank",
    category="speech",
    name="Wake Word Model (Hey Tank)",
    description="Custom wake word model — managed by openWakeWord's download_models()",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=False,
    install_method="pip",
    verify_only=True,
    package_name="openwakeword",
))

_register(PreloadItem(
    id="noise-suppression",
    category="speech",
    name="Noise Suppression (noisereduce)",
    description="Real-time noise suppression for microphone input — via noisereduce pip package",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    sha256="",
    required=False,
    install_method="pip",
    verify_only=True,
    package_name="noisereduce",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Vision AI Models
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="yolov8-nano",
    category="vision",
    name="YOLOv8 Nano",
    description="Ultra-lightweight object detection model",
    url="https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
    filename="yolov8n.pt",
    install_path=f"{VISION_DIR}/yolo",
    size_mb=6.3,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="yolov8-small",
    category="vision",
    name="YOLOv8 Small",
    description="Balanced object detection model",
    url="https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
    filename="yolov8s.pt",
    install_path=f"{VISION_DIR}/yolo",
    size_mb=22.5,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="face-recognition",
    category="vision",
    name="Face Recognition Model",
    description="Face detection and recognition model",
    url="https://github.com/serengil/deepface_models/releases/download/v1.0/facenet512_weights.h5",
    filename="facenet512_weights.h5",
    install_path=f"{VISION_DIR}/face",
    size_mb=90.0,
    sha256="",
    required=False,
    install_method="copy",
))

_register(PreloadItem(
    id="apriltag",
    category="vision",
    name="AprilTag Detector",
    description="Fiducial marker detection for docking/localization",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="apriltag",
))

_register(PreloadItem(
    id="ocr-model",
    category="vision",
    name="OCR Model (EasyOCR)",
    description="Optical character recognition model",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="easyocr",
))

_register(PreloadItem(
    id="hand-tracking",
    category="vision",
    name="Hand Tracking (MediaPipe)",
    description="Hand landmark detection model",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="mediapipe",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 5: ROS2 & Navigation
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="slam-toolbox",
    category="navigation",
    name="SLAM Toolbox",
    description="2D SLAM library for ROS2",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="rtabmap",
    category="navigation",
    name="RTAB-Map",
    description="RGB-D SLAM with loop closure",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="nav2",
    category="navigation",
    name="Nav2 Stack",
    description="ROS2 Navigation stack (planner, controller, recovery)",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="cartographer",
    category="navigation",
    name="Cartographer (optional)",
    description="Google's 2D/3D SLAM library",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 6: Offline Assets (Icons, Themes, Sounds, etc.)
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="ui-icons",
    category="assets",
    name="UI Icons",
    description="Complete icon set for TankOS interface",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="ui-fonts",
    category="assets",
    name="UI Fonts",
    description="System fonts for TankOS interface",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="sounds-pack",
    category="assets",
    name="Sounds & Audio Pack",
    description="Boot sounds, notification sounds, UI audio feedback",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="boot-animation",
    category="assets",
    name="Boot Animation",
    description="TankOS startup animation frames",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="avatar-assets",
    category="assets",
    name="AI Avatar Assets",
    description="Animated robot avatar sprites and expressions",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Robot Drivers & Firmware
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="camera-driver-libcamera",
    category="drivers",
    name="libcamera (Camera Stack)",
    description="Camera stack for Jetson Orin Nano — includes libcamera, libcamera-apps",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="lidar-driver",
    category="drivers",
    name="LiDAR Driver (RPLIDAR/YDLIDAR)",
    description="Serial/USB driver for common 2D LiDAR sensors",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="motor-driver",
    category="drivers",
    name="Motor Driver (PCA9685 / DRV8833)",
    description="I2C/PWM motor controller drivers",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=True,
    package_name="adafruit-circuitpython-motorkit",
))

_register(PreloadItem(
    id="imu-driver",
    category="drivers",
    name="IMU Driver (ICM-20948 / MPU-9250)",
    description="I2C IMU sensor drivers",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="icm20948",
))

_register(PreloadItem(
    id="oled-driver",
    category="drivers",
    name="OLED Display Driver (SSD1306 / SH1106)",
    description="I2C OLED display driver for status display",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="adafruit-circuitpython-ssd1306",
))

_register(PreloadItem(
    id="servo-driver",
    category="drivers",
    name="Servo Driver (PCA9685)",
    description="PWM servo controller for pan/tilt/gripper",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="adafruit-circuitpython-servokit",
))

_register(PreloadItem(
    id="audio-driver",
    category="drivers",
    name="Audio Driver (ALSA / PulseAudio)",
    description="Audio input/output drivers for microphone and speaker",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="usb-rules",
    category="drivers",
    name="USB Device Rules",
    description="udev rules for persistent device names (camera, LiDAR, etc.)",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="esp32-firmware",
    category="drivers",
    name="ESP32-S3 Eye Display Firmware",
    description="Firmware source for ESP32 eye display module — build from firmware/eyes_esp32 sketch using PlatformIO",
    url="",
    filename="tank_eyes.bin",
    install_path=f"{BASE}/firmware",
    size_mb=1.5,
    sha256="",
    required=False,
    install_method="copy",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 8: System Packages
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="system-ros2-humble",
    category="system",
    name="ROS2 Humble",
    description="ROS2 Humble Hawksbill middleware",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="system-ffmpeg",
    category="system",
    name="FFmpeg",
    description="Multimedia framework for audio/video processing",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="system-opencv",
    category="system",
    name="OpenCV (system)",
    description="OpenCV system libraries with GPU support",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="system-gstreamer",
    category="system",
    name="GStreamer",
    description="Streaming media framework for camera pipelines",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="system-nginx",
    category="system",
    name="Nginx",
    description="Web server for web UI and API endpoints",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="system-sqlite3",
    category="system",
    name="SQLite3",
    description="Embedded database engine",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="system-build-tools",
    category="system",
    name="Build Tools (cmake, gcc, make)",
    description="C/C++ build toolchain for compiling packages",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="system-docker",
    category="system",
    name="Docker (optional)",
    description="Container runtime for isolated services",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 9: Developer Tools
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="dev-vscode-server",
    category="developer",
    name="VS Code Server (optional)",
    description="Remote VS Code server for web-based code editing",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="dev-ros-utils",
    category="developer",
    name="ROS2 Utilities",
    description="ROS2 development tools (rqt, rviz2, tf2 tools)",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="dev-profiler",
    category="developer",
    name="Profiling Tools (perf, valgrind)",
    description="Performance profiling and memory analysis tools",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="apt",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="dev-test-framework",
    category="developer",
    name="Testing Framework (pytest, coverage)",
    description="Python testing toolchain for TankOS unit tests",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="pip",
    verify_only=True,
    required=False,
    package_name="pytest",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 10: Recovery Resources
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="recovery-backup-utils",
    category="recovery",
    name="Backup Utilities",
    description="System backup and restore scripts",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="recovery-rollback",
    category="recovery",
    name="Rollback Packages",
    description="Previous versions of critical packages for rollback",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="recovery-emergency-boot",
    category="recovery",
    name="Emergency Boot Environment",
    description="Minimal recovery environment for system repair",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 11: AI Knowledge Base
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="hardware-db",
    category="knowledge",
    name="Hardware Database",
    description="Known hardware devices, IDs, and configuration profiles",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=False,
))

_register(PreloadItem(
    id="system-prompts",
    category="knowledge",
    name="System Prompts",
    description="AI system prompts for all subsystems and agents",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="tool-definitions",
    category="knowledge",
    name="Tool Definitions",
    description="Schema definitions for all AI-callable tools",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=True,
))

_register(PreloadItem(
    id="command-registry",
    category="knowledge",
    name="Command Registry",
    description="Built-in voice and text command definitions",
    url="",
    filename="",
    install_path="",
    size_mb=0.0,
    install_method="copy",
    verify_only=True,
    required=True,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 12: Media & Download Stack
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="media-qbittorrent",
    category="media",
    name="qBittorrent-nox",
    description="Headless torrent server with web UI",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="media-aria2",
    category="media",
    name="aria2",
    description="Multi-protocol download utility (HTTP/BT/Metalink)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="media-yt-dlp",
    category="media",
    name="yt-dlp",
    description="Video/audio downloader (YouTube, 1000+ sites)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="yt-dlp",
))

_register(PreloadItem(
    id="media-jellyfin",
    category="media",
    name="Jellyfin Server",
    description="Open-source media streaming server (Docker-based)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="media-navidrome",
    category="media",
    name="Navidrome",
    description="Self-hosted music streaming server (Docker-based)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="media-transmission",
    category="media",
    name="Transmission",
    description="Lightweight BitTorrent daemon",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="media-rss-bridge",
    category="media",
    name="RSS Bridge",
    description="RSS feed generation for websites without feeds",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="rss-bridge",
))

_register(PreloadItem(
    id="media-kodi",
    category="media",
    name="Kodi",
    description="Local media player and entertainment center",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 13: Cloud & Storage Stack
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="cloud-nextcloud",
    category="cloud-storage",
    name="Nextcloud",
    description="Personal cloud platform (files, calendar, contacts — Docker/snap)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="cloud-webdav",
    category="cloud-storage",
    name="WebDAV Server",
    description="HTTP-based remote file access (Apache mod_dav)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="cloud-syncthing",
    category="cloud-storage",
    name="Syncthing",
    description="Peer-to-peer continuous file synchronization",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="cloud-rclone",
    category="cloud-storage",
    name="rclone",
    description="Cloud storage sync (Drive, S3, R2, 40+ providers)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="cloud-restic",
    category="cloud-storage",
    name="Restic",
    description="Fast, encrypted backup tool",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="cloud-filebrowser",
    category="cloud-storage",
    name="File Browser",
    description="Web file manager with text editor",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="filebrowser",
))

_register(PreloadItem(
    id="cloud-ocrmypdf",
    category="cloud-storage",
    name="OCRmyPDF",
    description="PDF text extraction and OCR",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="cloud-tesseract",
    category="cloud-storage",
    name="Tesseract OCR",
    description="Open-source OCR engine for text extraction",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 14: Server & Database Stack
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="server-postgresql",
    category="server",
    name="PostgreSQL",
    description="Advanced relational database",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="server-redis",
    category="server",
    name="Redis",
    description="In-memory data structure store / cache",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="server-portainer",
    category="server",
    name="Portainer",
    description="Docker container management GUI (Docker container)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="server-nodered",
    category="server",
    name="Node-RED",
    description="Visual automation and workflow editor (npm/Docker)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="server-langchain",
    category="server",
    name="LangChain",
    description="LLM application framework for AI workflows",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="langchain",
))

_register(PreloadItem(
    id="server-beautifulsoup",
    category="server",
    name="BeautifulSoup",
    description="HTML/XML parsing for web scraping",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="beautifulsoup4",
))

_register(PreloadItem(
    id="server-playwright",
    category="server",
    name="Playwright",
    description="Browser automation for web scraping/testing",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="playwright",
))


# ═══════════════════════════════════════════════════════════════════════
# Section 15: Networking & Security Stack
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="net-ufw",
    category="security",
    name="UFW",
    description="Uncomplicated firewall",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="net-fail2ban",
    category="security",
    name="Fail2ban",
    description="Intrusion prevention / brute-force protection",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="net-avahi",
    category="security",
    name="Avahi",
    description="Zero-config local network discovery (mDNS/DNS-SD)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="sec-clamav",
    category="security",
    name="ClamAV",
    description="Open-source antivirus engine",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="sec-logwatch",
    category="security",
    name="Logwatch",
    description="System log analysis and daily reporting",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))

_register(PreloadItem(
    id="sec-crowdsec",
    category="security",
    name="CrowdSec",
    description="Community-powered intrusion protection (curl install)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="sec-motion",
    category="security",
    name="Motion",
    description="Camera motion detection and recording",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="apt", verify_only=True, required=False,
))


# ═══════════════════════════════════════════════════════════════════════
# Section 16: Smart Home Stack
# ═══════════════════════════════════════════════════════════════════════

_register(PreloadItem(
    id="smarthome-homeassistant",
    category="server",
    name="Home Assistant",
    description="Home automation platform (Docker container)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="smarthome-zigbee2mqtt",
    category="server",
    name="Zigbee2MQTT",
    description="Zigbee to MQTT bridge for smart home devices (npm/Docker)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="sec-frigate",
    category="security",
    name="Frigate NVR",
    description="AI-powered camera recording and object detection (Docker)",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="ai-ollama",
    category="ai-runtime",
    name="Ollama",
    description="Local LLM model manager and runner",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="copy", verify_only=False, required=False,
))

_register(PreloadItem(
    id="ai-sqlite-vec",
    category="ai-runtime",
    name="sqlite-vec",
    description="Vector similarity search extension for SQLite",
    url="", filename="", install_path="", size_mb=0.0,
    install_method="pip", verify_only=True, required=False,
    package_name="sqlite-vec",
))

def get_item(item_id: str) -> Optional[PreloadItem]:
    """Get a manifest item by ID."""
    return MANIFEST.get(item_id)


def get_category(category: str) -> List[PreloadItem]:
    """Get all items in a category."""
    return [i for i in MANIFEST.values() if i.category == category]


def categories() -> Dict[str, List[PreloadItem]]:
    """Get all items grouped by category."""
    result: Dict[str, List[PreloadItem]] = {}
    for item in MANIFEST.values():
        result.setdefault(item.category, []).append(item)
    return result


def summary() -> Dict[str, object]:
    """Get a summary of the manifest."""
    cats = categories()
    total = len(MANIFEST)
    total_size = sum(i.size_mb for i in MANIFEST.values())
    required_count = sum(1 for i in MANIFEST.values() if i.required)
    return {
        "total_items": total,
        "total_size_mb": round(total_size, 1),
        "required_items": required_count,
        "categories": {k: len(v) for k, v in sorted(cats.items())},
    }


def required_items() -> List[PreloadItem]:
    """Get all required items."""
    return [i for i in MANIFEST.values() if i.required]


def downloadable_items() -> List[PreloadItem]:
    """Get all items that have download URLs (not verify-only)."""
    return [i for i in MANIFEST.values() if i.url and not i.verify_only]
