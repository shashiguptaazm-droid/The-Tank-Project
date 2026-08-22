# Architecture

The Tank Project ships as a single ROS2 Humble colcon workspace split
into sixteen `ament_python` packages plus an out-of-tree Arduino
sketch for the ESP32-S3 eyes and the Arduino UNO Q motor/sensor firmware, **plus the TankOS graphical operating environment**.

## Six-Layer Architecture

TankOS introduces a 6-layer architecture that wraps the ROS2 workspace:

| Layer | Name | Description |
|-------|------|-------------|
| **Layer 5** | Simple Internet | Universal downloader & search: REST API (:8900), web dashboard, CLI (15 commands), 6 voice plugins, FastAPI server, torrent/search/library management |
| **Layer 4** | Tank Shell | PySide6 full-screen GUI (13 apps: Home, Chat, Camera, Nav, Memory, Security, Patrol, Files, Diagnostics, Developer, Settings, Power, Updates) |
| **Layer 3** | TankOS Core | 35 AI-powered managers: Event Bus, Plugin System, Theme Engine, Animation Engine, Robot Manager, Vision Manager, Security Manager, Memory Manager, Emotion Manager, Diagnostics, Recovery, Network, Storage, **Preload Manager** (95-dependency manifest), **Unified Installer** (12-step), Internet Manager, **Evolution Bridge** (14 LLM providers + rotation orchestrator), **Local LLM Provider** (offline GGUF inference), **Model Discovery** (auto-discover models from APIs), etc. |
| **Layer 2** | ROS2 | 16 unchanged ROS2 Humble packages: tank_motion, tank_vision, tank_assistant, tank_navigation, tank_security, tank_health, tank_dashboard, tank_meta, tank_display, tank_patrol, tank_task, tank_personalize, tank_command_bridge, etc. |
| **Layer 1** | Hardware | NVIDIA Jetson Orin Nano (AI brain) running JetPack 6 — ROS2 + AI models + TankOS GUI. Arduino UNO Q (real-time controller) — motor PWM, encoder ticks, sensor polling over I²C/GPIO, serial bridge to Jetson |

Phases built so far:

- Phase 1 — Foundation, motion, vision (tank_bringup, tank_motion,
  tank_sensors, tank_vision)
- Phase 2 — Eyes, tracker, mapping (tank_vision extras, tank_navigation)
- Phase 5 — Voice + assistant + memory (tank_speech, tank_memory, tank_assistant, tank_text, tank_dock, tank_health, tank_security, tank_dashboard, tank_nas)
- Phase 5½ — Emotion-driven face on eyes + OLED + dashboard (one /emotion/state → fan-out to 3 sinks)
- Phase 6½ — Append-only event logger + learner (tank_log)
- Phase 9  — Bidirectional AI ↔ robot bridge (Port 8082; tank_command_bridge + tank_assistant.external_llm_client)
- Phase 10 — Voice task framework (tank_task)
- Phase 10½ — AI humanness + preferences (tank_personalize)
- Phase 11 — TankOS GUI (tank_os/ — graphical AI operating environment)

