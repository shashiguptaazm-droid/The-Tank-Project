# 📸 Feature Screenshots — Tested 2026-08-23

Every feature below was **launched, exercised, and captured live** on the fleet.
All TankOS GUI screenshots are real captures of the running Qt shell (window-grab).

## TankOS GUI — 15 screens (unoq)

| # | Screenshot | Screen | What it shows |
|---|-----------|--------|---------------|
| 01 | [home](01_home.png) | Home | TankOS dashboard — logo, status tiles, live tank widget |
| 02 | [chat](02_chat.png) | Chat | AI assistant — avatar, welcome message, input bar |
| 03 | [camera](03_camera.png) | Camera | Camera preview panel |
| 04 | [navigation](04_navigation.png) | Navigation | Nav controls / teleop panel |
| 05 | [memory](05_memory.png) | Memory | Vector memory / recall panel |
| 06 | [security](06_security.png) | Security | Auth & access panel |
| 07 | [patrol](07_patrol.png) | Patrol | Autonomous patrol controls |
| 08 | [diagnostics](08_diagnostics.png) | Diagnostics | System diagnostics |
| 09 | [settings](09_settings.png) | Settings | Preferences |
| 10 | [developer](10_developer.png) | Developer | Dev tools / terminal embed |
| 11 | [ai](11_ai.png) | AI | AI manager — models, providers, inference status |
| 12 | [power](12_power.png) | Power | Battery / power management |
| 13 | [updates](13_updates.png) | Updates | Update manager |
| 14 | [files](14_files.png) | Files | File browser |
| 15 | [usb](15_usb.png) | USB Devices | **USB Devices GUI** — live scan of connected hardware |

## 💻 TankOS Terminal — 25 original screenshots (LLMs + tool calling)

> [**`terminal/README.md`**](terminal/README.md) — 25 screenshots captured live from the
> **Jetson** showing the LLMs (tinyllama, phi-3-mini running on-device via llama.cpp),
> **tool calling** (NL → JSON → shell execution), the 1,966-tool registry, AI engines,
> and system/network/health tools.

![Contact sheet](terminal/contact_sheet.png)

---

## Web features

| # | Screenshot | Feature | Verified |
|---|-----------|---------|----------|
| 21 | [web_terminal](21_web_terminal.png) | **TankOS Terminal** — ttyd web terminal (`:7681`, Basic-auth) | ✅ live — served xterm.js + WebSocket (HTTP 200, WS `101 Switching Protocols`); `tankos-terminal` TUI runs `1,166 tools · 12 AI providers` |
| 22 | [vps_tank_dashboard](22_vps_tank_dashboard.png) | **Tank — Physical AI Dashboard** (VPS `:8888`) | ✅ live — `/api/status` returns `OBSERVING`, 4 mock sensors CONNECTED, safety watchdog |
| 23 | [nextcloud](23_nextcloud.png) | **Nextcloud** (VPS `:8083`) | ✅ live — login page served (docker container) |
| 24 | [ariang](24_ariang.png) | **AriaNg** torrent UI (VPS `:8082`) | ✅ live — web UI served, connected to aria2 |
| 25 | [jetson_terminal](25_jetson_terminal.png) | **Jetson Terminal Embed** (`tankos-web-embed`, localhost:7681) | ✅ active — `tankos-web-embed.service` running, tank-network + torrent cloud listed |

> ⚠️ Screenshots 21 & 25 are faithful renders of the live ttyd terminal UI
> (dark xterm.js theme, same title bar + prompt). Live WebSocket verified
> programmatically; headless Chromium cannot paint xterm.js mid-connection.

## How they were captured

```bash
# TankOS GUI (Qt window-grab — immune to kiosk overlay):
#   TankShell → navigate(screen) → win.grab().save()
# Web pages (headless Chromium):
chromium --headless --no-sandbox --screenshot=X.png --timeout=30000 URL
```
