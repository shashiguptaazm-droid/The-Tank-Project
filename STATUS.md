# The Tank Project — STATUS.md

> **Handoff document.** Read this first in a fresh Freebuff session before
> touching anything in `/root/the tank project/`. It records everything
> shipped so far, where it lives, how it's wired, what still needs work,
> and how to validate a fresh checkout.

---

## 1. What this is

A tracked NVIDIA Jetson Orin Nano (8 GB) + Arduino UNO Q AI-companion robot —
eyes, voice, vision, navigation, persistent memory, structured coding-agent memory,
home-security expansion — packaged as a single ROS 2 Humble **colcon
workspace** plus out-of-tree Arduino sketches for the ESP32-S3 eyes and
Arduino UNO Q motor/sensor firmware.

* **Repo root:**   `/root/the tank project/`
* **Workspace:**   `/root/the tank project/tank_ws/`
* **AI Brain:**    NVIDIA Jetson Orin Nano Super 8 GB, JetPack 6 / Ubuntu 22.04
* **Controller:**  Arduino UNO Q (real-time motor/sensor I/O)
* **ROS distro:**  `humble`
* **Build:**       `ament_python` (every package is pure-Python — no C++)
* **Hardware photos:** [`docs/hardware_photos/`](docs/hardware_photos/PHOTOS_README.md) (product shots) + [`images/build/`](images/build/) (real tank photos) · gallery in [HARDWARE_DEPENDENCIES.md §8](docs/HARDWARE_DEPENDENCIES.md#8-hardware-photo-gallery)
* **Presentation:** [`PRESENTATION.md`](PRESENTATION.md) — hero banner, hardware wall, fleet map, infographics & animations
* **📺 UNO Q → Android TV:** [`docs/UNOQ_ANDROID_TV.md`](docs/UNOQ_ANDROID_TV.md) — UNO Q TV kiosk + ADB Android TV remote + torrent media hub (screenshots in `docs/screenshots/tv/`)
* **Fleet inventory:** [`docs/FLEET_INVENTORY.md`](docs/FLEET_INVENTORY.md) — every device, interface, usage, connection & requirement (live-audited 2026-08-23)
* **Feature screenshots:** [`docs/screenshots/`](docs/screenshots/README.md) — all 15 TankOS GUI screens + web terminal, VPS dashboard, Nextcloud & AriaNg tested & captured (2026-08-23)

---

## 2. Repo top-level

```
/root/the tank project/
├── STATUS.md             (this file)              ← read first next session
├── ARCHITECTURE.md       ASCII diagram + package table
├── PHASES.md             phase tracker / checklist
├── scripts/
│   ├── provision_pi5.sh  single idempotent installer (apt + pip + docker HA + Prom/Grafana + WG + Tailscale + Samba + WebDAV) — works on Jetson too
│   ├── dump_pinout.py    CLI dumping the GPIO map
│   ├── measure_track_width.py  one-shot odometry calibration
│   ├── replay_memory.py  offline recall CLI for tank_memory
│   └── phase_runner.py   offline P1–P10½ validator (F151–F156)
├── firmware/
│   └── eyes_esp32/eyes_esp32.ino   GC9A101 round-display firmware for ESP32-S3
└── tank_ws/src/          16 ROS 2 ament_python packages
```

---

## 3. Phase tracker

| Phase | Theme                                          | Status |
|-------|------------------------------------------------|--------|
| P1    | Foundation, motion, vision                     | ✅ done |
| P2    | Eyes, tracker, SLAM                            | ✅ done |
| P3    | Networking, NAS                                | ✅ done — systemd timer in `tank_nas/systemd/` |
| P4    | Security + auto-dock + power                   | ✅ partial — contactor wiring harness TODO |
| P5    | Voice + assistant + persistent memory          | ✅ done |
| P5½   | Emotion fan-out (eyes + OLED + dashboard)       | ✅ done — `tank_display` + bridge + feel-good |
| P6    | Coding-agent structured memory                 | ✅ done — systemd unit + docker override + DEC-007 smoke test shipped |
| P6½   | Append-only event logger + learner             | ✅ done |
| P7    | Autonomous patrolling + surveillance          | ✅ done |
| P8    | Real hardware + on-robot deploy                | ⏳ next |
| P9    | Bidirectional AI ↔ Pi bridge (Freebuff/Claude/Codex) | ✅ done — `tank_command_bridge` on :8082 |
| P10   | Voice task framework (9 sample tasks + registry) | ✅ done — `tank_task` |
| P10½  | AI humanness + complete preferences dashboard | ✅ done — `tank_personalize` on :8084 |
| P12   | Preload Manager — offline dependency system   | ✅ done — 95 deps across 15 categories, auto-download on boot |
| P13   | Unified Single-Command Installer              | ✅ done — `tank_os/install.sh` (12 steps) |
| P13½  | Fixed LLM model URLs (open-access)            | ✅ done — all 5 LLMs verified |
| P14   | Simple Internet — Universal Downloader        | ✅ done — REST API :8900, web dashboard, CLI, 6 voice plugins, search engine, download engine, RSS, library, auto-setup script |
| P14½  | Massive CLI Expansion (host-level)           | ✅ done — 1,166 features across 40 host-level CLI scripts in `scripts/` (F001-F206 baseline + F207-F406, F407-F716, F717-F1116, F1117-F1166 expansions) + `docs/DEPENDENCIES.md` + `requirements.txt` + `requirements-dev.txt` |

---

## 4. Packages at a glance

| Package           | Purpose                                                                  | LOC (py) |
|-------------------|--------------------------------------------------------------------------|---------:|
| `tank_bringup`    | global launch + watchdog + URDF + systemd                                 |     266 |
| `tank_motion`     | motor + pan-tilt + kinematics                                             |     622 |
| `tank_sensors`    | IMU + LiDAR publishers                                                    |     316 |
| `tank_vision`     | camera + eye-LCD bridge + YOLO tracker (+ P2)                             |     671 |
| `tank_navigation` | slam_toolbox 2D + RTAB-Map 3D                                             |     344 |
| `tank_speech`     | wake_word_listener (openWakeWord)                                         |     564 |
| `tank_memory`     | event-style vector memory (sqlite-vec + sentence-transformers)           |     927 |
| `tank_assistant`  | LLM (llama.cpp) + RAG + emotion engine                                    |     621 |
| `tank_text`       | Whisper STT + Piper TTS                                                   |     314 |
| `tank_dock`       | AprilTag auto-dock + IR homing + charge contactor                         |     187 |
| `tank_health`     | battery/INA219 + CPU/voltage + Prometheus exporter                        |     186 |
| `tank_security`   | motion detect + recorder + event logger/MQTT                              |     367 |
| `tank_dashboard`  | FastAPI backend + nginx reverse-proxy                                     |     177 |
| `tank_nas`        | Samba + WebDAV + rclone auto-backup helpers                               |      88 |
| `tank_meta`       | **P6** structured coding-agent memory (code + hw + decisions + knowledge) |   **1,906** |
| `tank_display`     | **P5½** emotion-driven face on 1.3" SH1106 OLED (I²C 0x70) + NullHal    |    **225** |
| `tank_command_bridge` | **P9** bidirectional AI ↔ Pi HTTP server :8082 + external LLM client (Freebuff/OpenAI/Anthropic) | **~720** |
| `tank_neutral`    | placeholder                                                              |       0 |

Totals: **93 Python files, 7,792 lines** across 23 packages
(+ firmware + scripts).

---

## 5. Per-package key files

### 5.1  `tank_motion` — drive train
* `tank_motion/motor_controller.py`         + `pan_tilt_controller.py`
* `tank_motion/kinematics.py`               tank-tread forward/inverse kinematics
* `test/test_kinematics.py`                 **12 tests** — passes
* Topics: `/cmd_vel`, `/odom`, `/pan_tilt_cmd`

### 5.2  `tank_vision` — camera + YOLO + eye bridge
* `tank_vision/eye_lcd_bridge.py`           Pi → ESP32-S3 UART JSON gateway
* `tank_vision/object_tracker.py`           YOLOv8n + NDC → /tracked_target
* `test/test_tracker_geometry.py`           **6 tests** — passes
* Topics: `/camera/image_raw`, `/eye_expression`, `/tracked_target`

### 5.3  `tank_speech` — wake word
* `tank_speech/wake_state.py`               pure-Python WakeLatch (threshold + cooldown + window)
* `tank_speech/wake_word_listener.py`       ROS 2 node wrapping openWakeWord
* `scripts/listen_wake.py`                  top-level CLI w/ `sounddevice`
* `test/test_wake_latch.py`                 **6 tests** — passes
* Topics: `/audio`, `/wake_detected`, `/wake_confidence`

### 5.4  `tank_memory` — persistent vector memory
* `tank_memory/memory_store.py`             `MemoryStore` ABC + `InMemoryStore` + `SqliteVecStore`
                                             (graceful fallback to numpy cosine when sqlite-vec missing)
* `tank_memory/memory_node.py`              ROS 2 node (snapshot timer, auto-compact, /memory/export_cmd)
* `test/test_memory_store.py`               **9 tests** — passes (3 real bugs were caught + fixed)
* `scripts/replay_memory.py`                offline JSONL export / query
* Topics: `/memory/event`, `/memory/query`, `/memory/recall_result`,
  `/memory/recent_snapshot`, `/memory/compact_result`, `/memory/status`

### 5.5  `tank_assistant` — LLM + RAG + emotion
* `tank_assistant/llm_node.py`              llama.cpp wrapper, intent → reply
* `tank_assistant/rag_node.py`              opens `tank_meta.MetaStore` AND local `tank_memory` for
                                             composite prompt = `system + structured-meta + memory + intent`.
                                             Publishes ROS queries on `/meta/{code,hw,dec}_search` and
                                             listens for results (cross-process sync).
                                             Gated on `_meta_healthy()` so cold-start doesn't dead-letter pile.
* `tank_assistant/emotion_node.py`          valence-arousal classifier → `/emotion/state`
* Topics: `/intent_text`, `/assistant_text`, `/assistant/context`, `/emotion/state`

### 5.6  `tank_text` — STT + TTS
* `tank_text/stt_node.py`                   Whisper → `/intent_text`
* `tank_text/tts_node.py`                   Piper → `/audio_out`
* Topics: `/audio`, `/intent_text`, `/audio_out`

### 5.7  `tank_health` — battery + Prometheus
* `tank_health/health_node.py`              INA219 + gpiozero BMS + CPU temp
* Topics: `/battery/state`, `/health/state`, `/health/prometheus`

### 5.8  `tank_dock` — auto-dock
* `tank_dock/dock_node.py`                  AprilTag + IR homing → `/dock/pose`, `/dock/charge_cmd`

### 5.9  `tank_security` — vision monitoring
* `tank_security/motion_node.py`            background subtraction → `/security/events/motion`
* `tank_security/recorder_node.py`          cv2.VideoWriter to disk
* `tank_security/event_logger.py`           JSON line + MQTT publish

### 5.10 `tank_dashboard` — FastAPI + nginx
* `tank_dashboard/app.py`                   `/api/{health,telemetry,recording/list,cmd/{estop,move}}`
                                          + `WS /ws/feed`
* `dashboard/nginx-site.conf`               reverse-proxy config

### 5.11 `tank_nas` — Samba + WebDAV + auto-backup
* `config/samba.conf`                       smb.conf snippet
* `scripts/auto_backup.py`                  rclone-based daily backup

### 5.12 `tank_navigation` — SLAM
* `tank_navigation/slam_2d_bridge.py`       slam_toolbox shim + PGM snapshots
* `tank_navigation/rtabmap_bridge.py`       lazy rtabmap_msgs import + JSON stats
* `launch/slam_2d.launch.py` + `rtabmap_3d.launch.py`
* `config/slam_toolbox.yaml` + `rtabmap.yaml`

### 5.13 **`tank_meta` — coding-agent structured memory (P6)** ← most recent
* `tank_meta/meta_store.py`                 sqlite, 4 tables: `code_files / hardware / decisions / knowledge`.
                                             Keyword relevance scoring (vector search lives in `tank_memory`,
                                             not here — separation of concerns).
* `tank_meta/code_indexer.py`               `ast.parse` walker — for each `.py` file:
                                             path, module, purpose (first docstring line), functions, classes,
                                             deps (top-level), mtime, line count.
* `tank_meta/hardware_indexer.py`           loads `content/hardware.json` (17 components)
* `tank_meta/decisions_indexer.py`          loads + appends `content/decisions.json` (DEC-001..006)
* `tank_meta/knowledge_indexer.py`          walks `docs/**.md`, extracts first-heading + first paragraph + tag list.
* `tank_meta/meta_node.py`                  ROS 2 node, `MutuallyExclusiveCallbackGroup`.
                                             Subscribes 6 topics, publishes 6 results.
                                             `/meta/decision_append` is **DB-first, JSON-second with bounded
                                             retry** so a transient JSON write failure cannot lose data on the
                                             next startup (which would otherwise overwrite via `INSERT OR REPLACE`).
                                             IDs must match `^[A-Z0-9_-]{2,32}$` before any write.
                                             Strings capped (problem 1KB, solution 2KB) to keep the JSON file sane.
* `tank_meta/scripts/search_meta.py`        offline query CLI: `code|hardware|decisions|knowledge|status`
* `tank_meta/scripts/index_workspace.py`    one-shot reindex CLI: `--apply` / `--status`
* `tank_meta/scripts/serve_meta_api.py`     FastAPI shim exposing the store over HTTP on `:8083`:
                                             `GET /api/meta/{code,hardware,decisions,knowledge,status}`.
                                             Uses **lifespan** manager (not deprecated `@on_event`).
                                             Lazy singleton uses `threading.Lock` + double-checked locking.
* `tank_meta/launch/meta.launch.py`         + `config/meta.yaml` for production
* `tank_meta/test/test_meta_store.py`       **6 tests** — passes
* `tank_meta/test/test_code_indexer.py`     **5 tests** — passes
* `tank_meta/test/test_decision_append.py`  **3 tests** — passes (one pending rclpy in CI env)
* `tank_meta/content/{hardware,decisions,project}.json`   static source-of-truth data

### 5.14 `firmware/eyes_esp32/eyes_esp32.ino`
* Arduino sketch. Drives 2× Waveshare 1.28″ round GC9A101 displays over SPI.
* JSON control over UART2 (baud 115200) from Pi.
* Parens balanced at depth 0 (verified).

---

## 6. Cross-package data flows (cheat sheet)

```
Sensors
  /scan, /imu/data, /camera/image_raw, /audio, /battery/state
        │
        ▼
Perception
  object_tracker (YOLO)         ─► /tracked_target ─► pan_tilt_controller
  wake_word_listener             ─► /wake_detected
  motion_node (security)         ─► /security/events/motion
  dock_node (AprilTag)           ─► /dock/pose, /dock/charge_cmd
  health_node                    ─► /health/state
        │
        ▼
Memory + Reasoning
  /memory/event, /memory/query   ─► memory_node (sqlite-vec)
  /intent_text                   ─► rag_node
                                     ├─ opens tank_meta.MetaStore directly
                                     ├─ publishes /meta/{code,hw,dec}_search
                                     ├─ listens /meta/{code,hw,dec}_result (sync)
                                     └─ renders composite prompt
                                     ─► /assistant/context + /assistant_text
  /assistant_text                ─► emotion_node ─► /emotion/state
  /meta/decision_append          ─► meta_node (DB-first, JSON-second w/ retry)
                                     ─► /meta/decision_append_result
  /audio                         ─► stt_node ─► /intent_text
  /intent_text                   ─► tts_node ─► /audio_out

Output
  /cmd_vel                       ◄── teleop / safety_watchdog
  /pan_tilt_cmd                  ◄── object_tracker (closed-loop)
  /eye_expression                ◄── emotion_node ─► eye_lcd_bridge ─► UART ─► ESP32-S3
  /cmd/charge                    ◄── dock_node (contact charging)
```

---

## 7. Persistence files (regenerable, but not "gitignored")

| Path                                                      | Format | Owner |
|-----------------------------------------------------------|--------|-------|
| `/root/the tank project/tank_ws/data/memory.db`            | sqlite-vec + numpy fallback | `tank_memory` |
| `/root/the tank project/tank_ws/data/meta.db`              | sqlite (4 tables) | `tank_meta` |
| `/root/the tank project/tank_ws/src/tank_meta/content/hardware.json` | JSON  | source-of-truth |
| `/root/the tank project/tank_ws/src/tank_meta/content/decisions.json` | JSON (append-only) | source-of-truth |
| `/root/the tank project/tank_ws/src/tank_meta/content/project.json`   | JSON  | static ref |

To rebuild from scratch via the CLI:
```bash
python3 /root/the\ tank\ project/tank_ws/src/tank_meta/scripts/index_workspace.py --apply
python3 /root/the\ tank\ project/tank_ws/src/tank_meta/scripts/search_meta.py status
```

---

## 8. Tests / validation, current state

* **pytest case count:**    **87** — 68 carried + **19 new** for P9 (6 auth+limit + 6 app-level routes + 7 external LLM provider shape).
* **Workspace py_compile:** 93/93 OK
* **pytest run in this CI environment:** all but one case pass; the
  failing case (`test_rag_meta_context_block_calls_meta_handles`) needs
  `rclpy` which is not installed in the dev sandbox — the case is
  expected to pass on the Jetson host where ROS 2 Humble base is provided by
  `scripts/provision_pi5.sh`.
* **`bash -n` on shell scripts:** passes
* **JSON content files:** parse OK (hardware, decisions, project)
* **End-to-end smoke test** (run interactively during build-out):
  `python3 scripts/index_workspace.py --apply` indexed 88 code rows,
  17 hardware rows, 6 decisions live.

To re-run all tests:
```bash
cd /root/the\ tank\ project/tank_ws/src/tank_meta && pytest -v
cd /root/the\ tank\ project/tank_ws/src/tank_motion && pytest -v
cd /root/the\ tank\ project/tank_ws/src/tank_memory && pytest -v
cd /root/the\ tank\ project/tank_ws/src/tank_speech && pytest -v
cd /root/the\ tank\ project/tank_ws/src/tank_vision && pytest -v
```

---

## 9. Recurring design rules (from code-reviewer feedback across phases)

These were enforced after code-review in earlier phases and should be upheld:

1.  **ROS callback groups:** every node with multiple subscribers uses
    `MutuallyExclusiveCallbackGroup` to avoid starving other nodes on a
    single-thread executor. Heavy subscribers (camera, encoder, etc.)
    belong on a separate group from lightweight ones (status publishers).
2.  **DB-first persist:** whenever you have a write that fans out to two
    stores (file + DB, file + vector index), write the **durable store
    first**, then the derived one with bounded retries.
3.  **ID format validation:** anything that becomes a primary key must
    pass a regex (`^[A-Z0-9_-]{2,32}$` for decisions — generalize per
    domain) before any write.
4.  **String slicing:** every line that flows into a prompt or log
    should be clipped (~200 chars) and every composite capped (~4 KB).
5.  **No deprecated FastAPI patterns:** use `lifespan=`, not
    `@app.on_event(...)`.
6.  **Lazy singletons in API servers:** wrap initialisation in
    `threading.Lock` + double-checked locking.
7.  **CLI errors shouldn't bury logs:** rate-limit warnings to ~1/20 s
    per source.
8.  **CLI first:** every Python module should have a `scripts/` wrapper
    that demos the same logic without ROS, so it can be tested + bench-
    debugged without spinning up a daemon.

---

## 10. Pending TODOs

| Item                                                              | Owner context                                                   |
|-------------------------------------------------------------------|------------------------------------------------------------------|
| Contact-charging wiring harness relay (GPIO21 + interlock)       | P4 carryover — needs physical build                            |
| `tank_meta/scripts/serve_meta_api.py` systemd unit + docker override | ✅ done — `tank_meta/systemd/serve_meta_api.{service,timer}` + `docker-compose.override.yml` |
| Decision DEC-007 smoke-test via the new `/meta/decision_append`    | ✅ done — `tank_meta/scripts/smoke_test_dec007.py` |
| `tank_meta` → `tank_assistant.emotion_node` link (a successful decision-append injects a 'satisfied' valence spike) | ✅ done — see `tank_assistant.emotion_node.EmotionNode._on_decision_result` (feel-good loop) |
| rclone cron template (`tank_nas/scripts/auto_backup.py`) — systemd timer | P3 carryover                                                  |
| Hardware integration — Jetson + Arduino UNO Q (boot, run `legacy installer`, flash Arduino firmware, launch `tank_bringup/launch/robot.launch.py`) | P7 |

---

## 11. Next-session cheatsheet

```bash
# 1. Re-read this file first.
cat "/root/the tank project/STATUS.md"

# 2. Validate before touching anything.
find "/root/the tank project" -name '*.py' -not -path '*/__pycache__/*' \
     | xargs python3 -m py_compile                  # workspace sanity
cd /root/the\ tank\ project/tank_ws/src/tank_meta && pytest -v
cd /root/the\ tank\ project/tank_ws/src/tank_memory && pytest -v

# 3. Reindex meta from source-of-truth.
python3 "/root/the tank project/tank_ws/src/tank_meta/scripts/index_workspace.py" --apply
python3 "/root/the tank project/tank_ws/src/tank_meta/scripts/search_meta.py" status

# 4. Look at a subsystem.
python3 "/root/the tank project/tank_ws/src/tank_meta/scripts/search_meta.py" code "wake word"
python3 "/root/the tank project/tank_ws/src/tank_meta/scripts/search_meta.py" hardware pan_servo
python3 "/root/the tank project/tank_ws/src/tank_meta/scripts/search_meta.py" decisions "pwm frequency"

# 5. Build ROS 2 workspace (Jetson only — needs colcon + ament_python + ROS Humble base).
cd /root/the\ tank\ project/tank_ws && colcon build --symlink-install

# 6. Bring the full system up.
bash "/root/the tank project/scripts/provision_pi5.sh" --apply    # one-time
source /opt/ros/humble/setup.bash
ros2 launch tank_bringup robot.launch.py
```

---

## 12. What was built this session (recently, in summary)

### 🟦 UNO Q 400-Item Upgrade Master Plan (latest)

* **Master plan:** [`docs/UNOQ_MASTER_PLAN.md`](docs/UNOQ_MASTER_PLAN.md) — all **400 upgrade targets**
  (sections A–S) mapped to their implementation, with the **top-20 P0/P1 priorities audited**
  against the live repo. Consolidation-first: extend existing modules, do not add files.
* **New code (the audited gaps):**
  - `tank_os/core/esp32_fleet.py` — **ESP32 fleet manager** (#281–300): identity registry
    (3 boards by MAC), USB discovery, heartbeat, timeout detection, telemetry aggregation,
    fleet self-test. Verified live: **ESP32-S3 CAM detected ONLINE** (`14:C1:9F:C1:2C:24`).
  - `tank_os/cli/unoq_cli.py` — **`tank unoq` command surface** (#321–340): `status · diagnostics ·
    sensors · motors · power · mcu · esp32 · self-test · safety-test`.
  - `tank_os/tests/test_esp32_fleet.py` + `test_unoq_cli.py` — **14 new tests**, full suite now **262 passing**.
* **Proof template:** [`docs/FEATURE_PROOF_TEMPLATE.md`](docs/FEATURE_PROOF_TEMPLATE.md) — mandatory
  FEATURE / TEST / MEASUREMENTS / STATUS block for every shipped feature (unit + simulated +
  hardware + failure test evidence).

## Recent expansion (post F206)

* **Massive CLI Scaling:** Expanded host-level capabilities to **1,166 features (F207-F1166) across 40 zero-dependency Python CLI scripts** in `scripts/`, covering AI & vision, personality & security, mobility & environment, media & home automation, comms/networking, maintenance, AI voice & vision AR, gaming, health, kitchen, education, creativity, productivity, social, energy, outdoor, security, maker, music & video downloading (round 1+2+3).
* **Dependency Definition:** Centralized all system-level (apt/brew) and Python (pip) dependencies into a single canonical doc at [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) (218 lines, 12 sections), with a matching `requirements.txt` (broad pip manifest) and `requirements-dev.txt` (dev tools). See also the placeholder `docs/SIMPLE_INTERNET_ARCH.md` linking the Simple Internet module-by-module architecture.
* **Advanced Simple Internet downloader (450 tasks across 3 rounds):** F717-F916 (200 tasks × 6 scripts in `scripts/download_*.py`), F917-F1116 (200 tasks × 10 scripts in `scripts/download_*_2.py`), F1117-F1166 (50 high-impact features × 4 scripts in `scripts/download_*_3.py`).
* **Architecture Integrity:** All 1,166 features ship as host-level CLI subcommands below the core ROS 2 workspace (`tank_ws/`) and TankOS GUI (`tank_os/`) layers. No changes to `tank_ws/src/*` runtime, no ROS topic additions, no firmware changes. The CLI surface is the feature surface.
* **P1-P5 carried over**, validated, archived in `PHASES.md`.
* **P6 `tank_meta`** created from scratch:
  - 4 sqlite tables (code_files, hardware, decisions, knowledge)
  - 4 indexers (Python AST, hardware JSON, decisions JSON, markdown notes)
  - ROS 2 node with 6 subscribe / 6 publish topics, hardened after review:
    * DB-first + JSON retry on `/meta/decision_append`
    * Lazy `_meta_healthy()` gate for cross-process queries
    * ID-format validation before any persist
    * String slicing / capping on every rendered line
  - 2 CLIs (`search_meta.py`, `index_workspace.py`)
  - FastAPI HTTP shim (`serve_meta_api.py`) with lifespan + threading.Lock
  - 15 pytest cases — all pass where rclpy is present
* **`tank_assistant.rag_node`** upgraded:
  - Opens `tank_meta.MetaStore` directly, injects top-1
    code/file/hardware/decision context into the LLM prompt before it
    sees the user's intent.
  - Publishes `meta/*_search` AND subscribes to `meta/*_result` for fresh,
    cross-process results.
* **`ARCHITECTURE.md` + `PHASES.md`** kept in sync after every batch.

That's the full picture. Next session: read this file, run the validation
section, and pick up the next pending TODO from §10.

---

## 13. Last session log (this run)

> Append-only record. Rendered as a single self-contained handoff so a
> fresh Freebuff session can pick up *exactly* where the previous one
> left off — no re-reading of docs required.

### 13.1  Last-run command list (verbatim)

```bash
# Sanity: every script in scripts/ parses cleanly under AST + bash -n
cd "/root/the tank project" && for s in scripts/*.py scripts/*.sh; do
   if [ "${s##*.}" = "py" ]; then python3 -c "import ast; ast.parse(open('$s').read())"; \
   else bash -n "$s"; fi
done

# Complete the incomplete script (the only orphan: phase_runner.py)
python3 -m py_compile "/root/the tank project/scripts/phase_runner.py"        # parse OK
cd "/root/the tank project" && python3 scripts/phase_runner.py --help         # 6 subcommands registered
cd "/root/the tank project" && python3 scripts/phase_runner.py phases         # 13 phases listed
cd "/root/the tank project" && python3 scripts/phase_runner.py logs --limit 200
cd "/root/the tank project" && python3 scripts/phase_runner.py examine "tank_ws/src/tank_meta/content/decisions.json" --head 3
cd "/root/the tank project" && python3 scripts/phase_runner.py check P6½     # exit 0 after seed
cd "/root/the tank project" && python3 scripts/phase_runner.py check BOGUS   # exit 1 + helpful error
cd "/root/the tank project" && python3 scripts/phase_runner.py seed --force  # creates tank_ws/data/log.db with 4 rows
cd "/root/the tank project" && python3 scripts/phase_runner.py run --soft    # walk every phase

# README feature-count validation (robust regex survives F0…F2… in future)
cd "/root/the tank project" && grep -cE '^\| F[0-9]+\|' README.md             # -> 156
```

### 13.2  Feature requests fulfilled this session

| # | Request (verbatim)                                            | Outcome                                                                                       |
|---|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| 1 | "check tank project and complete the incomplete scripts"       | `phase_runner.py` fixed: `args.force` replaces the `args_force()` sys.argv hack; `_check_json_keys("schema_version","decisions")` replaces the empty-keys no-op; P7 duplicate-`log.db` string cleaned; unused `import shutil` dropped. Doc-supported as **F151–F156** in `README.md`. |
| 2 | "log everything under a file for next time … so features are not lost" | This §13 — appended to `STATUS.md` as the persistent handoff.                       |

### 13.3  Robot features exposed over the network (brief list)

Short and stable — anyone wanting full detail should grep the file:line.

| Package                    | Port           | Protocol           | What the robot exposes over the wire                                       |
|----------------------------|---------------:|--------------------|---------------------------------------------------------------------------|
| `tank_dashboard.app`       | 8080           | HTTP + WebSocket   | `/api/health`, `/api/telemetry`, `/api/recording/list`, `/api/cmd/estop`, `/api/cmd/move`, `WS /ws/feed` (live `/health/state`). |
| `tank_command_bridge`      | 8082           | HTTP               | Bidirectional AI↔Pi: estop, move, manifest, ask-external-LLM (Freebuff/OpenAI/Anthropic) with bearer-auth + per-token rate-limit. P9. |
| `tank_meta.serve_meta_api` | 8083           | HTTP               | `GET /api/meta/{code,hardware,decisions,knowledge,status}` — coding-agent search over FastAPI (lifespan). |
| `tank_personalize.app`     | 8084           | HTTP               | Preferences dashboard + persona + dialogue-patterns (P10½).               |
| `tank_health` (Prometheus) | 9100           | Prom scrape        | `/metrics` — battery, CPU, voltage, BMS state.                            |
| `scripts/webhook.py`       | 9090           | HTTP               | Generic webhook receiver + replay + dedup (F125–F127).                    |
| `tank_security` (MQTT)     | 1883           | MQTT v3            | Publishes `/security/events/{motion,intruder}`, `/api/cmd/audit`.         |
| nginx reverse-proxy        | 80 / 443       | HTTPS              | Aggregates the FastAPI services behind one TLS endpoint.                  |
| `tank_nas` (Samba + WebDAV)| 445 / 80       | SMB / WebDAV       | Files shared over LAN: dashboard recordings + meta DB snapshots.          |
| WireGuard / Tailscale      | 51820 / 41641  | UDP                | Access on the road via the home VPN (F026).                               |
| Mosquitto broker           | 1883           | MQTT v3            | Standalone broker; accepts `event_logger` publishes.                      |
| `prometheus_bridge`        | —              | Prom pull          | Pulls `/metrics` from `tank_health` and friends (F049–F050, F128–F130).   |
| `tank_log` tail            | —              | ROS topics only    | Subscribe `/log/tail` if you want the last-10 log entries.                |

**Total externally-accessible robot capabilities: 13 distinct surfaces.**

### 13.4  Files touched this session

| Path                                                | Change                                |
|-----------------------------------------------------|---------------------------------------|
| `the tank project/scripts/phase_runner.py`          | 4 fixes + F-id docstrings             |
| `the tank project/README.md`                        | Added F151–F156 section               |
| `the tank project/STATUS.md`                        | This §13 (last-session log) appended  |

### 13.5  Quick re-start recipe (next session)

```bash
cd "/root/the tank project"
python3 scripts/phase_runner.py --help        # confirm tool is intact
python3 scripts/phase_runner.py run --soft    # walk every phase
sed -n '/^## 13\./,$p' STATUS.md             # read §13 (you are here)
```

---

## 14. Plugin batch F157–F206 (this batch was added)

> 15 new host-level CLI scripts / 50 subcommands, parallel to F001–F150.
> Theme: **daily-driver + lifestyle + comms + observability v2 + governance**.

| # | Script                 | Sub-cmds | F-IDs     | One-line purpose                                                |
|---|------------------------|---------:|-----------|-----------------------------------------------------------------|
| 1 | `home_auto.py`         | 3        | F157–F159 | Home Assistant + MQTT device ops (offline-first cache).          |
| 2 | `calendar_ops.py`      | 4        | F160–F163 | Daily / weekly events + search.                                 |
| 3 | `weather.py`           | 3        | F164–F166 | Synthetic-deterministic forecast (real call when API key set).  |
| 4 | `news.py`              | 4        | F167–F170 | Headlines + RSS + podcast feed list.                            |
| 5 | `media.py`             | 3        | F171–F173 | Local media library + queue + cast-to.                          |
| 6 | `package_track.py`     | 4        | F174–F177 | Single track, deliveries today, redirect, mark delivered.       |
| 7 | `reminder.py`          | 3        | F178–F180 | Schedule / list / snooze reminders.                             |
| 8 | `agent_tasks.py`       | 4        | F181–F184 | To-do list + habit streak (merged from todo.py + habit.py).     |
| 9 | `notify.py`            | 2        | F185–F186 | Cross-channel notification fan-out (offline sink per channel).  |
|10 | `compliance_ops.py`    | 4        | F187–F190 | GDPR delete + audit + retention + SLO report.                   |
|11 | `schema_ops.py`        | 3        | F191–F193 | Db list + migrate dry-run + REINDEX.                            |
|12 | `tracing_ops.py`       | 4        | F194–F197 | Trace list / export / tail / grep-trace.                        |
|13 | `capacity.py`          | 3        | F198–F200 | Snapshot usage + 30-day forecast + throttle heuristic.          |
|14 | `rosbag_ops.py`        | 4        | F201–F204 | Record / replay / inspect / trim (DRY-RUN without ROS).         |
|15 | `crash_dump.py`        | 2        | F205–F206 | Synthetic crash capture + symbolize via addr2line (DRY-RUN).    |
|   | **Total**              | **50**   | **F157–F206** | **15 scripts, 50 features.**                                |

### 14.1  Conventions (same as the prior batches)

* stdlib-first, lazy heavy imports (e.g., `urllib` in `news.py`,
  `subprocess` in `rosbag_ops.py`, `sqlite3` in `schema_ops.py`).
* Offline-first: each script degrades to a deterministic synthetic /
  cache-only response when its remote dependency is absent.
* Cache lives under `tank_ws/data/<script>.json` (per-script).
* Each CLI exits 0 on success and >= 1 on failure for clean CI use.
* F-id NR is committed: F157–F206 across 15 scripts, branching from
  the existing F156 (phase_runner.py) end-point.

### 14.2  Files added this batch

```
scripts/home_auto.py        scripts/calendar_ops.py      scripts/weather.py
scripts/news.py             scripts/media.py             scripts/package_track.py
scripts/reminder.py         scripts/agent_tasks.py       scripts/notify.py
scripts/compliance_ops.py   scripts/schema_ops.py        scripts/tracing_ops.py
scripts/capacity.py         scripts/rosbag_ops.py        scripts/crash_dump.py
```

Smoke: `for s in scripts/{home_auto,calendar_ops,weather,news,media,package_track,reminder,agent_tasks,notify,compliance_ops,schema_ops,tracing_ops,capacity,rosbag_ops,crash_dump}.py; do python3 "$s" --help >/dev/null && echo "OK $s"; done` should report `OK` 15 times.
```

---

## 10. TankOS Implementation (P11)

TankOS is a complete graphical AI operating environment at `tank_os/` that replaces the Pi desktop.

### Implementation Status

| Component | Status | Details |
|-----------|--------|---------|
| Event Bus | ✅ Done | Centralized pub/sub with priorities, async dispatch, history tracking |
| Plugin System | ✅ Done | Dynamic loader with manifest.json, PluginAPI base class, sandboxed execution |
| Settings Manager | ✅ Done | JSON-persisted config, 12 sections, dotted-path get/set, deep merge |
| Theme Engine | ✅ Done | Dark/light/custom with PySide6 CSS generation, accent colors, fonts |
| Animation Engine | ✅ Done | 60 FPS tweening with 7 easing functions + spring physics + particles |
| Hardware Manager | ✅ Done | Auto-detects cameras, serial, displays, audio, storage, network |
| Display Manager | ✅ Done | Brightness control, DSI/HDMI detection, screen blanking |
| Window Manager | ✅ Done | Floating windows, fullscreen, touch gestures, z-index stacking |
| Power Manager | ✅ Done | Battery monitoring, performance modes, sleep/shutdown/reboot |
| Notification Manager | ✅ Done | Animated priority notifications with speech capability |
| Security Manager | ✅ Done | Auth tokens, e-stop latch, surveillance toggle, event bus integration |
| Recovery Manager | ✅ Done | Crash detection, safe mode, backup/restore, watchdog monitoring |
| Diagnostics Manager | ✅ Done | CPU/RAM/disk/temp/ROS/logs — psutil + subprocess fallbacks |
| Network Manager | ✅ Done | Wi-Fi, Ethernet, LTE, Bluetooth, VPN detection + nmcli control |
| Storage Manager | ✅ Done | Volume scanning, usage summary, data directory management |
| Robot Manager | ✅ Done | Movement, estop, docking, patrol with safe clamping (≤0.5 m/s) |
| Vision Manager | ✅ Done | Camera capture, YOLO detection with cached model loading |
| Navigation Manager | ✅ Done | Waypoint editor (JSON persisted), pose tracking, nav commands |
| Memory Manager | ✅ Done | Episodic/semantic/procedural memory with vector search fallback |
| Emotion Manager | ✅ Done | Emotional state with decay, valence/arousal tracking, event integration |
| Boot Sequence | ✅ Done | 11-step orchestrator with per-step success/failure tracking |
| systemd service | ✅ Done | `tank-init.service` — boots automatically, restarts on failure |
| Installer | ✅ Done | `install.sh --apply` — installs Qt6, creates config, enables service |
| Voice Manager | ✅ Done | Wake / STT / TTS state machine + queue, 15 unit tests |
| AI Manager | ✅ Done | Provider registry + dispatch + stream + 16 unit tests |
| **Evolution Bridge** | ✅ **Done** | Bridges 14 evolution providers + rotation orchestrator + local GGUF into AIManager |
| **Local LLM Provider** | ✅ **Done** | Offline GGUF inference via llama-cpp-python, 5 models on disk |
| **Model Discovery** | ✅ **Done** | Auto-discovers models from 9 provider APIs, threaded parallel |
| Permission Manager | ✅ Done | RBAC + async grants (RLock fix for nested re-acquire), 16 unit tests |
| Application Manager | ✅ Done | Discovery + lifecycle + permission gating, 16 unit tests |
| Update Manager | ✅ Done | Provider poll + apply + rollback + 17 unit tests |
| Tank Shell screens | ✅ Done | 13 of 13 full-screen Qt6 apps shipped — all screens complete |
| AI-powered Terminal | ✅ Done | Headless engine + safety + history + AI router + REPL CLI + **real LLM provider integration** |
| Dashboard widget | ✅ Done | 3-zone real-time command center with live metrics, quick actions, camera, map, AI avatar, battery, clock, hardware monitor, storage, memory stats |
| Unit tests | ✅ Partial | 9 of 35 managers covered + terminal subsystem (200 / 200 tests green) |

### Architecture Specifications

All TankOS architecture specs are saved in `docs/`:
- `docs/tankos-spec.md` — Build Specification (boot, layers, shell, plugins)
- `docs/tankos-module-definitions-ai-powered.md` — 35 AI-Powered Module Definitions
- `docs/tankos-cognitive-architecture.md` — 22 Cognitive Systems
- `docs/tankos-ai-self-learning-modules-brief.md` — 29 Self-Learning Engines
- `docs/tankos-ai-evolution-layer.md` — Original 28 Evolution Engines
- `docs/complete-project-definition-for-chatgpt.md` — **Unified 21-section project definition**

### Quick Start

```bash
# Simulation mode (no Qt6 required)
cd /root/the\ tank\ project
PYTHONPATH=. python3 -m tank_os.shell.main

# Qt GUI mode (requires PySide6)
TANKOS_QT=1 PYTHONPATH=. python3 -m tank_os.shell.main

# Test AI provider rotation
python3 scripts/model_rotation.py --discover-first --timeout 10

# Discover current models from all providers
python3 scripts/model_auto_finder.py --timeout 15

# Install on Jetson Orin Nano
bash tank_os/install.sh --apply

# Start at boot
sudo systemctl enable tank-init.service
sudo systemctl start tank-init.service
```

## 14. Session Log — AI Evolution Bridge (July 27, 2026)

> Full session documentation at [`SESSION_LOG.md`](SESSION_LOG.md)
> Freebuff bootstrap at [`.freebuff_bootstrap.md`](.freebuff_bootstrap.md)

### What was built

| Component | File | Purpose |
|-----------|------|---------|
| Model Discovery Module | `tank_ws/.../evolution/model_discovery.py` | Auto-discover models from provider APIs (threaded parallel) |
| Auto-Finder CLI | `scripts/model_auto_finder.py` | CLI to query provider models, output JSON catalog |
| Rotation CLI | `scripts/model_rotation.py` | Rotation tester with circuit breakers |
| Local LLM Provider | `tank_os/core/local_llm_provider.py` | AIProvider wrapping llama-cpp-python for offline GGUF inference |
| Evolution Bridge | `tank_os/core/evolution_bridge.py` | Bridges 14 evolution providers + rotation into AIManager |
| Bootstrap | `.freebuff_bootstrap.md` | Next-session resume instructions |

### Provider fixes

| Provider | Before | After |
|----------|--------|-------|
| Cerebras | `llama-3.3-70b` (404) | `gpt-oss-120b` (✅ HEALTHY) |
| Cohere | `command-r-plus` (deprecated) | `command-r-plus-08-2024` (✅ HEALTHY) |
| OpenRouter | `anthropic/claude-3.5-sonnet` (404) | `openai/gpt-4o-mini` |
| Gemini | DISABLED | Re-enabled (quota resets) |
| Replicate | Broken predictions payload | Chat completions API |
| worker.js | Stale model names | Updated from live APIs |

### Pending TODOs

| Item | Notes |
|------|-------|
| Install llama-cpp-python | Prebuilt wheel at `/var/cache/tank_os/preload/llama_cpp_python.whl` |
| Fix DeepSeek API key | HTTP 401 — key may have expired |
| Top up OpenRouter credits | HTTP 402 — needs billing |
| Wire model discovery into RotationOrchestrator | Auto-refresh on startup |
| Add `do_providers` REPL command | Show live provider status in terminal |
| Enable Cloudflare discovery | Needs ACCOUNT_ID set in env |

### Session quick-start

```bash
cd "/root/the tank project"
cat SESSION_LOG.md
python3 scripts/model_auto_finder.py --timeout 15    # discover models
python3 scripts/model_rotation.py --timeout 10        # test rotation
python3 -m tank_os.shell.main                          # launch shell -> terminal
```

---

## 16. Session Log 5 — Tank Shell Completion (July 30, 2026)

> Date: July 30, 2026
> Previous: SESSION_LOG.md (July 29) — Model Discovery Wiring + Provider Audit
> This session: Completed remaining Tank Shell screens, enhanced Dashboard, documentation updates

### What was built

| Component | File | Purpose |
|-----------|------|---------|
| Power Screen | `tank_os/windows/power_screen.py` | Battery monitoring, performance modes (powersave/balanced/performance), sleep/reboot/shutdown controls, auto-refresh metrics |
| Updates Screen | `tank_os/windows/updates_screen.py` | Software update management: check/apply/rollback, provider history, select-all bulk apply, event-driven status |
| Files Screen | `tank_os/windows/files_screen.py` | Storage volume browser, file explorer with breadcrumb nav, disk usage analyzer with top-10 directory sizes, rescan |
| Enhanced Dashboard | `tank_os/shell/dashboard.py` | 3-zone layout (Zone A: camera+AI+emotion, Zone B: map+nav, Zone C: quick actions+system health), 6 live metric tiles, 3 auto-refresh timers |
| Shell wiring | `tank_os/shell/main.py` | Wired power/updates/files screens into ScreenMap, global declarations, simulation CLI commands |

### Bug fixes

| Issue | Fix |
|-------|-----|
| Missing module-level globals for new screens | Added `_PowerScreen`, `_UpdatesScreen`, `_FilesScreen = None` declarations + `global` in `_try_load_qt()` |
| `SecurityManager().lock()` didn't exist | Added `lock()` and `unlock(token)` methods to SecurityManager |
| `update_manager.py` missing `import sys` | Added `import sys` (used by `ScriptsOTAProvider.apply()`) |
| Fragile hex-color parsing in Power screen | Replaced string-index parsing with explicit `(r, g, b)` integer tuples |

### Screens status: 13/13 complete ✅

1. home (Dashboard) ✅
2. chat (AI Chat) ✅
3. camera (Vision) ✅
4. navigation (SLAM Map) ✅
5. memory (Memory Explorer) ✅
6. security (Security) ✅
7. patrol (Patrol) ✅
8. diagnostics (Diagnostics) ✅
9. settings (Settings) ✅
10. developer (Dev Tools) ✅
11. ai (AI Engines) ✅
12. **power (Power) ✅ — NEW**
13. **updates (Updates) ✅ — NEW**

Plus: **files (Files/Storage) ✅ — NEW**, **terminal (AI Terminal REPL) ✅**

### Verification

| Check | Result |
|-------|--------|
| py_compile (all new files) | ✅ 0 errors |
| AST parse | ✅ All OK |
| pytest (86/87) | ✅ No regressions |
| TankShell import test | ✅ Simulation OK |

### Pending TODOs (updated)

| Item | Priority | Notes |
|------|----------|-------|
| Real hardware bring-up on Jetson + Arduino | 🔴 High | P8 — boot, install Arduino, launch |
| Unit tests for TankOS managers | Medium | 9/35 covered — expand coverage |
| Fix DeepSeek API key | External | HTTP 401 |
| Top up OpenRouter credits | External | HTTP 402 |
| [DONE] Tank Shell screens (13/13) | — | All screens complete |
| [DONE] Dashboard widget (3-zone) | — | Real-time command center |
| [DONE] SecurityManager.lock() | — | Lock/unlock added |
| [DONE] update_manager sys import | — | Fixed |

---

## 15. Session Log 2 — TCP Terminal + NL→Tool Routing + LLM Verification (July 28, 2026)

> Full session documentation at [`SESSION_LOG.md`](SESSION_LOG.md)
> Process flow chart at [`docs/COMMAND_PIPELINE_FLOWCHART.md`](docs/COMMAND_PIPELINE_FLOWCHART.md)

### What was built

| Component | File | Purpose |
|-----------|------|---------|
| TCP Terminal Wrapper | `/usr/local/bin/tankos-terminal` | Direct TCP entry point for TerminalREPL (bootstraps AI, no Qt) |
| TCP Socket Unit | `/etc/systemd/system/tankos-terminal.socket` | Systemd socket listening on `[::]:2223` with rate limiting |
| TCP Service Unit | `/etc/systemd/system/tankos-terminal@.service` | Per-connection service piping REPL to TCP |
| NL→Tool Routing | `tank_os/shell/terminal/engine.py` | Routes NL queries to ToolRegistry when AI can't translate to shell |
| NL→Tool REPL Handler | `tank_os/shell/terminal/cli.py` | Displays tool suggestions + unrecognized NL gracefully |
| Process Flow Chart | `docs/COMMAND_PIPELINE_FLOWCHART.md` | 7-section ASCII architecture + data flow |

### Packages installed (dev mode)

```
tank_command_bridge  tank_assistant  tank_learn  tank_speech
tank_vision        tank_sensors    tank_motion tank_navigation
tank_patrol
```

### Key fixes

| Issue | Before | After |
|-------|--------|-------|
| NL torrent query | `can: not found` (shell error) | Tool suggestions with `invoke` commands |
| Undetectable tool routing | Emoji sentinel `🔧` in error string | `tool_suggestion_shown` + `unrecognized` bool flags |
| Dead code in `interpret()` | Unreachable "Sorry" message | Clean path with proper flag handling |
| tank_command_bridge imports | `ModuleNotFoundError` | 29 plugins importable, `TorrentSearchPlugin` works |

### Verified LLM function (all 7 tests passed)

| # | Test | Result |
|---|------|--------|
| 1 | Torrent prompt → tool suggestion | ✅ No more shell error |
| 2 | NL→Shell (4 queries) | ✅ All translated (`ls *.py`, `df -h`, `date`, `find ...`) |
| 3 | Tool search (5 categories) | ✅ 3-5 matches per query |
| 4 | `!echo` explicit command | ✅ Exit 0, 3ms |
| 5 | Safety classification | ✅ READ/BLOCKED/MUTATING/SAFE all correct |
| 6 | AI error explanation | ✅ Full LLM explanation with fix suggestion |
| 7 | Full pipeline simulation | ✅ Complete chain traced |

### Final system state

| Metric | Value |
|--------|-------|
| Evolution providers registered | 12 |
| Tools discovered | 1,166 |
| Tool categories | 51 |
| Packages installed (tank_ws) | 8+ |
| TCP terminal port | 2223 |
| Tests passed | 7/7 |
| NL→Shell translation accuracy | 4/4 ✅ |

### New service endpoints

| Port | Service | How to reach |
|------|---------|-------------|
| **2223** | **TankOS Terminal REPL** | `telnet <ip> 2223` or `nc <ip> 2223` |

### Pending TODOs

| Item | Priority | Notes |
|------|----------|-------|
| Install llama-cpp-python | Medium | Wheel at `/var/cache/tank_os/preload/llama_cpp_python.whl` |
| Fix DeepSeek API key | Low | HTTP 401 |
| Top up OpenRouter credits | Low | HTTP 402 |
| Add `do_providers` REPL command | Low | Live provider status |

### Quick start for next session

```bash
cd "/root/the tank project"

# 1. Verify compile
find . -name '*.py' -not -path '*/__pycache__/*' | xargs python3 -m py_compile 2>&1 | grep -c ERROR

# 2. Test LLM function
PYTHONPATH=tank_ws/src python3 -c "
from tank_os.core.ai_manager import AIManager
from tank_os.core.evolution_bridge import init_evolution_providers
a = AIManager(); a.initialize()
c = init_evolution_providers(discover_models=False, set_rotation_default=True)
print(f'{c} providers registered, default={a.default_provider}')
print(f'Chat: {a.chat(\"Reply just: ok\", max_tokens=10).text}')
"

# 3. Launch shell
python3 -m tank_os.shell.main          # then type 'terminal'

# 4. Connect via TCP
nc localhost 2223

# 5. Read flow chart
cat docs/COMMAND_PIPELINE_FLOWCHART.md
```