```
            ┌────────────────┐
operator ──►│ teleop (ext)   │──► /cmd_vel ──┐
            └────────────────┘                │
                                            ▼
                  ┌──────────────────────────────────┐
                  │        safety_watchdog           │──► /estop ──┐
                  └──────────────────────────────────┘              ▼
                                                       ┌─────────────────────┐
                                                       │   motor_controller  │──► /odom, /motor_status
                                                       └─────────────────────┘

  /pan_tilt_cmd ──► pan_tilt_controller ──► /pan_tilt_state
  /scan      ◀──  lidar_publisher
  /imu/data  ◀──  imu_publisher
  /camera/image_raw ◀── camera_publisher

  /audio ──► wake_word_listener ──► /wake_detected (Bool, latched)
                              ├──► /wake_confidence
                              └──► /wake_event

      /camera/image_raw ──► object_tracker ──► /tracked_target (NDC)
                                            └► /pan_tilt_cmd (closed-loop)
      /eye_expression, /eye_target, /eye_blink ──► eye_lcd_bridge ──► UART ──► ESP32-S3 eyes

  /scan + /odom + /camera ──► slam_toolbox ──► /map (2D)
                          └──► rtabmap_ros  ──► /rtabmap/cloud_map (3D)

  /memory/event ──► memory_node (sqlite-vec + sentence-transformers) ──► /memory/recall_result
      /memory/query ────────────────────/
      /memory/compact_cmd ────────/

  /intent_text ──► rag_node ──► llm_node ──► /assistant_text ──► emotion_node ──► /emotion/state
                ──► stt_node ──► /intent_text (Whisper)
                ─► tts_node ──► /audio_out (Piper)

  /camera/image_raw ──► motion_node ──► /security/events/motion
                          ├──► recorder_node ──► /security/recording_path
                          └──► event_logger  ──► /security/event_log + MQTT

  /camera/image_raw ──► dock_node (AprilTag + IR homing) ──► /dock/pose, /dock/charge_cmd

  /battery/state ──► health_node ──► /health/state, /health/ok, /health/prometheus
                                   └► Prometheus scrape

  FastAPI dashboard (tank_dashboard.app)
      GET /api/health, GET /api/telemetry, GET /api/recording/list
      POST /api/cmd/estop, POST /api/cmd/move
      WS /ws/feed → JSON stream of /health/state

  /meta/code_search       ──► meta_node (sqlite, AST code index + hardware JSON + decisions JSON + docs) ──► /meta/code_search_result
      /meta/hardware_lookup    ──/                                                  ──► /meta/hardware_lookup_result
      /meta/decision_search    ──/                                                  ──► /meta/decision_search_result
      /meta/knowledge_query    ──/                                                  ──► /meta/knowledge_query_result
      /meta/index_now          ──/ (triggers reindex from `search_meta` CLI)

  ~21 system topics (wake/intent/cmd_vel/estop/security/dock/health/...) ──► log_node (sqlite, append-only)
                                                              ├─► /log/stats  (every 10s)
                                                              └─► /log/tail   (every 2s, last 10 entries)
  periodic learner  (every 30s by default) ──► topic_summary (busiest topic + priority-ordered anomaly: estop_stuck > dock_charging_but_health_not_ok > wake_no_intent)
```

## Simple Internet — Universal Downloader & Search (Layer 5)

Simple Internet is a complete download management system built into TankOS:

### Components

| Component | Location | Description | Features |
|-----------|----------|-------------|----------|
| **Download Engine** | `tank_os/internet/downloader.py` | Core download engine | Multi-protocol (HTTP/FTP/BT/Magnet/YouTube), aria2 RPC, yt-dlp, FFmpeg, queue, resume, bandwidth control, auto-categorization, watch directory, post-download extraction/conversion |
| **Search Engine** | `tank_os/internet/search.py` | Meta-search aggregation | YouTube, SoundCloud, web (DuckDuckGo), images, news; search filters; bookmarks; suggestions; history; plugin-based sources |
| **Internet Manager** | `tank_os/internet/manager.py` | Unified manager | Library DB, RSS automation, EventBus integration, automated scanning |
| **Web Dashboard** | `tank_os/internet/server.py` | FastAPI server + 5-page dashboard | 22 REST API endpoints, real-time auto-refresh, dark theme, responsive layout, toast notifications |
| **CLI Tool** | `tank_os/internet/cli.py` (+ 39 host-level scripts) | Command-line interface | Extends to **1,166 subcommands across 40 host-level CLI scripts** in `scripts/` (F001-F206 + the F207-F1166 expansion covering AI, media, home automation, comm/networking, maintenance, health/education/gaming/kitchen/creativity/productivity/social/energy/outdoor/security/maker, and Simple Internet multi-round downloading 1+2+3). The 6 in-tree CLI files covering Simple Internet specifically are `scripts/download_music.py`, `download_video.py`, `download_data.py`, `download_torrent.py`, `download_scheduled.py`, `download_deepweb.py` (F717-F916), plus `download_*_2.py` (F917-F1116) and `download_*_3.py` (F1117-F1166). |
| **Voice Plugin** | `tank_os/internet/voice_plugin.py` | 6 TankOS voice commands | voice.internet_download, _search, _queue, _cancel, _status, _library with TTS feedback |

### Quick Start

```bash
# Start the web dashboard (port 8900)
python3 -m tank_os.internet.server

# Use the CLI
python3 -m tank_os.internet.cli download "magnet:?xt=urn:btih:..."
python3 -m tank_os.internet.cli search "ubuntu 24.04" --source=torrent
python3 -m tank_os.internet.cli queue
python3 -m tank_os.internet.cli stats
```

