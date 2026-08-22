# 🚀 The Tank Project — Complete Definition for ChatGPT

> **What this is:** A comprehensive, single-document definition of the entire Tank Project — a tracked AI robot built on NVIDIA Jetson Orin Nano + ROS 2 Humble + Python. Share this with any AI assistant (ChatGPT, Claude, Freebuff, Codex) to give it full context on the codebase it's working with.

---

## 1. 🎯 Project Identity

**Name:** The Tank Project
**Type:** Tracked AI-companion robot
**Hardware:** NVIDIA Jetson Orin Nano (8 GB) + ESP32-S3 + custom chassis
**Software:** ROS 2 Humble colcon workspace (pure Python, no C++)
**AI Stack:** Local LLM (llama.cpp), Whisper STT, Piper TTS, openWakeWord, YOLOv8n
**Repo Root:** `/root/the tank project/`

### Quick Philosophy

The Tank is an **emotionally-aware, always-on, voice-operated companion robot** that:
- Navigates autonomously (2D SLAM + 3D RTAB-Map)
- Recognizes objects and tracks faces (YOLOv8n)
- Speaks and listens (Piper TTS + Whisper STT)
- Has persistent memory (sqlite-vec + sentence-transformers)
- Feels emotions (26-emotion Plutchik-inspired taxonomy with decay)
- Expresses through eyes (ESP32-driven round LCDs) + OLED face + dashboard
- Auto-docks (AprilTag + IR homing)
- Patrols and provides security (motion detection + recording)
- Learns from interactions and updates its own knowledge base
- Can be commanded by AI coding agents via HTTP bridge (port 8082)

---

## 2. 🏗️ Architecture Overview

### ROS 2 Topic Graph

```
           ┌────────────────┐
operator ─►│ teleop (ext)   │──► /cmd_vel ──┐
           └────────────────┘               │
                                           ▼
                 ┌──────────────────────────────────┐
                 │       safety_watchdog            │──► /estop ──┐
                 └──────────────────────────────────┘             ▼
                                                      ┌─────────────────────┐
                                                      │   motor_controller  │──► /odom, /motor_status
                                                      └─────────────────────┘

 /pan_tilt_cmd ──► pan_tilt_controller ──► /pan_tilt_state
 /scan      ◄──  lidar_publisher
 /imu/data  ◄──  imu_publisher
 /camera/image_raw ◄── camera_publisher

 /audio ──► wake_word_listener ──► /wake_detected (Bool, latched)
                             ├──► /wake_confidence
                             └──► /wake_event

     /camera/image_raw ──► object_tracker ──► /tracked_target (NDC)
                                           └► /pan_tilt_cmd (closed-loop)

 /scan + /odom + /camera ──► slam_toolbox ──► /map (2D)
                         └──► rtabmap_ros  ──► /rtabmap/cloud_map (3D)

 /memory/event ──► memory_node (sqlite-vec + sentence-transformers) ──► /memory/recall_result
     /memory/query ────────────────────────────/
     /memory/compact_cmd ──────────────────/

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

 /meta/code_search        ──► meta_node (sqlite, AST code index + hardware JSON + decisions JSON + docs)
 /meta/hardware_lookup    ──/                                                  ──► /meta/code_search_result
 /meta/decision_search    ──/                                                  ──► /meta/hardware_lookup_result
 /meta/knowledge_query    ──/                                                  ──► /meta/decision_search_result
 /meta/index_now          ──/ (triggers reindex from `search_meta` CLI)       ──► /meta/knowledge_query_result

 ~21 system topics ──► log_node (sqlite, append-only)
                       ├─► /log/stats (every 10s)
                       └─► /log/tail (every 2s, last 10 entries)
 periodic learner (every 30s) ──► topic_summary + anomaly detection
                                  (estop_stuck > dock_charging_but_health_not_ok > wake_no_intent)
```

---

## 3. 📦 Package Inventory (16 Packages, ~7,800 LOC Python)

### Core Infrastructure

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_bringup` | 266 | Global launch tree, safety watchdog, URDF, systemd | `launch/robot.launch.py`, `safety_watchdog.py` |
| `tank_motion` | 622 | Motor controller, pan-tilt, skid-steer kinematics | `motor_controller.py`, `truck_kinematics.py`, `pan_tilt_controller.py` |
| `tank_sensors` | 316 | IMU (BNO055) + LiDAR (RPLidar) publishers | `imu_publisher.py`, `lidar_publisher.py` |

### Vision & Navigation

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_vision` | 671 | Camera publisher, YOLOv8n tracker, eye LCD bridge, media player, animations | `camera_publisher.py`, `object_tracker.py`, `eye_lcd_bridge.py` |
| `tank_navigation` | 344 | slam_toolbox 2D + RTAB-Map 3D bridges | `slam_2d_bridge.py`, `rtabmap_bridge.py` |
| `tank_dock` | 187 | AprilTag auto-dock + IR homing + charge contactor | `dock_node.py` |

### Speech & Audio

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_speech` | 564 | Wake word listener (openWakeWord), STT, intent routing | `wake_word_listener.py`, `stt_node.py`, `intent_router.py` |
| `tank_text` | 314 | Whisper STT + Piper TTS | `stt_node.py`, `tts_node.py` |

### AI & Memory

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_assistant` | 621 | LLM (llama.cpp), RAG bridge, emotion engine, external LLM client | `llm_node.py`, `rag_node.py`, `emotion_node.py`, `external_llm_client.py` |
| `tank_memory` | 927 | Persistent vector memory (sqlite-vec + sentence-transformers) | `memory_store.py`, `memory_node.py` |
| `tank_meta` | **1,906** | **Structured coding-agent memory**: AST code index, hardware, decisions, docs | `meta_store.py`, `code_indexer.py`, `meta_node.py` |
| `tank_log` | ~500 | Append-only event logger + periodic anomaly learner | `log_store.py`, `log_node.py`, `learner.py` |
| `tank_learn` | ~400 | Discovery store, memory store, consolidation, feedback | `ingest.py`, `consolidation.py`, `discovery_learner.py` |

