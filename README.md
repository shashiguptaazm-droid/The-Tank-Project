# The Tank Project

> A tracked AI robot — Raspberry Pi 5 + ROS2 Humble + Python + **TankOS GUI**.

An emotionally-aware, always-on, voice-operated AI-companion robot with a complete
graphical operating environment (**TankOS**) that replaces the Raspberry Pi desktop.

```
the tank project/
├── tank_ws/src/                # the ROS2 colcon workspace (16 packages)
├── tank_os/                    # TankOS — graphical AI operating environment
│   ├── core/                   # 28+ AI-powered manager implementations
│   │   ├── ai_manager.py       #   Provider registry + dispatch
│   │   ├── evolution_bridge.py #   [NEW] Bridges 14 evolution providers into AIManager
│   │   └── local_llm_provider.py#  [NEW] Offline GGUF inference adapter
│   ├── shell/                  # PySide6 Tank Shell (replaces Pi desktop)
│   ├── internet/               # Simple Internet — universal downloader & search
│   │   ├── server.py           #   FastAPI REST API + web dashboard (:8900)
│   │   ├── downloader.py       #   Multi-protocol download engine (aria2, yt-dlp)
│   │   ├── search.py           #   Search aggregation (web, YouTube, torrents)
│   │   ├── manager.py          #   Unified InternetManager
│   │   ├── cli.py              #   15-command CLI for headless operation
│   │   └── voice_plugin.py     #   6 voice commands for TankOS
│   ├── startup/                # Boot sequence + systemd service
│   └── install.sh              # Provisioning installer
├── scripts/                    # 60+ host-level CLIs (206+ subcommands)
│   ├── model_auto_finder.py    # [NEW] Discover LLM models from provider APIs
│   ├── model_rotation.py       # [NEW] Test provider rotation with circuit breakers
│   └── tankos_setup.sh         # Auto-download & verification script
├── tank_ws/src/tank_assistant/tank_assistant/evolution/
│   ├── model_discovery.py      # [NEW] Auto-discover models from 9 provider APIs
│   ├── concrete.py             # [FIXED] 14 provider classes with current model names
│   ├── registry.py             # [FIXED] Gemini re-enabled
│   └── orchestrators/rotation.py  # Rotation orchestrator with circuit breakers
├── .freebuff_bootstrap.md      # [NEW] Next-session resume instructions
├── SESSION_LOG.md              # [NEW] Comprehensive session documentation
├── docs/                       # Architecture, phases, wiring, TankOS specs
├── firmware/                   # ESP32-S3 eye display firmware
└── cad/                        # 3D-printable chassis CAD files
````

## TankOS — Graphical AI Operating Environment

## Documentation

Companion docs in `docs/`:

- [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) - canonical software & Python dependency manifest for the Simple Internet application layer (apt + brew + pip + Raspberry Pi add-ons).
- [`docs/SIMPLE_INTERNET_ARCH.md`](docs/SIMPLE_INTERNET_ARCH.md) - module-by-module architecture write-up: User Interfaces, Core Service, Download Engine, Media Resolver, Post-Processing, Search & Discovery, Scheduler, Security/Privacy, Storage, Plugin System, Cloud/Remote.


TankOS is a **complete PySide6/Qt6 graphical operating environment** that:
- Boots automatically via `tank-init.service` — no Pi desktop ever appears
- Provides 13 full-screen apps: Home, AI Chat, Camera, Navigation, Memory, Security, Patrol, Files, Diagnostics, Developer, Settings, Power, Updates
- Runs all AI locally (llama.cpp, Whisper STT, Piper TTS, YOLOv8n, openWakeWord)
- Uses a 4-layer architecture: Linux → ROS2 → TankOS Core → Tank Shell
- Communicates through a centralized Event Bus (no direct component coupling)
- Features 35 AI-powered managers: Event Bus, Plugin System, Theme Engine, Animation Engine, Robot Manager, Vision Manager, Memory Manager, Emotion Manager, Security Manager, and 26 more
- Includes a 22-system Cognitive Architecture (Perception, Attention, Reasoning, Planning, Decision, Learning, Memory, Emotion, Metacognition, etc.)
- Has a 29-engine Self-Learning System for continuous improvement

## TankOS Preload Manager — Fully Offline Operation

TankOS includes a **Preload Manager** that automatically downloads, verifies,
installs, and configures all required software, AI models, libraries, firmware,
and system packages during initial setup. After installation, TankOS is fully
functional offline except for optional cloud services.

**59 dependencies across 11 categories:**

| Category | Items | Examples |
|----------|-------|---------|
| AI Runtime | 5 | llama.cpp, ONNX Runtime, FAISS, Sentence Transformers |
| Speech AI | 7 | Whisper (tiny/base), Piper TTS, openWakeWord, noise suppression |
| Vision AI | 6 | YOLOv8 (nano/small), Face Recognition, AprilTag, OCR, Hand Tracking |
| Local LLMs | 5 | Primary (Phi-3 2.3B), Fallback (TinyLlama 1.1B), Code Gen (Qwen2.5-Coder 1.5B), Vision (Qwen2-VL 7B), MMProj |
| Navigation | 4 | SLAM Toolbox, RTAB-Map, Nav2, Cartographer |
| Robot Drivers | 9 | Camera, LiDAR, Motor, IMU, OLED, Servo, Audio, USB rules, ESP32 firmware |
| System Packages | 8 | ROS2 Humble, FFmpeg, OpenCV, GStreamer, Nginx, SQLite, Build tools, Docker |
| Developer Tools | 4 | VS Code Server, ROS utils, Profilers, Testing framework |
| Recovery | 3 | Backup utilities, Rollback packages, Emergency boot |
| Offline Assets | 5 | Icons, Fonts, Sounds, Boot animation, Avatar |
| AI Knowledge | 4 | Hardware DB, System prompts, Tool definitions, Command registry |

**Total size:** ~8.6 GB (AI models make up ~8 GB)

**Usage:**
```bash
# Start background download in terminal
cd "/root/the tank project"
nohup python3 -c "
from tank_os.core.preload_manager import PreloadManager
pm = PreloadManager()
pm.initialize()
pm.download_all()
" > /tmp/preload.log 2>&1 &
```

**Auto-download on boot:**
The PreloadManager initializes automatically when TankOS starts. If online
and missing dependencies, it downloads them in a **background thread** without
blocking the GUI. Progress is reported via EventBus events.

**Monitor download status:**
```bash
# Check download log
tail -f /tmp/llm_download_nohup.log

# Check preload status (in simulation mode)
python3 -m tank_os.shell.main
# Then type:  preload
```

**Python API:**
```python
from tank_os.core.preload_manager import PreloadManager

pm = PreloadManager()
pm.initialize()          # Scan what's installed
pm.download_required()   # Download only critical items
pm.download_all()        # Download everything (~8.6 GB)
pm.download_category("llm")  # Download a specific category
pm.print_report()        # Show detailed status
```

> **TankOS is not a replacement Linux kernel.** Linux exists only as the hardware abstraction layer. TankOS is the only interface the user sees.

```bash
# Run TankOS in simulation mode
PYTHONPATH=. python3 -m tank_os.shell.main

# Run with Qt GUI (requires PySide6)
TANKOS_QT=1 PYTHONPATH=. python3 -m tank_os.shell.main

# SINGLE COMMAND — Install EVERYTHING on Pi 5
sudo bash tank_os/install.sh --apply

# Install without AI models (run later with internet)
sudo bash tank_os/install.sh --apply --skip-models

# Legacy scripts still work (they delegate)
sudo bash scripts/setup_pi5.sh --apply
sudo bash scripts/provision_pi5.sh --apply
```

The unified installer (`tank_os/install.sh`) does it all in 12 steps:
1. **Platform detection** — Pi vs x86, RAM, disk space
2. **Hardware config** — I2C, SPI, UART, RPLidar udev rules
3. **System packages** — 24 apt packages (Qt6, Docker, ROS2, ffmpeg, etc.)
4. **ROS2 Humble** — base + slam-toolbox + colcon
5. **Python packages** — 22 pip packages (PySide6, OpenCV, ultralytics, etc.)
6. **PYTHONPATH** — /etc/environment + profile script
7. **Data directories** — /var/lib/tank_os/models/ for all AI models
8. **TankOS config** — default settings.json
9. **Optional services** — Tailscale, MQTT, Samba
10. **AI Model downloads** — PreloadManager (~8 GB, resumable)
11. **Systemd service** — tank-init.service for autoboot
12. **Verification** — 9-point check

---

## Quick start

```bash
# 1.  SINGLE COMMAND — install EVERYTHING on Pi 5 (hardware, system, AI models, service)
sudo bash tank_os/install.sh --apply

# 2.  Launch TankOS graphical environment
TANKOS_QT=1 python3 -m tank_os.shell.main

# Or launch in simulation mode (no display required)
python3 -m tank_os.shell.main

# 3.  On a Pi 5 — TankOS boots automatically at startup via tank-init.service
systemctl start tank-init.service

# 4.  ROS2 workspace (for development / direct robot control)
cd "tank_ws"
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y 2>/dev/null
colcon build --symlink-install
source install/setup.bash
ros2 launch tank_bringup robot.launch.py
```

> **Legacy scripts** `scripts/setup_pi5.sh` and `scripts/provision_pi5.sh` still work — they now delegate to the unified `tank_os/install.sh`.

## Phase 1 scope

Components live in this commit:

| Subsystem       | Node                       | Topic(s)                                |
|-----------------|----------------------------|-----------------------------------------|
| Motion          | `motor_controller`         | `/cmd_vel → /odom`, `/motor_status`     |
| Motion          | `pan_tilt_controller`      | `/pan_tilt_cmd → /pan_tilt_state`       |
| Vision          | `camera_publisher`         | `/camera/image_raw`, `/camera/camera_info` |
| Sensors         | `imu_publisher`            | `/imu/data`, `/imu/mag`, `/imu/calib`   |
| Sensors         | `lidar_publisher`          | `/scan` (sensor_msgs/LaserScan)         |
| Safety          | `safety_watchdog`          | `/operator/ping → /estop` (latched)     |

See [`PHASES.md`](PHASES.md) for the full roadmap and [`ARCHITECTURE.md`](ARCHITECTURE.md)
for the node/topic graph and velocity command chain.

## Host utilities — 50 new upgrade features

The `scripts/` directory now ships **15 host-level CLIs** with a combined
**50 subcommands** for day-2 robot maintenance. Every command is offline-first
(gracefully degrades when ROS 2 / FastAPI / CUDA are missing), uses stdlib +
argparse, and emits output a human can paste into a run-book.

### Feature index (F001 – F050)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F001 | Robotics battery health probe | `diagnostics.py`            | `battery`         | `python3 scripts/diagnostics.py battery` |
| F002 | IMU zero-offset / sanity check        | `diagnostics.py`            | `imu`             | `python3 scripts/diagnostics.py imu` |
| F003 | LiDAR frame verification              | `diagnostics.py`            | `lidar`           | `python3 scripts/diagnostics.py lidar --port /dev/rplidar` |
| F004 | Camera frame grab + size report       | `diagnostics.py`            | `camera`          | `python3 scripts/diagnostics.py camera --device 0` |
| F005 | Wi-Fi SSID / RSSI / channel probe     | `diagnostics.py`            | `wifi`            | `python3 scripts/diagnostics.py wifi` |
| F006 | Audio device listing (input / output) | `diagnostics.py`            | `audio`           | `python3 scripts/diagnostics.py audio` |
| F007 | Watchdog liveness + heartbeat          | `diagnostics.py`            | `watchdog`        | `python3 scripts/diagnostics.py watchdog --seconds 10` |
| F008 | ROS 2 topic / node liveness rollup     | `diagnostics.py`            | `ros`             | `python3 scripts/diagnostics.py ros` |
| F009 | 5 V / 12 V rail probe (sysfs)          | `diagnostics.py`            | `power`           | `python3 scripts/diagnostics.py power` |
| F010 | E-stop strobe / latch test            | `diagnostics.py`            | `strobe`          | `python3 scripts/diagnostics.py strobe --pin 25` |
| F011 | IMU gyro / accel zero-offset dump      | `calibrate.py`              | `imu`             | `python3 scripts/calibrate.py imu --apply 119 --121 --123` |
| F012 | Camera intrinsics from chessboard      | `calibrate.py`              | `camera`          | `python3 scripts/calibrate.py camera --images ./frames` |
| F013 | Pan-tilt center hunt                  | `calibrate.py`              | `pantilt`         | `python3 scripts/calibrate.py pantilt --degrees 78 102` |
| F014 | LiDAR ramp (motor spin-up)            | `calibrate.py`              | `lidar`           | `python3 scripts/calibrate.py lidar` |
| F015 | Battery discharge curve recorder      | `calibrate.py`              | `battery`         | `python3 scripts/calibrate.py battery --poll 30` |
| F016 | Track-width back-derivation           | `calibrate.py`              | `track`           | `python3 scripts/calibrate.py track --period 12.4` |
| F017 | Topic bus → JSONL recorder            | `recorder.py`               | `topic`           | `python3 scripts/recorder.py topic /battery/state --seconds 60` |
| F018 | Bridge audit-log pull + pretty-print  | `recorder.py`               | `audit`           | `python3 scripts/recorder.py audit --limit 50` |
| F019 | Bridge live manifest dump             | `recorder.py`               | `manifest`        | `python3 scripts/recorder.py manifest` |
| F020 | Bridge end-to-end smoke (estop / move)| `recorder.py`               | `smoke`           | `python3 scripts/recorder.py smoke http://tank.lan:8082` |
| F021 | Replay recorded JSONL                 | `recorder.py`               | `replay`          | `python3 scripts/recorder.py replay ./out.jsonl` |
| F022 | First-boot full audit report          | `cold_start_audit.py`       | `first`           | `python3 scripts/cold_start_audit.py first` |
| F023 | Daily diff report                     | `cold_start_audit.py`       | `daily`           | `python3 scripts/cold_start_audit.py daily` |
| F024 | Wi-Fi latency / AP scan               | `network.py`                | `wifi`            | `python3 scripts/network.py wifi --probe 1.1.1.1` |
| F025 | Bandwidth periodic sampler            | `network.py`                | `bandwidth`       | `python3 scripts/network.py bandwidth --every 5 --count 12` |
| F026 | WireGuard / Tailscale / LTE probe     | `network.py`                | `vpn-lte`         | `python3 scripts/network.py vpn-lte` |
| F027 | Wake-word offline test                | `audio_smoketest.py`        | `wake`            | `python3 scripts/audio_smoketest.py wake --seconds 4` |
| F028 | TTS synth hello                       | `audio_smoketest.py`        | `tts`             | `python3 scripts/audio_smoketest.py tts --text "hello pilot"` |
| F029 | STT decode sample                     | `audio_smoketest.py`        | `stt`             | `python3 scripts/audio_smoketest.py stt ./sample.wav` |
| F030 | YOLO detector probe                   | `vision_smoketest.py`       | `yolo`            | `python3 scripts/vision_smoketest.py yolo ./frame.jpg` |
| F031 | AprilTag dock-tag calibration         | `vision_smoketest.py`       | `apriltag`        | `python3 scripts/vision_smoketest.py apriltag ./dock.jpg` |
| F032 | `tank_meta` sqlite integrity          | `meta_cli.py`               | `health`          | `python3 scripts/meta_cli.py health` |
| F033 | Doc coverage vs disk                  | `meta_cli.py`               | `doc-index`       | `python3 scripts/meta_cli.py doc-index` |
| F034 | Meta DB snapshot                      | `meta_cli.py`               | `db-snapshot`     | `python3 scripts/meta_cli.py db-snapshot` |
| F035 | `data/*.db` snapshot helper           | `backup.py`                 | `snapshot`        | `python3 scripts/backup.py snapshot` |
| F036 | `data/*.db` restore helper            | `backup.py`                 | `restore`         | `python3 scripts/backup.py restore --from ./snap.db` |
| F037 | DB push to NAS mount                  | `backup.py`                 | `push`            | `python3 scripts/backup.py push --mount /mnt/nas` |
| F038 | `pyflakes` + `ast` lint               | `lint.py`                   | `python`          | `python3 scripts/lint.py python tank_ws/src` |
| F039 | `shellcheck` driver                   | `lint.py`                   | `shell`           | `python3 scripts/lint.py shell scripts` |
| F040 | YAML + JSON schema validate           | `lint.py`                   | `yaml`            | `python3 scripts/lint.py yaml tank_ws/src/*/config` |
| F041 | `systemctl` facade for `tank_*`       | `service.py`                | `facade`          | `python3 scripts/service.py facade start tank_meta` |
| F042 | Restart every `tank_*` unit           | `service.py`                | `restart`         | `python3 scripts/service.py restart` |
| F043 | Service status summary                | `service.py`                | `status`          | `python3 scripts/service.py status` |
| F044 | Fast grep across the topic log        | `log.py`                    | `grep`            | `python3 scripts/log.py grep estop` |
| F045 | Topic summary rollup                  | `log.py`                    | `topic-summary`   | `python3 scripts/log.py topic-summary` |
| F046 | Emotion history dump                  | `log.py`                    | `emotion-history` | `python3 scripts/log.py emotion-history --hours 1` |
| F047 | `tank_personalize` prefs dump          | `prefs.py`                  | `prefs`           | `python3 scripts/prefs.py prefs --section audio` |
| F048 | Persona history                       | `prefs.py`                  | `persona`         | `python3 scripts/prefs.py persona` |
| F049 | Prometheus `/metrics` pull            | `prom.py`                   | `metrics`         | `python3 scripts/prom.py metrics http://tank.lan:9100/metrics` |
| F050 | Health scrape (Prometheus + custom)   | `prom.py`                   | `health`          | `python3 scripts/prom.py health` |

### Installation + conventions

* Pure `python3` (no ROS or CUDA required). Heavy deps (`adarlfruit-bno055`,
  `rplidar`, `ultralytics`, etc.) are imported lazily and degrade gracefully.
* Every CLI follows the standard `--help` pattern + exits `0` on success and
  `>=1` on partial failure so they slot into `systemd --user` / cron / tmux
  dashboards.
* Shell scripts keep the `bash -euo pipefail` + `--apply` idempotent pattern
  already used in the unified installer (`tank_os/install.sh`).

### 5-second smoke test

```bash
# Make sure every script at least parses + shows --help.
for s in the\ tank\ project/scripts/{diagnostics,calibrate,recorder,cold_start_audit,network,audio_smoketest,vision_smoketest,meta_cli,backup,lint,service,log,prefs,prom}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

# Read a one-pager map of the upgrade surface (the table above):
grep -E '^\| F0[0-9]' "the tank project/README.md" | wc -l   # -> 50
```

---

## Host utilities — 50 more features (F051 – F100)

A second batch of **15 CLIs** / **50 subcommands** that complement
F001–F050 — focusing on **ROS introspection, training pipeline,
perimeter/power deep-ops, mission planning, OTA, fleet, drift, and UX**.

Conventions are identical (stdlib-first, lazy heavy imports, `--help`,
non-zero exit on failure). They coexist with the F001–F050 set.

### Feature index (F051 – F100)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F051 | One-shot topic publish             | `topic_ops.py`      | `pub`               | `python3 scripts/topic_ops.py pub /cmd_vel '[0.1,0,0]' --once` |
| F052 | Topic freq / hz probe              | `topic_ops.py`      | `hz`                | `python3 scripts/topic_ops.py hz /camera/image_raw --seconds 5` |
| F053 | Topic msg/sec sample               | `topic_ops.py`      | `bandwidth`         | `python3 scripts/topic_ops.py bandwidth /scan --seconds 10` |
| F054 | Image snapshot from `/camera/*`    | `topic_ops.py`      | `image-snapshot`    | `python3 scripts/topic_ops.py image-snapshot /camera/image_raw` |
| F055 | ROS node roster                    | `node_ops.py`       | `node-list`         | `python3 scripts/node_ops.py node-list` |
| F056 | ROS service roster                 | `node_ops.py`       | `service-list`      | `python3 scripts/node_ops.py service-list` |
| F057 | ROS param dump                     | `node_ops.py`       | `param-dump`        | `python3 scripts/node_ops.py param-dump /motor_controller` |
| F058 | TF-tree summary                    | `node_ops.py`       | `tf-tree`           | `python3 scripts/node_ops.py tf-tree` |
| F059 | PCA9685 servo sweep                | `hardware_io.py`    | `servo-sweep`       | `python3 scripts/hardware_io.py servo-sweep --channel 0` |
| F060 | GPIO readback sweep                | `hardware_io.py`    | `gpio-readback`     | `python3 scripts/hardware_io.py gpio-readback --pins 23 24` |
| F061 | I²C pull-up diag                   | `hardware_io.py`    | `i2c-pullup`        | `python3 scripts/hardware_io.py i2c-pullup --bus 1` |
| F062 | SPI bus probe                      | `hardware_io.py`    | `spi-probe`         | `python3 scripts/hardware_io.py spi-probe --bus 0` |
| F063 | Training dataset prep              | `train_pipeline.py` | `dataset-prep`      | `python3 scripts/train_pipeline.py dataset-prep ./frames` |
| F064 | Holdout eval probe                 | `train_pipeline.py` | `holdout-eval`      | `python3 scripts/train_pipeline.py holdout-eval ./model.pt` |
| F065 | Model download manager             | `train_pipeline.py` | `model-download`    | `python3 scripts/train_pipeline.py model-download yolov8n.pt` |
| F066 | ONNX export                        | `train_pipeline.py` | `onnx-export`       | `python3 scripts/train_pipeline.py onnx-export ./model.pt` |
| F067 | Geofence polygon editor            | `perimeter.py`      | `geofence`          | `python3 scripts/perimeter.py geofence --add 0,0 10,0 10,10` |
| F068 | Motion-zone plotter                | `perimeter.py`      | `motion-zone`       | `python3 scripts/perimeter.py motion-zone --from ./zones.json` |
| F069 | Night-mode schedule                | `perimeter.py`      | `night-mode`        | `python3 scripts/perimeter.py night-mode --from 22:00 --to 06:00` |
| F070 | Intrusion timeline                 | `perimeter.py`      | `intrusion`         | `python3 scripts/perimeter.py intrusion --hours 24` |
| F071 | Solar yield logger                 | `power_deep.py`     | `solar-yield`       | `python3 scripts/power_deep.py solar-yield --poll 60` |
| F072 | Sleep / wake test                  | `power_deep.py`     | `sleep-wake`        | `python3 scripts/power_deep.py sleep-wake --seconds 30` |
| F073 | Dock-place sequence                | `power_deep.py`     | `dock-seq`          | `python3 scripts/power_deep.py dock-seq` |
| F074 | Dual-battery balancer              | `power_deep.py`     | `dual-balancer`     | `python3 scripts/power_deep.py dual-balancer` |
| F075 | TTS voice rotate                   | `voice_ops.py`      | `voice-rotate`      | `python3 scripts/voice_ops.py voice-rotate --voice tank_amy` |
| F076 | Sentiment warmup                   | `voice_ops.py`      | `sentiment-warmup`  | `python3 scripts/voice_ops.py sentiment-warmup` |
| F077 | Emotion-wheel visualisation        | `voice_ops.py`      | `emotion-wheel`     | `python3 scripts/voice_ops.py emotion-wheel` |
| F078 | Waypoint editor (JSON)             | `mission.py`        | `waypoint-edit`     | `python3 scripts/mission.py waypoint-edit --mission house.json` |
| F079 | Mission JSON linter                | `mission.py`        | `mission-lint`      | `python3 scripts/mission.py mission-lint ./house.json` |
| F080 | Task-graph viz (DOT)               | `mission.py`        | `task-graph`        | `python3 scripts/mission.py task-graph --out ./dag.dot` |
| F081 | Recipe marketplace exchange         | `mission.py`        | `recipe-trade`      | `python3 scripts/mission.py recipe-trade --from ./recipes.json` |
| F082 | Bench-test runner                  | `bench_ci.py`       | `bench-runner`      | `python3 scripts/bench_ci.py bench-runner --suite bench.yaml` |
| F083 | Cyclomatic complexity probe        | `bench_ci.py`       | `complexity`        | `python3 scripts/bench_ci.py complexity tank_ws/src` |
| F084 | Doc coverage gauge                 | `bench_ci.py`       | `doc-coverage`      | `python3 scripts/bench_ci.py doc-coverage tank_ws/src` |
| F085 | Function-length lint               | `gamma_lint.py`     | `func-len`          | `python3 scripts/gamma_lint.py func-len tank_ws/src --max 60` |
| F086 | Dead-import detector               | `gamma_lint.py`     | `dead-imports`      | `python3 scripts/gamma_lint.py dead-imports tank_ws/src` |
| F087 | Image-version pin                  | `ota.py`            | `image-pin`         | `python3 scripts/ota.py image-pin --tag 2026.07.22` |
| F088 | Tarball diff                       | `ota.py`            | `tarball-diff`      | `python3 scripts/ota.py tarball-diff old.tar new.tar` |
| F089 | A/B partition toggle               | `ota.py`            | `ab-toggle`         | `python3 scripts/ota.py ab-toggle --slot b` |
| F090 | SD-card burn helper                | `ota.py`            | `sd-burn`           | `python3 scripts/ota.py sd-burn tank.img /dev/sdb` |
| F091 | Voice soundboard ping              | `ux_polish.py`      | `soundboard`        | `python3 scripts/ux_polish.py soundboard --cue hi` |
| F092 | Dashboard theme rotate             | `ux_polish.py`      | `dashboard-theme`   | `python3 scripts/ux_polish.py dashboard-theme --theme dawn` |
| F093 | 24 h drift summary                 | `drift.py`          | `drift-24h`         | `python3 scripts/drift.py drift-24h` |
| F094 | Anomaly heatmap (ASCII)            | `drift.py`          | `heatmap`           | `python3 scripts/drift.py heatmap --hours 12` |
| F095 | Scheduler replay                   | `drift.py`          | `scheduler-replay`  | `python3 scripts/drift.py scheduler-replay --from ./sched.json` |
| F096 | Bot roster (multi-Pi)             | `fleet.py`          | `bot-roster`        | `python3 scripts/fleet.py bot-roster --file ./fleet.yaml` |
| F097 | Capability negotiation             | `fleet.py`          | `cap-negotiate`     | `python3 scripts/fleet.py cap-negotiate tank-1 tank-2` |
| F098 | Leader election status             | `fleet.py`          | `leader-election`   | `python3 scripts/fleet.py leader-election` |
| F099 | Occupancy snapshot                 | `mission_x.py`      | `occupancy`         | `python3 scripts/mission_x.py occupancy --from ./pings.jsonl` |
| F100 | Persistence verify                 | `mission_x.py`      | `persistence-verify`| `python3 scripts/mission_x.py persistence-verify` |