### Auto-Setup & Verification

```bash
# Full setup (system packages + AI models + verification)
sudo bash scripts/tankos_setup.sh

# Verify only (no downloads)
sudo bash scripts/tankos_setup.sh --verify

# Download missing AI models only
sudo bash scripts/tankos_setup.sh --download

# Show setup status
sudo bash scripts/tankos_setup.sh --status
```

## Recent expansion (post F206)

* **Massive CLI Scaling:** Expanded host-level capabilities to **1,166 features (F207-F1166) across 40 zero-dependency Python CLI scripts** in `scripts/`, covering AI & vision, personality & security, mobility & environment, media & home automation, comms/networking, maintenance, AI voice & vision AR, gaming, health, kitchen, education, creativity, productivity, social, energy, outdoor, security, maker, music & video downloading (round 1+2+3).
* **Dependency Definition:** Centralized all system-level (apt/brew) and Python (pip) dependencies into a single canonical doc at [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) (218 lines, 12 sections), with a matching `requirements.txt` (broad pip manifest) and `requirements-dev.txt` (dev tools). See also the placeholder `docs/SIMPLE_INTERNET_ARCH.md` linking the Simple Internet module-by-module architecture.
* **Advanced Simple Internet downloader (450 tasks across 3 rounds):** F717-F916 (200 tasks × 6 scripts in `scripts/download_*.py`), F917-F1116 (200 tasks × 10 scripts in `scripts/download_*_2.py`), F1117-F1166 (50 high-impact features × 4 scripts in `scripts/download_*_3.py`).
* **Architecture Integrity:** All 1,166 features ship as host-level CLI subcommands below the core ROS 2 workspace (`tank_ws/`) and TankOS GUI (`tank_os/`) layers. No changes to `tank_ws/src/*` runtime, no ROS topic additions, no firmware changes. The CLI surface is the feature surface.

## Packages

| Package           | Type         | Owns (Phase)                                                                                              |
|-------------------|--------------|----------------------------------------------------------------------------------------------------------|
| `tank_bringup`    | ament_python | global launch + watchdog + URDF + systemd (P1)                                                            |
| `tank_motion`     | ament_python | motor + pan-tilt + kinematics + tests (P1)                                                                |
| `tank_sensors`    | ament_python | IMU + LiDAR (P1)                                                                                         |
| `tank_vision`     | ament_python | camera + eye-LCD bridge + YOLO tracker (P1, P2)                                                           |
| `tank_navigation` | ament_python | slam_toolbox + RTAB-Map + bridges (P2)                                                                    |
| `tank_speech`     | ament_python | wake_word_listener (openWakeWord) (P5)                                                                    |
| `tank_memory`     | ament_python | persistent vector memory (sqlite-vec + sentence-transformers) (P5)                                        |
| `tank_assistant`  | ament_python | LLM (llama.cpp) + RAG + emotion engine (P5)                                                              |
| `tank_text`       | ament_python | Whisper STT + Piper TTS (P5)                                                                              |
| `tank_dock`       | ament_python | AprilTag auto-dock + charge contactor (P4)                                                                |
| `tank_health`     | ament_python | battery + CPU/voltage + Prometheus exporter (P2/P4)                                                       |
| `tank_security`   | ament_python | motion detect + recorder + event logger/MQTT (P2/P4)                                                      |
| `tank_dashboard`  | ament_python | FastAPI backend + nginx reverse-proxy (P5)                                                                |
| `tank_nas`        | ament_python | Samba + WebDAV + rclone auto-backup helpers (P3)                                                          |
| `tank_meta`       | ament_python | coding-agent structured memory: AST code index, hardware lookup, decision log, markdown knowledge (P6) |
| `tank_log`        | ament_python | append-only event-stream logger + periodic learner (P6½)                                            |
| `tank_patrol`    | ament_python | autonomous patrolling (waypoint + random) + AI surveillance fusion (P7)                                  |
| `tank_display`   | ament_python | emotion-driven face on 1.3" SH1106 OLED (I²C 0x70) + NullHal fallback (P5½)                              || `tank_command_bridge` | ament_python | bidirectional AI ↔ robot command bridge on port 8082 (Freebuff/Claude/Codex) with bearer auth + per-token rate-limit + manifest introspection (P9) |
| `tank_personalize` | ament_python | AI humanness layer: Persona dataclass + Preferences (motion/privacy/audio) + UserMemory + composed system prompt + dialogue patterns + complete preferences dashboard on port 8084 (P10½) |
| firmware (out-of-tree) | Arduino | ESP32-S3 eyes firmware (P2) + Arduino UNO Q motor/sensor firmware (P1) |