### Emotions & Personality

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_emotions` | ~800 | 26-emotion taxonomy, companion engine, Plutchik wheel, decay | `companion.py`, `taxonomy.py`, `core.py`, `wheel.py`, `emotions/*.py` |
| `tank_display` | 225 | Emotion-driven face on 1.3" SH1106 OLED (I²C 0x70) + NullHal | `display_node.py`, `faces.py`, `oled_hal.py` |
| `tank_personalize` | ~500 | Persona, preferences, user memory, dialogue patterns, dashboard | `persona.py`, `preferences.py`, `memory.py`, `app.py` |

### Security & Health

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_security` | 367 | Motion detection, video recording, event logging/MQTT | `motion_node.py`, `recorder_node.py`, `event_logger.py` |
| `tank_health` | 186 | Battery (INA219), CPU/voltage, Prometheus exporter | `health_node.py` |

### Dashboard & Bridge

| Package | LOC | Purpose | Key Files |
|---------|-----|---------|-----------|
| `tank_dashboard` | 177 | FastAPI + nginx reverse-proxy | `app.py` |
| `tank_command_bridge` | **~720** | **Bidirectional AI ↔ Pi HTTP bridge on :8082** | `app.py`, `auth.py`, `manifest.py`, `commands.py`, `plugins/*.py` |
| `tank_patrol` | ~350 | Autonomous patrolling (waypoint + random) + AI surveillance fusion | `patrol_modes.py`, `patrol_node.py`, `surveillance.py` |
| `tank_task` | ~300 | Voice task framework (9 sample tasks + registry) | `base.py`, `registry.py`, `tasks/*.py` |

### Supporting

| Package | LOC | Purpose |
|---------|-----|---------|
| `tank_nas` | 88 | Samba + WebDAV + rclone auto-backup helpers |
| `tank_neutral` | 0 | Placeholder |

### Firmware (out-of-tree)

| Component | Language | Purpose |
|-----------|----------|---------|
| `firmware/eyes_esp32/eyes_esp32.ino` | Arduino (C++) | Drives 2× Waveshare 1.28" round GC9A101 displays over SPI. JSON control via UART2 from Pi. |

---

## 4. 🧠 Emotion System (Tank's "Soul")

### 26 Emotions in a Plutchik Wheel

The emotion system is a comprehensive, academically-grounded affective computing engine inspired by:

- **Plutchik** (8 primary emotions on a wheel)
- **Ekman** (6 basic emotions, cross-cultural facial-action units)
- **Izard** (10 differential emotions, self-conscious subset)
- **Geneva Emotion Wheel** (4 families)
- **Parrott** (3-level emotion tree)

| Emotion | Valence | Arousal | Safety |
|---------|---------|---------|--------|
| Joy | +0.95 | +0.60 | No |
| Trust | +0.70 | +0.20 | No |
| Fear | -0.80 | +0.85 | Yes |
| Surprise | +0.10 | +0.80 | No |
| Sadness | -0.80 | -0.50 | No |
| Disgust | -0.70 | +0.40 | No |
| Anger | -0.85 | +0.75 | Yes |
| Anticipation | +0.30 | +0.60 | No |
| Love | +0.90 | +0.60 | No |
| Gratitude | +0.85 | +0.30 | No |
| Compassion | +0.60 | -0.20 | No |
| Contentment | +0.70 | -0.60 | No |
| Pride | +0.65 | +0.40 | No |
| Hope | +0.50 | +0.50 | No |
| Relief | +0.70 | -0.40 | No |
| Nostalgia | +0.30 | -0.30 | No |
| Awe | +0.40 | +0.70 | No |
| Guilt | -0.70 | -0.30 | No |
| Shame | -0.75 | -0.20 | No |
| Embarrassment | -0.50 | +0.30 | No |
| Jealousy | -0.60 | +0.50 | Yes |
| Envy | -0.50 | +0.40 | No |
| Contempt | -0.40 | +0.20 | No |
| Melancholy | -0.50 | -0.60 | No |
| Relief | +0.70 | -0.40 | No |
| Hope | +0.50 | +0.50 | No |

### Emotion Pipeline

1. **Trigger**: Events, voice tone, companion interactions trigger emotions
2. **Intensity Decay**: Each emotion decays with a configurable half-life (`decay_s`, typically 8-12s)
3. **Emotion Node**: Publishes `/emotion/state` with the current dominant emotion + intensity
4. **1:N Fan-out**:
   - `/eye_expression` → `eye_lcd_bridge` → UART → ESP32-S3 round LCDs
   - `tank_display` → I²C → 1.3" SH1106 OLED face on chassis
   - `tank_dashboard` → WebSocket → browser UI face
5. **Feel-good Loop**: Subscribe to `/meta/decision_append_result` — on success, inject 5s "happy" spike
6. **Hysteresis**: Emotion doesn't flip on every message; requires sustained signal to switch

### Companion Engine

The companion module (`companion.py`) is the decision engine that:
- Maps emotions to appropriate physical/speech responses
- Handles safety-flagged emotions (fear, anger, jealousy → escalate to operator)
- Generates dialogue patterns based on current emotional state
- Manages the transition between emotions smoothly

---

## 5. 🗣️ Voice & Speech Pipeline

### Wake Word → Intent → Response Flow

```
   Audio In (ReSpeaker mic array)
       │
       ▼
   wake_word_listener (openWakeWord)
       │
       ▼  /wake_detected (Bool, latched)
   stt_node (Whisper)
       │
       ▼  /intent_text (transcribed text)
   intent_router
       │
       ├─► Built-in tasks (via tank_task registry)
       │      • come_to_owner, follow_me, go_to_room
       │      • return_to_dock, status_report, pick_up_trash
       │      • fetch_named_object, find_owner, list_tasks
       │
       ├─► rag_node → meta_node (knowledge lookup)
       │      • Queries tank_meta (code, hardware, decisions, docs)
       │      • Queries tank_memory (episodic/vector recall)
       │      • Composes system + retrieved context prompt
       │
       ├─► llm_node (llama.cpp, local GGUF)
       │      • Generates response from composed context
       │      • Fires /assistant/uncertain if reply < 12 chars
       │      • External LLM fallback (Freebuff/OpenAI/Anthropic) steps in
       │
       └─► emotion_node (classifies emotion from intent + response)
              • Publishes /emotion/state
              • Drives face, eyes, dashboard display
       │
       ▼  /assistant_text
   tts_node (Piper ONNX)
       │
       ▼  /audio_out
   Speaker (3W 8Ω or amplified USB speaker)
```

### Wake Word Edge Cases
- **WakeLatch**: Threshold-based latching with configurable cooldown & window
- **Confidence Filter**: `/wake_confidence` must exceed threshold to trigger
- **Cooldown Period**: Prevents re-trigger within N seconds
- **Wake State Machine**: Separate `wake_state.py` manages transition states

---

## 6. 🔌 AI ↔ Pi Command Bridge (Phase 9 — Port 8082)

### What It Is

A bidirectional HTTP bridge that lets ANY AI coding assistant (Freebuff, Claude, ChatGPT, Codex) command the Tank directly over the network. Think of it as a REST API for robot control.

### Authentication

- **Bearer Token**: `Authorization: Bearer <token>`
- **Source of truth**: `TANK_API_KEYS` env var (JSON dict of `token → role`)
- **Fallback**: Single `TANK_API_KEY` env var
- **Timing-safe**: Uses `secrets.compare_digest` against timing attacks
- **Rate limited**: 60 read/min, 10 write/min per token (configurable, 429 on exceed)

### AI Cheat Sheet

The file `docs/ai-commands.md` is a markdown document that any coding assistant can read to discover the bridge without reading code.

### Available Commands

| Command | Method | Description | Rate Class |
|---------|--------|-------------|------------|
| `estop` | POST | Latch/release hardware e-stop | write |
| `move` | POST | Drive skid-steer for bounded duration (vx ±0.5 m/s, wz ±1.5 rad/s, max 5s) | write |
| `patrol` | POST | Start/pause autonomous patrolling (waypoint/random/pause/stop) | write |
| `dock` | POST | Toggle AprilTag auto-docking | write |
| `capture` | POST | Snap camera frame as base64 JPEG data: URL | read |
| `telemetry` | POST | Aggregate battery/health/estop/emotion snapshot | read |
| `query` | POST | Query tank_meta structured memory (code/hardware/decisions/knowledge) | read |
| `chat` | POST | Send free-form message to local LLM assistant | read |
| `manifest` | GET | Introspect full tool surface (OpenAI tools=[...] format) | - |
| `audit` | GET | View audit log of recent commands | - |

### Plugin System

Voice-command plugins are auto-discovered from `plugins/` and register themselves into the manifest:
- `chassis_drive.py`, `chassis_turn.py`, `chassis_speed.py`, `chassis_follow.py`
- `vision_detect.py`, `vision_security.py`
- `play_music.py`, `play_youtube.py`, `play_tv.py`, `play_alexa.py`
- `torrent_search.py`, `aria2_add.py`, `aria2_progress.py`
- `vpn.py`, `power.py`, `whereami.py`, `move_to.py`, `find_devices.py`

### External LLM Fallback

When the local llama.cpp produces a short/uncertain reply (`< 12 chars`), the system can fall back to external providers:
- **OpenAIProvider**: GPT-4o-mini / GPT-4o
- **AnthropicProvider**: Claude 3.5 Haiku / Sonnet
- **FreebuffProvider**: OpenAI-shaped, uses Freebuff's hosted models

---

## 7. 🧠 Memory Systems (Three-Layer Architecture)

### Layer 1: Event Memory (tank_memory)

**Purpose:** Records what happened — conversations, commands, observations.

**Technology:**
- **Primary**: `sqlite-vec` (SQLite with vector extension)
- **Fallback**: numpy cosine similarity
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)

**Storage:**
- `memory/event` → stores episodes (turn-by-turn assistant interactions)
- `memory/query` → vector recall with top-k results
- Auto-compaction: periodic cleanup of stale entries
- Export command: `/memory/export_cmd` for JSONL dump

### Layer 2: Structured Coding-Agent Memory (tank_meta)

**Purpose:** Curated knowledge about the robot itself — its code, hardware, decisions, documentation. This is what makes a coding agent self-aware of its own codebase.

**4 Tables in SQLite (meta.db):**

| Table | Rows | Purpose |
|-------|------|---------|
| `code_files` | 88+ | One row per Python file: path, module, purpose, functions, classes, deps, line count, last modified |
| `hardware` | 17 | One row per component: name, kind, bus, pin, driver, notes |
| `decisions` | 6+ | Append-only log: DEC-001 through DEC-NNN with problem, reason, solution, result |
| `knowledge` | ~20 | Markdown docs indexed: title, source, path, text, tags |

**ROS Topics:**
- `/meta/code_search` / `/meta/code_search_result`
- `/meta/hardware_lookup` / `/meta/hardware_lookup_result`
- `/meta/decision_search` / `/meta/decision_search_result`
- `/meta/knowledge_query` / `/meta/knowledge_query_result`
- `/meta/index_now` — trigger reindex from CLI

**Design Principles:**
- DB-first persist: write to SQLite FIRST, then JSON file with bounded retries
- ID format validation: `^[A-Z0-9_-]{2,32}$` before any write
- String slicing: every line into prompt/log clipped (~200 chars)
- Thread-safe: one writer at a time via `threading.Lock`

### Layer 3: Event Logger (tank_log)

**Purpose:** Raw, append-only event stream for observability and anomaly detection.

**Schema:**
```sql
CREATE TABLE topic_logs (
    ts        REAL NOT NULL,
    topic     TEXT NOT NULL,
    msgtype   TEXT NOT NULL,
    source    TEXT NOT NULL,
    payload   TEXT,              -- JSON, capped at 8 KB
    truncated INTEGER DEFAULT 0,
    PRIMARY KEY (ts, topic, source)
) WITHOUT ROWID;
```

**Subscribed Topics** (21 system topics):
/cmd_vel, /intent_text, /wake_detected, /assistant_text, /estop,
/security/events/motion, /dock/pose, /dock/charge_cmd, /battery/state,
/health/state, /meta/*_result, /memory/recall_result, and more

**Learner (Anomaly Detection):**
Every 30s, the learner analyzes patterns and flags anomalies by priority:
1. `estop_stuck` — estop latched for > 30s (safety first)
2. `dock_charging_but_health_not_ok` — charging but battery not improving
3. `wake_no_intent` — wake word triggered but no intent followed

---

## 8. 🎨 UI & Display Systems

### Three Visual Outputs

#### 1. ESP32-S3 Round LCD Eyes (Waveshare 1.28" GC9A101)
- 2× round displays, 240×240 px each
- Driven over SPI by ESP32-S3 DevKitC-1 N16R8
- Receives JSON over UART2 from Pi (115200 baud)
- Can show: pupil dilation, blinking, directional gaze, emotional expressions

#### 2. 1.3" SH1106 OLED Face (I²C 0x70)
- Mounted on chassis front
- Pillow bitmaps for: happy, sad, angry, scared, neutral
- Driven by `tank_display.display_node` via `oled_hal.py`
- NullHal fallback for benches/CI (no physical OLED needed)
- CLI test: `python3 -m tank_display.scripts.run_oled --no-luma`

#### 3. Dashboard (FastAPI Web UI)
- **Port:** 8084 (tank_personalize) / 8080 (tank_dashboard)
- **Endpoints:**
  - `GET /api/health` — system health
  - `GET /api/telemetry` — battery, CPU, estop state
  - `GET /api/emotion/{current,history}` — emotion state + timeline
  - `GET /api/recording/list` — security recordings
  - `POST /api/cmd/{estop,move}` — command robot
  - `WS /ws/feed` — real-time JSON stream of /health/state
  - `WS /ws/emotion` — real-time emotion state
- **Features:**
  - Live CSS face animation
  - Persona editing (name, tone, voice, backstory)
  - Preferences management (motion/privacy/audio)
  - User memory browser

### Emotion-Driven Display Flow

```
/emotion/state
    │
    ├─► eye_lcd_bridge ──► UART ──► ESP32-S3 ──► Round LCD Eyes (animated pupils, blinks, gaze)
    │
    ├─► tank_display ──► I²C 0x70 ──► SH1106 OLED Face (bitmap expressions)
    │
    └─► tank_dashboard ──► WebSocket ──► Browser UI Face (CSS animations)
```

---

## 9. ⚙️ Hardware Specifications

### Compute & Brains (~₹17,200)
| Component | Spec | Role |
|-----------|------|------|
| NVIDIA Jetson Orin Nano 8GB | 85×56mm, USB-C PD | Master controller, ROS 2 Humble |
| MicroSD 64GB A2 | Boot drive | Jetson OS |
| M.2 NVMe 256GB | Samsung/WD/Crucial | `/var/lib/tank` for DBs, bags, recordings |
| Jetson M.2 HAT+ | PCIe-Gen2-x1 | Houses NVMe |
| ESP32-S3 DevKitC-1 N16R8 | Dual-core Xtensa LX7 | Eye display driver over SPI |

### Vision & Display (~₹8,400)
| Component | Role |
|-----------|------|
| 2× Waveshare 1.28" Round LCD (GC9A101) | Animated eye expressions |
| 1.3" SH1106 OLED I²C | Status face on chassis |
| Pi Camera Module 3 (IMX708) | Main camera, 1280×960 @ 30fps |

### Motion & Drive (~₹9,650)
| Component | Role |
|-----------|------|
| 2× 12V DC geared motor w/ encoder (JGB37-520) | Drive motors |
| 2× BTS7960 43A motor driver | H-bridge (already owned) |
| Tracked chassis (aluminium, ~15cm wheelbase) | Robot body |
| 2× Tower Pro SG90 micro servo | Pan-tilt camera head |
| PCA9685 16-channel PWM/servo HAT | Servo driver (I²C 0x40) |

### Sensors (~₹9,950)
| Component | Interface | Role |
|-----------|-----------|------|
| RPLidar A1 / LD19 | USB-UART, 115200 baud | 360° LiDAR for SLAM |
| BNO055 9-DOF IMU | I²C 0x28 | Orientation + IMU data |
| 2× INA219 current/voltage | I²C | Battery telemetry (Pi + motor rail) |
| R307/ZFM-708 fingerprint | UART | Biometric security |
| 2× HC-SR04 ultrasonic | GPIO | Obstacle abort |
| 3× DS18B20 waterproof temp | 1-Wire GPIO4 | Battery/motor/chassis temp |

### Audio (~₹4,750)
| Component | Role |
|-----------|------|
| ReSpeaker 4-Mic Array (USB) | Wake word + voice capture |
| USB Audio DAC | Audio output |
| 3W 8Ω speaker | Voice output |
| Mini amplified USB speaker | Dashboard audio |

### Power (Dual Rail)
- **Jetson Rail:** USB-C PD power bank ≥ 27W → Jetson (5V/5A)
- **Motor Rail:** 12V SLA/3S Li-ion → BTS7960 drivers → motors
- **Key Principle:** Isolated grounds to prevent motor spikes from resetting Pi

### Networking
- Jetson onboard Wi-Fi + USB Wi-Fi 6 adapter
- Quectel EC25/SIM7600E LTE modem (cellular failover)
- USB Ethernet adapter (wired backhaul preferred)
- WireGuard + Tailscale VPN (installed by provision_pi5.sh)

### Wiring Summary
| Bus | Devices |
|-----|---------|
| I²C (bus 1) | BNO055 (0x28), PCA9685 (0x40), SH1106 OLED (0x70) |
| SPI (bus 0) | Reserved for display variant |
| UART | RPLidar A1 (`/dev/ttyUSB0`), ESP32-S3 (`/dev/ttyAMA0`) |
| GPIO | DIR/PWM for motors (17,18,27,22), E-STOP LED (25) |

---

## 10. 🔄 Phase Roadmap (Current Status)

| Phase | Theme | Status | What Ships |
|-------|-------|--------|------------|
| **P1** | Foundation, Motion, Vision | ✅ **Done** | Motor control, kinematics, IMU, LiDAR, camera, watchdog, bringup |
| **P2** | Eyes, Tracker, SLAM | ✅ **Done** | ESP32-S3 eye firmware, YOLO tracker, slam_toolbox 2D, RTAB-Map 3D |
| **P3** | Networking, NAS | ✅ **Done** | Samba, WebDAV, rclone auto-backup, WireGuard, Tailscale |
| **P4** | Security + Dock + Power | ✅ **Partial** | Motion detection, video recording, event logger, AprilTag dock, health |
| **P5** | Voice + Assistant + Memory | ✅ **Done** | Wake word, Whisper STT, Piper TTS, LLM, RAG, vector memory, dashboard |
| **P5½** | Emotion Fan-out | ✅ **Done** | Emotion → eyes + OLED + dashboard, feel-good loop, decay |
| **P6** | Coding-Agent Memory | ✅ **Done** | tank_meta: AST code index, hardware, decisions, knowledge, meta_node |
| **P6½** | Event Logger + Learner | ✅ **Done** | Append-only log, anomaly detection, topic summary, learner |
| **P7** | Autonomous Patrolling | ✅ **Done** | Waypoint + random patrol, AI surveillance fusion |
| **P8** | Real Hardware Deploy | ⏳ **Next** | On-robot validation, contactor wiring |
| **P9** | AI ↔ Pi Bridge | ✅ **Done** | Port 8082 command bridge, bearer auth, rate limit, manifest, external LLM |
| **P10** | Voice Task Framework | ✅ **Done** | 9 sample tasks + registry, BaseTask class |
| **P10½** | AI Humanness | ✅ **Done** | Persona, preferences, user memory, dialogue patterns, full dashboard |

---

## 11. 🧪 Testing & Validation

### Current Test Count: 87+ tests

| Package | Tests | Status |
|---------|-------|--------|
| tank_motion | 12 | ✅ All pass |
| tank_vision | 8 | ✅ All pass |
| tank_speech | 6 | ✅ All pass |
| tank_memory | 9 | ✅ All pass |
| tank_meta | 14 | ✅ All pass |
| tank_log | 7 | ✅ All pass |
| tank_display | 7 | ✅ All pass |
| tank_command_bridge | 19 | ✅ All pass |
| tank_emotions | 12+ | ✅ All pass |
| tank_personalize | 10+ | ✅ All pass |

### Workspace: 93/93 Python files compile OK
### Shell scripts: `bash -n` passes

### Smoke Test Suite (156+ host-level CLIs)
The `scripts/` directory contains 60+ Python CLIs with 206+ subcommands (F001–F206) covering:
- Diagnostics (battery, IMU, LiDAR, camera, Wi-Fi, audio, watchdog, ROS)
- Calibration (IMU, camera, pan-tilt, LiDAR, battery, track-width)
- Recording & Replay (topics, audit log, manifest, smoke tests)
- Networking (Wi-Fi, bandwidth, VPN/LTE)
- Audio (wake word, TTS, STT)
- Vision (YOLO, AprilTag)
- Meta & Backup (meta DB health, snapshot, restore, NAS push)
- Linting (Python, shell, YAML/JSON)
- Systemd service management
- Log analysis

---

## 12. 🔑 Key Design Rules (From Code Reviews)

These rules were enforced across all phases and must be maintained:

1. **ROS Callback Groups**: Every node with multiple subscribers uses `MutuallyExclusiveCallbackGroup` to prevent starvation
2. **DB-first Persist**: Write to durable store first, then derived stores with bounded retries
3. **ID Format Validation**: Everything that becomes a primary key must pass regex `^[A-Z0-9_-]{2,32}$` before any write
4. **String Slicing**: Every line into prompt or log should be clipped (~200 chars), composites capped (~4KB)
5. **No Deprecated FastAPI**: Use `lifespan=` manager, not `@app.on_event(...)`
6. **Lazy Singletons**: Wrap initialization in `threading.Lock` + double-checked locking
7. **CLI First**: Every Python module should have a scripts/ entry point before ROS integration
8. **Offline-first**: Every host CLI degrades gracefully when ROS/FastAPI/CUDA is missing
9. **Graceful Hardware Fallback**: All hardware drivers have NullHal/dummy implementations for benches/CI

---

## 13. 📁 Project File Tree

```
├── scripts/                          # 60+ host-level CLIs (206+ subcommands)
│   ├── setup_pi5.sh                  # One-shot Jetson installer
│   ├── provision_pi5.sh              # Idempotent master installer
│   ├── diagnostics.py                # Battery, IMU, LiDAR, camera, Wi-Fi, audio
│   ├── calibrate.py                  # IMU, camera, pan-tilt, LiDAR, battery, track
│   ├── recorder.py                   # Topic, audit, manifest, smoke, replay
│   ├── phase_runner.py               # P1–P10½ validator (F151–F156)
│   └── ...50+ more...
├── docs/
│   ├── ai-commands.md                                   # AI cheat sheet for the bridge
│   ├── complete-project-definition-for-chatgpt.md       # ← THIS FILE
│   ├── tankos-spec.md                                   # TankOS Build Specification
│   ├── tankos-module-definitions-ai-powered.md          # 35 AI-Powered Modules
│   ├── tankos-ai-self-learning-modules-brief.md         # 29 Self-Learning Engines
│   ├── tankos-cognitive-architecture.md                 # 22 Cognitive Systems
│   └── tankos-ai-evolution-layer.md                     # 28 Original Evolution Engines
├── firmware/
│   └── eyes_esp32/eyes_esp32.ino     # ESP32-S3 eye display firmware
├── cad/chassis_v1_slim/              # CAD files, SCAD, STL, BOM
├── hardware.md                       # Complete BOM with ₹ pricing
├── WIRING.md                         # GPIO pinout, I²C, SPI, UART, power
├── PHASES.md                         # Phase tracker (P1–P10½)
├── ARCHITECTURE.md                   # ASCII topic graph + package table
├── STATUS.md                         # Handoff document with current state
├── README.md                         # Quick start, feature index (F001–F206)
└── tank_ws/                          # ROS 2 Humble colcon workspace
    └── src/
        ├── tank_bringup/             # Launch tree, watchdog, URDF, systemd
        ├── tank_motion/              # Motor control, pan-tilt, kinematics
        ├── tank_sensors/             # IMU + LiDAR publishers
        ├── tank_vision/              # Camera, YOLO tracker, eye bridge
        ├── tank_navigation/          # slam_toolbox 2D + RTAB-Map 3D
        ├── tank_speech/              # Wake word, STT, intent routing
        ├── tank_text/                # Whisper STT + Piper TTS
        ├── tank_assistant/           # LLM, RAG, emotion engine, external LLM
        ├── tank_memory/              # Vector memory (sqlite-vec)
        ├── tank_meta/                # Structured coding-agent memory
        ├── tank_log/                 # Append-only event logger + learner
        ├── tank_learn/               # Discovery store, consolidation
        ├── tank_emotions/            # 26-emotion taxonomy + companion engine
        ├── tank_display/             # OLED face driver
        ├── tank_personalize/         # Persona, preferences, dialogue
        ├── tank_dashboard/           # FastAPI web UI
        ├── tank_dock/                # AprilTag auto-dock
        ├── tank_health/              # Battery + Prometheus exporter
        ├── tank_security/            # Motion detection + recording
        ├── tank_patrol/              # Autonomous patrolling
        ├── tank_command_bridge/      # AI ↔ Pi HTTP bridge (port 8082)
        ├── tank_task/                # Voice task framework
        ├── tank_nas/                 # Samba + WebDAV + auto-backup
        └── tank_neutral/             # Placeholder
└── tank_os/                          # TankOS graphical AI operating environment
    ├── core/                          # Layer 3 — 28+ manager implementations
    │   ├── event_bus.py               # Central publish/subscribe event bus ✅
    │   ├── plugin_manager.py          # Dynamic plugin loader ✅
    │   ├── settings_manager.py        # JSON-persisted settings ✅
    │   ├── theme_engine.py            # Dark/light/custom themes ✅
    │   ├── animation_engine.py        # 60fps tweening, spring physics ✅
    │   ├── hardware_manager.py        # Auto-detects cameras/serial/displays ✅
    │   ├── security_manager.py        # Auth, e-stop, surveillance ✅
    │   ├── robot_manager.py           # Movement, motors, servos, dock ✅
    │   ├── vision_manager.py          # Camera, YOLO, face, AprilTags ✅
    │   ├── memory_manager.py          # Embeddings, episodic recall ✅
    │   └── ...18 more managers
    ├── shell/main.py                  # Layer 4 — PySide6 Tank Shell ✅
    ├── startup/
    │   ├── boot_sequence.py           # 11-step startup orchestrator ✅
    │   └── tank-init.service          # systemd boot service ✅
    ├── install.sh                     # Provisioning installer ✅
    ├── widgets/                       # Reusable widget library (ready for build)
    ├── themes/                        # JSON theme files (built-in themes exist)
    └── plugins/                       # Sample plugins (ready for build)
```

---

## 14. 🚀 Quick Start (How to Work With This Codebase)

### First Time in a New Session
```bash
# 1. Read the handoff document
cat "/root/the tank project/STATUS.md"

# 2. Read the architecture
cat "/root/the tank project/ARCHITECTURE.md"

# 3. Read the phase tracker
cat "/root/the tank project/PHASES.md"

# 4. Explore the workspace
ls "/root/the tank project/tank_ws/src/"

# 5. Run tests on a package
cd "/root/the tank project/tank_ws/src/tank_motion" && python3 -m pytest -v
```

### TankOS — Running and Installing

```bash
# Run TankOS in simulation mode (no Qt required)
cd "/root/the tank project"
PYTHONPATH=. python3 -m tank_os.shell.main

# Run TankOS with Qt GUI (requires PySide6)
TANKOS_QT=1 PYTHONPATH=. python3 -m tank_os.shell.main

# Install TankOS on NVIDIA Jetson Orin Nano
bash tank_os/install.sh --apply

# Start TankOS as a system service
sudo systemctl enable tank-init.service
sudo systemctl start tank-init.service

# View TankOS logs
journalctl -u tank-init.service -f
```

### Key Env Vars to Set
- `TANK_API_KEY` or `TANK_API_KEYS` — for the command bridge auth
- `OPENAI_API_KEY` — for external LLM fallback (OpenAIProvider)
- `ANTHROPIC_API_KEY` — for Anthropic fallback (AnthropicProvider)
- `FREEBUFF_API_KEY` — for Freebuff fallback (FreebuffProvider)

### Running the Bridge (standalone, no ROS)
```bash
cd "/root/the tank project/tank_ws/src/tank_command_bridge"
TANK_API_KEY=test-key python3 -m tank_command_bridge.scripts.run_bridge --bench
```

### Commanding the Tank (from another terminal)
```bash
curl -s http://localhost:8082/api/cmd/manifest | python3 -m json.tool
curl -s -X POST http://localhost:8082/api/cmd/telemetry \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"audit_id":"demo-0001-0001-0001-000000000001","params":{}}'
```

---

## 15. 🎯 Summary for AI Assistants

**When I (an AI assistant) am working on this project, I should:**

1. **Read STATUS.md first** — it's the handoff document with everything shipped
2. **Check ARCHITECTURE.md** — for the ROS topic graph and package map
3. **Use the command bridge** — to command the Tank via HTTP (port 8082)
4. **Query meta store** — ask `/api/cmd/query` for code/hardware/decisions/knowledge
5. **Respect design rules** — DB-first, callback groups, string slicing, etc.
6. **Run tests before/after changes** — pytest in affected packages
7. **Use the phase runner** — `python3 scripts/phase_runner.py run --soft` to validate
8. **Check existing CLIs** — 206+ subcommands exist; don't reimplement
9. **Don't assume hardware** — all hardware drivers have NullHal fallbacks
10. **Default to port 8082** — for AI ↔ Pi communication (not 8080)

---

## 16. 🖥️ TankOS — Graphical AI Operating Environment

> **TankOS is not a replacement Linux kernel.** It is a complete operating environment that boots automatically on NVIDIA Jetson Orin Nano and becomes the only interface the user sees. Linux exists only as the hardware abstraction layer.

TankOS is a full PySide6/Qt6 graphical environment replacing the Jetson desktop, designed to be:
- **AI-first**: Every subsystem is AI-aware and AI-coordinated
- **Voice-first**: Wake word → STT → AI → TTS pipeline as primary interaction
- **Touch-first**: Optimized for 7-inch DSI touchscreen
- **Offline-first**: All AI runs locally (llama.cpp, Whisper, Piper, YOLO)
- **ROS2-native**: Communicates exclusively through ROS topics and existing bridge APIs

### Four-Layer Architecture

| Layer | Name | Contents |
|-------|------|----------|
| **Layer 1** | Linux | Drivers, networking, audio, USB, Bluetooth, power, Jetson hardware |
| **Layer 2** | ROS2 | Existing 16 packages unchanged: tank_motion, tank_vision, tank_assistant, tank_navigation, tank_security, tank_health, tank_dashboard, tank_meta, tank_display, tank_patrol, tank_task, tank_personalize, tank_command_bridge, etc. |
| **Layer 3** | TankOS Core | Application Manager, Plugin Manager, Notification Manager, Permission Manager, Display Manager, Theme Manager, Voice Manager, Window Manager, Settings Manager, Update Manager, Power Manager, Hardware Manager, Event Bus, AI Manager |
| **Layer 4** | Tank Shell | The full-screen Qt6 GUI — Home, AI Chat, Camera, Navigation, Memory, Security, Patrol, Files, Diagnostics, Developer Mode, Settings, Power, Updates screens |

### Boot Process
```
Power On → Pi Firmware → Linux Kernel → systemd → tank-init.service
→ Hardware Detection → ROS2 Core → TankOS Core → Tank Shell → Dashboard
```
No Jetson desktop should ever appear.

### Tank Shell Screens

| Screen | Purpose |
|--------|---------|
| Home | Dashboard with camera, AI avatar, map, status |
| AI Chat | Conversational LLM interface |
| Camera | Live camera with YOLO detections |
| Navigation | SLAM map, robot position, waypoint editor |
| Memory | Chat history, long-term memory, vector search |
| Security | Live camera, motion detection, recordings |
| Patrol | Waypoint and random patrol routes |
| Files | File browser and storage management |
| Diagnostics | CPU, RAM, disk, battery, ROS nodes |
| Developer | ROS topic viewer, node manager, API tester |
| Settings | Network, audio, voice, AI, personality, privacy |
| Power | Battery, sleep, shutdown, performance modes |
| Updates | Software update checking and installation |

---

## 17. 🧩 TankOS Module Architecture (35 AI-Powered Modules)

TankOS is composed of 35 AI-powered modules that coordinate through the Event Bus. Each module has an AI dimension — from AI-driven initialization to AI-assisted recommendations.

### Core & Shell
| # | Module | AI-powered purpose |
|---|--------|-------------------|
| 1 | TankOS Core | AI-driven core that initializes, coordinates, and intelligently manages every subsystem |
| 2 | Tank Shell | AI-first desktop that adapts layout, widgets, and interactions based on behavior and context |
| 3 | AI Manager | Master intelligence for reasoning, planning, memory, tool use, multimodal understanding |
| 4 | AI Agent Framework | Hosts specialized agents (Navigation, Vision, Security, Coding, Health, Companion) |
| 5 | AI Skills & Tools Manager | Registers every capability as AI-callable tools with permission schemas |

### Application & Plugin Management
| # | Module | Purpose |
|---|--------|---------|
| 6 | Application Manager | AI-organizes, launches, optimizes, and recovers applications |
| 7 | Plugin Manager | Loads AI plugins dynamically, sandboxes execution, auto-discovers capabilities |

### Perception & Interaction
| # | Module | Purpose |
|---|--------|---------|
| 8 | Voice Manager | Multilingual, emotion-aware speech, wake-word, interruption handling |
| 9 | Vision Manager | YOLO, OCR, facial recognition, object tracking, scene understanding |
| 10 | Memory Manager | Short-term, long-term, episodic, semantic, procedural, vector memory |
| 11 | Emotion Manager | Emotional state, personality, empathy, mood transitions, expression sync |

### Robot Control & Navigation
| # | Module | Purpose |
|---|--------|---------|
| 12 | Robot Manager | Coordinates motion, servos, docking, patrols through AI planning |
| 13 | Navigation Manager | SLAM, localization, path planning, obstacle avoidance, waypoints |

### Hardware & System
| # | Module | Purpose |
|---|--------|---------|
| 14 | Hardware Manager | AI-powered discovery, configuration, monitoring, failure diagnosis |
| 15 | Power Manager | AI-predicts battery life, optimizes energy, manages charging |
| 16 | Resource Manager | AI-allocates CPU, GPU, RAM, storage, network bandwidth dynamically |
| 17 | Network Manager | AI-optimizes Wi-Fi, Ethernet, LTE, VPN, failover, bandwidth |
| 18 | Storage Manager | AI-manages files, databases, backups, deduplication, compression |

### Security & Safety
| # | Module | Purpose |
|---|--------|---------|
| 19 | Security Manager | AI-powered intrusion detection, surveillance, face/fingerprint auth |
| 20 | Display Manager | AI-generated adaptive interfaces across touchscreen, OLED, eyes |
| 21 | Window Manager | AI-assisted multitasking, floating windows, gestures, workspaces |
| 22 | Dashboard Manager | Real-time AI command center: health, telemetry, cameras, maps |
| 23 | Notification Manager | AI-intelligent alerts, priority, urgency prediction, voice delivery |

### Automation & Assistant
| # | Module | Purpose |
|---|--------|---------|
| 24 | Automation Manager | AI-learns routines, creates workflows, schedules autonomous behaviors |
| 25 | Assistant Interface | Unified conversational interface: voice, touch, keyboard, gestures |

### Infrastructure
| # | Module | Purpose |
|---|--------|---------|
| 26 | Event Bus | AI-aware publish/subscribe connecting ROS, apps, hardware, plugins, agents |
| 27 | System API | Secure APIs for AI agents, apps, plugins, mobile, web dashboards |
| 28 | Developer Manager | AI-assisted coding, debugging, ROS inspection, profiling |
| 29 | Diagnostics Manager | AI-predictive health monitoring, fault isolation, troubleshooting |
| 30 | Recovery Manager | AI-automatic failure detection, safe mode, rollback, crash recovery |
| 31 | Update Manager | AI-validates compatibility, tests in isolation, safe install + revert |
| 32 | Theme Manager | AI-generates adaptive themes, animations, colors reflecting preferences |
| 33 | Settings Manager | AI-recommended configuration for hardware, AI, networking, privacy |
| 34 | Permission Manager | AI-enforced fine-grained access control with role-based security |
| 35 | Boot Manager | AI-warm-up, secure boot, splash animations, no Linux desktop exposed |

---

## 18. 🧠 TankOS Cognitive Architecture (22 Systems)

The Cognitive Architecture describes HOW TankOS thinks — the internal mental processes that transform sensor data into intelligent action.

| # | System | Function |
|---|--------|----------|
| 1 | **Perception System** | Fuses camera, microphone, LiDAR, IMU, touch, thermal, battery, network into unified world state |
| 2 | **Attention System** | Prioritizes events by urgency/danger/user interaction, allocates processing resources |
| 3 | **Working Memory** | Temporary storage for active conversations, navigation, reasoning — discarded when irrelevant |
| 4 | **Long-Term Memory** | Permanent indexed storage for conversations, experiences, locations, objects, skills, maps |
| 5 | **Learning System** | Learns from every action, observation, success, failure — continuously updates knowledge |
| 6 | **Reasoning System** | Analyzes information, retrieves memories, compares solutions, predicts outcomes, generates plans |
| 7 | **Planning System** | Breaks goals into tasks, schedules execution, monitors progress, adapts and replans |
| 8 | **Decision System** | Selects optimal actions considering goals, safety, emotion, confidence, resources |
| 9 | **Prediction System** | Anticipates user intentions, hardware failures, battery depletion, obstacles, future events |
| 10 | **Curiosity System** | Identifies knowledge gaps, explores environments, researches topics during idle time |
| 11 | **Creativity System** | Combines knowledge, memories, skills to generate novel solutions and strategies |
| 12 | **Emotion System** | Internal emotional model influencing speech, expressions, decisions — safety-constrained |
| 13 | **Self-Reflection System** | Reviews completed tasks, evaluates performance, extracts lessons, sets improvement goals |
| 14 | **Metacognition System** | Monitors own thinking — estimates confidence, detects uncertainty, validates conclusions |
| 15 | **Self-Model System** | Complete awareness of hardware config, software status, capabilities, limitations |
| 16 | **World Model System** | Continuously updated digital twin of environment: maps, rooms, objects, people, zones |
| 17 | **Social Intelligence System** | Learns user identities, communication styles, emotional preferences, relationships |
| 18 | **Skill Learning System** | Converts repeated task sequences into reusable optimized skills |
| 19 | **Knowledge Validation System** | Confidence scoring, cross-validation, conflict detection before permanent storage |
| 20 | **Goal Management System** | Maintains short/long-term objectives, resolves conflicts, tracks progress |
| 21 | **Safety & Ethics System** | Evaluates every action against safety rules, permissions, hardware limits, ethics |
| 22 | **Cognitive Coordinator** | Executive brain synchronizing all 21 systems into unified cognitive architecture |

---

## 19. 📚 TankOS AI Self-Learning System (29 Engines)

The Self-Learning System enables TankOS to continuously improve through experience without manual retraining.

### Core Learning
| # | Engine | Function |
|---|--------|----------|
| 1 | AI Learning Core | Central continuous learning from conversations, sensors, tasks, code, experiences |
| 2 | Experience Engine | Records every interaction, observation, command, event as structured experiences |
| 3 | Knowledge Graph | Connects people, places, objects, tasks into intelligent relationship graph |
| 4 | Long-Term Memory Consolidator | Daily review — removes duplicates, summarizes, stores permanently |
| 5 | Continuous Learning Engine | Automatic learning from successful and failed actions |

### Behavior & Preference Learning
| # | Engine | Function |
|---|--------|----------|
| 6 | Habit Learning Engine | Identifies routines, schedules, repeated behaviors for proactive assistance |
| 7 | Preference Learning Engine | Learns communication style, personality, favorite commands, interaction patterns |
| 8 | Autonomous Skill Builder | Combines tools into reusable workflows after repeated successful execution |

### Optimization & Evaluation
| # | Engine | Function |
|---|--------|----------|
| 9 | Task Optimization Engine | Analyzes and improves execution speed, accuracy, resource efficiency |
| 10 | Self-Evaluation Engine | Scores performance, identifies mistakes, generates improvements |
| 11 | Mistake Learning Engine | Stores failures, identifies root causes, prevents repetition |

### World & Prediction Models
| # | Engine | Function |
|---|--------|----------|
| 12 | World Model Engine | Evolving understanding of rooms, objects, people, devices, environment |
| 13 | Predictive Intelligence Engine | Predicts user intentions, battery, maintenance, hardware failures |
| 14 | Curiosity Engine | Safely explores new devices, environments, capabilities during idle time |
| 15 | Research Engine | Searches trusted sources, validates, summarizes, expands knowledge base |

### Domain-Specific Learning
| # | Engine | Function |
|---|--------|----------|
| 16 | Code Learning Engine | Learns from source code, docs, architecture changes, test results |
| 17 | Robotics Learning Engine | Improves navigation, docking, manipulation, tracking through experience |
| 18 | Vision Learning Engine | Learns new objects, faces, gestures, environments over time |
| 19 | Conversation Learning Engine | Improves dialogue quality, context understanding, natural communication |
| 20 | Emotion Adaptation Engine | Learns appropriate emotional responses, maintains safe personality |
| 21 | Multi-Agent Learning Engine | Specialized agents share knowledge, review solutions, learn collaboratively |

### Consolidation & Improvement
| # | Engine | Function |
|---|--------|----------|
| 22 | Daily Reflection Engine | Daily summary of activities, lessons, memory updates, improvement goals |
| 23 | Weekly Knowledge Consolidation | Deep optimization — merges duplicates, strengthens, removes outdated info |
| 24 | Self-Improvement Engine | Analyzes OS performance, recommends optimizations, tunes configs |
| 25 | AI Performance Analyzer | Measures reasoning quality, learning progress, accuracy, efficiency |
| 26 | Autonomous Goal Manager | Creates long-term learning objectives, tracks progress, prioritizes |

### Safety & Transparency
| # | Engine | Function |
|---|--------|----------|
| 27 | Knowledge Validation Engine | Confidence scoring, contradiction detection, prevents incorrect permanent knowledge |
| 28 | Explainability Engine | Records reasoning behind AI decisions and learning outcomes |
| 29 | Learning Scheduler | Schedules learning, reflection, optimization without affecting real-time performance |

---

## 20. 🛠️ TankOS Implementation Status

### tank_os/ Directory Structure
```
tank_os/
├── core/                           # Layer 3 — 28+ manager implementations
│   ├── event_bus.py                # Central publish/subscribe event system ✅
│   ├── plugin_manager.py           # Dynamic plugin loading with manifest.json ✅
│   ├── plugin_api.py               # Base Plugin class for all plugins ✅
│   ├── settings_manager.py         # JSON-persisted settings with defaults ✅
│   ├── theme_engine.py             # Dark/light/custom themes, CSS generation ✅
│   ├── animation_engine.py         # 60fps tweening, spring physics, particles ✅
│   ├── hardware_manager.py         # Auto-detects cameras, serial, displays, audio ✅
│   ├── display_manager.py          # Brightness, blanking, DSI/HDMI ✅
│   ├── window_manager.py           # Floating windows, fullscreen, touch gestures ✅
│   ├── power_manager.py            # Battery monitoring, sleep, performance modes ✅
│   ├── notification_manager.py     # Animated priority notifications with speech ✅
│   ├── security_manager.py         # Auth, e-stop, surveillance, fingerprint ✅
│   ├── recovery_manager.py         # Crash recovery, safe mode, watchdog, backups ✅
│   ├── diagnostics_manager.py      # CPU/RAM/disk/temp/ROS/logs diagnostics ✅
│   ├── network_manager.py          # Wi-Fi, Ethernet, LTE, Bluetooth, VPN ✅
│   ├── storage_manager.py          # NVMe, SD card, backups, cloud sync ✅
│   ├── robot_manager.py            # Unified movement, motors, servos, dock, patrol ✅
│   ├── vision_manager.py           # Camera, YOLO, face, AprilTags, tracking ✅
│   ├── navigation_manager.py       # SLAM, waypoints, path planning ✅
│   ├── memory_manager.py           # Conversations, embeddings, episodic recall ✅
│   ├── emotion_manager.py          # Emotional state, personality, decay ✅
│   ├── voice_manager.py            # Wake word, STT, TTS integration (stub) 🔧
│   ├── ai_manager.py               # Local/external LLM provider (stub) 🔧
│   ├── permission_manager.py       # Role-based access control (stub) 🔧
│   ├── application_manager.py      # App discovery and lifecycle (stub) 🔧
│   └── update_manager.py           # Update checking and install (stub) 🔧
├── shell/                          # Layer 4 — Tank Shell
│   └── main.py                     # PySide6 entry point with simulation fallback ✅
├── startup/                        # Boot & system integration
│   ├── boot_sequence.py            # 11-step startup orchestrator ✅
│   └── tank-init.service           # systemd service (replaces Pi desktop) ✅
├── install.sh                      # Provisioning installer script ✅
├── widgets/                        # Reusable widget library (empty — ready for build)
├── themes/                         # JSON theme files (empty — built-in themes exist)
├── plugins/                        # Sample plugins (empty — ready for build)
├── services/                       # Background services (empty — ready)
├── voice/                          # Voice processing (empty — stub exists)
├── ai/                             # AI integration (empty — stub exists)
├── diagnostics/                    # (empty — ready for build)
├── recovery/                       # (empty — ready for build)
├── tests/                          # Unit tests (empty — ready for build)
└── docs/                           # Documentation
```

### Status Summary
- **28+ manager implementations** in `tank_os/core/` — 22 fully built, 5 stubs ready for expansion
- **Tank Shell entry point** — PySide6 with NullHal simulation fallback
- **Boot sequence** — 11-step startup orchestrator with systemd service
- **Installer** — Full provisioning script compatible with `provision_pi5.sh`
- **All imports verified** — `from tank_os.core import *` and `tank_os.shell.main` pass cleanly
- **All managers follow singleton pattern** with `threading.Lock`, EventBus integration, graceful degradation

---

## 21. 📋 Complete Spec Document Index

All TankOS specification documents saved in `docs/`:

| Document | Path | Sections |
|----------|------|----------|
| TankOS Complete Build Specification | `docs/tankos-spec.md` | Base platform, boot, architecture, shell, dashboard, plugins |
| TankOS AI-Powered Module Definitions | `docs/tankos-module-definitions-ai-powered.md` | 35 AI-powered module definitions |
| TankOS AI Self-Learning Modules | `docs/tankos-ai-self-learning-modules-brief.md` | 29 self-learning engines |
| TankOS Cognitive Architecture | `docs/tankos-cognitive-architecture.md` | 22 cognitive systems |
| TankOS AI Evolution Layer | `docs/tankos-ai-evolution-layer.md` | 28 original evolution engines |

---

*Generated from STATUS.md, ARCHITECTURE.md, PHASES.md, README.md, hardware.md, WIRING.md, and all 16 ROS 2 packages in the project. Extended with TankOS specifications and `tank_os/` implementation status.*