### Smoke test (F051–F100)

```bash
cd "the tank project"
for s in scripts/{topic_ops,node_ops,hardware_io,train_pipeline,perimeter,power_deep,voice_ops,mission,bench_ci,gamma_lint,ota,ux_polish,drift,fleet,mission_x}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

# Total feature IDs documented in README: must equal 100 (50 + 50).
grep -E '^\| F[0-9]' "the tank project/README.md" | wc -l   # -> 100
```

---

## Host utilities — 50 more features (F101 – F150)

A third batch of **15 CLIs** / **50 subcommands** that complement
F001–F100 — focusing on **LLM ops, memory internals, SLAM / vision
internals, DDS / profiling, webhook + metrics, i18n, DSP, crypto,
battery/budget, and integration suite**.

Conventions are identical (stdlib-first, lazy heavy imports, `--help`,
non-zero exit on failure).

### Feature index (F101 – F150)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F101 | Token-budget plan                | `llm_ops.py`            | `token-budget`        | `python3 scripts/llm_ops.py token-budget --budget 4096` |
| F102 | Prompt-cache fingerprint         | `llm_ops.py`            | `prompt-cache`        | `python3 scripts/llm_ops.py prompt-cache --rule doc+summary` |
| F103 | Scheduler CRON parser            | `llm_ops.py`            | `scheduler`           | `python3 scripts/llm_ops.py scheduler --cron '*/5 * * * *'` |
| F104 | Model-load smoke test            | `llm_ops.py`            | `model-load`          | `python3 scripts/llm_ops.py model-load ./llama-7b.gguf` |
| F105 | Vector recall batch              | `memory_ops.py`         | `vector-recall`       | `python3 scripts/memory_ops.py vector-recall --query "kitchen"` |
| F106 | LoRA adapter spec                | `memory_ops.py`         | `lora`                | `python3 scripts/memory_ops.py lora --rank 8` |
| F107 | Memory vacuum                    | `memory_ops.py`         | `vacuum`              | `python3 scripts/memory_ops.py vacuum --older-than 30d` |
| F108 | Batch recall JSONL export        | `memory_ops.py`         | `batch-recall`        | `python3 scripts/memory_ops.py batch-recall --top-k 10` |
| F109 | slam_toolbox tune                | `slam_ops.py`           | `slam-tune`           | `python3 scripts/slam_ops.py slam-tune --loop-closure 0.7` |
| F110 | RTAB-Map export                  | `slam_ops.py`           | `rtabmap-export`      | `python3 scripts/slam_ops.py rtabmap-export ./map.db` |
| F111 | Map snapshot                     | `slam_ops.py`           | `map-snapshot`        | `python3 scripts/slam_ops.py map-snapshot --out ./map.pgm` |
| F112 | YOLO threshold tune              | `vision_ops.py`         | `yolo-tune`           | `python3 scripts/vision_ops.py yolo-tune --conf 0.30 --iou 0.50` |
| F113 | Tracker state dump               | `vision_ops.py`         | `tracker-state`       | `python3 scripts/vision_ops.py tracker-state` |
| F114 | Monocular depth probe            | `vision_ops.py`         | `depth-estimate`      | `python3 scripts/vision_ops.py depth-estimate --frame ./f.jpg` |
| F115 | Color-space probe                | `vision_ops.py`         | `color-space`         | `python3 scripts/vision_ops.py color-space --frame ./f.jpg` |
| F116 | DDS QoS profile emit            | `dds_ops.py`            | `qos-profile`         | `python3 scripts/dds_ops.py qos-profile --name sensor_data` |
| F117 | DDS topic tune                   | `dds_ops.py`            | `topic-tune`          | `python3 scripts/dds_ops.py topic-tune --topic /cmd_vel` |
| F118 | DDS peer discovery              | `dds_ops.py`            | `peer-discovery`      | `python3 scripts/dds_ops.py peer-discovery` |
| F119 | ros2 trace profile               | `profiler.py`           | `ros-trace`           | `python3 scripts/profiler.py ros-trace --seconds 5` |
| F120 | Memory-leak sniffer              | `profiler.py`           | `leak-detect`         | `python3 scripts/profiler.py leak-detect --pid $PID` |
| F121 | Perf summary                     | `profiler.py`           | `perf-summary`        | `python3 scripts/profiler.py perf-summary --seconds 5` |
| F122 | Traffic shaper                   | `net_qos.py`            | `shape-traffic`       | `python3 scripts/net_qos.py shape-traffic --mbps 5` |
| F123 | DDS bandwidth probe              | `net_qos.py`            | `dds-bandwidth`       | `python3 scripts/net_qos.py dds-bandwidth --topic /scan` |
| F124 | Latency probe                    | `net_qos.py`            | `latency-probe`       | `python3 scripts/net_qos.py latency-probe --peer tank.lan` |
| F125 | Webhook incoming                 | `webhook.py`            | `incoming`            | `python3 scripts/webhook.py incoming --port 9090` |
| F126 | Webhook replay                   | `webhook.py`            | `replay`              | `python3 scripts/webhook.py replay ./hits.jsonl` |
| F127 | Webhook dedup                    | `webhook.py`            | `dedup`               | `python3 scripts/webhook.py dedup ./hits.jsonl` |
| F128 | Prometheus snapshot              | `metrics_export.py`     | `prom-snapshot`       | `python3 scripts/metrics_export.py prom-snapshot http://tank.lan:9100/metrics` |
| F129 | TSDB bridge                      | `metrics_export.py`     | `tsdb-bridge`         | `python3 scripts/metrics_export.py tsdb-bridge --out ./influx.jsonl` |
| F130 | OTel export                      | `metrics_export.py`     | `otel-export`         | `python3 scripts/metrics_export.py otel-export --out ./otel.jsonl` |
| F131 | Locale list                      | `i18n_ops.py`           | `locale-list`         | `python3 scripts/i18n_ops.py locale-list` |
| F132 | Locale test                      | `i18n_ops.py`           | `locale-test`         | `python3 scripts/i18n_ops.py locale-test --locale es_ES` |
| F133 | Translation cache                | `i18n_ops.py`           | `translate-cache`     | `python3 scripts/i18n_ops.py translate-cache --build` |
| F134 | Waveform + RMS                   | `dsp_ops.py`            | `waveform`            | `python3 scripts/dsp_ops.py waveform ./sample.wav` |
| F135 | VAD-detect                       | `dsp_ops.py`            | `vad-detect`          | `python3 scripts/dsp_ops.py vad-detect ./sample.wav` |
| F136 | EQ profile                       | `dsp_ops.py`            | `eq-profile`          | `python3 scripts/dsp_ops.py eq-profile --bands 5` |
| F137 | Secrets rotate                   | `crypto.py`             | `secrets-rotate`      | `python3 scripts/crypto.py secrets-rotate --key TANK_API_KEY` |
| F138 | JWT issue                        | `crypto.py`             | `jwt-issue`           | `python3 scripts/crypto.py jwt-issue --sub pilot --ttl 3600` |
| F139 | Hash benchmark                   | `crypto.py`             | `hash-bench`          | `python3 scripts/crypto.py hash-bench --algo sha256` |
| F140 | Battery cell tap                 | `cell_battery.py`       | `cell-tap`            | `python3 scripts/cell_battery.py cell-tap --count 6` |
| F141 | Cycle count                      | `cell_battery.py`       | `cycle-count`         | `python3 scripts/cell_battery.py cycle-count` |
| F142 | BMS state probe                  | `cell_battery.py`       | `bms-state`           | `python3 scripts/cell_battery.py bms-state` |
| F143 | Watt-hour accounting             | `budget.py`             | `watthour-out`        | `python3 scripts/budget.py watthour-out --window 24h` |
| F144 | Dock windows                     | `budget.py`             | `dock-windows`        | `python3 scripts/budget.py dock-windows --peak 19:00` |
| F145 | Geofence/energy cost             | `budget.py`             | `geofence-cost`       | `python3 scripts/budget.py geofence-cost --area 60` |
| F146 | Launch check                     | `integration_suite.py`  | `launch-check`        | `python3 scripts/integration_suite.py launch-check robot.launch.py` |
| F147 | Node graph dump                  | `integration_suite.py`  | `node-graph`          | `python3 scripts/integration_suite.py node-graph --out ./graph.dot` |
| F148 | Fault inject                     | `integration_suite.py`  | `fault-inject`        | `python3 scripts/integration_suite.py fault-inject --kind msg-loss` |
| F149 | Snapshot compare                 | `integration_suite.py`  | `snapshot-compare`    | `python3 scripts/integration_suite.py snapshot-compare a.json b.json` |
| F150 | Emotion ↔ state bridge           | `tank_emotion_link.py`  | `emotion-link`        | `python3 scripts/tank_emotion_link.py emotion-link --query joyful` |

### Smoke test (F101–F150)

```bash
cd "the tank project"
for s in scripts/{llm_ops,memory_ops,slam_ops,vision_ops,dds_ops,profiler,net_qos,webhook,metrics_export,i18n_ops,dsp_ops,crypto,cell_battery,budget,integration_suite,tank_emotion_link}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

grep -E '^\| F[0-9]' "the tank project/README.md" | wc -l   # -> 150
```

---

## Host utilities — 6 phase-runner features (F151 – F156)

A small validation CLI that walks each phase declared in `STATUS.md`
(`P1` … `P10½`) and inspects the on-disk artefact (`sqlite`, `json`,
`jsonl`) the phase is supposed to populate. Designed to work both on a
fresh bench (empty `data/`) and on a running Pi.

Conventions match F001–F150: stdlib-first, lazy heavy imports, `--help`,
non-zero exit on failure.

### Feature index (F151 – F156)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F151 | List every registered phase (id + name + expected artefacts) | `phase_runner.py` | `phases`     | `python3 scripts/phase_runner.py phases` |
| F152 | List `tank_ws/data/` with sizes + sqlite table counts        | `phase_runner.py` | `logs`       | `python3 scripts/phase_runner.py logs --limit 200` |
| F153 | Peek into a single file (sqlite schema / json / jsonl head) | `phase_runner.py` | `examine`    | `python3 scripts/phase_runner.py examine tank_ws/src/tank_meta/content/decisions.json` |
| F154 | Seed a tiny demo `log.db` so the runner has data to inspect | `phase_runner.py` | `seed`       | `python3 scripts/phase_runner.py seed --force` |
| F155 | Run the file-bound checks for one phase                     | `phase_runner.py` | `check`      | `python3 scripts/phase_runner.py check P6½` |
| F156 | Walk every phase sequentially (CI-friendly with `--soft`)  | `phase_runner.py` | `run`        | `python3 scripts/phase_runner.py run --soft` |

### 5-second smoke test (F151–F156)

```bash
cd "the tank project"

# 1.  parses + shows --help
python3 scripts/phase_runner.py --help >/dev/null && echo "OK phase_runner.py"

# 2.  lists phases + seeds a demo log.db
python3 scripts/phase_runner.py phases
python3 scripts/phase_runner.py seed --force
python3 scripts/phase_runner.py check P6½          # exercise one phase
python3 scripts/phase_runner.py examine "tank_ws/data/log.db" --head 3

# 3.  total features documented in README (F001–F156 = 156 rows):
grep -E '^\| F[0-9]' "the tank project/README.md" | wc -l   # -> 156
```

---

## Host utilities — 50 more plugins (F157 – F206)

A fourth batch of **15 host-level CLIs** / **50 subcommands** that complement F001–F156 — daily-driver + lifestyle + comms + observability v2 + governance. Conforms to the same conventions as the prior batches.

### Feature index (F157 – F206)

| ID   | Feature | Script | Subcommand | Example |
|------|---------|--------|------------|---------|
| F157 | HA / MQTT device list (cache) | `home_auto.py` | `device-list` | `python3 scripts/home_auto.py device-list` |
| F158 | Single entity state          | `home_auto.py` | `entity-state` | `python3 scripts/home_auto.py entity-state --entity light.kitchen` |
| F159 | Fire a HA scene              | `home_auto.py` | `scene-run` | `python3 scripts/home_auto.py scene-run --scene movie_night` |
| F160 | Today's events               | `calendar_ops.py` | `today` | `python3 scripts/calendar_ops.py today` |
| F161 | Next 7-day events            | `calendar_ops.py` | `week` | `python3 scripts/calendar_ops.py week` |
| F162 | Append an event              | `calendar_ops.py` | `add-event` | `python3 scripts/calendar_ops.py add-event --title "lab deploy" --start 14:00` |
| F163 | Substring event search       | `calendar_ops.py` | `search` | `python3 scripts/calendar_ops.py search --query "deploy"` |
| F164 | Right-now weather            | `weather.py` | `current` | `python3 scripts/weather.py current --lat 28.6 --lon 77.2` |
| F165 | 24-hour forecast             | `weather.py` | `hourly` | `python3 scripts/weather.py hourly --lat 28.6 --lon 77.2` |
| F166 | Severe-weather alerts        | `weather.py` | `alerts` | `python3 scripts/weather.py alerts --lat 28.6 --lon 77.2` |
| F167 | Top headlines (synthetic)    | `news.py` | `headlines` | `python3 scripts/news.py headlines --n 10` |
| F168 | Topic-filtered stories       | `news.py` | `topic` | `python3 scripts/news.py topic --topic ai` |
| F169 | Known podcast feeds          | `news.py` | `podcast-list` | `python3 scripts/news.py podcast-list` |
| F170 | Fetch an arbitrary RSS       | `news.py` | `fetch-rss` | `python3 scripts/news.py fetch-rss --url https://hnrss.org/newest --dry-run` |
| F171 | View / append play queue     | `media.py` | `play-queue` | `python3 scripts/media.py play-queue` |
| F172 | Substring search in library  | `media.py` | `library-search` | `python3 scripts/media.py library-search --query ambient` |
| F173 | Cast queue to target         | `media.py` | `cast-to` | `python3 scripts/media.py cast-to --target tank.living_room --dry-run` |
| F174 | Single package track         | `package_track.py` | `track` | `python3 scripts/package_track.py track --id 1Z-DEMO-001` |
| F175 | Today's package list         | `package_track.py` | `deliveries-today` | `python3 scripts/package_track.py deliveries-today` |
| F176 | Mark package redirect        | `package_track.py` | `redirect` | `python3 scripts/package_track.py redirect --id 1Z-DEMO-001 --address "new addr"` |
| F177 | Mark package delivered       | `package_track.py` | `mark-delivered` | `python3 scripts/package_track.py mark-delivered --id 1Z-DEMO-001` |
| F178 | Schedule a reminder          | `reminder.py` | `set` | `python3 scripts/reminder.py set --title "check tank logs" --in-min 15` |
| F179 | Active reminders             | `reminder.py` | `list` | `python3 scripts/reminder.py list` |
| F180 | Snooze a reminder            | `reminder.py` | `snooze` | `python3 scripts/reminder.py snooze --id 1 --min 10` |
| F181 | Open to-do list              | `agent_tasks.py` | `todo-list` | `python3 scripts/agent_tasks.py todo-list` |
| F182 | Add to-do                    | `agent_tasks.py` | `todo-add` | `python3 scripts/agent_tasks.py todo-add --title "tank oil" --priority HIGH` |
| F183 | Complete to-do               | `agent_tasks.py` | `todo-complete` | `python3 scripts/agent_tasks.py todo-complete --id 1` |
| F184 | Habit streak lookup          | `agent_tasks.py` | `habit-streak` | `python3 scripts/agent_tasks.py habit-streak --habit meditate` |
| F185 | Send notification            | `notify.py` | `send` | `python3 scripts/notify.py send --title "ESOP" --channel email slack` |
| F186 | List channels                | `notify.py` | `channels-list` | `python3 scripts/notify.py channels-list` |
| F187 | GDPR delete simulator        | `compliance_ops.py` | `gdpr-delete` | `python3 scripts/compliance_ops.py gdpr-delete --key pilot_email` |
| F188 | Append audit event           | `compliance_ops.py` | `audit-log` | `python3 scripts/compliance_ops.py audit-log --kind decision_append --who pilot` |
| F189 | Retention prune              | `compliance_ops.py` | `retention-apply` | `python3 scripts/compliance_ops.py retention-apply --older-than 30` |
| F190 | SLO report                   | `compliance_ops.py` | `slo-report` | `python3 scripts/compliance_ops.py slo-report --days 7` |
| F191 | List sqlite dbs              | `schema_ops.py` | `list` | `python3 scripts/schema_ops.py list` |
| F192 | Migration dry-run            | `schema_ops.py` | `migrate-dry-run` | `python3 scripts/schema_ops.py migrate-dry-run --name add_index` |
| F193 | REINDEX a db                 | `schema_ops.py` | `reindex` | `python3 scripts/schema_ops.py reindex --db meta.db` |
| F194 | List recent spans            | `tracing_ops.py` | `trace-list` | `python3 scripts/tracing_ops.py trace-list --limit 50` |
| F195 | Export spans                 | `tracing_ops.py` | `trace-export` | `python3 scripts/tracing_ops.py trace-export --out traces.jsonl` |
| F196 | Tail a log file              | `tracing_ops.py` | `tail-logs` | `python3 scripts/tracing_ops.py tail-logs --file tank_ws/data/audit.jsonl` |
| F197 | Trace-id grep                | `tracing_ops.py` | `grep-trace` | `python3 scripts/tracing_ops.py grep-trace --tid abc-123` |
| F198 | Capacity snapshot            | `capacity.py` | `usage` | `python3 scripts/capacity.py usage` |
| F199 | 30-day forecast              | `capacity.py` | `forecast` | `python3 scripts/capacity.py forecast` |
| F200 | Throttle heuristic           | `capacity.py` | `throttle-check` | `python3 scripts/capacity.py throttle-check --mbps 5 --hours 24` |
| F201 | Rosbag record                | `rosbag_ops.py` | `record` | `python3 scripts/rosbag_ops.py record --topics /cmd_vel /scan` |
| F202 | Rosbag replay                | `rosbag_ops.py` | `replay` | `python3 scripts/rosbag_ops.py replay --bag out/demo.mcap` |
| F203 | Rosbag inspect               | `rosbag_ops.py` | `inspect` | `python3 scripts/rosbag_ops.py inspect --bag out/demo.mcap` |
| F204 | Rosbag trim                  | `rosbag_ops.py` | `trim` | `python3 scripts/rosbag_ops.py trim --bag out/demo.mcap --start 0 --end 60` |
| F205 | Crash capture (synthetic)    | `crash_dump.py` | `capture` | `python3 scripts/crash_dump.py capture --pid $$` |
| F206 | Symbolicate a stack trace    | `crash_dump.py` | `symbolize` | `python3 scripts/crash_dump.py symbolize --in crash.txt` |

### Smoke test (F157–F206)

```bash
cd "the tank project"
for s in scripts/{home_auto,calendar_ops,weather,news,media,package_track,reminder,agent_tasks,notify,compliance_ops,schema_ops,tracing_ops,capacity,rosbag_ops,crash_dump}.py; do
   python3 "$s" --help >/dev/null && echo "OK $s"
done

# Total feature IDs documented in README: must equal 206 (156 + 50).
grep -E '^\| F[0-9]+\|' "the tank project/README.md" | wc -l   # -> 206
```

---

## Host utilities — 200 new feature plugins (F207 – F406)

A massive sixth batch of **9 host-level CLIs / 200 subcommands** for vision Intelligence, emotion/personality, biometric security, mobility, environmental sensing, multimedia, home automation, comms, and robot self-maintenance. Every entry follows the same offline-first (“stdlib-first, lazy heavy imports, `--help`, non-zero exit on partial failure”) convention as F001 – F206.