## Provisioning (Jetson Orin Nano + Arduino UNO Q)

**SINGLE COMMAND: `sudo bash tank_os/install.sh --apply`**

The unified installer (`tank_os/install.sh`) is now the single master installer
that supersedes the legacy `setup_pi5.sh` and `provision_pi5.sh` scripts (both now
wrapper scripts that delegate to the unified installer).

**Hardware split:** Jetson Orin Nano runs ROS2 + TankOS + all AI inference.
Arduino UNO Q handles real-time motor/sensor I/O, bridging to Jetson over
serial (115200 baud) with a compact binary protocol.

12-step install flow:

| Step | What it installs |
|------|-----------------|
| 1 | Platform detection — Jetson vs x86, RAM, disk space |
| 2 | Hardware — I2C, SPI, UART, RPLidar udev rules, Arduino firmata upload |
| 3 | **24 apt packages** — Qt6, Docker, ROS2, ffmpeg, GStreamer, Nginx, etc. |
| 4 | **ROS2 Humble** — base + slam-toolbox + colcon |
| 5 | **22 pip packages** — PySide6, OpenCV, ultralytics, fastapi, etc. |
| 6 | **PYTHONPATH** — /etc/environment + profile script |
| 7 | **Data directories** — /var/lib/tank_os/models/ |
| 8 | **TankOS config** — settings.json with defaults |
| 9 | **Optional services** — Tailscale, MQTT, Samba |
| 10 | **AI Model downloads** — PreloadManager (~8 GB, resumable) |
| 11 | **Systemd service** — tank-init.service for autoboot |
| 12 | **Verification** — 9-point check |

Usage:
```bash
# Dry run (see what would be installed)
bash tank_os/install.sh

# Full install
sudo bash tank_os/install.sh --apply

# Without AI models (run later)
sudo bash tank_os/install.sh --apply --skip-models

# Legacy scripts (delegate to unified installer)
bash tank_os/install.sh --apply    # same effect
```

PreloadManager downloads 95 dependencies across 15 categories:
| Category | Items | Examples |
|----------|-------|---------|
| AI Runtime | 7 | llama.cpp, ONNX Runtime, FAISS, Sentence Transformers, Ollama, sqlite-vec, NumPy/SciPy |
| Speech AI | 7 | Whisper, Piper TTS, openWakeWord, noise suppression |
| Vision AI | 6 | YOLOv8 (nano/small), Face Recognition, AprilTag, OCR, Hand Tracking |
| Local LLMs | 5 | Phi-3 (2.2GB), TinyLlama (87MB), Qwen2.5-Coder (980MB), Qwen2-VL 7B (2.6GB), MMProj (1.3GB) |
| Navigation | 4 | SLAM Toolbox, RTAB-Map, Nav2, Cartographer |
| Robot Drivers | 9 | Camera, LiDAR, Motor, IMU, OLED, Servo, Audio, USB rules, ESP32 firmware |
| System | 8 | ROS2, FFmpeg, OpenCV, GStreamer, Nginx, SQLite, Build tools, Docker |
| Developer | 4 | VS Code Server, ROS utils, Profilers, Testing framework |
| Recovery | 3 | Backup, Rollback, Emergency boot |
| Assets | 5 | Icons, Fonts, Sounds, Boot animation, Avatar |
| Knowledge | 4 | Hardware DB, System prompts, Tool definitions, Command registry |
| Media Stack | 8 | qBittorrent, aria2, yt-dlp, Jellyfin, Navidrome, Transmission, RSS Bridge, Kodi |
| Cloud Storage | 8 | Nextcloud, WebDAV, Syncthing, rclone, Restic, File Browser, OCRmyPDF, Tesseract |
| Server Stack | 7 | PostgreSQL, Redis, Portainer, Node-RED, LangChain, BeautifulSoup, Playwright |
| Security Stack | 8 | UFW, Fail2ban, Avahi, ClamAV, Logwatch, CrowdSec, Motion, Frigate NVR |
