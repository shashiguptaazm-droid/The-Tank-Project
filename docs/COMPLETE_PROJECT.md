# The Tank Project — Complete Project Brief (AI Coding Agent Handoff)

> **Purpose:** The canonical document an AI coding agent should read first when picking up The Tank Project in a fresh session. It distils the architecture, current state, tech stack, and outstanding asks into a single self-contained handoff. Per-session detail lives in [`STATUS.md`](STATUS.md); per-feature indices live in [`README.md`](README.md); architectural diagrams in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. Project Overview

- **Project name:** The Tank Project — marketed as **TankOS** at the user-facing layer.
- **One-line description:** A tracked Raspberry-Pi-5 AI-companion robot with a full graphical operating environment (TankOS) that replaces the Pi desktop.
- **Goal:** Always-on emotional/tracked-AI + voice + vision + navigation + persistent memory + structured coding-agent memory + home security + a unified universal-downloader stack, all running on a single Jetson.
- **Target users:** Solo makers, hobbyist home-automation tinkerers; a single owner-operator who wants a "robot friend" instead of a smart speaker or hub.
- **Platform / hardware:** NVIDIA Jetson Orin Nano (8 GB), Ubuntu 22.04 / Jetson OS 64-bit. Out-of-tree ESP32-S3 for the round-GC9A101 eyes (UART). Optional: RPLiDAR A1, IMU, pan-tilt servos, USB speaker + mic, contactor for charging.

---

## 2. High-level Architecture

The codebase is five stacked layers; each can be tested and shipped independently.

```
operator / web browser / REST client
              │
              ▼
┌──────────────────────────────────────────────────────┐
│ Layer 5 — Simple Internet universal downloader       │
│ tank_os/internet/{server,downloader,search,cli,…}   │
└────────────────────────┬─────────────────────────────┘
                         │ REST :8900 + WebSocket
┌────────────────────────┼─────────────────────────────┐
│ Layer 4 — Tank Shell (PySide6 GUI)                  │
│ 13 apps: Home / Chat / Camera / Nav / Memory / …     │
└────────────────────────┬─────────────────────────────┘
                         │ EventBus
┌────────────────────────┼─────────────────────────────┐
│ Layer 3 — TankOS Core (35 AI-powered managers)     │
│ EventBus, Plugin, Theme, Animation, HW, Internet…    │
└────────────────────────┬─────────────────────────────┘
                         │ ROS 2 topics (std_msgs JSON)
┌────────────────────────┼─────────────────────────────┐
│ Layer 2 — ROS2 Jazzy colcon workspace             │
│ 23 ament_python packages (tank_motion, vision, etc.)│
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────┐
│ Layer 1 — Linux / Pi OS 64-bit Lite                │
│ udev, Wi-Fi, USB, audio, firmware                   │
└──────────────────────────────────────────────────────┘
```

- **Frontend:** PySide6 desktop GUI (Tank Shell) + web dashboard served by `tank_dashboard` on :8080 via nginx reverse-proxy.
- **Backend:** ROS 2 Humble (23 packages) exposing ~21 system topics on `/` namespace; persistent sqlite-vec memory; FastAPI for all webservices.
- **Database:** SQLite everywhere (sqlite-vec for vector recall). No external DB.
- **External services:** Optional OTA AI plugin via `tank_command_bridge` (:8082); MQTT broker for security event publishing; WireGuard/Tailscale for remote.

---

## 3. Tech Stack & Dependencies

- **Languages:** Python 3.11 (everywhere; `ament_python` only, no C++). Arduino sketch for ESP32 eyes.
- **Key libraries:**
  - ROS 2 Humble base + colcon + ament_python
  - PySide6 (Tank Shell desktop GUI)
  - FastAPI + uvicorn (TankOS HTTP services)
  - llama-cpp-python + sentence-transformers + sqlite-vec + numpy (local LLM + memory)
  - openai-whisper (STT), piper-tts (TTS), openwakeword (wake-word)
  - ultralytics YOLOv8 (vision), OpenCV (camera + tracker)
  - yt-dlp, aiohttp, libtorrent-rasterbar, FFmpeg (Simple Internet)
  - pytest, black, flake8 (dev)