### Feature index (F207 – F406)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F207 | YOLOv8n 80-class real-time object detect | `ai_vision.py` | `detect` | `python3 scripts/ai_vision.py detect` |
| F208 | Enroll known user face embedding | `ai_vision.py` | `face-enroll` | `python3 scripts/ai_vision.py face-enroll --user pilot` |
| F209 | Match frame against enrolled face DB | `ai_vision.py` | `face-match` | `python3 scripts/ai_vision.py face-match` |
| F210 | AMG8833 thermal human-presence (8x8) | `ai_vision.py` | `thermal-presence` | `python3 scripts/ai_vision.py thermal-presence` |
| F211 | Blend thermal heatmap with RGB frame | `ai_vision.py` | `thermal-overlay` | `python3 scripts/ai_vision.py thermal-overlay` |
| F212 | Hand-gesture (wave/OK/stop) | `ai_vision.py` | `gesture` | `python3 scripts/ai_vision.py gesture` |
| F213 | License-plate OCR (easyocr) | `ai_vision.py` | `plate` | `python3 scripts/ai_vision.py plate --frame ./car.jpg` |
| F214 | Pet detection + treat-dispenser trigger | `ai_vision.py` | `pet-detect` | `python3 scripts/ai_vision.py pet-detect` |
| F215 | Crying-sound baby monitor (librosa RMS) | `ai_vision.py` | `baby-monitor` | `python3 scripts/ai_vision.py baby-monitor -- wav ./cry.wav` |
| F216 | Doorstep package detector (motion + size) | `ai_vision.py` | `package-detect` | `python3 scripts/ai_vision.py package-detect --device 0` |
| F217 | Leaf colour + thermal water-stress probe | `ai_vision.py` | `plant-health` | `python3 scripts/ai_vision.py plant-health` |
| F218 | Fire/smoke detection (thermal + RGB) | `ai_vision.py` | `fire-smoke` | `python3 scripts/ai_vision.py fire-smoke` |
| F219 | Intruder human/animal/wind classifier | `ai_vision.py` | `intruder-class` | `python3 scripts/ai_vision.py intruder-class` |
| F220 | AI-produced next patrol waypoint | `ai_vision.py` | `patrol-ai` | `python3 scripts/ai_vision.py patrol-ai --x 1.5 --y 0.2` |
| F221 | Real-time target lock-on (frame-diff) | `ai_vision.py` | `object-track` | `python3 scripts/ai_vision.py object-track` |
| F222 | 5-DoF visual odometry (essential-matrix) | `ai_vision.py` | `visual-odom` | `python3 scripts/ai_vision.py visual-odom` |
| F223 | Stereo depth from dual Pi-Cam rig | `ai_vision.py` | `depth-stereo` | `python3 scripts/ai_vision.py depth-stereo` |
| F224 | Estimate body temperature from AMG8833 ROI | `ai_vision.py` | `body-temp` | `python3 scripts/ai_vision.py body-temp` |
| F225 | Deepface facial emotion recognition | `ai_vision.py` | `emotion-face` | `python3 scripts/ai_vision.py emotion-face` |
| F226 | Deepface age + gender estimate | `ai_vision.py` | `age-gender` | `python3 scripts/ai_vision.py age-gender` |
| F227 | Sitting / walking / falling recognition | `ai_vision.py` | `activity` | `python3 scripts/ai_vision.py activity` |
| F228 | Visible litter / trash detection | `ai_vision.py` | `trash-detect` | `python3 scripts/ai_vision.py trash-detect` |
| F229 | Identify a book cover -> lookup summary | `ai_vision.py` | `book-cover` | `python3 scripts/ai_vision.py book-cover --frame ./book.jpg` |
| F230 | Barcode/QR scan (pyzbar) | `ai_vision.py` | `barcode` | `python3 scripts/ai_vision.py barcode` |
| F231 | Pill-bottle recognition + reminder | `ai_vision.py` | `medication` | `python3 scripts/ai_vision.py medication` |
| F232 | Append photo + ts + name to visitor log | `ai_vision.py` | `visitor-log` | `python3 scripts/ai_vision.py visitor-log --name pilot` |
| F233 | Plate blacklist match (JSON lookup) | `ai_vision.py` | `plate-blacklist` | `python3 scripts/ai_vision.py plate-blacklist --plate KA01AB1234` |
| F234 | Bird / wildlife classifier | `ai_vision.py` | `wildlife` | `python3 scripts/ai_vision.py wildlife` |
| F235 | IR LED toggle for NoIR camera mode | `ai_vision.py` | `night-patrol` | `python3 scripts/ai_vision.py night-patrol --on` |
| F236 | Auto-crop best portrait faces | `ai_vision.py` | `best-faces` | `python3 scripts/ai_vision.py best-faces` |
| F237 | Happy-eye expression | `personality.py` | `eye-happy` | `python3 scripts/personality.py eye-happy` |
| F238 | Sad-eye expression | `personality.py` | `eye-sad` | `python3 scripts/personality.py eye-sad` |
| F239 | Bind eye state to /assistant/mood | `personality.py` | `eye-mood-link` | `python3 scripts/personality.py eye-mood-link --src /assistant/mood` |
| F240 | Droopy eyes on low battery | `personality.py` | `eye-battery` | `python3 scripts/personality.py eye-battery --pct 15` |
| F241 | Confused eyes when WiFi RSSI drops | `personality.py` | `eye-wifi` | `python3 scripts/personality.py eye-wifi --rssi -85` |
| F242 | Heart eyes on face-match | `personality.py` | `eye-recog` | `python3 scripts/personality.py eye-recog --user-match` |
| F243 | Close eyes after 10 min idle | `personality.py` | `eye-sleep` | `python3 scripts/personality.py eye-sleep --idle-min 15` |
| F244 | Snap-open eyes on wake-word | `personality.py` | `eye-wake` | `python3 scripts/personality.py eye-wake --wake 'hey tank'` |
| F245 | X-eyes on critical error | `personality.py` | `eye-error` | `python3 scripts/personality.py eye-error --severity critical` |
| F246 | Battery-fill charge animation | `personality.py` | `eye-charge` | `python3 scripts/personality.py eye-charge --pct 60` |
| F247 | Narrow scanning patrol eyes | `personality.py` | `eye-patrol` | `python3 scripts/personality.py eye-patrol --side left` |
| F248 | Sweat-drop on CPU overheat | `personality.py` | `eye-temp` | `python3 scripts/personality.py eye-temp --cpu-c 78` |
| F249 | EQ-style reactive eye animation | `personality.py` | `eye-music` | `python3 scripts/personality.py eye-music --bands 8` |
| F250 | Blinking envelope on new notification | `personality.py` | `eye-notify` | `python3 scripts/personality.py eye-notify --channel email` |
| F251 | Red flashing alarm eyes | `personality.py` | `eye-alarm` | `python3 scripts/personality.py eye-alarm --hz 2` |
| F252 | Game-mode playful competitive eyes | `personality.py` | `eye-game` | `python3 scripts/personality.py eye-game` |
| F253 | Pet touch squint on capacitive sensor | `personality.py` | `eye-pet` | `python3 scripts/personality.py eye-pet` |
| F254 | Open eye-frame designer web route | `personality.py` | `eye-designer` | `python3 scripts/personality.py eye-designer --frame happy` |
| F255 | Random blink / surprise animations | `personality.py` | `eye-idle-rand` | `python3 scripts/personality.py eye-idle-rand --seed 42` |
| F256 | Seasonal themes (halloween, snow, ...) | `personality.py` | `eye-seasonal` | `python3 scripts/personality.py eye-seasonal --season winter` |
| F257 | Eyes follow a moving object (NDC) | `personality.py` | `eye-track` | `python3 scripts/personality.py eye-track --x 0.4 --y 0.5` |
| F258 | Cross-eyed / wall-eyed poses | `personality.py` | `eye-cross` | `python3 scripts/personality.py eye-cross --pose wall` |
| F259 | Auto-brightness adjustment | `personality.py` | `eye-bright` | `python3 scripts/personality.py eye-bright --pct 75` |
| F260 | Arrow eyes pointing at HUD notification | `personality.py` | `eye-attention` | `python3 scripts/personality.py eye-attention --direction up` |
| F261 | Boot calibration pattern | `personality.py` | `eye-self-test` | `python3 scripts/personality.py eye-self-test` |
| F262 | Fingerprint required for admin | `security_bio.py` | `fp-admin` | `python3 scripts/security_bio.py fp-admin --user pilot` |
| F263 | Multi-user fingerprint profiles | `security_bio.py` | `fp-multi-user` | `python3 scripts/security_bio.py fp-multi-user --users pilot guest` |
| F264 | Touch fingerprint to arm patrol | `security_bio.py` | `fp-arm` | `python3 scripts/security_bio.py fp-arm --arm` |
| F265 | Duress-finger emergency alert | `security_bio.py` | `fp-duress` | `python3 scripts/security_bio.py fp-duress --finger 99` |
| F266 | Two-factor (fingerprint + face) | `security_bio.py` | `two-factor` | `python3 scripts/security_bio.py two-factor` |
| F267 | Unknown face prompts for fingerprint | `security_bio.py` | `stranger-alert` | `python3 scripts/security_bio.py stranger-alert` |
| F268 | Motion-triggered siren (MAX98357A) | `security_bio.py` | `siren` | `python3 scripts/security_bio.py siren --seconds 8` |
| F269 | Define a secure-zone perimeter | `security_bio.py` | `secure-zone` | `python3 scripts/security_bio.py secure-zone --name front-gate --radius 3` |
| F270 | Tilt / lift tamper detection | `security_bio.py` | `tamper` | `python3 scripts/security_bio.py tamper --threshold 18` |
| F271 | Auto-cloud upload of intruder clip | `security_bio.py` | `footage-cloud` | `python3 scripts/security_bio.py footage-cloud --ms 12000` |
| F272 | LTE-based geofence breaching | `security_bio.py` | `geofence-lte` | `python3 scripts/security_bio.py geofence-lte --lat 28.61 --lon 77.21` |
| F273 | Front-door night-lock mode | `security_bio.py` | `night-lock` | `python3 scripts/security_bio.py night-lock` |
| F274 | Fingerprint-controlled solenoid locker | `security_bio.py` | `fp-locker` | `python3 scripts/security_bio.py fp-locker --solenoid door1` |
| F275 | Voiceprint speaker identification | `security_bio.py` | `voiceprint` | `python3 scripts/security_bio.py voiceprint --user pilot` |
| F276 | Auto-logout + fingerprint unlock | `security_bio.py` | `auto-logout` | `python3 scripts/security_bio.py auto-logout --minutes 10` |
| F277 | Panic keyword -> emergency contact call | `security_bio.py` | `panic-word` | `python3 scripts/security_bio.py panic-word --phrase mayday` |
| F278 | Per-day security patrol schedules | `security_bio.py` | `patrol-schedule` | `python3 scripts/security_bio.py patrol-schedule --schedule '02:00,03:00'` |
| F279 | Intruder follow-me recording | `security_bio.py` | `drone-follow` | `python3 scripts/security_bio.py drone-follow --dist 1.5` |
| F280 | HC-SR04 tripwire across doorway | `security_bio.py` | `tripwire` | `python3 scripts/security_bio.py tripwire --beam front` |
| F281 | Encrypted camera stream (AES-GCM) | `security_bio.py` | `enc-stream` | `python3 scripts/security_bio.py enc-stream --fps 10` |
| F282 | ROS2 autonomous /cmd_vel navigation | `mobility_nav.py` | `nav-autonomous` | `python3 scripts/mobility_nav.py nav-autonomous --vx 0.2` |
| F283 | Virtual leash follow-person | `mobility_nav.py` | `virtual-leash` | `python3 scripts/mobility_nav.py virtual-leash --user pilot --dist 0.6` |
| F284 | Cycle waypoint patrol mission | `mobility_nav.py` | `waypoint-patrol` | `python3 scripts/mobility_nav.py waypoint-patrol --mission house.json --loop` |
| F285 | Auto return to wireless dock on low batt | `mobility_nav.py` | `dock-return` | `python3 scripts/mobility_nav.py dock-return --battery 18` |
| F286 | Ultrasonic stair detection / avoidance | `mobility_nav.py` | `stair-detect` | `python3 scripts/mobility_nav.py stair-detect --front 130` |
| F287 | IR downward cliff detection | `mobility_nav.py` | `cliff-detect` | `python3 scripts/mobility_nav.py cliff-detect --ir 0.45` |
| F288 | Dynamic speed near people vs open | `mobility_nav.py` | `dynamic-speed` | `python3 scripts/mobility_nav.py dynamic-speed --max 0.6 --people-near 1` |
| F289 | Precise in-place 360 turn | `mobility_nav.py` | `tank-turn` | `python3 scripts/mobility_nav.py tank-turn --deg 360` |
| F290 | Smooth trapezoidal accel/decel | `mobility_nav.py` | `smooth-accel` | `python3 scripts/mobility_nav.py smooth-accel` |
| F291 | Remember furniture locations | `mobility_nav.py` | `obstacle-memory` | `python3 scripts/mobility_nav.py obstacle-memory --path memory://obs.db` |
| F292 | Wall-follow corridor navigation | `mobility_nav.py` | `wall-follow` | `python3 scripts/mobility_nav.py wall-follow --side right` |
| F293 | Doorway width alignment & traversal | `mobility_nav.py` | `doorway-cross` | `python3 scripts/mobility_nav.py doorway-cross --width 0.9` |
| F294 | IMU incline torque boost on ramps | `mobility_nav.py` | `ramp-climb` | `python3 scripts/mobility_nav.py ramp-climb --incline 14` |
| F295 | Web-based virtual joystick control | `mobility_nav.py` | `joystick-web` | `python3 scripts/mobility_nav.py joystick-web` |
| F296 | Bluetooth gamepad teleop | `mobility_nav.py` | `gamepad` | `python3 scripts/mobility_nav.py gamepad --device /dev/input/js0` |
| F297 | Record + replay a manual route | `mobility_nav.py` | `path-record` | `python3 scripts/mobility_nav.py path-record --ms 25000` |
| F298 | Crowd-navigation: weave between legs | `mobility_nav.py` | `crowd-navigation` | `python3 scripts/mobility_nav.py crowd-navigation --legs 3` |
| F299 | Outdoor grass/gravel mode | `mobility_nav.py` | `outdoor-mode` | `python3 scripts/mobility_nav.py outdoor-mode` |
| F300 | Snow / loose-surface power split | `mobility_nav.py` | `snow-mode` | `python3 scripts/mobility_nav.py snow-mode` |
| F301 | 3D-printed weatherproofing enclosure | `mobility_nav.py` | `weather-kit` | `python3 scripts/mobility_nav.py weather-kit --ip IP54` |
| F302 | Outdoor GPS waypoint mission | `mobility_nav.py` | `gps-waypoint` | `python3 scripts/mobility_nav.py gps-waypoint --lat 28.61 --lon 77.21` |
| F303 | Magnetic virtual fence (lawn-mower style) | `mobility_nav.py` | `magnetic-boundary` | `python3 scripts/mobility_nav.py magnetic-boundary` |
| F304 | Physically-leashed follow-me sensor | `mobility_nav.py` | `follow-leash` | `python3 scripts/mobility_nav.py follow-leash --pull 0.4` |
| F305 | Soccer mode (chase ball) | `mobility_nav.py` | `soccer-mode` | `python3 scripts/mobility_nav.py soccer-mode --x 220 --y 180` |
| F306 | Skid-steer dance choreographies | `mobility_nav.py` | `skid-dance` | `python3 scripts/mobility_nav.py skid-dance --move spin-360 --duration 5` |
| F307 | AMG8833 room heat-map build | `environment.py` | `temp-map` | `python3 scripts/environment.py temp-map` |
| F308 | Humidity sensor reading | `environment.py` | `humidity` | `python3 scripts/environment.py humidity` |
| F309 | PM2.5 / VOC air-quality probe | `environment.py` | `air-quality` | `python3 scripts/environment.py air-quality` |
| F310 | CO2-level warning | `environment.py` | `co2-level` | `python3 scripts/environment.py co2-level --threshold 1000` |
| F311 | Ambient light-meter (lux) | `environment.py` | `light-meter` | `python3 scripts/environment.py light-meter` |
| F312 | Loud sound anomaly detector | `environment.py` | `noise-monitor` | `python3 scripts/environment.py noise-monitor --threshold 80` |
| F313 | Earthquake / tremor detector (MPU6050) | `environment.py` | `quake` | `python3 scripts/environment.py quake` |
| F314 | Temperature/humidity/pressure station | `environment.py` | `weather-station` | `python3 scripts/environment.py weather-station` |
| F315 | Rain sensor + rush-inside trigger | `environment.py` | `rain-detect` | `python3 scripts/environment.py rain-detect` |
| F316 | Thermal-camera appliance monitor | `environment.py` | `thermal-appliance` | `python3 scripts/environment.py thermal-appliance --target fridge` |
| F317 | MQ-2 gas-leak detector | `environment.py` | `gas-leak` | `python3 scripts/environment.py gas-leak` |
| F318 | Flood / water-level sensor | `environment.py` | `flood` | `python3 scripts/environment.py flood` |
| F319 | UV index measurement | `environment.py` | `uv-index` | `python3 scripts/environment.py uv-index` |
| F320 | Soil moisture probe (garden) | `environment.py` | `soil-moisture` | `python3 scripts/environment.py soil-moisture --threshold 35` |
| F321 | Barometric pressure trend (rain soon?) | `environment.py` | `baro-trend` | `python3 scripts/environment.py baro-trend` |
| F322 | Heat-index + wind-chill calculation | `environment.py` | `heat-wind` | `python3 scripts/environment.py heat-wind` |
| F323 | Thermal time-lapse recording | `environment.py` | `thermal-timelapse` | `python3 scripts/environment.py thermal-timelapse --frames 180` |
| F324 | Fireplace heat-signature monitor | `environment.py` | `fireplace` | `python3 scripts/environment.py fireplace` |
| F325 | Freezer temperature alarm | `environment.py` | `freezer-alarm` | `python3 scripts/environment.py freezer-alarm --threshold -15` |
| F326 | Sauna session thermal timer | `environment.py` | `sauna-monitor` | `python3 scripts/environment.py sauna-monitor --elapsed 12 --alert 20` |
| F327 | Music library web stream | `media_hub.py` | `music-server` | `python3 scripts/media_hub.py music-server` |
| F328 | A2DP bluetooth speaker (MAX98357A) | `media_hub.py` | `bluetooth-speaker` | `python3 scripts/media_hub.py bluetooth-speaker --device phone-42` |
| F329 | Internet-radio player | `media_hub.py` | `internet-radio` | `python3 scripts/media_hub.py internet-radio --station bbc-world` |
| F330 | Podcast auto-download new episodes | `media_hub.py` | `podcast-downloader` | `python3 scripts/media_hub.py podcast-downloader --feed lex-fridman` |
| F331 | Audiobook player with speed ctrl | `media_hub.py` | `audiobook` | `python3 scripts/media_hub.py audiobook --title hitchhiker --speed 1.25` |
| F332 | TTS news headlines read aloud | `media_hub.py` | `news-tts` | `python3 scripts/media_hub.py news-tts` |
| F333 | Voice-controlled music jukebox | `media_hub.py` | `voice-jukebox` | `python3 scripts/media_hub.py voice-jukebox --genre jazz` |
| F334 | Multi-room ESP32 speaker sync | `media_hub.py` | `multi-room-audio` | `python3 scripts/media_hub.py multi-room-audio --clients 4` |
| F335 | Soundboard (applause / laughter) | `media_hub.py` | `soundboard` | `python3 scripts/media_hub.py soundboard --cue applause` |
| F336 | DJ mode: crossfade + reverb | `media_hub.py` | `dj-mode` | `python3 scripts/media_hub.py dj-mode --fade 600` |
| F337 | Karaoke mode (lyrics on DSI / eye display) | `media_hub.py` | `karaoke` | `python3 scripts/media_hub.py karaoke --song bohemian` |
| F338 | White-noise generator (rain/ocean/fan) | `media_hub.py` | `white-noise` | `python3 scripts/media_hub.py white-noise --noise ocean` |
| F339 | Alarm clock with gradual light wake-up | `media_hub.py` | `alarm-clock` | `python3 scripts/media_hub.py alarm-clock --in-min 30` |
| F340 | Sunset eye warm-dim wind-down | `media_hub.py` | `sunset-mode` | `python3 scripts/media_hub.py sunset-mode --duration 15` |
| F341 | Party mode (flash + dance + music) | `media_hub.py` | `party-mode` | `python3 scripts/media_hub.py party-mode` |
| F342 | Storyteller: read children's books | `media_hub.py` | `storyteller` | `python3 scripts/media_hub.py storyteller --book caterpillar` |
| F343 | DSI touchscreen game console | `media_hub.py` | `game-console` | `python3 scripts/media_hub.py game-console --title snake --controller joystick` |
| F344 | Trivia quiz-master mode | `media_hub.py` | `trivia` | `python3 scripts/media_hub.py trivia` |
| F345 | Virtual Tamagotchi pet | `media_hub.py` | `virtual-pet` | `python3 scripts/media_hub.py virtual-pet --name Tankito` |
| F346 | Home-theater IR projector control | `media_hub.py` | `projector-control` | `python3 scripts/media_hub.py projector-control --projector living-room` |
| F347 | Music ambient visualizer on eyes | `media_hub.py` | `ambient-viz` | `python3 scripts/media_hub.py ambient-viz` |
| F348 | Meditation breathing animation | `media_hub.py` | `meditation` | `python3 scripts/media_hub.py meditation --cycle 6` |
| F349 | Lullaby singer for baby | `media_hub.py` | `lullaby` | `python3 scripts/media_hub.py lullaby --volume 20` |
| F350 | Birthday surprise + candle blowout | `media_hub.py` | `birthday` | `python3 scripts/media_hub.py birthday --candles 5` |
| F351 | Magic 8-ball vibrations + fortune | `media_hub.py` | `magic-8-ball` | `python3 scripts/media_hub.py magic-8-ball` |
| F352 | Zigbee/Z-Wave smart-home hub | `home_automation.py` | `hub-smart` | `python3 scripts/home_automation.py hub-smart` |
| F353 | Voice-controlled lights | `home_automation.py` | `light-voice` | `python3 scripts/home_automation.py light-voice --room kitchen --brightness 80` |
| F354 | Presence-aware thermostat setpoint | `home_automation.py` | `thermostat` | `python3 scripts/home_automation.py thermostat --c 22 --presence` |
| F355 | Relay-driven garage door opener | `home_automation.py` | `garage-door` | `python3 scripts/home_automation.py garage-door --door main` |
| F356 | Sunrise curtain-servo opener | `home_automation.py` | `curtain-servo` | `python3 scripts/home_automation.py curtain-servo --curtain living-room-1` |
| F357 | Scheduled pet feeder | `home_automation.py` | `pet-feeder` | `python3 scripts/home_automation.py pet-feeder --feeder cat-station --portion 20` |
| F358 | Mailbox notifier (sensor + snap) | `home_automation.py` | `mailbox-notify` | `python3 scripts/home_automation.py mailbox-notify` |
| F359 | Doorbell camera + VoIP answer | `home_automation.py` | `doorbell-cam` | `python3 scripts/home_automation.py doorbell-cam --count 1` |
| F360 | Soil-moisture driven irrigation | `home_automation.py` | `irrigation` | `python3 scripts/home_automation.py irrigation --zone front-garden --minutes 10` |
| F361 | Solar + battery energy dashboard | `home_automation.py` | `energy-monitor` | `python3 scripts/home_automation.py energy-monitor` |
| F362 | Share NVMe as NAS | `home_automation.py` | `nas-share` | `python3 scripts/home_automation.py nas-share` |
| F363 | Plex / Jellyfin media transcoder | `home_automation.py` | `plex-server` | `python3 scripts/home_automation.py plex-server` |
| F364 | Pi-hole DNS ad-blocker | `home_automation.py` | `pihole` | `python3 scripts/home_automation.py pihole` |
| F365 | WireGuard VPN server | `home_automation.py` | `vpn-server` | `python3 scripts/home_automation.py vpn-server` |
| F366 | Share USB printer (IPP/CUPS) | `home_automation.py` | `print-server` | `python3 scripts/home_automation.py print-server --name HP_laserjet` |
| F367 | Torrent-box (qbittorrent ISO seeder) | `home_automation.py` | `torrent-box` | `python3 scripts/home_automation.py torrent-box` |
| F368 | Personal cloud photo/document sync | `home_automation.py` | `personal-cloud` | `python3 scripts/home_automation.py personal-cloud --provider nextcloud` |
| F369 | 24/7 camera NVR on NVMe | `home_automation.py` | `nvr-surveillance` | `python3 scripts/home_automation.py nvr-surveillance --cams 2` |
| F370 | Auto-backup household PCs to robot | `home_automation.py` | `auto-backup` | `python3 scripts/home_automation.py auto-backup --host laptop-01` |
| F371 | Guest WiFi with fingerprint captive-portal | `home_automation.py` | `guest-wifi` | `python3 scripts/home_automation.py guest-wifi --ssid TANK_GUEST --hours 24` |
| F372 | Voice shopping-list manager | `home_automation.py` | `shopping-list` | `python3 scripts/home_automation.py shopping-list --text milk` |
| F373 | Family calendar + reminder server | `home_automation.py` | `calendar-server` | `python3 scripts/home_automation.py calendar-server` |
| F374 | Cooking step read-out + timers | `home_automation.py` | `recipe` | `python3 scripts/home_automation.py recipe --step 3 --seconds 90` |
| F375 | ESP32 intercom mesh around the house | `home_automation.py` | `intercom` | `python3 scripts/home_automation.py intercom --msg 'dinner ready'` |
| F376 | Chore assign + verify task tracker | `home_automation.py` | `chore-tracker` | `python3 scripts/home_automation.py chore-tracker --assignee pilot --chore trash` |
| F377 | SIM7600G SMS on critical events | `comm_networking.py` | `sms-alert` | `python3 scripts/comm_networking.py sms-alert --to +91xxxxxxxxxx --msg intruder` |
| F378 | 4G failover internet + hotspot | `comm_networking.py` | `lte-failover` | `python3 scripts/comm_networking.py lte-failover --rssi -78 --clients 2` |
| F379 | WebRTC low-latency teleoperation | `comm_networking.py` | `teleop-web` | `python3 scripts/comm_networking.py teleop-web` |
| F380 | DSI + camera video-call bot | `comm_networking.py` | `video-call` | `python3 scripts/comm_networking.py video-call --to pilot@home.lan` |
| F381 | Walkie-talkie push-to-talk VoIP | `comm_networking.py` | `walkie-talkie` | `python3 scripts/comm_networking.py walkie-talkie` |
| F382 | Robot speaks custom message from phone | `comm_networking.py` | `tts-broadcast` | `python3 scripts/comm_networking.py tts-broadcast --text hello` |
| F383 | Slack/email notifications | `comm_networking.py` | `notifications-slack` | `python3 scripts/comm_networking.py notifications-slack --msg online` |
| F384 | MQTT bridge to Home Assistant | `comm_networking.py` | `mqtt-bridge` | `python3 scripts/comm_networking.py mqtt-bridge` |
| F385 | Node-RED / Blynk custom dashboard | `comm_networking.py` | `blynk-node-red` | `python3 scripts/comm_networking.py blynk-node-red --dash main` |
| F386 | ESP-NOW sensor mesh around house | `comm_networking.py` | `esp-now-mesh` | `python3 scripts/comm_networking.py esp-now-mesh` |
| F387 | BLE beacon scanner (presence) | `comm_networking.py` | `ble-scan` | `python3 scripts/comm_networking.py ble-scan --beacons 4` |
| F388 | NFC tag verification (medicine, tools) | `comm_networking.py` | `nfc-tag` | `python3 scripts/comm_networking.py nfc-tag --tag medicine-2026` |
| F389 | IR blaster for legacy TV/AC | `comm_networking.py` | `ir-blaster` | `python3 scripts/comm_networking.py ir-blaster --device tv_samsung --code POWER` |
| F390 | Zigbee coordinator | `comm_networking.py` | `zigbee-coord` | `python3 scripts/comm_networking.py zigbee-coord` |
| F391 | LoRaWAN long-range sensor node | `comm_networking.py` | `lorawan` | `python3 scripts/comm_networking.py lorawan` |
| F392 | Best Wi-Fi channel auto-selection | `comm_networking.py` | `wifi-channel` | `python3 scripts/comm_networking.py wifi-channel` |
| F393 | Internet speed-test scheduler | `comm_networking.py` | `speed-test` | `python3 scripts/comm_networking.py speed-test` |
| F394 | Remote SSH endpoint (secure) | `comm_networking.py` | `ssh-access` | `python3 scripts/comm_networking.py ssh-access` |
| F395 | Webhook receiver (IFTTT) | `comm_networking.py` | `webhook-receiver` | `python3 scripts/comm_networking.py webhook-receiver --port 9090` |
| F396 | RSS headline reader on DSI display | `comm_networking.py` | `rss-display` | `python3 scripts/comm_networking.py rss-display --feed hnrss.org/newest` |
| F397 | Full self-diagnostic of sensors/motors | `maintenance.py` | `self-diag` | `python3 scripts/maintenance.py self-diag` |
| F398 | Battery SoH + cycle-count estimate | `maintenance.py` | `battery-health` | `python3 scripts/maintenance.py battery-health` |
| F399 | Motor-stall detect -> cut power + alert | `maintenance.py` | `motor-stall` | `python3 scripts/maintenance.py motor-stall --current 18 --threshold 15` |
| F400 | Log rotation / prune | `maintenance.py` | `log-rotate` | `python3 scripts/maintenance.py log-rotate --keep 5` |
| F401 | Over-the-air firmware updates | `maintenance.py` | `ota` | `python3 scripts/maintenance.py ota --component eyes_esp32 --version 2026.07.27` |
| F402 | Servo-driven camera lens wiper | `maintenance.py` | `lens-clean` | `python3 scripts/maintenance.py lens-clean --cover 100` |
| F403 | CPU thermal-throttle on overtemp | `maintenance.py` | `thermal-throttle` | `python3 scripts/maintenance.py thermal-throttle --cpu-c 78` |
| F404 | Kernel-level watchdog timer (auto-reboot) | `maintenance.py` | `watchdog-timer` | `python3 scripts/maintenance.py watchdog-timer --seconds 30` |
| F405 | Encrypted cloud config backup | `maintenance.py` | `cloud-backup` | `python3 scripts/maintenance.py cloud-backup --provider s3` |
| F406 | Hardware-upgrade suggestion advisor | `maintenance.py` | `hardware-advisor` | `python3 scripts/maintenance.py hardware-advisor --since 7d` |

