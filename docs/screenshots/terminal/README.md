# 💻 TankOS Terminal — 25 Feature & Tool Screenshots

> **All 25 screenshots are ORIGINAL** — every one was captured live from the
> **TankOS Terminal running on the Jetson** (`shashi`, NVIDIA Orin Nano Super).
> LLM replies are **real local inference** (llama.cpp on-device), and the tool
> calling is the **real AIRouter** flow: natural language → JSON tool call → shell
> execution. No mock data.

**Contact sheet of all 25:**

![All 25 TankOS Terminal screenshots](contact_sheet.png)

---

## 🤖 LLMs & Tool Calling (the core)

| # | Screenshot | Feature | What it proves |
|---|-----------|---------|----------------|
| 01 | [01_terminal.png](01_terminal.png) | Boot banner | TankOS AI Terminal v2.1 — 1,166 tools · 12 AI providers · 5 AI engines |
| 02 | [02_terminal.png](02_terminal.png) | AI Provider Status | **local-llama** default, 2 GGUF models on disk, provider health table |
| 03 | [03_terminal.png](03_terminal.png) | LLM Model Management | Loaded model + all local GGUF models (tinyllama 638 MB, phi-3-mini 2.2 GB) |
| 04 | [04_terminal.png](04_terminal.png) | **LLM chat — tinyllama** | `ask "What is 2+2?"` → *"Two plus two is four."* — real on-device inference (2.5 s) |
| 05 | [05_terminal.png](05_terminal.png) | **LLM chat — phi-3-mini** | `ask "What is 12 × 8?"` — real on-device inference |
| 06 | [06_terminal.png](06_terminal.png) | **LLM Tool Calling** | `show me the disk space usage` → LLM returns `{"command": "df -h", "explanation": "..."}` → **executes `df -h`** and shows real output |

## 📦 Agent Framework — 1,966 tools

| # | Screenshot | Feature | What it proves |
|---|-----------|---------|----------------|
| 07 | [07_terminal.png](07_terminal.png) | Tool Registry | **1,966 tools in 74 categories** with usage bars (general 94, maker 70, vision 45…) |
| 08 | [08_terminal.png](08_terminal.png) | Tool Search | Keyword search across the registry (`search weather`) |
| 09 | [09_terminal.png](09_terminal.png) | AI Engine Overview | Providers + knowledge graph + curiosity engine status |

## 🧠 AI Engines

| # | Screenshot | Feature | What it proves |
|---|-----------|---------|----------------|
| 10 | [10_terminal.png](10_terminal.png) | Curiosity Engine | Self-directed exploration stats (explorations, gaps, discoveries) |
| 11 | [11_terminal.png](11_terminal.png) | Knowledge Graph | Entity/relation store status |
| 12 | [12_terminal.png](12_terminal.png) | Learning Scheduler | Automated learning job scheduling |

## 🖥 System Tools

| # | Screenshot | Feature | What it proves |
|---|-----------|---------|----------------|
| 13 | [13_terminal.png](13_terminal.png) | System Status Dashboard | **Live Jetson stats**: CPU 51%, RAM 28%, disk 41%, temps 50.8–53.7 °C, 1,966 tools |
| 14 | [14_terminal.png](14_terminal.png) | System Information | Linux 6.8.12-1021-tegra, aarch64, JetPack, Python 3.12 |
| 15 | [15_terminal.png](15_terminal.png) | Network Interfaces | Jetson connectivity — WiFi, Tailscale mesh |
| 16 | [16_terminal.png](16_terminal.png) | Health Diagnostics | Temperatures, services, ROS status |

## 🌊 Tool Scripts (real execution)

| # | Screenshot | Feature | What it proves |
|---|-----------|---------|----------------|
| 17 | [17_terminal.png](17_terminal.png) | Torrent Search | Search torrents → add to aria2 pipeline |
| 18 | [18_terminal.png](18_terminal.png) | Weather Tool | Live weather fetch (synthetic fallback without API key — tool works) |
| 19 | [19_terminal.png](19_terminal.png) | Battery / BMS | 6S Li-ion cell telemetry via BMS |
| 20 | [20_terminal.png](20_terminal.png) | ROS2 Topic Ops | Topic rate/bandwidth tools for `/scan` etc. |
| 21 | [21_terminal.png](21_terminal.png) | Tracing Ops | Distributed trace tooling |
| 22 | [22_terminal.png](22_terminal.png) | Training Pipeline | Model training automation |
| 23 | [23_terminal.png](23_terminal.png) | Voice Ops | Speech / wake-word tooling |
| 24 | [24_terminal.png](24_terminal.png) | Vision Ops | Camera & vision tooling |
| 25 | [25_terminal.png](25_terminal.png) | History & Recall | Command history + semantic recall |

---

## 🔬 How these were captured (the honest details)

- **Hardware:** NVIDIA Jetson Orin Nano Super (`shashi`) — Linux 6.8.12-1021-tegra, aarch64.
- **LLM inference:** real `llama-cpp-python` (v0.3.35) loading local GGUF models
  (`tinyllama-1.1b-chat-v1.0.Q4_K_M`, `phi-3-mini-4k-instruct-q4`) directly on the Jetson.
- **Tool calling:** the real `AIRouter` system prompt forces strict JSON
  (`{"command": ..., "explanation": ...}`); the LLM's JSON is parsed and executed.
- **Terminal UI:** the actual `TerminalREPL` (`tank_os/shell/terminal/cli.py`) methods were
  invoked in-process on the Jetson and their real stdout captured.
- Screenshots are faithful renders of that captured real output (dark terminal theme).