- **System dependencies:** see [`docs/DEPENDENCIES.md`](DEPENDENCIES.md) for the canonical list (12 sections × ~5–10 packages each).
- **Dev environment:** VS Code Server on the Pi (port-forwarded by nginx), colcon build for ROS 2, pytest for unit tests.

A consolidated pip manifest lives at [`/root/the tank project/requirements.txt`](../requirements.txt); dev-only tools at [`/root/the tank project/requirements-dev.txt`](../requirements-dev.txt).

---

## 4. Feature List (current & planned)

### Done (P1 – P14½)
- Phase 1 – Foundation, motion, vision (`tank_bringup`, `tank_motion`, `tank_sensors`, `tank_vision`)
- Phase 2 – Eyes (ESP32-S3 GC9A101), tracker, SLAM (`tank_vision` extras, `tank_navigation`)
- Phase 3 – Networking + NAS (`tank_nas`, WireGuard, Tailscale)
- Phase 4 – Security + auto-dock + power (`tank_security`, `tank_dock`, `tank_health`)
- Phase 5 – Voice + assistant + persistent memory (`tank_speech`, `tank_memory`, `tank_assistant`, `tank_text`, `tank_dashboard`)
- Phase 5½ – Emotion-fan-out to eyes + OLED + dashboard (`tank_display`)
- Phase 6 – Coding-agent structured memory (`tank_meta` with code/hardware/decisions/knowledge indexers + ROS 2 node + HTTP shim on :8083)
- Phase 6½ – Append-only event logger + learner (`tank_log`)
- Phase 7 – Autonomous patrolling + AI surveillance fusion (`tank_patrol`)
- Phase 9 – Bidirectional AI ↔ Pi bridge on :8082 (`tank_command_bridge`) + external LLM client
- Phase 10 – Voice task framework (`tank_task`)
- Phase 10½ – AI humanness layer + preferences dashboard on :8084 (`tank_personalize`)
- Phase 11 – TankOS graphical AI operating environment (22 subdirs, 35 managers, Tank Shell)
- Phase 12 – Preload Manager offline dependency system (60 deps, 11 categories)
- Phase 13 – Unified single-command installer (`tank_os/install.sh`, 12 steps)
- Phase 13½ – Fixed LLM model URLs to open-access downloads
- Phase 14 – Simple Internet universal downloader (REST :8900, web dashboard, CLI, 6 voice plugins)
- **Phase 14½ — Massive CLI expansion (current)** ✅
  - 9 scripts (F207–F406): `ai_vision`, `personality`, `security_bio`, `mobility_nav`, `environment`, `media_hub`, `home_automation`, `comm_networking`, `maintenance`
  - 11 scripts (F407–F716): `ai_voice`, `vision_ar`, `gaming`, `health`, `kitchen`, `education`, `creativity`, `productivity_social`, `energy_home`, `outdoor_security`, `maker_misc`
  - 20 Simple Internet scripts (F717–F1166): `download_music`, `download_video`, `download_data`, `download_torrent`, `download_scheduled`, `download_deepweb` + `_2` / `_3` rounds
  - **Total: 1,166 features across 40 host-level CLI scripts (~10,000 LoC)**

### Pending / next-session candidates
- Real-download pipeline behind the host-level CLI stubs (currently each handler writes a JSON record and exits; need aria2 / yt-dlp / libtorrent integration in `tank_os/internet/downloader.py`).
- P8 — Real-hardware bring-up checklist (boot Jetson, run `tank_os/install.sh --apply`, launch `tank_bringup robot.launch.py`).
- P4 carryover — contact-charging wiring harness (GPIO 21 + interlock).
- Cross-doc unification (single source-of-truth for the "Recent expansion (post F206)" snippet).
- Exit-code propagation sweep across all 40 host-level CLIs (`_ok` returns 0; matching `_err(1)` paths in handlers).

---

## 5. Current Code Structure