### Smoke test (F207 – F406)

```bash
cd "the tank project"
for s in scripts/{ai_vision,personality,security_bio,mobility_nav,environment,media_hub,home_automation,comm_networking,maintenance}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

# Total features documented: F001–F206 (existing) + F207–F406 (this batch) = 406 host-level features.
grep -E '^\| F[0-9]+' "the tank project/README.md" | wc -l   # -> 406
```

---

## Host utilities — 310 new feature plugins (F407 – F716)

A seventh batch of **11 host-level CLIs / 310 subcommands** for advanced AI, vision/AR, gaming, health, kitchen, education, art+photography, productivity+social, energy+cleaning, outdoor+security, and maker+misc features. Same offline-first convention as F001–F406.

### Feature index (F407 – F716)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F407 | AI butler pre-empts routines | `ai_voice.py` | `ai-butler` | `python3 scripts/ai_voice.py ai-butler` |
| F408 | Conversational memory | `ai_voice.py` | `conv-memory` | `python3 scripts/ai_voice.py conv-memory` |
| F409 | Mood journal + trends | `ai_voice.py` | `mood-journal` | `python3 scripts/ai_voice.py mood-journal --mood stressed` |
| F410 | Active-listening therapist light | `ai_voice.py` | `therapist` | `python3 scripts/ai_voice.py therapist` |
| F411 | Dream journal whisper capture | `ai_voice.py` | `dream-journal` | `python3 scripts/ai_voice.py dream-journal --text flew over tank` |
| F412 | Language learning partner | `ai_voice.py` | `language` | `python3 scripts/ai_voice.py language --target es` |
| F413 | Joke of the day | `ai_voice.py` | `joke` | `python3 scripts/ai_voice.py joke` |
| F414 | Riddle master with hints | `ai_voice.py` | `riddle` | `python3 scripts/ai_voice.py riddle --q easy` |
| F415 | AI story co-writer | `ai_voice.py` | `story-cowrite` | `python3 scripts/ai_voice.py story-cowrite` |
| F416 | Categorised idea board | `ai_voice.py` | `idea-board` | `python3 scripts/ai_voice.py idea-board --category invention --text self-watering pot` |
| F417 | Provocation brainstormer | `ai_voice.py` | `brainstorm` | `python3 scripts/ai_voice.py brainstorm --q rainy-saturday` |
| F418 | Memory palace (method of loci) | `ai_voice.py` | `memory-palace` | `python3 scripts/ai_voice.py memory-palace` |
| F419 | Lie-detector game (voice-stress) | `ai_voice.py` | `lie-detector` | `python3 scripts/ai_voice.py lie-detector` |
| F420 | Silly fortune teller | `ai_voice.py` | `fortune-teller` | `python3 scripts/ai_voice.py fortune-teller` |
| F421 | Time-capsule scheduled playback | `ai_voice.py` | `time-capsule` | `python3 scripts/ai_voice.py time-capsule --deliver 2027-12-25` |
| F422 | Custom wake word | `ai_voice.py` | `wake-word` | `python3 scripts/ai_voice.py wake-word --word buddy` |
| F423 | Multi-wake-word support | `ai_voice.py` | `multi-wake` | `python3 scripts/ai_voice.py multi-wake --triggers hey-tank hello-robot` |
| F424 | Voice cloning | `ai_voice.py` | `voice-clone` | `python3 scripts/ai_voice.py voice-clone --voice grandma` |
| F425 | Whisper mode | `ai_voice.py` | `whisper-mode` | `python3 scripts/ai_voice.py whisper-mode` |
| F426 | Child-friendly filter | `ai_voice.py` | `child-filter` | `python3 scripts/ai_voice.py child-filter --on` |
| F427 | Interrupt handling | `ai_voice.py` | `interrupt` | `python3 scripts/ai_voice.py interrupt` |
| F428 | Ambient conversation mode | `ai_voice.py` | `ambient` | `python3 scripts/ai_voice.py ambient` |
| F429 | Voice disguise | `ai_voice.py` | `voice-disguise` | `python3 scripts/ai_voice.py voice-disguise --voice darth` |
| F430 | Singing mode | `ai_voice.py` | `singing` | `python3 scripts/ai_voice.py singing --melody twinkle` |
| F431 | Accent training | `ai_voice.py` | `accent` | `python3 scripts/ai_voice.py accent --accent southern-us` |
| F432 | Sound effect recognition | `ai_voice.py` | `soundeffect` | `python3 scripts/ai_voice.py soundeffect --event doorbell` |
| F433 | Teleprompter mode | `ai_voice.py` | `teleprompter` | `python3 scripts/ai_voice.py teleprompter --wpm 140` |
| F434 | Voice-based timer | `ai_voice.py` | `voice-timer` | `python3 scripts/ai_voice.py voice-timer --minutes 12 --label pizza` |
| F435 | Multi-step command | `ai_voice.py` | `multistep` | `python3 scripts/ai_voice.py multistep` |
| F436 | Conversation with other robots | `ai_voice.py` | `other-robot` | `python3 scripts/ai_voice.py other-robot --peer tank-2` |
| F437 | Read-aloud from camera | `ai_voice.py` | `read-aloud` | `python3 scripts/ai_voice.py read-aloud --text hello` |
| F438 | Voice calculator | `ai_voice.py` | `voice-calc` | `python3 scripts/ai_voice.py voice-calc --q 17.5pct-of-230` |
| F439 | Voice unit converter | `ai_voice.py` | `unit-convert` | `python3 scripts/ai_voice.py unit-convert --fr cups --to liters --value 3` |
| F440 | Spelling bee | `ai_voice.py` | `spelling-bee` | `python3 scripts/ai_voice.py spelling-bee --word necessary --level hard` |
| F441 | Tongue-twister rater | `ai_voice.py` | `tongue-twisters` | `python3 scripts/ai_voice.py tongue-twisters --phrase "red-lorry"` |
| F442 | Virtual measuring tape | `vision_ar.py` | `virtualtape` | `python3 scripts/vision_ar.py virtualtape` |
| F443 | Color detector (color-blind aid) | `vision_ar.py` | `color-detect` | `python3 scripts/vision_ar.py color-detect` |
| F444 | Fashion consultant | `vision_ar.py` | `fashion-consult` | `python3 scripts/vision_ar.py fashion-consult` |
| F445 | Artwork identifier | `vision_ar.py` | `artwork-id` | `python3 scripts/vision_ar.py artwork-id` |
| F446 | Plant species identifier | `vision_ar.py` | `plant-species` | `python3 scripts/vision_ar.py plant-species` |
| F447 | Insect identifier | `vision_ar.py` | `insect-id` | `python3 scripts/vision_ar.py insect-id` |
| F448 | Calorie estimator (rough) | `vision_ar.py` | `calorie-estimate` | `python3 scripts/vision_ar.py calorie-estimate` |
| F449 | Puzzle solver (Sudoku/crossword) | `vision_ar.py` | `puzzle-solver` | `python3 scripts/vision_ar.py puzzle-solver` |
| F450 | AR furniture placement | `vision_ar.py` | `ar-furniture` | `python3 scripts/vision_ar.py ar-furniture` |
| F451 | Handwriting OCR | `vision_ar.py` | `handwritten-ocr` | `python3 scripts/vision_ar.py handwritten-ocr` |
| F452 | Monopoly banker (vision) | `vision_ar.py` | `monopoly-banker` | `python3 scripts/vision_ar.py monopoly-banker` |
| F453 | Card-game assistant | `vision_ar.py` | `card-assistant` | `python3 scripts/vision_ar.py card-assistant` |
| F454 | Breadboard wiring verifier | `vision_ar.py` | `breadboard-verify` | `python3 scripts/vision_ar.py breadboard-verify` |
| F455 | Resistor color-band reader | `vision_ar.py` | `resistor-color` | `python3 scripts/vision_ar.py resistor-color` |
| F456 | Solar sun tracker | `vision_ar.py` | `sun-tracker` | `python3 scripts/vision_ar.py sun-tracker` |
| F457 | Hide and seek | `gaming.py` | `hide-seek` | `python3 scripts/gaming.py hide-seek` |
| F458 | Laser-pointer chase (cat mode) | `gaming.py` | `laser-chase` | `python3 scripts/gaming.py laser-chase` |
| F459 | Red light / green light | `gaming.py` | `redlight-greenlight` | `python3 scripts/gaming.py redlight-greenlight` |
| F460 | Simon Says | `gaming.py` | `simon-says` | `python3 scripts/gaming.py simon-says` |
| F461 | Dance-off rating (with IMU tag) | `gaming.py` | `dance-rate` | `python3 scripts/gaming.py dance-rate` |
| F462 | Two-robot tag | `gaming.py` | `robot-tag` | `python3 scripts/gaming.py robot-tag` |
| F463 | Bowling with pin counting | `gaming.py` | `bowling` | `python3 scripts/gaming.py bowling` |
| F464 | Audio-clue treasure hunt | `gaming.py` | `treasure-hunt` | `python3 scripts/gaming.py treasure-hunt` |
| F465 | Mini-golf caddy | `gaming.py` | `mini-golf` | `python3 scripts/gaming.py mini-golf` |
| F466 | Escape room puzzle master | `gaming.py` | `escape-room` | `python3 scripts/gaming.py escape-room` |
| F467 | Karaoke scoring (comedic) | `gaming.py` | `karaoke-score` | `python3 scripts/gaming.py karaoke-score` |
| F468 | GPIO-butzer trivia | `gaming.py` | `trivia-buzzer` | `python3 scripts/gaming.py trivia-buzzer` |
| F469 | Pictionary on touchscreen | `gaming.py` | `pictionary` | `python3 scripts/gaming.py pictionary` |
| F470 | Charades via eyes/motion | `gaming.py` | `charades` | `python3 scripts/gaming.py charades` |
| F471 | Reaction time tester | `gaming.py` | `reaction-time` | `python3 scripts/gaming.py reaction-time` |
| F472 | Memory card pairs game | `gaming.py` | `memory-cards` | `python3 scripts/gaming.py memory-cards` |
| F473 | Two-player math duel | `gaming.py` | `math-duel` | `python3 scripts/gaming.py math-duel` |
| F474 | Robot soccer league (1v1) | `gaming.py` | `robot-soccer` | `python3 scripts/gaming.py robot-soccer` |
| F475 | Tug-of-war (rope) | `gaming.py` | `tug-of-war` | `python3 scripts/gaming.py tug-of-war` |
| F476 | Virtual pet battles over network | `gaming.py` | `pet-battles` | `python3 scripts/gaming.py pet-battles` |
| F477 | Fitness coach rep counter | `health.py` | `fitness-coach` | `python3 scripts/health.py fitness-coach` |
| F478 | Posture monitor | `health.py` | `posture-monitor` | `python3 scripts/health.py posture-monitor` |
| F479 | Hydration reminder | `health.py` | `hydration` | `python3 scripts/health.py hydration` |
| F480 | Servo pill dispenser | `health.py` | `med-dispenser` | `python3 scripts/health.py med-dispenser` |
| F481 | Sleep sound analyser | `health.py` | `sleep-sound` | `python3 scripts/health.py sleep-sound` |
| F482 | Stretch-break enforcer | `health.py` | `stretch-break` | `python3 scripts/health.py stretch-break --minutes 45` |
| F483 | Ergonomic workstation check | `health.py` | `ergonomic` | `python3 scripts/health.py ergonomic` |
| F484 | Hand-wash 20-s timer | `health.py` | `handwash-timer` | `python3 scripts/health.py handwash-timer` |
| F485 | Quarantine companion | `health.py` | `quarantine-companion` | `python3 scripts/health.py quarantine-companion` |
| F486 | Fall detection + emergency call | `health.py` | `fall-detect` | `python3 scripts/health.py fall-detect` |
| F487 | Cough analyser | `health.py` | `cough-analyser` | `python3 scripts/health.py cough-analyser` |
| F488 | Allergy + pollen forecaster | `health.py` | `allergy` | `python3 scripts/health.py allergy` |
| F489 | UV sunburn timer | `health.py` | `sunburn` | `python3 scripts/health.py sunburn` |
| F490 | Blood-pressure monitor integration | `health.py` | `bp-monitor` | `python3 scripts/health.py bp-monitor` |
| F491 | Smart weight scale integration | `health.py` | `weight-scale` | `python3 scripts/health.py weight-scale` |
| F492 | Menstrual cycle tracker | `health.py` | `cycle-tracker` | `python3 scripts/health.py cycle-tracker` |
| F493 | 60-second mindful minute | `health.py` | `mindful-minute` | `python3 scripts/health.py mindful-minute` |
| F494 | Gratitude journal | `health.py` | `gratitude-journal` | `python3 scripts/health.py gratitude-journal` |
| F495 | Daily compliment generator | `health.py` | `compliment` | `python3 scripts/health.py compliment` |
| F496 | Digital detox nudges | `health.py` | `digital-detox` | `python3 scripts/health.py digital-detox` |
| F497 | Voice-driven recipe reader | `kitchen.py` | `recipe-reader` | `python3 scripts/kitchen.py recipe-reader` |
| F498 | Visual timer dashboard | `kitchen.py` | `timer-dashboard` | `python3 scripts/kitchen.py timer-dashboard` |
| F499 | Ingredient substitute suggester | `kitchen.py` | `ingredient-substitute` | `python3 scripts/kitchen.py ingredient-substitute --missing eggs` |
| F500 | Voice unit converter (metric-imperial) | `kitchen.py` | `measure-converter` | `python3 scripts/kitchen.py measure-converter` |
| F501 | Oven preheat reminder | `kitchen.py` | `oven-preheat` | `python3 scripts/kitchen.py oven-preheat` |
| F502 | Shopping-list generator | `kitchen.py` | `shopping-gen` | `python3 scripts/kitchen.py shopping-gen` |
| F503 | Fridge inventory + meal suggest | `kitchen.py` | `fridge-inventory` | `python3 scripts/kitchen.py fridge-inventory` |
| F504 | Expiry date tracker | `kitchen.py` | `expiry-tracker` | `python3 scripts/kitchen.py expiry-tracker` |
| F505 | Wine pairing from dinner photo | `kitchen.py` | `wine-pairing` | `python3 scripts/kitchen.py wine-pairing` |
| F506 | Pour-over coffee log | `kitchen.py` | `coffee-log` | `python3 scripts/kitchen.py coffee-log` |
| F507 | Spice identifier (camera) | `kitchen.py` | `spice-id` | `python3 scripts/kitchen.py spice-id` |
| F508 | Knife sharpening reminder | `kitchen.py` | `knife-sharpen` | `python3 scripts/kitchen.py knife-sharpen` |
| F509 | Table-setting diagram | `kitchen.py` | `table-setting` | `python3 scripts/kitchen.py table-setting` |
| F510 | Cocktail recipe from ingredients | `kitchen.py` | `cocktail-recipe` | `python3 scripts/kitchen.py cocktail-recipe` |
| F511 | Leftovers freshness timer | `kitchen.py` | `leftovers-timer` | `python3 scripts/kitchen.py leftovers-timer` |
| F512 | Step-by-step math tutor | `education.py` | `math-tutor` | `python3 scripts/education.py math-tutor` |
| F513 | Flashcard maker from photos | `education.py` | `flashcard-maker` | `python3 scripts/education.py flashcard-maker` |
| F514 | Periodic table quiz | `education.py` | `periodic-quiz` | `python3 scripts/education.py periodic-quiz` |
| F515 | Geography bee | `education.py` | `geo-bee` | `python3 scripts/education.py geo-bee` |
| F516 | Historical-figure AI chat | `education.py` | `historical-chat` | `python3 scripts/education.py historical-chat --person einstein` |
| F517 | Typing tutor | `education.py` | `typing-tutor` | `python3 scripts/education.py typing-tutor` |
| F518 | Spelling practice | `education.py` | `spelling` | `python3 scripts/education.py spelling` |
| F519 | Coding teacher | `education.py` | `coding-teach` | `python3 scripts/education.py coding-teach --lang python` |
| F520 | Safe home science experiments | `education.py` | `science-experiments` | `python3 scripts/education.py science-experiments` |
| F521 | Book-cover summary | `education.py` | `book-summary` | `python3 scripts/education.py book-summary` |
| F522 | Web research assistant | `education.py` | `research` | `python3 scripts/education.py research --topic blackholes` |
| F523 | APA/MLA citation generator | `education.py` | `citation-gen` | `python3 scripts/education.py citation-gen --style apa` |
| F524 | Public-speaking coach | `education.py` | `public-speaking` | `python3 scripts/education.py public-speaking` |
| F525 | Study-session note bot | `education.py` | `note-bot` | `python3 scripts/education.py note-bot` |
| F526 | Mock exam from notes | `education.py` | `mock-exam` | `python3 scripts/education.py mock-exam` |
| F527 | AI art critic | `creativity.py` | `ai-art-critic` | `python3 scripts/creativity.py ai-art-critic` |
| F528 | Collaborative drawing | `creativity.py` | `collab-draw` | `python3 scripts/creativity.py collab-draw` |
| F529 | Time-lapse robot mover | `creativity.py` | `timelapse-move` | `python3 scripts/creativity.py timelapse-move` |
| F530 | Photogrammetry 3D scan | `creativity.py` | `3d-scan` | `python3 scripts/creativity.py 3d-scan` |
| F531 | Story illustrator | `creativity.py` | `story-illustrate` | `python3 scripts/creativity.py story-illustrate` |
| F532 | Poetry generator | `creativity.py` | `poetry` | `python3 scripts/creativity.py poetry --form haiku` |
| F533 | Music composer with hummed input | `creativity.py` | `music-composer` | `python3 scripts/creativity.py music-composer` |
| F534 | Tap-loop drum machine | `creativity.py` | `drum-machine` | `python3 scripts/creativity.py drum-machine` |
| F535 | Live kaleidoscope mode | `creativity.py` | `kaleidoscope` | `python3 scripts/creativity.py kaleidoscope` |
| F536 | Photo → pixel art | `creativity.py` | `pixel-art` | `python3 scripts/creativity.py pixel-art` |
| F537 | Meme generator | `creativity.py` | `meme-gen` | `python3 scripts/creativity.py meme-gen` |
| F538 | Voice-over artist | `creativity.py` | `voice-over` | `python3 scripts/creativity.py voice-over` |
| F539 | Soundscape creator | `creativity.py` | `soundscape` | `python3 scripts/creativity.py soundscape` |
| F540 | Digital graffiti wall | `creativity.py` | `digital-graffiti` | `python3 scripts/creativity.py digital-graffiti` |
| F541 | DIY craft assistant | `creativity.py` | `diy-craft` | `python3 scripts/creativity.py diy-craft` |
| F542 | Smart photo booth | `creativity.py` | `photo-booth` | `python3 scripts/creativity.py photo-booth` |
| F543 | Stop-motion studio | `creativity.py` | `stop-motion` | `python3 scripts/creativity.py stop-motion` |
| F544 | Hyperlapse walk | `creativity.py` | `hyperlapse` | `python3 scripts/creativity.py hyperlapse` |
| F545 | 360 panorama stitch | `creativity.py` | `360-pano` | `python3 scripts/creativity.py 360-pano` |
| F546 | Long-exposure stabiliser | `creativity.py` | `long-exposure` | `python3 scripts/creativity.py long-exposure` |
| F547 | Product turntable | `creativity.py` | `product-turntable` | `python3 scripts/creativity.py product-turntable` |
| F548 | Overhead document scanner | `creativity.py` | `doc-scanner` | `python3 scripts/creativity.py doc-scanner` |
| F549 | Photo sorting (faces/places) | `creativity.py` | `photo-sort` | `python3 scripts/creativity.py photo-sort` |
| F550 | Drone-style follow shot | `creativity.py` | `follow-shot` | `python3 scripts/creativity.py follow-shot` |
| F551 | Wildlife camera trap | `creativity.py` | `wildlife-trap` | `python3 scripts/creativity.py wildlife-trap` |
| F552 | Under-car low-profile camera | `creativity.py` | `under-car` | `python3 scripts/creativity.py under-car` |
| F553 | Plant time-lapse | `creativity.py` | `plant-timelapse` | `python3 scripts/creativity.py plant-timelapse` |
| F554 | Event candid photographer | `creativity.py` | `event-photog` | `python3 scripts/creativity.py event-photog` |
| F555 | Group selfie droner | `creativity.py` | `selfie-drone` | `python3 scripts/creativity.py selfie-drone` |
| F556 | AR props in photo booth | `creativity.py` | `ar-props` | `python3 scripts/creativity.py ar-props` |
| F557 | Pomodoro 25-min timer | `productivity_social.py` | `pomodoro` | `python3 scripts/productivity_social.py pomodoro` |
| F558 | Focus mode + DND | `productivity_social.py` | `focus-mode` | `python3 scripts/productivity_social.py focus-mode` |
| F559 | Stand-up meeting bot (pan-tilt) | `productivity_social.py` | `standup-bot` | `python3 scripts/productivity_social.py standup-bot` |
| F560 | Whiteboard capture + share | `productivity_social.py` | `whiteboard-cap` | `python3 scripts/productivity_social.py whiteboard-cap` |
| F561 | Household sticky notes | `productivity_social.py` | `sticky-notes` | `python3 scripts/productivity_social.py sticky-notes` |
| F562 | Meeting minute summariser | `productivity_social.py` | `meeting-minutes` | `python3 scripts/productivity_social.py meeting-minutes` |
| F563 | Calendar butler (announce) | `productivity_social.py` | `calendar-butler` | `python3 scripts/productivity_social.py calendar-butler` |
| F564 | Desk-plant water reminder | `productivity_social.py` | `desk-water` | `python3 scripts/productivity_social.py desk-water` |
| F565 | Ergonomic desk-stretch leader | `productivity_social.py` | `ergo-break` | `python3 scripts/productivity_social.py ergo-break` |
| F566 | Under-desk cable inspector (light) | `productivity_social.py` | `cable-mgmt` | `python3 scripts/productivity_social.py cable-mgmt` |
| F567 | Printer assistant + ink order | `productivity_social.py` | `printer-assist` | `python3 scripts/productivity_social.py printer-assist` |
| F568 | Package opener holder | `productivity_social.py` | `package-opener` | `python3 scripts/productivity_social.py package-opener` |
| F569 | Home-office CO2 alert | `productivity_social.py` | `air-quality` | `python3 scripts/productivity_social.py air-quality` |
| F570 | Auto video-call lighting | `productivity_social.py` | `light-control` | `python3 scripts/productivity_social.py light-control` |
| F571 | Background concentration music | `productivity_social.py` | `bg-music` | `python3 scripts/productivity_social.py bg-music` |
| F572 | Telepresence avatar | `productivity_social.py` | `telepresence` | `python3 scripts/productivity_social.py telepresence` |
| F573 | Voice social-media upload | `productivity_social.py` | `social-upload` | `python3 scripts/productivity_social.py social-upload` |
| F574 | Visitor video guestbook | `productivity_social.py` | `guestbook` | `python3 scripts/productivity_social.py guestbook` |
| F575 | Robot playdate (online chat) | `productivity_social.py` | `robot-playdate` | `python3 scripts/productivity_social.py robot-playdate` |
| F576 | Online robot race | `productivity_social.py` | `robot-race` | `python3 scripts/productivity_social.py robot-race` |
| F577 | Multi-robot fleet manager | `productivity_social.py` | `fleet-mgmt` | `python3 scripts/productivity_social.py fleet-mgmt` |
| F578 | Video postcard recorder | `productivity_social.py` | `video-postcard` | `python3 scripts/productivity_social.py video-postcard` |
| F579 | Neighborhood watch network | `productivity_social.py` | `neighborhood-watch` | `python3 scripts/productivity_social.py neighborhood-watch` |
| F580 | Birthday parade coordination | `productivity_social.py` | `birthday-parade` | `python3 scripts/productivity_social.py birthday-parade` |
| F581 | Tamagotchi pet meetup | `productivity_social.py` | `pet-meetup` | `python3 scripts/productivity_social.py pet-meetup` |
| F582 | Skill store downloader | `productivity_social.py` | `skill-store` | `python3 scripts/productivity_social.py skill-store` |
| F583 | Remote babysitter | `productivity_social.py` | `remote-babysitter` | `python3 scripts/productivity_social.py remote-babysitter` |
| F584 | Date-night package | `productivity_social.py` | `date-night` | `python3 scripts/productivity_social.py date-night` |
| F585 | Scavenger-hunt creator/verifier | `productivity_social.py` | `scavenger-hunt` | `python3 scripts/productivity_social.py scavenger-hunt` |
| F586 | Annual highlight reel | `productivity_social.py` | `highlight-reel` | `python3 scripts/productivity_social.py highlight-reel` |
| F587 | Smart charging dock | `energy_home.py` | `smart-dock` | `python3 scripts/energy_home.py smart-dock` |
| F588 | Solar charge controller | `energy_home.py` | `solar-controller` | `python3 scripts/energy_home.py solar-controller` |
| F589 | Battery swap reminder | `energy_home.py` | `battery-swap` | `python3 scripts/energy_home.py battery-swap` |
| F590 | Live power-usage dashboard | `energy_home.py` | `power-dashboard` | `python3 scripts/energy_home.py power-dashboard` |
| F591 | Generator auto-start relay | `energy_home.py` | `generator-autostart` | `python3 scripts/energy_home.py generator-autostart` |
| F592 | UPS status + graceful shutdown | `energy_home.py` | `ups-monitor` | `python3 scripts/energy_home.py ups-monitor` |
| F593 | Peak/off-peak heavy-task scheduler | `energy_home.py` | `peak-scheduler` | `python3 scripts/energy_home.py peak-scheduler` |
| F594 | Battery health (internal R) report | `energy_home.py` | `batt-health` | `python3 scripts/energy_home.py batt-health` |
| F595 | Qi-pad alignment helper | `energy_home.py` | `qi-alignment` | `python3 scripts/energy_home.py qi-alignment` |
| F596 | Power-outage LTE SMS | `energy_home.py` | `power-out-alert` | `python3 scripts/energy_home.py power-out-alert` |
| F597 | Energy-saving suggestions | `energy_home.py` | `energy-tips` | `python3 scripts/energy_home.py energy-tips` |
| F598 | Appliance power meter (smart plug) | `energy_home.py` | `smart-plug` | `python3 scripts/energy_home.py smart-plug` |
| F599 | Solar-yield forecast | `energy_home.py` | `solar-yield` | `python3 scripts/energy_home.py solar-yield` |
| F600 | Battery-storage simulator | `energy_home.py` | `storage-sim` | `python3 scripts/energy_home.py storage-sim` |
| F601 | 4S Li-ion per-cell voltage | `energy_home.py` | `4s-cell-monitor` | `python3 scripts/energy_home.py 4s-cell-monitor` |
| F602 | Autonomous dust mop | `energy_home.py` | `auto-dusting` | `python3 scripts/energy_home.py auto-dusting` |
| F603 | Spill detector | `energy_home.py` | `spill-detect` | `python3 scripts/energy_home.py spill-detect` |
| F604 | Sock-collecting robot | `energy_home.py` | `sock-bot` | `python3 scripts/energy_home.py sock-bot` |
| F605 | Robot vacuum IR trigger | `energy_home.py` | `vacuum-ir` | `python3 scripts/energy_home.py vacuum-ir` |
| F606 | Trash-can escort | `energy_home.py` | `trash-escort` | `python3 scripts/energy_home.py trash-escort` |
| F607 | Window-cleaner squeegee attach | `energy_home.py` | `window-cleaner` | `python3 scripts/energy_home.py window-cleaner` |
| F608 | Air freshener actuator | `energy_home.py` | `air-freshener` | `python3 scripts/energy_home.py air-freshener` |
| F609 | Plant watering peristaltic pump | `energy_home.py` | `plant-water` | `python3 scripts/energy_home.py plant-water` |
| F610 | Pet waste spot-detector | `energy_home.py` | `pet-waste` | `python3 scripts/energy_home.py pet-waste` |
| F611 | Lego colour/shape sorter | `energy_home.py` | `lego-sorter` | `python3 scripts/energy_home.py lego-sorter` |
| F612 | Laundry basket transport | `energy_home.py` | `laundry-transport` | `python3 scripts/energy_home.py laundry-transport` |
| F613 | Shoe polisher holder | `energy_home.py` | `shoe-polish` | `python3 scripts/energy_home.py shoe-polish` |
| F614 | Silverfish/pest chaser | `energy_home.py` | `silverfish-patrol` | `python3 scripts/energy_home.py silverfish-patrol` |
| F615 | Room essential-oil deodorizer | `energy_home.py` | `room-deo` | `python3 scripts/energy_home.py room-deo` |
| F616 | Door opener arm | `energy_home.py` | `door-opener` | `python3 scripts/energy_home.py door-opener` |
| F617 | Off-road outdoor explorer | `outdoor_security.py` | `off-road-explorer` | `python3 scripts/outdoor_security.py off-road-explorer` |
| F618 | Driveway snowplow | `outdoor_security.py` | `snowplow` | `python3 scripts/outdoor_security.py snowplow` |
| F619 | Rake-attach leaf sweeper | `outdoor_security.py` | `leaf-sweeper` | `python3 scripts/outdoor_security.py leaf-sweeper` |
| F620 | Garden bird-scarer | `outdoor_security.py` | `garden-scarecrow` | `python3 scripts/outdoor_security.py garden-scarecrow` |
| F621 | Compost pile turner | `outdoor_security.py` | `compost-turner` | `python3 scripts/outdoor_security.py compost-turner` |
| F622 | Campfire log carry + monitor | `outdoor_security.py` | `campfire` | `python3 scripts/outdoor_security.py campfire` |
| F623 | Stargazing constellation guide | `outdoor_security.py` | `stargazer` | `python3 scripts/outdoor_security.py stargazer` |
| F624 | Outdoor-projector leveller | `outdoor_security.py` | `outdoor-movie` | `python3 scripts/outdoor_security.py outdoor-movie` |
| F625 | Frisbee return | `outdoor_security.py` | `frisbee-return` | `python3 scripts/outdoor_security.py frisbee-return` |
| F626 | Metal detector add-on | `outdoor_security.py` | `metal-detect` | `python3 scripts/outdoor_security.py metal-detect` |
| F627 | Pond net skimmer | `outdoor_security.py` | `pond-skim` | `python3 scripts/outdoor_security.py pond-skim` |
| F628 | Bird-call broadcaster + response recorder | `outdoor_security.py` | `wildlife-caller` | `python3 scripts/outdoor_security.py wildlife-caller` |
| F629 | Greenhouse temp/humidity/vent | `outdoor_security.py` | `greenhouse` | `python3 scripts/outdoor_security.py greenhouse` |
| F630 | Berry ripeness detector | `outdoor_security.py` | `berry-picker` | `python3 scripts/outdoor_security.py berry-picker` |
| F631 | GPS hiking guide + water carrier | `outdoor_security.py` | `hiking-guide` | `python3 scripts/outdoor_security.py hiking-guide` |
| F632 | Decoy mode (TV-light simulation) | `outdoor_security.py` | `decoy-mode` | `python3 scripts/outdoor_security.py decoy-mode` |
| F633 | Laser tripwire + mirror | `outdoor_security.py` | `laser-tripwire` | `python3 scripts/outdoor_security.py laser-tripwire` |
| F634 | Safe fog machine trigger | `outdoor_security.py` | `fog-trigger` | `python3 scripts/outdoor_security.py fog-trigger` |
| F635 | Car-parking ultrasonic alert | `outdoor_security.py` | `parking-sensor` | `python3 scripts/outdoor_security.py parking-sensor` |
| F636 | Drone-noise audio detector | `outdoor_security.py` | `drone-detect` | `python3 scripts/outdoor_security.py drone-detect` |
| F637 | Voice-stress lie check | `outdoor_security.py` | `voice-stress-sec` | `python3 scripts/outdoor_security.py voice-stress-sec` |
| F638 | Fake cam shutter motion | `outdoor_security.py` | `fake-cam` | `python3 scripts/outdoor_security.py fake-cam` |
| F639 | GPS+LTE virtual fence | `outdoor_security.py` | `virtual-fence` | `python3 scripts/outdoor_security.py virtual-fence` |
| F640 | Loud-bark bark-back | `outdoor_security.py` | `bark-back` | `python3 scripts/outdoor_security.py bark-back` |
| F641 | Silent SMS-only alarm | `outdoor_security.py` | `silent-alarm` | `python3 scripts/outdoor_security.py silent-alarm` |
| F642 | Powerline comms backup | `outdoor_security.py` | `plc-backup` | `python3 scripts/outdoor_security.py plc-backup` |
| F643 | Window-break glass-frequency alarm | `outdoor_security.py` | `window-break` | `python3 scripts/outdoor_security.py window-break` |
| F644 | Loud amp air-horn | `outdoor_security.py` | `air-horn` | `python3 scripts/outdoor_security.py air-horn` |
| F645 | Strobe-LED disorient | `outdoor_security.py` | `strobe-led` | `python3 scripts/outdoor_security.py strobe-led` |
| F646 | Safeword alarm cancel | `outdoor_security.py` | `safeword` | `python3 scripts/outdoor_security.py safeword` |
| F647 | ROS2 tutorial node runner | `maker_misc.py` | `ros2-tutorial` | `python3 scripts/maker_misc.py ros2-tutorial` |
| F648 | On-screen Python sandbox | `maker_misc.py` | `python-sandbox` | `python3 scripts/maker_misc.py python-sandbox` |
| F649 | Electronics-lab assistant | `maker_misc.py` | `electronics-lab` | `python3 scripts/maker_misc.py electronics-lab` |
| F650 | Soldering iron temp timer | `maker_misc.py` | `soldering-timer` | `python3 scripts/maker_misc.py soldering-timer` |
| F651 | 3D print spaghetti-failure watch | `maker_misc.py` | `3dprint-watch` | `python3 scripts/maker_misc.py 3dprint-watch` |
| F652 | CNC workpiece-still check | `maker_misc.py` | `cnc-observer` | `python3 scripts/maker_misc.py cnc-observer` |
| F653 | Laser-engraver flame safety | `maker_misc.py` | `laser-safety` | `python3 scripts/maker_misc.py laser-safety` |
| F654 | Drone landing-pad marker | `maker_misc.py` | `drone-pad` | `python3 scripts/maker_misc.py drone-pad` |
| F655 | SDR ham-radio scanner | `maker_misc.py` | `ham-radio` | `python3 scripts/maker_misc.py ham-radio` |
| F656 | IoT ESP32 sensor graph hub | `maker_misc.py` | `iot-hub` | `python3 scripts/maker_misc.py iot-hub` |
| F657 | Retro game emulator | `maker_misc.py` | `retro-game` | `python3 scripts/maker_misc.py retro-game` |
| F658 | Rotary phone pulse dialer | `maker_misc.py` | `rotary-phone` | `python3 scripts/maker_misc.py rotary-phone` |
| F659 | Morse-code audio tutor | `maker_misc.py` | `morse-tutor` | `python3 scripts/maker_misc.py morse-tutor` |
| F660 | NTP-server atomic clock | `maker_misc.py` | `ntp-clock` | `python3 scripts/maker_misc.py ntp-clock` |
| F661 | Wet-rock weather oracle (joke) | `maker_misc.py` | `weather-rock` | `python3 scripts/maker_misc.py weather-rock` |
| F662 | Sunlight-projection sundial | `maker_misc.py` | `digital-sundial` | `python3 scripts/maker_misc.py digital-sundial` |
| F663 | Balloon-pop mic counter | `maker_misc.py` | `balloon-counter` | `python3 scripts/maker_misc.py balloon-counter` |
| F664 | Halloween voice changer | `maker_misc.py` | `voice-mask` | `python3 scripts/maker_misc.py voice-mask` |
| F665 | One-way-mirror magic info | `maker_misc.py` | `magic-mirror` | `python3 scripts/maker_misc.py magic-mirror` |
| F666 | Robot podcast host | `maker_misc.py` | `podcast-host` | `python3 scripts/maker_misc.py podcast-host` |
| F667 | Emotion-driven playlist picker | `maker_misc.py` | `emotion-music` | `python3 scripts/maker_misc.py emotion-music` |
| F668 | Daily smile count | `maker_misc.py` | `smile-counter` | `python3 scripts/maker_misc.py smile-counter` |
| F669 | Silly ghost detector | `maker_misc.py` | `ghost-detector` | `python3 scripts/maker_misc.py ghost-detector` |
| F670 | Dramatic time-machine announcer | `maker_misc.py` | `time-machine` | `python3 scripts/maker_misc.py time-machine` |
| F671 | Inter-robot beep language | `maker_misc.py` | `inter-robot-lang` | `python3 scripts/maker_misc.py inter-robot-lang` |
| F672 | Selfie-stick pan-tilt arm | `maker_misc.py` | `selfie-stick` | `python3 scripts/maker_misc.py selfie-stick` |
| F673 | Robot sun-salutation yoga | `maker_misc.py` | `yoga` | `python3 scripts/maker_misc.py yoga` |
| F674 | Pick-a-card magic trick | `maker_misc.py` | `magic-trick` | `python3 scripts/maker_misc.py magic-trick` |
| F675 | Balloon-animal twisting | `maker_misc.py` | `balloon-animal` | `python3 scripts/maker_misc.py balloon-animal` |
| F676 | Hold-and-shake blender button | `maker_misc.py` | `smoothie` | `python3 scripts/maker_misc.py smoothie` |
| F677 | Peristaltic-pump mini-bar | `maker_misc.py` | `mini-bar` | `python3 scripts/maker_misc.py mini-bar` |
| F678 | Fruit ripeness camera check | `maker_misc.py` | `fruit-check` | `python3 scripts/maker_misc.py fruit-check` |
| F679 | Carpool car-Bluetooth karaoke | `maker_misc.py` | `carpool-karaoke` | `python3 scripts/maker_misc.py carpool-karaoke` |
| F680 | Marriage ceremony officiant script | `maker_misc.py` | `marriage-officiant` | `python3 scripts/maker_misc.py marriage-officiant` |
| F681 | Personal phone ringtone | `maker_misc.py` | `ringtone` | `python3 scripts/maker_misc.py ringtone` |
| F682 | Tablet walking-pet display | `maker_misc.py` | `pet-walker` | `python3 scripts/maker_misc.py pet-walker` |
| F683 | GPS+pothole logs reporter | `maker_misc.py` | `pothole-reporter` | `python3 scripts/maker_misc.py pothole-reporter` |
| F684 | Sponge+water graffiti cleaner | `maker_misc.py` | `graffiti-cleaner` | `python3 scripts/maker_misc.py graffiti-cleaner` |
| F685 | Cup-dispense lemonade stand | `maker_misc.py` | `lemonade-stand` | `python3 scripts/maker_misc.py lemonade-stand` |
| F686 | Hourly AI-art gallery display | `maker_misc.py` | `art-gallery` | `python3 scripts/maker_misc.py art-gallery` |
| F687 | Autobiographer daily diary | `maker_misc.py` | `autobiographer` | `python3 scripts/maker_misc.py autobiographer` |
| F688 | Far-robot virtual-window feed | `maker_misc.py` | `virtual-window` | `python3 scripts/maker_misc.py virtual-window` |
| F689 | Robot-to-robot sleepover stories | `maker_misc.py` | `sleepover` | `python3 scripts/maker_misc.py sleepover` |
| F690 | UV-led invisible-ink decoder | `maker_misc.py` | `uv-decoder` | `python3 scripts/maker_misc.py uv-decoder` |
| F691 | Sundial-time compass | `maker_misc.py` | `sundial-compass` | `python3 scripts/maker_misc.py sundial-compass` |
| F692 | Tea-type steeping timer | `maker_misc.py` | `tea-timer` | `python3 scripts/maker_misc.py tea-timer` |
| F693 | Warm-spot bread-dough proofer | `maker_misc.py` | `bread-proofer` | `python3 scripts/maker_misc.py bread-proofer` |
| F694 | Fan+heater near wet shoes | `maker_misc.py` | `shoe-dryer` | `python3 scripts/maker_misc.py shoe-dryer` |
| F695 | Camera umpire ball/strike | `maker_misc.py` | `robot-umpire` | `python3 scripts/maker_misc.py robot-umpire` |
| F696 | Relay-fired (safe) fireworks | `maker_misc.py` | `fireworks-launcher` | `python3 scripts/maker_misc.py fireworks-launcher` |
| F697 | Spinning-wheel tennis launcher | `maker_misc.py` | `ball-launcher` | `python3 scripts/maker_misc.py ball-launcher` |
| F698 | Random feather-wand flailer | `maker_misc.py` | `cat-teaser` | `python3 scripts/maker_misc.py cat-teaser` |
| F699 | Water squirt to deter squirrels | `maker_misc.py` | `squirrel-squirt` | `python3 scripts/maker_misc.py squirrel-squirt` |
| F700 | Sign + speak to delivery driver | `maker_misc.py` | `package-accept` | `python3 scripts/maker_misc.py package-accept` |
| F701 | Laser-gate lap race timer | `maker_misc.py` | `race-timer` | `python3 scripts/maker_misc.py race-timer` |
| F702 | Marble-track designer/verifier | `maker_misc.py` | `marble-run` | `python3 scripts/maker_misc.py marble-run` |
| F703 | Holds your legs for sit-ups | `maker_misc.py` | `robot-stretching` | `python3 scripts/maker_misc.py robot-stretching` |
| F704 | Remote-controlled sauna ladle | `maker_misc.py` | `sauna-ladle` | `python3 scripts/maker_misc.py sauna-ladle` |
| F705 | Stick rotator over fire | `maker_misc.py` | `marshmallow-roaster` | `python3 scripts/maker_misc.py marshmallow-roaster` |
| F706 | Thermal-print fortune | `maker_misc.py` | `fortune-print` | `python3 scripts/maker_misc.py fortune-print` |
| F707 | Cotton-swab safety holder | `maker_misc.py` | `ear-cleaner` | `python3 scripts/maker_misc.py ear-cleaner` |
| F708 | Round-display crystal ball | `maker_misc.py` | `crystal-ball` | `python3 scripts/maker_misc.py crystal-ball` |
| F709 | Voice-password party bouncer | `maker_misc.py` | `bouncer` | `python3 scripts/maker_misc.py bouncer` |
| F710 | Multi-headphone silent disco | `maker_misc.py` | `silent-disco` | `python3 scripts/maker_misc.py silent-disco` |
| F711 | Gentle-voice pet calmer | `maker_misc.py` | `whisperer` | `python3 scripts/maker_misc.py whisperer` |
| F712 | Board-game piece mover | `maker_misc.py` | `board-mover` | `python3 scripts/maker_misc.py board-mover` |
| F713 | Beam-break laser harp | `maker_misc.py` | `laser-harp` | `python3 scripts/maker_misc.py laser-harp` |
| F714 | Marionette controller | `maker_misc.py` | `puppet` | `python3 scripts/maker_misc.py puppet` |
| F715 | Magic-show fog machine | `maker_misc.py` | `fog-show` | `python3 scripts/maker_misc.py fog-show` |
| F716 | Toy car wash line | `maker_misc.py` | `car-wash` | `python3 scripts/maker_misc.py car-wash --pancake-flipper fallback` |

### Smoke test (F407 – F716)

```bash
cd "the tank project"
for s in scripts/{ai_voice,vision_ar,gaming,health,kitchen,education,creativity,productivity_social,energy_home,outdoor_security,maker_misc}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

# Total feature IDs documented: F001-F206 (206) + F207-F406 (200) + F407-F716 (310) = 716.
grep -E "^\| F[0-9]+ \|" "the tank project/README.md" | wc -l   # -> 716
```

---

## Host utilities - 50 Simple-Internet high-impact features (round 3, items 401-450) (F1117 - F1166)

Round-3 closes the Simple Internet gap: cloud & sync hooks, AI-driven smart features, power-user tooling, and community/sharing. Each feature is a host-level CLI subcommand following the same offline-first pattern as F717-F916 and F917-F1116.

> The accompanying architecture write-up (UIs, Core Service, Download Engine, Media Resolver, Post-Processing, Search & Discovery, Scheduler, Security/Privacy, Storage, Plugin System, Cloud/Remote) lives outside the repo as design guidance; the CLIs here document the *surface area* each module exposes.

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F1117 | Google Drive upload after download | `download_cloud_3.py` | `cloud-upload-gdrive` | `python3 scripts/download_cloud_3.py cloud-upload-gdrive` |
| F1118 | encrypted cross-device queue/history | `download_cloud_3.py` | `cloud-sync-queue` | `python3 scripts/download_cloud_3.py cloud-sync-queue` |
| F1119 | phone-link send-to-PC | `download_cloud_3.py` | `remote-start-download` | `python3 scripts/download_cloud_3.py remote-start-download` |
| F1120 | Telegram bot URL intake | `download_cloud_3.py` | `telegram-bot-add` | `python3 scripts/download_cloud_3.py telegram-bot-add` |
| F1121 | forward email links to grabber | `download_cloud_3.py` | `email-to-download` | `python3 scripts/download_cloud_3.py email-to-download` |
| F1122 | Nextcloud private-cloud sink | `download_cloud_3.py` | `nextcloud-destination` | `python3 scripts/download_cloud_3.py nextcloud-destination` |
| F1123 | WebDAV/SMB/NFS mount | `download_cloud_3.py` | `webdav-mount` | `python3 scripts/download_cloud_3.py webdav-mount` |
| F1124 | auto-upload to remote seedbox | `download_cloud_3.py` | `seedbox-upload` | `python3 scripts/download_cloud_3.py seedbox-upload` |
| F1125 | LAN peer chunk sync | `download_cloud_3.py` | `lan-peer-sync` | `python3 scripts/download_cloud_3.py lan-peer-sync` |
| F1126 | encrypted one-click recovery | `download_cloud_3.py` | `disaster-export` | `python3 scripts/download_cloud_3.py disaster-export` |
| F1127 | AI recommendations | `download_ai_3.py` | `ai-recommendations` | `python3 scripts/download_ai_3.py ai-recommendations` |
| F1128 | perceptual-hash dedup | `download_ai_3.py` | `perceptual-hash-dedup` | `python3 scripts/download_ai_3.py perceptual-hash-dedup` |
| F1129 | acoustic ID + auto tag | `download_ai_3.py` | `auto-tag-media` | `python3 scripts/download_ai_3.py auto-tag-media` |
| F1130 | spoken command intake | `download_ai_3.py` | `voice-command` | `python3 scripts/download_ai_3.py voice-command` |
| F1131 | natural-language search | `download_ai_3.py` | `nl-search` | `python3 scripts/download_ai_3.py nl-search` |
| F1132 | content-aware folder sort | `download_ai_3.py` | `content-aware-sorting` | `python3 scripts/download_ai_3.py content-aware-sorting` |
| F1133 | queue optimizer | `download_ai_3.py` | `queue-optimizer` | `python3 scripts/download_ai_3.py queue-optimizer` |
| F1134 | broken-link predictor | `download_ai_3.py` | `broken-link-warn` | `python3 scripts/download_ai_3.py broken-link-warn` |
| F1135 | audio silence trim | `download_ai_3.py` | `silence-trim` | `python3 scripts/download_ai_3.py silence-trim` |
| F1136 | AI chapter bookmarks | `download_ai_3.py` | `video-chapter-extract` | `python3 scripts/download_ai_3.py video-chapter-extract` |
| F1137 | transcribe for search | `download_ai_3.py` | `speech-to-text` | `python3 scripts/download_ai_3.py speech-to-text` |
| F1138 | auto-gen captions | `download_ai_3.py` | `auto-subtitles` | `python3 scripts/download_ai_3.py auto-subtitles` |
| F1139 | multi-device cooperative bandwidth | `download_ai_3.py` | `bandwidth-sharing` | `python3 scripts/download_ai_3.py bandwidth-sharing` |
| F1140 | finish-time prediction | `download_ai_3.py` | `download-forecast` | `python3 scripts/download_ai_3.py download-forecast` |
| F1141 | contextual file naming | `download_ai_3.py` | `contextual-naming` | `python3 scripts/download_ai_3.py contextual-naming` |
| F1142 | built-in hex editor | `download_power_3.py` | `hex-editor` | `python3 scripts/download_power_3.py hex-editor` |
| F1143 | file splitter + joiner | `download_power_3.py` | `file-splitter` | `python3 scripts/download_power_3.py file-splitter` |
| F1144 | zip on the fly | `download_power_3.py` | `zip-on-fly` | `python3 scripts/download_power_3.py zip-on-fly` |
| F1145 | in-progress stream-to-VLC | `download_power_3.py` | `stream-to-vlc` | `python3 scripts/download_power_3.py stream-to-vlc` |
| F1146 | headless service/API | `download_power_3.py` | `headless-mode` | `python3 scripts/download_power_3.py headless-mode` |
| F1147 | Docker image | `download_power_3.py` | `docker-deploy` | `python3 scripts/download_power_3.py docker-deploy` |
| F1148 | webhook on events | `download_power_3.py` | `webhook-actions` | `python3 scripts/download_power_3.py webhook-actions` |
| F1149 | custom regex/XPath scraper | `download_power_3.py` | `custom-scraper` | `python3 scripts/download_power_3.py custom-scraper` |
| F1150 | filter DSL | `download_power_3.py` | `filter-language` | `python3 scripts/download_power_3.py filter-language` |
| F1151 | dry-run simulation | `download_power_3.py` | `download-simulation` | `python3 scripts/download_power_3.py download-simulation` |
| F1152 | network throttle emulator | `download_power_3.py` | `network-emulator` | `python3 scripts/download_power_3.py network-emulator` |
| F1153 | disk space forecast | `download_power_3.py` | `disk-forecast` | `python3 scripts/download_power_3.py disk-forecast` |
| F1154 | multi-mirror parallel merge | `download_power_3.py` | `parallel-merge` | `python3 scripts/download_power_3.py parallel-merge` |
| F1155 | parallel multi-source | `download_power_3.py` | `multi-mirror` | `python3 scripts/download_power_3.py multi-mirror` |
| F1156 | ISP data-cap stop | `download_power_3.py` | `data-cap` | `python3 scripts/download_power_3.py data-cap` |
| F1157 | collaborative shared list | `download_community_3.py` | `shared-list` | `python3 scripts/download_community_3.py shared-list` |
| F1158 | plugin marketplace | `download_community_3.py` | `plugin-marketplace` | `python3 scripts/download_community_3.py plugin-marketplace` |
| F1159 | site compatibility reports | `download_community_3.py` | `site-compat-reports` | `python3 scripts/download_community_3.py site-compat-reports` |
| F1160 | personal download journal | `download_community_3.py` | `download-journal` | `python3 scripts/download_community_3.py download-journal` |
| F1161 | public download status | `download_community_3.py` | `public-download-status` | `python3 scripts/download_community_3.py public-download-status` |
| F1162 | friend direct transfer | `download_community_3.py` | `friend-direct-transfer` | `python3 scripts/download_community_3.py friend-direct-transfer` |
| F1163 | collaborative archival project | `download_community_3.py` | `collab-archival` | `python3 scripts/download_community_3.py collab-archival` |
| F1164 | creator tip jar | `download_community_3.py` | `tip-jar` | `python3 scripts/download_community_3.py tip-jar` |
| F1165 | library HTML export | `download_community_3.py` | `library-html-export` | `python3 scripts/download_community_3.py library-html-export` |
| F1166 | yearly stats wrap-up | `download_community_3.py` | `yearly-stats` | `python3 scripts/download_community_3.py yearly-stats` |