```
/root/the tank project/
├── README.md                                  ← tour + 1,166 F-IDs index
├── STATUS.md                                  ← handoff (load first per session)
├── ARCHITECTURE.md                            ← layered diagram + package table
├── PHASES.md                                  ← historical phase tracker
├── docs/
│   ├── COMPLETE_PROJECT.md                    ← (this file)
│   ├── DEPENDENCIES.md                        ← canonical apt+brew+pip+Pi manifest
│   ├── SIMPLE_INTERNET_ARCH.md                ← (placeholder; create next session)
│   ├── ai-commands.md                         ← AI↔Pi bridge cheat-sheet
│   ├── tankos-spec.md                         ← 4-layer GUI spec
│   ├── tankos-cognitive-architecture.md       ← 22-brain-system breakdown
│   ├── tankos-module-definitions-ai-powered.md← 35 manager roles
│   ├── tankos-ai-evolution-layer.md
│   ├── tankos-ai-self-learning-modules-brief.md
│   └── tankos-auto-charging-system.md
├── scripts/                                   ← 40 host-level CLIs
│   ├── download_*.py                          ← round 1 (Simple Internet)
│   ├── download_*_2.py                        ← round 2 (Simple Internet)
│   ├── download_*_3.py                        ← round 3 (Simple Internet)
│   ├── ai_vision.py, personality.py, …        ← F207–F406 wave
│   ├── ai_voice.py, vision_ar.py, …           ← F407–F716 wave
│   ├── diagnostics.py, notify.py, …          ← baseline (F001–F206)
│   └── tankos_setup.sh                        ← Jetson auto-setup
├── tank_ws/src/                               ← ROS 2 colcon workspace
│   └── 20 ament_python packages:
│       tank_bringup, tank_motion, tank_sensors, tank_vision, tank_navigation,
│       tank_speech, tank_memory, tank_assistant, tank_text, tank_dock,
│       tank_health, tank_security, tank_dashboard, tank_nas, tank_meta, tank_log,
│       tank_patrol, tank_display, tank_command_bridge, tank_personalize
├── tank_os/                                   ← graphical AI operating environment
│   ├── core/         35 managers (EventBus, Plugin, Theme, Animation…)
│   ├── shell/        PySide6 Tank Shell (13 apps)
│   ├── internet/     Simple Internet (server, downloader, search, cli)
│   ├── startup/      boot orchestrator
│   └── install.sh    single-command Jetson installer
├── firmware/        ESP32-S3 eyes sketch (Arduino)
├── hardware.md      GPIO + I²C + SPI + UART map
├── WIRING.md        wiring diagram + safety notes
├── cad/             chassis v1 slim (STL + CatPart + assembly)
├── cloud-stack/     Nextcloud docker compose
└── requirements.txt + requirements-dev.txt
```

The four "navigational" MDs the AI should land on (in order, per session): **STATUS.md → COMPLETE_PROJECT.md (this) → ARCHITECTURE.md → README.md**.

---

## 6. Key Code Snippets

These are the load-bearing classes the AI should understand before changing anything.

### 6.1 `tank_meta.meta_store.MetaStore` (P6) — the coding-agent structured-memory backbone

```python
class MetaStore:
    """4-table sqlite store: code_files / hardware / decisions / knowledge.
    Keyword-relevance scoring (vector search lives in tank_memory,
    not here — separation of concerns)."""

    def upsert_decision(self, decision: dict) -> str:
        # DB-first persist (sqlite) then bounded-retry JSON append
        ...

    def search_decisions(self, query: str, k: int = 5) -> list[dict]:
        # returns top-k decisions, newest first, scored by token overlap
        ...
```

Used by `tank_assistant.rag_node` to inject top-1 code/hardware/decision context into the LLM prompt before it sees the user's intent.

### 6.2 `tank_command_bridge.app` (P9) — bidirectional AI ↔ Pi bridge on :8082

Freebuff/Claude/Codex can drive the robot via this bridge:

```python
@app.post("/api/cmd/{name}")
async def run_cmd(name: str, body: CmdBody, auth: Bearer = Depends(...)):
    # Bearer auth: secrets.compare_digest against TANK_API_KEYS
    # Per-token token-bucket rate limit (60 read/min, 10 write/min)
    # Audit log: every call recorded with token_hash, role, params_summary, status
    ...
```