```bash
for s in scripts/download_{cloud,ai,power,community}_3.py; do
  python3 "$s" --help >/dev/null && echo "OK  $s"
done
grep -cE '^\| F[0-9]+ \|' README.md   # expect 1166
```

Total host-level feature count after this batch: **F001-F206 + F207-F406 + F407-F716 + F717-F916 + F917-F1116 + F1117-F1166 = 1166 features across 40 host-level CLIs.**
## Host utilities - 200 Simple-Internet download tasks (round 2, items 201-400) (F917 - F1116)

This is the second 200-task batch for the Simple Internet universal downloader (items 201-400), extending the prior F717-F916 batch with deeper music/video cuts, wider data sources, broader torrent/P2P coverage, more automation, deeper-web hooks, image/library sets, and wildcard downloads. Each feature is a host-level CLI subcommand that returns a synthetic-JSON payload and persists a stub record under `tank_ws/data/<scriptname>/`.

> **Disclaimer** - many of these items (Spotify-to-MP3, Patreon exclusives, paid trackers, Z-Library mirrors, Tor hidden services, etc.) are de facto grey-area downloads. The CLI surface here is documented for *legitimate, authorized* uses (your own playlists, public-domain content, paid services you have accounts on). Respect copyright and your local laws.

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F917 | opera performance archive | `download_music_2.py` | `opera-archive` | `python3 scripts/download_music_2.py opera-archive` |
| F918 | IG music sticker audio extract | `download_music_2.py` | `instagram-music-sticker` | `python3 scripts/download_music_2.py instagram-music-sticker` |
| F919 | Mixcloud DJ set | `download_music_2.py` | `mixcloud-save` | `python3 scripts/download_music_2.py mixcloud-save` |
| F920 | movie soundtrack wiki scrape | `download_music_2.py` | `movie-soundtrack-wiki` | `python3 scripts/download_music_2.py movie-soundtrack-wiki` |
| F921 | singing bowl loop | `download_music_2.py` | `singing-bowl-loop` | `python3 scripts/download_music_2.py singing-bowl-loop` |
| F922 | Patreon exclusive podcast audio | `download_music_2.py` | `patreon-podcast-audio` | `python3 scripts/download_music_2.py patreon-podcast-audio` |
| F923 | Odysee music MP3 | `download_music_2.py` | `odysee-music-mp3` | `python3 scripts/download_music_2.py odysee-music-mp3` |
| F924 | YT rain ambience 1h | `download_music_2.py` | `youtube-ambience-rain` | `python3 scripts/download_music_2.py youtube-ambience-rain` |
| F925 | FB group MP3 files | `download_music_2.py` | `facebook-group-files` | `python3 scripts/download_music_2.py facebook-group-files` |
| F926 | vintage radio ad museum | `download_music_2.py` | `vintage-radio-ad` | `python3 scripts/download_music_2.py vintage-radio-ad` |
| F927 | uni language lesson audio | `download_music_2.py` | `language-lesson-audio` | `python3 scripts/download_music_2.py language-lesson-audio` |
| F928 | isolated karaoke vocals | `download_music_2.py` | `karaoke-vocals` | `python3 scripts/download_music_2.py karaoke-vocals` |
| F929 | drum sample pack Reddit | `download_music_2.py` | `reddit-drumkits` | `python3 scripts/download_music_2.py reddit-drumkits` |
| F930 | house mix from forum | `download_music_2.py` | `house-mix-forum` | `python3 scripts/download_music_2.py house-mix-forum` |
| F931 | Flash SWF soundtrack | `download_music_2.py` | `flash-swf-soundtrack` | `python3 scripts/download_music_2.py flash-swf-soundtrack` |
| F932 | game OGG album | `download_music_2.py` | `game-ogg-album` | `python3 scripts/download_music_2.py game-ogg-album` |
| F933 | public-domain hymns | `download_music_2.py` | `public-domain-hymns` | `python3 scripts/download_music_2.py public-domain-hymns` |
| F934 | retro Muzak playlist | `download_music_2.py` | `muzak-retro` | `python3 scripts/download_music_2.py muzak-retro` |
| F935 | TikTok custom ringtone | `download_music_2.py` | `tiktok-custom-ringtone` | `python3 scripts/download_music_2.py tiktok-custom-ringtone` |
| F936 | Spotify audiobook chapter | `download_music_2.py` | `spotify-audiobook-chapter` | `python3 scripts/download_music_2.py spotify-audiobook-chapter` |
| F937 | 3D side-by-side movie | `download_video_2.py` | `sidebyside-3d-movie` | `python3 scripts/download_video_2.py sidebyside-3d-movie` |
| F938 | Webex recording | `download_video_2.py` | `webex-recording` | `python3 scripts/download_video_2.py webex-recording` |
| F939 | TikTok slideshow MP4 | `download_video_2.py` | `tiktok-slideshow-mp4` | `python3 scripts/download_video_2.py tiktok-slideshow-mp4` |
| F940 | Instagram Live replay | `download_video_2.py` | `instagram-live-replay` | `python3 scripts/download_video_2.py instagram-live-replay` |
| F941 | PeerTube festival entry | `download_video_2.py` | `peertube-festival` | `python3 scripts/download_video_2.py peertube-festival` |
| F942 | YouTube VR 360 | `download_video_2.py` | `youtube-vr-360` | `python3 scripts/download_video_2.py youtube-vr-360` |
| F943 | DTube crypto video | `download_video_2.py` | `dtube-crypto` | `python3 scripts/download_video_2.py dtube-crypto` |
| F944 | Utreon creator | `download_video_2.py` | `utreon-creator` | `python3 scripts/download_video_2.py utreon-creator` |
| F945 | BitChute documentary | `download_video_2.py` | `bitchute-doc` | `python3 scripts/download_video_2.py bitchute-doc` |
| F946 | Veoh classic | `download_video_2.py` | `veoh-classic` | `python3 scripts/download_video_2.py veoh-classic` |
| F947 | Metacafe nostalgia | `download_video_2.py` | `metacafe-clip` | `python3 scripts/download_video_2.py metacafe-clip` |
| F948 | VidLii retro upload | `download_video_2.py` | `vidlii-upload` | `python3 scripts/download_video_2.py vidlii-upload` |
| F949 | Streamable clip | `download_video_2.py` | `streamable-clip` | `python3 scripts/download_video_2.py streamable-clip` |
| F950 | Short of the Week film | `download_video_2.py` | `shortoftheweek` | `python3 scripts/download_video_2.py shortoftheweek` |
| F951 | Amazon miniTV | `download_video_2.py` | `amazon-minitv` | `python3 scripts/download_video_2.py amazon-minitv` |
| F952 | PBS Kids | `download_video_2.py` | `pbs-kids` | `python3 scripts/download_video_2.py pbs-kids` |
| F953 | FB church live | `download_video_2.py` | `facebook-church-live` | `python3 scripts/download_video_2.py facebook-church-live` |
| F954 | WooCommerce review video | `download_video_2.py` | `woocommerce-review-video` | `python3 scripts/download_video_2.py woocommerce-review-video` |
| F955 | Weibo video | `download_video_2.py` | `weibo-video` | `python3 scripts/download_video_2.py weibo-video` |
| F956 | OK.ru video album | `download_video_2.py` | `okru-video-album` | `python3 scripts/download_video_2.py okru-video-album` |
| F957 | city transport timetables PDF | `download_data_2.py` | `transport-timetables-pdf` | `python3 scripts/download_data_2.py transport-timetables-pdf` |
| F958 | govt nutrition DB | `download_data_2.py` | `nutrition-database` | `python3 scripts/download_data_2.py nutrition-database` |
| F959 | country e-laws | `download_data_2.py` | `national-laws-portal` | `python3 scripts/download_data_2.py national-laws-portal` |
| F960 | Nobel winners JSON | `download_data_2.py` | `nobel-json` | `python3 scripts/download_data_2.py nobel-json` |
| F961 | CRM contact export | `download_data_2.py` | `crm-export-link` | `python3 scripts/download_data_2.py crm-export-link` |
| F962 | SEC filings bulk | `download_data_2.py` | `sec-filings-bulk` | `python3 scripts/download_data_2.py sec-filings-bulk` |
| F963 | patent + drawings | `download_data_2.py` | `patent-with-drawings` | `python3 scripts/download_data_2.py patent-with-drawings` |
| F964 | WHO dataset | `download_data_2.py` | `who-research-data` | `python3 scripts/download_data_2.py who-research-data` |
| F965 | undersea cables KML | `download_data_2.py` | `undersea-cables-kml` | `python3 scripts/download_data_2.py undersea-cables-kml` |
| F966 | AI conf papers | `download_data_2.py` | `ai-conf-papers` | `python3 scripts/download_data_2.py ai-conf-papers` |
| F967 | docs site PDF archive | `download_data_2.py` | `docs-site-pdf-archive` | `python3 scripts/download_data_2.py docs-site-pdf-archive` |
| F968 | airline safety cards | `download_data_2.py` | `airline-safety-cards` | `python3 scripts/download_data_2.py airline-safety-cards` |
| F969 | font specimen PDF | `download_data_2.py` | `font-specimen-pdf` | `python3 scripts/download_data_2.py font-specimen-pdf` |
| F970 | voter registration DB | `download_data_2.py` | `voter-registration` | `python3 scripts/download_data_2.py voter-registration` |
| F971 | building code standard | `download_data_2.py` | `building-code-standard` | `python3 scripts/download_data_2.py building-code-standard` |
| F972 | Kaggle comp data | `download_data_2.py` | `kaggle-competition-data` | `python3 scripts/download_data_2.py kaggle-competition-data` |
| F973 | postal code directory | `download_data_2.py` | `postal-code-directory` | `python3 scripts/download_data_2.py postal-code-directory` |
| F974 | chemistry molecule DB | `download_data_2.py` | `chemistry-molecule-db` | `python3 scripts/download_data_2.py chemistry-molecule-db` |
| F975 | Unicode code charts | `download_data_2.py` | `unicode-code-charts` | `python3 scripts/download_data_2.py unicode-code-charts` |
| F976 | 1800s recipe book | `download_data_2.py` | `public-domain-recipe-1800s` | `python3 scripts/download_data_2.py public-domain-recipe-1800s` |
| F977 | console ROM set | `download_torrent_2.py` | `console-rom-set` | `python3 scripts/download_torrent_2.py console-rom-set` |
| F978 | Linux weekly build | `download_torrent_2.py` | `linux-weekly-build` | `python3 scripts/download_torrent_2.py linux-weekly-build` |
| F979 | Blender open movie | `download_torrent_2.py` | `blender-open-movie` | `python3 scripts/download_torrent_2.py blender-open-movie` |
| F980 | Wiktionary torrent | `download_torrent_2.py` | `wiktionary-torrent` | `python3 scripts/download_torrent_2.py wiktionary-torrent` |
| F981 | biodiversity image set | `download_torrent_2.py` | `biodiversity-image-set` | `python3 scripts/download_torrent_2.py biodiversity-image-set` |
| F982 | historical weather data | `download_torrent_2.py` | `historical-weather-data` | `python3 scripts/download_torrent_2.py historical-weather-data` |
| F983 | 4K test patterns | `download_torrent_2.py` | `4k-test-patterns` | `python3 scripts/download_torrent_2.py 4k-test-patterns` |
| F984 | childrens book torrent | `download_torrent_2.py` | `childrens-book-torrent` | `python3 scripts/download_torrent_2.py childrens-book-torrent` |
| F985 | HDRI env pack | `download_torrent_2.py` | `hdri-env-pack` | `python3 scripts/download_torrent_2.py hdri-env-pack` |
| F986 | scifi ebook collection | `download_torrent_2.py` | `scifi-ebook-collection` | `python3 scripts/download_torrent_2.py scifi-ebook-collection` |
| F987 | chess game DB | `download_torrent_2.py` | `chess-game-database` | `python3 scripts/download_torrent_2.py chess-game-database` |
| F988 | GRCh38 genome | `download_torrent_2.py` | `grch38-genome` | `python3 scripts/download_torrent_2.py grch38-genome` |
| F989 | typography font torrent | `download_torrent_2.py` | `typography-font-torrent` | `python3 scripts/download_torrent_2.py typography-font-torrent` |
| F990 | industrial sound pack | `download_torrent_2.py` | `industrial-sound-pack` | `python3 scripts/download_torrent_2.py industrial-sound-pack` |
| F991 | 3D print models | `download_torrent_2.py` | `3d-print-models` | `python3 scripts/download_torrent_2.py 3d-print-models` |
| F992 | CGI textures | `download_torrent_2.py` | `cgi-textures` | `python3 scripts/download_torrent_2.py cgi-textures` |
| F993 | movie trailers pack | `download_torrent_2.py` | `movie-trailers-pack` | `python3 scripts/download_torrent_2.py movie-trailers-pack` |
| F994 | music edu course | `download_torrent_2.py` | `music-education-course` | `python3 scripts/download_torrent_2.py music-education-course` |
| F995 | folklore text archive | `download_torrent_2.py` | `folklore-text-archive` | `python3 scripts/download_torrent_2.py folklore-text-archive` |
| F996 | safe software torrents | `download_torrent_2.py` | `safe-software-torrents` | `python3 scripts/download_torrent_2.py safe-software-torrents` |
| F997 | subreddit video feed | `download_scheduled_2.py` | `subreddit-video-feed` | `python3 scripts/download_scheduled_2.py subreddit-video-feed` |
| F998 | quarterly finance rpt | `download_scheduled_2.py` | `quarterly-finance-report` | `python3 scripts/download_scheduled_2.py quarterly-finance-report` |
| F999 | APOD wallpaper | `download_scheduled_2.py` | `apod-wallpaper` | `python3 scripts/download_scheduled_2.py apod-wallpaper` |
| F1000 | govt tender monitor | `download_scheduled_2.py` | `govt-tender-monitor` | `python3 scripts/download_scheduled_2.py govt-tender-monitor` |
| F1001 | TV fansite RSS | `download_scheduled_2.py` | `tv-fansite-rss` | `python3 scripts/download_scheduled_2.py tv-fansite-rss` |
| F1002 | weekly Top40 | `download_scheduled_2.py` | `weekly-top40` | `python3 scripts/download_scheduled_2.py weekly-top40` |
| F1003 | daily satellite image | `download_scheduled_2.py` | `daily-satellite-image` | `python3 scripts/download_scheduled_2.py daily-satellite-image` |
| F1004 | CERT advisory list | `download_scheduled_2.py` | `cert-advisory-list` | `python3 scripts/download_scheduled_2.py cert-advisory-list` |
| F1005 | GitHub release RSS | `download_scheduled_2.py` | `github-release-rss` | `python3 scripts/download_scheduled_2.py github-release-rss` |
| F1006 | news archive hourly | `download_scheduled_2.py` | `news-archive-hourly` | `python3 scripts/download_scheduled_2.py news-archive-hourly` |
| F1007 | livestream auto-rip | `download_scheduled_2.py` | `livestream-auto-rip` | `python3 scripts/download_scheduled_2.py livestream-auto-rip` |
| F1008 | weekly blog playlist | `download_scheduled_2.py` | `weekly-blog-playlist` | `python3 scripts/download_scheduled_2.py weekly-blog-playlist` |
| F1009 | monthly magazine PDF | `download_scheduled_2.py` | `monthly-magazine-pdf` | `python3 scripts/download_scheduled_2.py monthly-magazine-pdf` |
| F1010 | IoT sensor dump | `download_scheduled_2.py` | `iot-sensor-dump` | `python3 scripts/download_scheduled_2.py iot-sensor-dump` |
| F1011 | daily health rpt | `download_scheduled_2.py` | `daily-health-report` | `python3 scripts/download_scheduled_2.py daily-health-report` |
| F1012 | Gmail label attachments | `download_scheduled_2.py` | `gmail-label-attachments` | `python3 scripts/download_scheduled_2.py gmail-label-attachments` |
| F1013 | continuous meme feed | `download_scheduled_2.py` | `continuous-meme-feed` | `python3 scripts/download_scheduled_2.py continuous-meme-feed` |
| F1014 | vlog daily video | `download_scheduled_2.py` | `vlog-daily-video` | `python3 scripts/download_scheduled_2.py vlog-daily-video` |
| F1015 | blockchain snapshot | `download_scheduled_2.py` | `blockchain-snapshot` | `python3 scripts/download_scheduled_2.py blockchain-snapshot` |
| F1016 | Dropbox folder watch | `download_scheduled_2.py` | `dropbox-folder-watch` | `python3 scripts/download_scheduled_2.py dropbox-folder-watch` |
| F1017 | ZeroNet site | `download_deepweb_2.py` | `zeronet-site` | `python3 scripts/download_deepweb_2.py zeronet-site` |
| F1018 | SSB blob | `download_deepweb_2.py` | `ssb-blob` | `python3 scripts/download_deepweb_2.py ssb-blob` |
| F1019 | Yggdrasil file | `download_deepweb_2.py` | `yggdrasil-file` | `python3 scripts/download_deepweb_2.py yggdrasil-file` |
| F1020 | I2P eepsite | `download_deepweb_2.py` | `i2p-eepsite` | `python3 scripts/download_deepweb_2.py i2p-eepsite` |
| F1021 | Freenet freesite | `download_deepweb_2.py` | `freenet-freesite` | `python3 scripts/download_deepweb_2.py freenet-freesite` |
| F1022 | .onion via Tor | `download_deepweb_2.py` | `onion-via-tor` | `python3 scripts/download_deepweb_2.py onion-via-tor` |
| F1023 | Nostr relay media | `download_deepweb_2.py` | `nostr-relay-media` | `python3 scripts/download_deepweb_2.py nostr-relay-media` |
| F1024 | RetroShare forum | `download_deepweb_2.py` | `retroshare-forum` | `python3 scripts/download_deepweb_2.py retroshare-forum` |
| F1025 | GNUnet peer | `download_deepweb_2.py` | `gnunet-peer` | `python3 scripts/download_deepweb_2.py gnunet-peer` |
| F1026 | IPFS folder CID | `download_deepweb_2.py` | `ipfs-folder-cid` | `python3 scripts/download_deepweb_2.py ipfs-folder-cid` |
| F1027 | Hyphanet manifest | `download_deepweb_2.py` | `hyphanet-manifest` | `python3 scripts/download_deepweb_2.py hyphanet-manifest` |
| F1028 | Briar attachment | `download_deepweb_2.py` | `briar-attachment` | `python3 scripts/download_deepweb_2.py briar-attachment` |
| F1029 | Twister timeline | `download_deepweb_2.py` | `twister-timeline` | `python3 scripts/download_deepweb_2.py twister-timeline` |
| F1030 | MaidSafe file | `download_deepweb_2.py` | `maidsafe-file` | `python3 scripts/download_deepweb_2.py maidsafe-file` |
| F1031 | Loki attachment | `download_deepweb_2.py` | `loki-session-attachment` | `python3 scripts/download_deepweb_2.py loki-session-attachment` |
| F1032 | Jami sent file | `download_deepweb_2.py` | `jami-sent-file` | `python3 scripts/download_deepweb_2.py jami-sent-file` |
| F1033 | Tox history file | `download_deepweb_2.py` | `tox-history-file` | `python3 scripts/download_deepweb_2.py tox-history-file` |
| F1034 | Matrix media | `download_deepweb_2.py` | `matrix-media` | `python3 scripts/download_deepweb_2.py matrix-media` |
| F1035 | XMPP upload | `download_deepweb_2.py` | `xmpp-upload` | `python3 scripts/download_deepweb_2.py xmpp-upload` |
| F1036 | Ricochet Refresh doc | `download_deepweb_2.py` | `ricochet-refresh-doc` | `python3 scripts/download_deepweb_2.py ricochet-refresh-doc` |
| F1037 | wallpaper group | `download_images_2.py` | `wallpaper-group` | `python3 scripts/download_images_2.py wallpaper-group` |
| F1038 | historical map collection | `download_images_2.py` | `historical-map-collection` | `python3 scripts/download_images_2.py historical-map-collection` |
| F1039 | open-source emoji set | `download_images_2.py` | `open-source-emoji-set` | `python3 scripts/download_images_2.py open-source-emoji-set` |
| F1040 | designer icon pack | `download_images_2.py` | `designer-icon-pack` | `python3 scripts/download_images_2.py designer-icon-pack` |
| F1041 | museum open art | `download_images_2.py` | `museum-open-art` | `python3 scripts/download_images_2.py museum-open-art` |
| F1042 | comic covers wiki | `download_images_2.py` | `comic-covers-wiki` | `python3 scripts/download_images_2.py comic-covers-wiki` |
| F1043 | sprite sheet archive | `download_images_2.py` | `sprite-sheet-archive` | `python3 scripts/download_images_2.py sprite-sheet-archive` |
| F1044 | messaging sticker pack | `download_images_2.py` | `messaging-sticker-pack` | `python3 scripts/download_images_2.py messaging-sticker-pack` |
| F1045 | country flag vectors | `download_images_2.py` | `country-flags-vector` | `python3 scripts/download_images_2.py country-flags-vector` |
| F1046 | botanical illustration set | `download_images_2.py` | `botanical-illustration-set` | `python3 scripts/download_images_2.py botanical-illustration-set` |
| F1047 | space mission patches | `download_images_2.py` | `space-mission-patches` | `python3 scripts/download_images_2.py space-mission-patches` |
| F1048 | vintage travel posters | `download_images_2.py` | `vintage-travel-posters` | `python3 scripts/download_images_2.py vintage-travel-posters` |
| F1049 | anatomy diagram set | `download_images_2.py` | `anatomy-diagram-set` | `python3 scripts/download_images_2.py anatomy-diagram-set` |
| F1050 | calligraphic borders | `download_images_2.py` | `calligraphic-borders` | `python3 scripts/download_images_2.py calligraphic-borders` |
| F1051 | city public art | `download_images_2.py` | `city-public-art` | `python3 scripts/download_images_2.py city-public-art` |
| F1052 | topo map series | `download_images_2.py` | `topo-map-series` | `python3 scripts/download_images_2.py topo-map-series` |
| F1053 | 360 HDR sky | `download_images_2.py` | `hdri-360-sky` | `python3 scripts/download_images_2.py hdri-360-sky` |
| F1054 | film grain overlays | `download_images_2.py` | `film-grain-overlays` | `python3 scripts/download_images_2.py film-grain-overlays` |
| F1055 | light leak effects | `download_images_2.py` | `light-leak-effects` | `python3 scripts/download_images_2.py light-leak-effects` |
| F1056 | facial expression dataset | `download_images_2.py` | `facial-expression-dataset` | `python3 scripts/download_images_2.py facial-expression-dataset` |
| F1057 | PortableApps collection | `download_software_2.py` | `portableapps-collection` | `python3 scripts/download_software_2.py portableapps-collection` |
| F1058 | legacy version archive | `download_software_2.py` | `legacy-version-archive` | `python3 scripts/download_software_2.py legacy-version-archive` |
| F1059 | offline language pack | `download_software_2.py` | `offline-language-pack` | `python3 scripts/download_software_2.py offline-language-pack` |
| F1060 | CLI tools minimal OS | `download_software_2.py` | `cli-tools-minimal-os` | `python3 scripts/download_software_2.py cli-tools-minimal-os` |
| F1061 | Kiwix ZIM wiki | `download_software_2.py` | `kiwix-zim-wiki` | `python3 scripts/download_software_2.py kiwix-zim-wiki` |
| F1062 | Windows update standalone | `download_software_2.py` | `windows-update-standalone` | `python3 scripts/download_software_2.py windows-update-standalone` |
| F1063 | Linux package repo snapshot | `download_software_2.py` | `linux-package-repo-snapshot` | `python3 scripts/download_software_2.py linux-package-repo-snapshot` |
| F1064 | legacy driver pack | `download_software_2.py` | `legacy-driver-pack` | `python3 scripts/download_software_2.py legacy-driver-pack` |
| F1065 | design tool installer | `download_software_2.py` | `design-tool-offline-installer` | `python3 scripts/download_software_2.py design-tool-offline-installer` |
| F1066 | Steam demo external | `download_software_2.py` | `steam-demo-external` | `python3 scripts/download_software_2.py steam-demo-external` |
| F1067 | cheat sheets PDF | `download_software_2.py` | `cheatsheets-pdf` | `python3 scripts/download_software_2.py cheatsheets-pdf` |
| F1068 | OVA virtual appliance | `download_software_2.py` | `ova-virtual-appliance` | `python3 scripts/download_software_2.py ova-virtual-appliance` |
| F1069 | offline SDK collection | `download_software_2.py` | `offline-sdk-collection` | `python3 scripts/download_software_2.py offline-sdk-collection` |
| F1070 | CRX extension | `download_software_2.py` | `crx-browser-extension` | `python3 scripts/download_software_2.py crx-browser-extension` |
| F1071 | free Unity assets | `download_software_2.py` | `free-unity-assets` | `python3 scripts/download_software_2.py free-unity-assets` |
| F1072 | offline dictionary data | `download_software_2.py` | `offline-dictionary-data` | `python3 scripts/download_software_2.py offline-dictionary-data` |
| F1073 | gist Bash scripts | `download_software_2.py` | `gist-bash-scripts` | `python3 scripts/download_software_2.py gist-bash-scripts` |
| F1074 | design palette file | `download_software_2.py` | `design-palette-file` | `python3 scripts/download_software_2.py design-palette-file` |
| F1075 | music software presets | `download_software_2.py` | `music-software-presets` | `python3 scripts/download_software_2.py music-software-presets` |
| F1076 | Photoshop brush pack | `download_software_2.py` | `photoshop-brush-pack` | `python3 scripts/download_software_2.py photoshop-brush-pack` |
| F1077 | MIT OCW zip | `download_ebooks_2.py` | `mit-ocw-zip` | `python3 scripts/download_ebooks_2.py mit-ocw-zip` |
| F1078 | Teach Yourself language | `download_ebooks_2.py` | `teach-yourself-language` | `python3 scripts/download_ebooks_2.py teach-yourself-language` |
| F1079 | childrens illustration book | `download_ebooks_2.py` | `childrens-illustration-book` | `python3 scripts/download_ebooks_2.py childrens-illustration-book` |
| F1080 | philosophy classics | `download_ebooks_2.py` | `philosophy-classics` | `python3 scripts/download_ebooks_2.py philosophy-classics` |
| F1081 | security cert study guide | `download_ebooks_2.py` | `security-cert-study-guide` | `python3 scripts/download_ebooks_2.py security-cert-study-guide` |
| F1082 | math formula handbook | `download_ebooks_2.py` | `math-formula-handbook` | `python3 scripts/download_ebooks_2.py math-formula-handbook` |
| F1083 | library cookbook | `download_ebooks_2.py` | `library-cookbook` | `python3 scripts/download_ebooks_2.py library-cookbook` |
| F1084 | free wiki travel guides | `download_ebooks_2.py` | `free-wiki-travel-guides` | `python3 scripts/download_ebooks_2.py free-wiki-travel-guides` |
| F1085 | yearly social PDF | `download_ebooks_2.py` | `yearly-social-pdf` | `python3 scripts/download_ebooks_2.py yearly-social-pdf` |
| F1086 | massive poetry collection | `download_ebooks_2.py` | `massive-poetry-collection` | `python3 scripts/download_ebooks_2.py massive-poetry-collection` |
| F1087 | free-today self-help | `download_ebooks_2.py` | `free-today-self-help` | `python3 scripts/download_ebooks_2.py free-today-self-help` |
| F1088 | Wikipedia featured articles | `download_ebooks_2.py` | `wikipedia-featured-articles` | `python3 scripts/download_ebooks_2.py wikipedia-featured-articles` |
| F1089 | historical newspaper archive | `download_ebooks_2.py` | `historical-newspaper-archive` | `python3 scripts/download_ebooks_2.py historical-newspaper-archive` |
| F1090 | family history book | `download_ebooks_2.py` | `family-history-book` | `python3 scripts/download_ebooks_2.py family-history-book` |
| F1091 | knitting pattern book | `download_ebooks_2.py` | `knitting-pattern-book` | `python3 scripts/download_ebooks_2.py knitting-pattern-book` |
| F1092 | survival guide outdoor | `download_ebooks_2.py` | `survival-guide-outdoor` | `python3 scripts/download_ebooks_2.py survival-guide-outdoor` |
| F1093 | herbal medicine encyclopedia | `download_ebooks_2.py` | `herbal-medicine-encyclopedia` | `python3 scripts/download_ebooks_2.py herbal-medicine-encyclopedia` |
| F1094 | magic tricks book | `download_ebooks_2.py` | `magic-tricks-book` | `python3 scripts/download_ebooks_2.py magic-tricks-book` |
| F1095 | world religions guide | `download_ebooks_2.py` | `world-religions-guide` | `python3 scripts/download_ebooks_2.py world-religions-guide` |
| F1096 | bird ID guide | `download_ebooks_2.py` | `bird-id-guide` | `python3 scripts/download_ebooks_2.py bird-id-guide` |
| F1097 | Spotify playlists metadata | `download_misc_2.py` | `spotify-playlists-metadata` | `python3 scripts/download_misc_2.py spotify-playlists-metadata` |
| F1098 | IANA timezones | `download_misc_2.py` | `iana-timezones` | `python3 scripts/download_misc_2.py iana-timezones` |
| F1099 | periodic table CSV | `download_misc_2.py` | `periodic-table-csv` | `python3 scripts/download_misc_2.py periodic-table-csv` |
| F1100 | NASA tech standards | `download_misc_2.py` | `nasa-tech-standards` | `python3 scripts/download_misc_2.py nasa-tech-standards` |
| F1101 | game custom map pack | `download_misc_2.py` | `game-custom-map-pack` | `python3 scripts/download_misc_2.py game-custom-map-pack` |
| F1102 | Japanese emoji fan site | `download_misc_2.py` | `japanese-emoji-fansite` | `python3 scripts/download_misc_2.py japanese-emoji-fansite` |
| F1103 | BW coloring pages | `download_misc_2.py` | `coloring-pages-bw` | `python3 scripts/download_misc_2.py coloring-pages-bw` |
| F1104 | Zoom virtual backgrounds | `download_misc_2.py` | `zoom-virtual-backgrounds` | `python3 scripts/download_misc_2.py zoom-virtual-backgrounds` |
| F1105 | random word list | `download_misc_2.py` | `random-word-list` | `python3 scripts/download_misc_2.py random-word-list` |
| F1106 | constellation boundaries | `download_misc_2.py` | `constellation-boundaries` | `python3 scripts/download_misc_2.py constellation-boundaries` |
| F1107 | famous author quotes | `download_misc_2.py` | `famous-author-quotes` | `python3 scripts/download_misc_2.py famous-author-quotes` |
| F1108 | countries capitals list | `download_misc_2.py` | `countries-capitals-list` | `python3 scripts/download_misc_2.py countries-capitals-list` |
| F1109 | financial templates | `download_misc_2.py` | `financial-templates` | `python3 scripts/download_misc_2.py financial-templates` |
| F1110 | printable Sudoku | `download_misc_2.py` | `printable-sudoku` | `python3 scripts/download_misc_2.py printable-sudoku` |
| F1111 | knitting chart symbols | `download_misc_2.py` | `knitting-chart-symbols` | `python3 scripts/download_misc_2.py knitting-chart-symbols` |
| F1112 | guitar chord library | `download_misc_2.py` | `guitar-chord-library` | `python3 scripts/download_misc_2.py guitar-chord-library` |
| F1113 | low-poly 3D models | `download_misc_2.py` | `low-poly-3d-models` | `python3 scripts/download_misc_2.py low-poly-3d-models` |
| F1114 | standard resistor values | `download_misc_2.py` | `standard-resistor-values` | `python3 scripts/download_misc_2.py standard-resistor-values` |
| F1115 | ham radio Q-codes | `download_misc_2.py` | `ham-radio-qcodes` | `python3 scripts/download_misc_2.py ham-radio-qcodes` |
| F1116 | LTT meme soundboard | `download_misc_2.py` | `linus-tech-tips-soundboard` | `python3 scripts/download_misc_2.py linus-tech-tips-soundboard` |

```bash
# Smoke test the 10 round-2 scripts:
for s in scripts/download_{music,video,data,torrent,scheduled,deepweb,images,software,ebooks,misc}_2.py; do
  python3 "$s" --help >/dev/null && echo "OK  $s"
done
grep -cE '^\| F[0-9]+ \|' README.md   # expect 1116
```

Total host-level feature count after this batch: **F001-F206 + F207-F406 + F407-F716 + F717-F916 + F917-F1116 = 1116 features across 36 host-level CLIs.**
## Host utilities - 200 Simple-Internet download tasks (F717 - F916)

An eighth batch of **6 host-level CLIs / 200 subcommands** for the **Simple Internet** universal downloader (underlying plumbing lives in `tank_os/internet/`). Each subcommand maps to a real download task; offline-first returns a synthetic JSON descriptor and routes to the actual download engine on a real run.

> Reminder: respect copyright and ToS. Several tasks refer to commercial sources (Spotify, BBC, Netflix, etc.) which require auth or licensing; the CLI surface documents the workflow - actual download execution must be authorised by the rightsholder.

### Feature index (F717 - F916)

| ID | Feature | Script | Subcommand | Example |
|----|---------|--------|------------|---------|
| F717 | Bandcamp album download (auth for paid) | `download_music.py` | `album-bandcamp` | `python3 scripts/download_music.py album-bandcamp` |
| F718 | YouTube Music playlist -> MP3 | `download_music.py` | `playlist-ytm` | `python3 scripts/download_music.py playlist-ytm` |
| F719 | SoundCloud DJ mix save | `download_music.py` | `soundcloud-mix` | `python3 scripts/download_music.py soundcloud-mix` |
| F720 | YouTube concert video -> audio | `download_music.py` | `live-concert-audio` | `python3 scripts/download_music.py live-concert-audio` |
| F721 | Internet Archive discography | `download_music.py` | `artist-discography-ia` | `python3 scripts/download_music.py artist-discography-ia` |
| F722 | Spotify podcast (public RSS) | `download_music.py` | `spotify-podcast-rss` | `python3 scripts/download_music.py spotify-podcast-rss` |
| F723 | HDtracks hi-res FLAC | `download_music.py` | `hdtracks-flac` | `python3 scripts/download_music.py hdtracks-flac` |
| F724 | Reddit best-of thread MP3 batch | `download_music.py` | `reddit-best-music` | `python3 scripts/download_music.py reddit-best-music` |
| F725 | blog MediaFire MP3s | `download_music.py` | `blog-mediafire` | `python3 scripts/download_music.py blog-mediafire` |
| F726 | YT lyric video -> MP3 + embed lyrics | `download_music.py` | `yt-lyric-embed` | `python3 scripts/download_music.py yt-lyric-embed` |
| F727 | station weekly radio archive | `download_music.py` | `radio-archive` | `python3 scripts/download_music.py radio-archive` |
| F728 | Jamendo album offline | `download_music.py` | `jamendo-album` | `python3 scripts/download_music.py jamendo-album` |
| F729 | LibriVox audiobook chapters | `download_music.py` | `librivox-chapters` | `python3 scripts/download_music.py librivox-chapters` |
| F730 | Pixabay royalty-free BG music | `download_music.py` | `pixabay-bg-music` | `python3 scripts/download_music.py pixabay-bg-music` |
| F731 | Vimeo music video audio | `download_music.py` | `vimeo-music-video` | `python3 scripts/download_music.py vimeo-music-video` |
| F732 | band official singles dump | `download_music.py` | `band-official-singles` | `python3 scripts/download_music.py band-official-singles` |
| F733 | auto-fetch new podcast episodes | `download_music.py` | `podcast-auto-new` | `python3 scripts/download_music.py podcast-auto-new` |
| F734 | Insight Timer public tracks | `download_music.py` | `insight-timer-tracks` | `python3 scripts/download_music.py insight-timer-tracks` |
| F735 | Twitch VOD music segment | `download_music.py` | `twitch-vod-music` | `python3 scripts/download_music.py twitch-vod-music` |
| F736 | TikTok compilation audio | `download_music.py` | `tiktok-compilation-audio` | `python3 scripts/download_music.py tiktok-compilation-audio` |
| F737 | Spotify playlist via integrated plugin | `download_music.py` | `spotify-playlist-plugin` | `python3 scripts/download_music.py spotify-playlist-plugin` |
| F738 | Free Music Archive genre dump | `download_music.py` | `fma-genre` | `python3 scripts/download_music.py fma-genre` |
| F739 | K-pop YT channel audio only | `download_music.py` | `kpop-videos-audio` | `python3 scripts/download_music.py kpop-videos-audio` |
| F740 | obscure church Christmas carols | `download_music.py` | `christmas-carols` | `python3 scripts/download_music.py christmas-carols` |
| F741 | Dailymotion concert -> MP3 | `download_music.py` | `dailymotion-mp3` | `python3 scripts/download_music.py dailymotion-mp3` |
| F742 | BBC Radio 1 Essential Mix | `download_music.py` | `bbc-essentials` | `python3 scripts/download_music.py bbc-essentials` |
| F743 | Billboard Top100 via YT search | `download_music.py` | `billboard-top100` | `python3 scripts/download_music.py billboard-top100` |
| F744 | NPR Tiny Desk audio+video | `download_music.py` | `npr-tiny-desk` | `python3 scripts/download_music.py npr-tiny-desk` |
| F745 | Substack audio post | `download_music.py` | `substack-audio` | `python3 scripts/download_music.py substack-audio` |
| F746 | all MP3s on single HTML page | `download_music.py` | `html-page-mp3s` | `python3 scripts/download_music.py html-page-mp3s` |
| F747 | Apple Music 30s preview | `download_music.py` | `apple-music-preview` | `python3 scripts/download_music.py apple-music-preview` |
| F748 | indie game soundtrack itch.io | `download_music.py` | `itch-game-soundtrack` | `python3 scripts/download_music.py itch-game-soundtrack` |
| F749 | Zedge ringtone + auto trim | `download_music.py` | `zedge-ringtone` | `python3 scripts/download_music.py zedge-ringtone` |
| F750 | VK video audio | `download_music.py` | `vk-video-audio` | `python3 scripts/download_music.py vk-video-audio` |
| F751 | public Google Drive music folder | `download_music.py` | `gdrive-music-folder` | `python3 scripts/download_music.py gdrive-music-folder` |
| F752 | BeatStars instrumental | `download_music.py` | `beatstars-instrumental` | `python3 scripts/download_music.py beatstars-instrumental` |
| F753 | Musopen classical recording | `download_music.py` | `musopen-classical` | `python3 scripts/download_music.py musopen-classical` |
| F754 | Facebook live rare track | `download_music.py` | `fb-video-audio` | `python3 scripts/download_music.py fb-video-audio` |
| F755 | YT year-search full album | `download_music.py` | `year-search-yt` | `python3 scripts/download_music.py year-search-yt` |
| F756 | audio Bible narration | `download_music.py` | `bible-is-narration` | `python3 scripts/download_music.py bible-is-narration` |
| F757 | university lecture podcast | `download_music.py` | `uni-lecture-series` | `python3 scripts/download_music.py uni-lecture-series` |
| F758 | PD movie soundtrack | `download_music.py` | `pd-movie-soundtrack` | `python3 scripts/download_music.py pd-movie-soundtrack` |
| F759 | auto-fetch new SC uploads | `download_music.py` | `soundcloud-rss-uploads` | `python3 scripts/download_music.py soundcloud-rss-uploads` |
| F760 | Hearthis.at mix -> MP3 | `download_music.py` | `hearthis-mix` | `python3 scripts/download_music.py hearthis-mix` |
| F761 | Audius track via API | `download_music.py` | `audius-api` | `python3 scripts/download_music.py audius-api` |
| F762 | BBC Sounds radio drama | `download_music.py` | `bbc-sounds-drama` | `python3 scripts/download_music.py bbc-sounds-drama` |
| F763 | 24/7 chillhop stream tracks | `download_music.py` | `chillhop-stream-tracks` | `python3 scripts/download_music.py chillhop-stream-tracks` |
| F764 | Coursera course audio | `download_music.py` | `coursera-audio` | `python3 scripts/download_music.py coursera-audio` |
| F765 | niche forum vinyl-rip magnet | `download_music.py` | `niche-forum-magnet` | `python3 scripts/download_music.py niche-forum-magnet` |
| F766 | Telegram channel music files | `download_music.py` | `telegram-channel-music` | `python3 scripts/download_music.py telegram-channel-music` |
| F767 | YouTube 4K documentary download | `download_video.py` | `yt-4k-doc` | `python3 scripts/download_video.py yt-4k-doc` |
| F768 | Twitch stream VOD archive | `download_video.py` | `twitch-vod` | `python3 scripts/download_video.py twitch-vod` |
| F769 | Vimeo showcase dump | `download_video.py` | `vimeo-showcase` | `python3 scripts/download_video.py vimeo-showcase` |
| F770 | Netflix public trailer max quality | `download_video.py` | `netflix-trailer` | `python3 scripts/download_video.py netflix-trailer` |
| F771 | Dailymotion tutorial series | `download_video.py` | `dailymotion-tutorial` | `python3 scripts/download_video.py dailymotion-tutorial` |
| F772 | Facebook Watch series offline | `download_video.py` | `fb-watch-series` | `python3 scripts/download_video.py fb-watch-series` |
| F773 | Instagram Reel recipe save | `download_video.py` | `ig-reel` | `python3 scripts/download_video.py ig-reel` |
| F774 | TikTok trend compilation | `download_video.py` | `tiktok-hashtag` | `python3 scripts/download_video.py tiktok-hashtag` |
| F775 | Reddit video with sound | `download_video.py` | `reddit-video` | `python3 scripts/download_video.py reddit-video` |
| F776 | YouTube live-stream DVR | `download_video.py` | `yt-live-dvr` | `python3 scripts/download_video.py yt-live-dvr` |
| F777 | Udemy course with auth | `download_video.py` | `udemy-course` | `python3 scripts/download_video.py udemy-course` |
| F778 | IMDb trailer 1080p | `download_video.py` | `imdb-trailer` | `python3 scripts/download_video.py imdb-trailer` |
| F779 | X/Twitter media tab | `download_video.py` | `twitter-x-media` | `python3 scripts/download_video.py twitter-x-media` |
| F780 | LinkedIn Learning (subscription) | `download_video.py` | `linkedin-learning` | `python3 scripts/download_video.py linkedin-learning` |
| F781 | Periscope replay before expiry | `download_video.py` | `periscope-replay` | `python3 scripts/download_video.py periscope-replay` |
| F782 | Bilibili anime + subs | `download_video.py` | `bilibili-anime-sub` | `python3 scripts/download_video.py bilibili-anime-sub` |
| F783 | Peertube federated instance | `download_video.py` | `peertube-instance` | `python3 scripts/download_video.py peertube-instance` |
| F784 | Rumble video download | `download_video.py` | `rumble` | `python3 scripts/download_video.py rumble` |
| F785 | Flickr video album | `download_video.py` | `flickr-video` | `python3 scripts/download_video.py flickr-video` |
| F786 | Snapchat Spotlight link | `download_video.py` | `snapchat-spotlight` | `python3 scripts/download_video.py snapchat-spotlight` |
| F787 | Pinterest video pin | `download_video.py` | `pinterest-pin` | `python3 scripts/download_video.py pinterest-pin` |
| F788 | Douyin Chinese TikTok save | `download_video.py` | `douyin` | `python3 scripts/download_video.py douyin` |
| F789 | ESPN highlight clip | `download_video.py` | `espn-highlight` | `python3 scripts/download_video.py espn-highlight` |
| F790 | NASA YouTube 8K astronomy | `download_video.py` | `nasa-yt-8k` | `python3 scripts/download_video.py nasa-yt-8k` |
| F791 | TED Talk + embedded subs | `download_video.py` | `ted-talk-sub` | `python3 scripts/download_video.py ted-talk-sub` |
| F792 | Lynda tutorial series | `download_video.py` | `lynda-tutorials` | `python3 scripts/download_video.py lynda-tutorials` |
| F793 | Crunchyroll free episode backup | `download_video.py` | `crunchyroll-ep` | `python3 scripts/download_video.py crunchyroll-ep` |
| F794 | CNN news clip | `download_video.py` | `cnn-clip` | `python3 scripts/download_video.py cnn-clip` |
| F795 | BBC iPlayer (UK TV license) | `download_video.py` | `bbc-iplayer` | `python3 scripts/download_video.py bbc-iplayer` |
| F796 | ARTE FR/DE documentary | `download_video.py` | `arte-doc` | `python3 scripts/download_video.py arte-doc` |
| F797 | 9GAG video meme | `download_video.py` | `9gag-meme` | `python3 scripts/download_video.py 9gag-meme` |
| F798 | YouTube Shorts compilation | `download_video.py` | `yt-shorts-bulk` | `python3 scripts/download_video.py yt-shorts-bulk` |
| F799 | Vevo ProRes music video | `download_video.py` | `vevo-prores` | `python3 scripts/download_video.py vevo-prores` |
| F800 | public Zoom cloud webinar | `download_video.py` | `zoom-webinar` | `python3 scripts/download_video.py zoom-webinar` |
| F801 | MS Stream org (with perms) | `download_video.py` | `ms-stream-org` | `python3 scripts/download_video.py ms-stream-org` |
| F802 | Wistia product demo | `download_video.py` | `wistia-demo` | `python3 scripts/download_video.py wistia-demo` |
| F803 | Loom shared video | `download_video.py` | `loom-colleague` | `python3 scripts/download_video.py loom-colleague` |
| F804 | public Google Drive video | `download_video.py` | `gdrive-video` | `python3 scripts/download_video.py gdrive-video` |
| F805 | Apple Trailers 4K HDR | `download_video.py` | `apple-trailer-4k-hdr` | `python3 scripts/download_video.py apple-trailer-4k-hdr` |
| F806 | Kickstarter project video | `download_video.py` | `kickstarter-project` | `python3 scripts/download_video.py kickstarter-project` |
| F807 | Bandcamp music video rip | `download_video.py` | `bandcamp-music-vid` | `python3 scripts/download_video.py bandcamp-music-vid` |
| F808 | OnlyFans public preview clip | `download_video.py` | `onlyfans-preview` | `python3 scripts/download_video.py onlyfans-preview` |
| F809 | Cameo (with permission) | `download_video.py` | `cameo-with-perm` | `python3 scripts/download_video.py cameo-with-perm` |
| F810 | YouTube Kids videos for car ride | `download_video.py` | `yt-kids-long-ride` | `python3 scripts/download_video.py yt-kids-long-ride` |
| F811 | Public Domain Torrents full movie | `download_video.py` | `pd-torrents-movie` | `python3 scripts/download_video.py pd-torrents-movie` |
| F812 | GitHub repo demo video | `download_video.py` | `github-demo-vid` | `python3 scripts/download_video.py github-demo-vid` |
| F813 | Discord attachment video | `download_video.py` | `discord-attachment` | `python3 scripts/download_video.py discord-attachment` |
| F814 | WordPress blog video | `download_video.py` | `wp-blog-vid` | `python3 scripts/download_video.py wp-blog-vid` |
| F815 | Google Photos shared album video | `download_video.py` | `gphotos-album` | `python3 scripts/download_video.py gphotos-album` |
| F816 | Amazon Prime Video trailer | `download_video.py` | `prime-video-trailer` | `python3 scripts/download_video.py prime-video-trailer` |
| F817 | academic journal open-access PDFs | `download_data.py` | `journal-pdfs` | `python3 scripts/download_data.py journal-pdfs` |
| F818 | gov open data CSV dump | `download_data.py` | `gov-csv` | `python3 scripts/download_data.py gov-csv` |
| F819 | all images on Wikipedia page | `download_data.py` | `wiki-images` | `python3 scripts/download_data.py wiki-images` |
| F820 | full site mirror (HTTrack) | `download_data.py` | `website-offline-httrack` | `python3 scripts/download_data.py website-offline-httrack` |
| F821 | Gutenberg author e-books | `download_data.py` | `gutenberg-author-ebooks` | `python3 scripts/download_data.py gutenberg-author-ebooks` |
| F822 | Shakespeare complete works | `download_data.py` | `shakespeare-text` | `python3 scripts/download_data.py shakespeare-text` |
| F823 | GitHub repo ZIP | `download_data.py` | `github-repo-zip` | `python3 scripts/download_data.py github-repo-zip` |
| F824 | Google Sheets published link to XLSX | `download_data.py` | `gsheets-xl` | `python3 scripts/download_data.py gsheets-xl` |
| F825 | Canva design as PDF | `download_data.py` | `canva-pdf` | `python3 scripts/download_data.py canva-pdf` |
| F826 | Prezi presentation | `download_data.py` | `prezi` | `python3 scripts/download_data.py prezi` |
| F827 | Figma file via share link | `download_data.py` | `figma-export` | `python3 scripts/download_data.py figma-export` |
| F828 | Notion page as HTML | `download_data.py` | `notion-html` | `python3 scripts/download_data.py notion-html` |
| F829 | Miro board image | `download_data.py` | `miro-board-img` | `python3 scripts/download_data.py miro-board-img` |
| F830 | public Dropbox folder | `download_data.py` | `dropbox-shared-folder` | `python3 scripts/download_data.py dropbox-shared-folder` |
| F831 | Google Fonts collection | `download_data.py` | `google-fonts` | `python3 scripts/download_data.py google-fonts` |
| F832 | Docker Hub image tar | `download_data.py` | `docker-image-tar` | `python3 scripts/download_data.py docker-image-tar` |
| F833 | Wikipedia full DB dump | `download_data.py` | `wiki-db-dump` | `python3 scripts/download_data.py wiki-db-dump` |
| F834 | OpenStreetMap tile set | `download_data.py` | `osm-tiles-region` | `python3 scripts/download_data.py osm-tiles-region` |
| F835 | AWS S3 public bucket | `download_data.py` | `s3-public-list` | `python3 scripts/download_data.py s3-public-list` |
| F836 | daily weather forecast PDF | `download_data.py` | `weather-pdf-daily` | `python3 scripts/download_data.py weather-pdf-daily` |
| F837 | Yahoo Finance stock data | `download_data.py` | `yahoo-finance-csv` | `python3 scripts/download_data.py yahoo-finance-csv` |
| F838 | CoinGecko crypto history | `download_data.py` | `coingecko-price-history` | `python3 scripts/download_data.py coingecko-price-history` |
| F839 | Google Trends CSV | `download_data.py` | `google-trends-csv` | `python3 scripts/download_data.py google-trends-csv` |
| F840 | Reddit subreddit top monthly | `download_data.py` | `reddit-top-images-month` | `python3 scripts/download_data.py reddit-top-images-month` |
| F841 | Imgur gallery memes | `download_data.py` | `imgur-gallery` | `python3 scripts/download_data.py imgur-gallery` |
| F842 | Pinterest board folder | `download_data.py` | `pinterest-board-folder` | `python3 scripts/download_data.py pinterest-board-folder` |
| F843 | public IG account photos | `download_data.py` | `ig-photos-public` | `python3 scripts/download_data.py ig-photos-public` |
| F844 | Flickr high-res album | `download_data.py` | `flickr-album` | `python3 scripts/download_data.py flickr-album` |
| F845 | Unsplash curated sets | `download_data.py` | `unsplash-curated` | `python3 scripts/download_data.py unsplash-curated` |
| F846 | every XKCD comic | `download_data.py` | `xkcd-all-time` | `python3 scripts/download_data.py xkcd-all-time` |
| F847 | NASA APOD archive | `download_data.py` | `nasa-apod-archive` | `python3 scripts/download_data.py nasa-apod-archive` |
| F848 | Bulbapedia images | `download_data.py` | `pokedex-bulbapedia` | `python3 scripts/download_data.py pokedex-bulbapedia` |
| F849 | Sketchfab 3D model | `download_data.py` | `sketchfab-model` | `python3 scripts/download_data.py sketchfab-model` |
| F850 | Thingiverse STL collection | `download_data.py` | `thingiverse-stl` | `python3 scripts/download_data.py thingiverse-stl` |
| F851 | DaFont font family | `download_data.py` | `dafont-family` | `python3 scripts/download_data.py dafont-family` |
| F852 | official ISO mirror | `download_data.py` | `iso-mirror` | `python3 scripts/download_data.py iso-mirror` |
| F853 | APK from APKMirror | `download_data.py` | `apk-apkmirror` | `python3 scripts/download_data.py apk-apkmirror` |
| F854 | Debian pkg + recursive deps | `download_data.py` | `deb-pkg-deps` | `python3 scripts/download_data.py deb-pkg-deps` |
| F855 | PyPI wheel download | `download_data.py` | `pypi-wheel` | `python3 scripts/download_data.py pypi-wheel` |
| F856 | Standard Ebooks EPUB | `download_data.py` | `epub-standard-ebooks` | `python3 scripts/download_data.py epub-standard-ebooks` |
| F857 | webcomic RSS strip save | `download_data.py` | `webcomic-rss` | `python3 scripts/download_data.py webcomic-rss` |
| F858 | subtitle by movie hash | `download_data.py` | `subtitles-by-hash` | `python3 scripts/download_data.py subtitles-by-hash` |
| F859 | FSI public language course | `download_data.py` | `fsi-language-course` | `python3 scripts/download_data.py fsi-language-course` |
| F860 | PACER public court docs | `download_data.py` | `pacer-case-docs` | `python3 scripts/download_data.py pacer-case-docs` |
| F861 | Flaticon vector icons | `download_data.py` | `flaticon-icons` | `python3 scripts/download_data.py flaticon-icons` |
| F862 | game-dev texture pack | `download_data.py` | `game-texture-pack` | `python3 scripts/download_data.py game-texture-pack` |
| F863 | Wayback Machine WARC save | `download_data.py` | `wayback-warc` | `python3 scripts/download_data.py wayback-warc` |
| F864 | YouTube video transcript text | `download_data.py` | `yt-transcript` | `python3 scripts/download_data.py yt-transcript` |
| F865 | Google Doc as PDF | `download_data.py` | `gdoc-as-pdf` | `python3 scripts/download_data.py gdoc-as-pdf` |
| F866 | IMAP auto-fetch mail attachment | `download_data.py` | `imap-attachment-rule` | `python3 scripts/download_data.py imap-attachment-rule` |
| F867 | Linux ISO via magnet link | `download_torrent.py` | `linux-iso-magnet` | `python3 scripts/download_torrent.py linux-iso-magnet` |
| F868 | seed Creative Commons Big Buck Bunny | `download_torrent.py` | `seed-cc-film` | `python3 scripts/download_torrent.py seed-cc-film` |
| F869 | PD TV show season | `download_torrent.py` | `pd-tv-show-season` | `python3 scripts/download_torrent.py pd-tv-show-season` |
| F870 | lossless album torrent (private tracker) | `download_torrent.py` | `lossless-album` | `python3 scripts/download_torrent.py lossless-album` |
| F871 | open-source software suite torrent | `download_torrent.py` | `oss-suite-torrent` | `python3 scripts/download_torrent.py oss-suite-torrent` |
| F872 | Nexus Mods mod torrent | `download_torrent.py` | `nexus-mods-collection` | `python3 scripts/download_torrent.py nexus-mods-collection` |
| F873 | Academic Torrents dataset | `download_torrent.py` | `academic-torrent-dataset` | `python3 scripts/download_torrent.py academic-torrent-dataset` |
| F874 | Wikipedia DB dump torrent | `download_torrent.py` | `wiki-db-torrent` | `python3 scripts/download_torrent.py wiki-db-torrent` |
| F875 | seed humanitarian research dataset | `download_torrent.py` | `seed-research-dataset` | `python3 scripts/download_torrent.py seed-research-dataset` |
| F876 | open textbooks torrent | `download_torrent.py` | `open-textbooks-torrent` | `python3 scripts/download_torrent.py open-textbooks-torrent` |
| F877 | fanedit film magnet | `download_torrent.py` | `fanedit-film-magnet` | `python3 scripts/download_torrent.py fanedit-film-magnet` |
| F878 | public domain 3D movie | `download_torrent.py` | `pd-3d-movie` | `python3 scripts/download_torrent.py pd-3d-movie` |
| F879 | Sonniss GDC sound effects | `download_torrent.py` | `soniss-gdc-soundfx` | `python3 scripts/download_torrent.py soniss-gdc-soundfx` |
| F880 | Stack Exchange data dump | `download_torrent.py` | `stack-exchange-data` | `python3 scripts/download_torrent.py stack-exchange-data` |
| F881 | HathiTrust PD books | `download_torrent.py` | `hathitrust-collection` | `python3 scripts/download_torrent.py hathitrust-collection` |
| F882 | OSBoxes VM image | `download_torrent.py` | `osboxes-vm-image` | `python3 scripts/download_torrent.py osboxes-vm-image` |
| F883 | metal music discography | `download_torrent.py` | `music-discography-metal` | `python3 scripts/download_torrent.py music-discography-metal` |
| F884 | Humble Bundle torrent option | `download_torrent.py` | `humble-bundle-torrent` | `python3 scripts/download_torrent.py humble-bundle-torrent` |
| F885 | HOTOSM mapping dataset seed | `download_torrent.py` | `hotosm-mapping-seed` | `python3 scripts/download_torrent.py hotosm-mapping-seed` |
| F886 | CC free-release movie torrent | `download_torrent.py` | `cc-free-movie` | `python3 scripts/download_torrent.py cc-free-movie` |
| F887 | auto-download new YouTube channel videos | `download_scheduled.py` | `channel-auto-new` | `python3 scripts/download_scheduled.py channel-auto-new` |
| F888 | save every new podcast episode | `download_scheduled.py` | `podcast-auto-new-ep` | `python3 scripts/download_scheduled.py podcast-auto-new-ep` |
| F889 | daily newspaper PDF morning | `download_scheduled.py` | `daily-news-paper-pdf` | `python3 scripts/download_scheduled.py daily-news-paper-pdf` |
| F890 | weather satellite imagery hourly | `download_scheduled.py` | `weather-sat-hourly` | `python3 scripts/download_scheduled.py weather-sat-hourly` |
| F891 | daily wildlife webcam photo | `download_scheduled.py` | `wildlife-cam-daily` | `python3 scripts/download_scheduled.py wildlife-cam-daily` |
| F892 | arXiv keyword-watch new papers | `download_scheduled.py` | `arxiv-keyword-watch` | `python3 scripts/download_scheduled.py arxiv-keyword-watch` |
| F893 | follow Bandcamp artist new releases | `download_scheduled.py` | `bandcamp-follow-new` | `python3 scripts/download_scheduled.py bandcamp-follow-new` |
| F894 | watch page for new download links | `download_scheduled.py` | `monitor-page-new-links` | `python3 scripts/download_scheduled.py monitor-page-new-links` |
| F895 | public cloud backup weekly | `download_scheduled.py` | `cloud-backup-weekly` | `python3 scripts/download_scheduled.py cloud-backup-weekly` |
| F896 | re-fetch on software update | `download_scheduled.py` | `software-auto-update` | `python3 scripts/download_scheduled.py software-auto-update` |
| F897 | daily FX rates JSON | `download_scheduled.py` | `daily-fx-rates-json` | `python3 scripts/download_scheduled.py daily-fx-rates-json` |
| F898 | auto-build personal trailers collection | `download_scheduled.py` | `auto-movie-trailer-netflix` | `python3 scripts/download_scheduled.py auto-movie-trailer-netflix` |
| F899 | morning briefing video compilation | `download_scheduled.py` | `morning-briefing-video` | `python3 scripts/download_scheduled.py morning-briefing-video` |
| F900 | auto-fetch specific sender attachments | `download_scheduled.py` | `imap-attachment-auto` | `python3 scripts/download_scheduled.py imap-attachment-auto` |
| F901 | SFX library monthly sync | `download_scheduled.py` | `sfx-library-monthly-sync` | `python3 scripts/download_scheduled.py sfx-library-monthly-sync` |
| F902 | Gopher hole for retro computing | `download_deepweb.py` | `gopher-hole-archive` | `python3 scripts/download_deepweb.py gopher-hole-archive` |
| F903 | IPFS hash content fetch | `download_deepweb.py` | `ipfs-hash-fetch` | `python3 scripts/download_deepweb.py ipfs-hash-fetch` |
| F904 | Gemini capsule offline save | `download_deepweb.py` | `gemini-capsule-save` | `python3 scripts/download_deepweb.py gemini-capsule-save` |
| F905 | Usenet binary via NZB | `download_deepweb.py` | `usenet-nzb-binary` | `python3 scripts/download_deepweb.py usenet-nzb-binary` |
| F906 | Z-Library mirror e-book | `download_deepweb.py` | `zlib-mirror-ebook` | `python3 scripts/download_deepweb.py zlib-mirror-ebook` |
| F907 | official Tor Browser bundle | `download_deepweb.py` | `tor-browser-bundle` | `python3 scripts/download_deepweb.py tor-browser-bundle` |
| F908 | Freenet sites collection | `download_deepweb.py` | `freenet-collection` | `python3 scripts/download_deepweb.py freenet-collection` |
| F909 | onion site via Tor proxy | `download_deepweb.py` | `onion-via-tor` | `python3 scripts/download_deepweb.py onion-via-tor` |
| F910 | public FTP server resume | `download_deepweb.py` | `ftp-resume` | `python3 scripts/download_deepweb.py ftp-resume` |
| F911 | Arweave decentralized dataset | `download_deepweb.py` | `arweave-dataset` | `python3 scripts/download_deepweb.py arweave-dataset` |
| F912 | I2P eepsite fetch | `download_deepweb.py` | `i2p-fetch` | `python3 scripts/download_deepweb.py i2p-fetch` |
| F913 | retro BBS archive pull | `download_deepweb.py` | `retro-bbs-archive` | `python3 scripts/download_deepweb.py retro-bbs-archive` |
| F914 | textfiles.com classic archive | `download_deepweb.py` | `textfiles-com` | `python3 scripts/download_deepweb.py textfiles-com` |
| F915 | Faraday-radio relay capture | `download_deepweb.py` | `faraday-grab` | `python3 scripts/download_deepweb.py faraday-grab` |
| F916 | anon-files cached mirror | `download_deepweb.py` | `anon-files-cached` | `python3 scripts/download_deepweb.py anon-files-cached` |

### Smoke test (F717 - F916)

```bash
cd "the tank project"
for s in scripts/{download_music,download_video,download_data,download_torrent,download_scheduled,download_deepweb}.py; do
   python3 "$s" --help >/dev/null && echo "OK  $s"
done

# Total F-IDs in README = F001-F206 (206) + F207-F406 (200) + F407-F716 (310) + F717-F916 (200) = 916 host-level features.
grep -E "^\| F[0-9]+ \|" "the tank project/README.md" | wc -l   # -> 916
```

## License

TBD — your call.