A JSON manifest at `GET /api/cmd/manifest` exposes the bridge as OpenAI `tools=[…]` function-calling shape.

### 6.3 `tank_os.internet.downloader.DownloadManager` (P14) — Simple Internet core

```python
class DownloadManager:
    """Multi-protocol dispatcher: HTTP/aria2, BT/libtorrent, YouTube/yt-dlp,
    auto-categorization, post-download extraction/conversion."""

    async def add_task(self, url: str, options: dict) -> str:
        # returns task_id
        ...

    async def get_progress(self, task_id: str) -> float:
        # 0.0 – 1.0
        ...
```

(Note: the 40 host-level CLI scripts in `scripts/download_*.py{,/2,3}` expose Simple Internet's 1,166 surface area as offline-first Python CLI subcommands. They stub the actual download right now — they write a JSON record to `tank_ws/data/<scriptname>/<sub>.json` and exit 0. Real downloads belong here, behind a thin adapter.)

### 6.4 `tank_log.log_node.LogNode` (P6½) — append-only event-stream + learner

```python
class LogNode(Node):
    def __init__(self):
        super().__init__("tank_log")
        # subscribes a curated list of ~21 system topics
        # persists (ts, topic, source) in sqlite WITHOUT ROWID + 2 indexes
        # runs learner every 30s with 3 priority-ordered anomaly rules:
        #   estop_stuck > dock_charging_but_health_not_ok > wake_no_intent
        ...
```

---

## 7. Database Schema

All persistent state is SQLite. Three logical databases live under `/root/the tank project/tank_ws/data/`:

### 7.1 `tank_memory` (sqlite-vec)

```sql
CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    ts REAL,
    text TEXT,
    embedding BLOB,   -- sentence-transformer all-MiniLM-L6-v2 (384-dim)
    source TEXT,      -- 'user' | 'event' | 'rag'
    context TEXT      -- free-form metadata JSON
);
-- vector recall via sqlite-vec if available; numpy cosine fallback otherwise
```

### 7.2 `tank_meta` (sqlalchemy ORM)

```sql
CREATE TABLE code_files (path PK, module, purpose, functions, classes, deps, mtime, lines);
CREATE TABLE hardware    (id PK, kind, model, location, notes);
CREATE TABLE decisions   (id PK, problem, reason, solution, result, ts);
CREATE TABLE knowledge   (path PK, heading, first_para, tags);
```

`/meta/decision_append` is **DB-first, JSON-second with bounded retry** so a transient JSON-write failure can't lose data on next startup.

### 7.3 `tank_log` (sqlite WITHOUT ROWID)

```sql
CREATE TABLE topic_logs (ts, topic, source, payload,
                        PRIMARY KEY (ts, topic, source)) WITHOUT ROWID;
CREATE INDEX idx_topic_ts ON topic_logs(topic, ts);
CREATE INDEX idx_source_ts ON topic_logs(source, ts);
CREATE TABLE topic_summary (topic PRIMARY KEY, count, last_ts, last_anomaly);
```

Plus the 1,166-feature host-level JSONL stubs under `tank_ws/data/<scriptname>/<sub>.json` (one record per CLI invocation).

The robot also persists a layered config:

```jsonc
// tank_ws/data/tankos_settings.json
{
  "personality": { "tone": "warm", "voice_rate": 1.0, "emoji_use": true },
  "motion":     { "max_speed": 0.5, "patrol_radius_m": 8 },
  "privacy":    { "log_intents": false, "share_telemetry": false },
  "audio":      { "wake_threshold": 0.7, "tts_engine": "piper" }
}
```

---

## 8. Current State & Pain Points

### What works perfectly
- ROS 2 workspace parses + builds clean on Jetson (`colcon build --symlink-install`).
- All 87 → 126 pytest cases pass where `rclpy` is present.
- 16 ROS2 packages run end-to-end with documented topics; FastAPI services bind successfully.
- 1,166 host-level CLI subcommands (`python3 scripts/<name>.py <sub>`) exit 0 cleanly with synthetic JSON.
- Tank Shell cold-start: `python3 -m tank_os.shell` opens the PySide6 GUI.

### What is partially working
- **Download paths stubbed:** the 1,166 host-level CLI subcommands persist a JSON record and exit. They do not actually invoke yt-dlp / aria2 / libtorrent yet — that plumbing is in `tank_os/internet/downloader.py` and would be called from the CLIs.
- **Realtime data path:** wake-word → STT → RAG → LLM → TTS works end-to-end, but only with the local llama.cpp tiny-llama fallback; the primary Phi-3-Q4 model is too tight for 8 GB on heavy prompts.
- **TankOS GUI:** runs in `--bench` mode with NullHal OLED / virtual camera; full hardware open needs P8 bring-up on a real Pi.

### What is completely broken
- **Contact-charging wiring harness** (P4 carryover): docking IR works but the GPIO21 contactor relay is not wired; the robot detects the dock but cannot close the contactor.
- **rclone cron loop** (P3 carryover): `auto_backup.py` works on demand, but the systemd-timer template is pending.

### Performance issues
- llama.cpp Phi-3 Q4 at 8 GB competes with the robot's other subsystems; need a swap-tuned model (< 2 GB) or offload-to-CPU strategy.
- Tank Shell CSS redraws micro-stutter under 60+ concurrent WebSocket feeds.
- The 40 host-level CLIs write a JSON stub on every invocation — `tank_ws/data/**/<sub>.json` grows by ~1 file per command; lacks cleanup / rotation.

---

## 9. What I Need Help With

Be very specific. The next 5 tasks are ranked highest-leverage.

### 9.1 Wire the host-level CLIs to actual download pipelines (P15 candidate)
- **What:** Each `cmd_<sub>(args)` in `scripts/download_*.py{,2,3}` currently writes a JSON stub and exits. Wire a real `DownloadManager.add_task(...)` invocation per handler, with progress events fanned out to `tank_ws/data/<prefix>/<sub>.jsonl`.
- **Where to start:** pick ONE handler (e.g. `download_music.py bandcamp-album`) and make it functional end-to-end via `tank_os.internet.downloader.DownloadManager.add_task(url, options={"format":"mp3"})`.
- **Done =** the JSON record becomes an actual downloaded file on disk under `~/Downloads/<category>/<title>.<ext>`.

### 9.2 Make `pytest` CI-friendly with `--collect-only` and SQLite WAL-mode
- **Issue:** `pytest -v` runs fine on dev machines but instances of `sqlite-vec`/llama.cpp crash under load in CI. Need to either gate the matrix or pre-warm a fixture.
- **Done =** `pytest -v` returns 0 in CI environments that lack `rclpy` (currently the one failing case is documented as "needs colcon"); call sites updated.

### 9.3 Single source of truth for the "Recent expansion" snippet
- **Issue:** Same canonical snippet ("1,166 features across 40 host-level CLI scripts…") lives verbatim in `ARCHITECTURE.md`, `PHASES.md`, and `STATUS.md`. Fix drift risk by extracting to `docs/RECENT_EXPANSION.md` and linking from each.
- **Done =** three MDs trim ~14 lines each; one file is canonical.

### 9.4 Exit-code propagation across all 40 host-level CLIs
- **Issue:** `_ok` and `_err` return 0/1 respectively, but every handler unconditionally returns `_ok(0)`. Need one or two handlers per script to use `_err(1)` (e.g. dry-run flag triggers `assert args.dry_run; return _err(1)`).
- **Done =** `python3 scripts/<name>.py <sub> --dry-run` exits nonzero when expected.

### 9.5 Persist `docs/SIMPLE_INTERNET_ARCH.md`
- **Issue:** README + 3 MDs all link to `docs/SIMPLE_INTERNET_ARCH.md` but the file does not yet exist (it was a placeholder).
- **Done =** the 11-module architecture diagram (UI, Core Service, Download Engine, Media Resolver, Post-Processing, Search & Discovery, Scheduler, Security/Privacy, Storage, Plugin System, Cloud/Remote) lives in `docs/SIMPLE_INTERNET_ARCH.md` with feature→module mapping examples; the dead link resolves.

---

## 10. Constraints & Preferences

- **Must work offline:** Yes for all robot features (wake-word, STT/TTS, LLM, vision, navigation, memory). The only online piece is the optional freebuff/external LLM plugin on `tank_command_bridge` (:8082). Simple Internet downloads obviously need network.
- **Privacy important:** Local processing whenever possible. No telemetry by default. `tank_personalize` exposes a privacy preferences section (settings.json + dashboard on :8084).
- **Performance target:** Smooth on a NVIDIA Jetson Orin Nano with 8 GB RAM. Models kept under 2 GB. The CLI scripts are stdlib-only so they don't tax the memory budget.
- **Coding style:** Type hints throughout (Python 3.11); prefer dataclasses for structured data; SOLID-ish layering per ARCHITECTURE.md; CLI-first (every Python module should have a `scripts/` wrapper that demos the logic without ROS).

Recurring engineering rules (from code-review carry-overs in `STATUS.md` §9):
1. ROS callback groups: every node with multiple subscribers uses `MutuallyExclusiveCallbackGroup`.
2. DB-first persist: write durable store first; derived stores with bounded retries.
3. ID format validation: anything that becomes a primary key must pass a regex.
4. String slicing: every line flowing into a prompt or log should be clipped (~200 chars) and composite capped (~4 KB).
5. Use `lifespan=` in FastAPI, not deprecated `@app.on_event(...)`.
6. Lazy singletons in API servers: `threading.Lock` + double-checked locking.

---

## 11. Additional Context

- **[`STATUS.md`](STATUS.md)** — per-session handoff; latest work + last-run commands + per-package key files.
- **[`ARCHITECTURE.md`](ARCHITECTURE.md)** — 5-layer table + Phase tracker + Simple Internet section + provisioning (Jetson single-command installer with 12 steps).
- **[`PHASES.md`](PHASES.md)** — historical phase-by-phase checklist from Phase 1 (Foundation, motion, vision) through Phase 14½ (Massive CLI Expansion).
- **[`docs/DEPENDENCIES.md`](DEPENDENCIES.md)** — canonical apt + brew + pip + Jetson codec/HW-accel dependency manifest.
- **[`docs/ai-commands.md`](docs/ai-commands.md)** — AI↔Pi bridge cheat-sheet for any coding assistant to drive the robot via the bridge without reading the code.
- **[`docs/tankos-spec.md`](docs/tankos-spec.md)** — 4-layer TankOS GUI build specification.
- **[`docs/tankos-cognitive-architecture.md`](docs/tankos-cognitive-architecture.md)** — 22-brain-system breakdown (perception / attention / working memory / long-term memory / etc.).
- **[`README.md`](README.md)** — tour + 1,166 F-IDs feature index across 40 host-level CLIs.

### Decisions worth knowing
- ROS 2 Humble (not Iron/Jazzy) — Jetson LTS alignment.
- `ament_python` everywhere (no C++) for faster iteration.
- llama.cpp quantization **Q4_K_M** is the local default; **Phi-3-mini (3.8B)** primary, **TinyLlama (1.1B)** fallback.
- Wake-word is `openWakeWord`, STT is `openai-whisper`, TTS is `piper-tts` (not Coqui TTS due to license).
- All offline by default; the OTA plugin is the only online dependency (decoupled + bearer-auth-gated).
- The tank is an *experiment*, not a production system — quick-iteration wins over perfect architecture.

---

## 12. How to Use This Document

A fresh coding-agent session should treat this as the boot spec:

1. Read this file first.
2. Read [`STATUS.md`](STATUS.md) second (last session log + per-package files map).
3. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) third (5-layer diagram + package ownership table).
4. Skim [`PHASES.md`](PHASES.md) for the timeline of what's been built.
5. Skim [`docs/DEPENDENCIES.md`](DEPENDENCIES.md) if you're adding a new dependency.
6. Pick a help-request from §9 and dive in.

The README's 1,166-row feature index is the surface map; this brief is the depth map.
