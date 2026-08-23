# 🎨 TankOS Media Assets

Presentation-ready visuals for the repo — **GIFs** (animated) and **infographics** (SVG, render natively on GitHub).

## 🎬 GIFs

| GIF | What it shows | Where |
|-----|---------------|-------|
| ![eyes](gifs/eyes_expressions.gif) | **Round-eye expressions** — the tank's dual 1.28" eyes cycling happy → alert → blink → neutral → surprise (exactly what the eye firmware draws) | `gifs/eyes_expressions.gif` |
| ![network](gifs/network_failover.gif) | **Network failover** — animated WiFi → 4G LTE → Hotspot → Tailscale hierarchy with pulsing active link | `gifs/network_failover.gif` |

Regenerate with: `python3 scripts/make_eyes_gif.py` · `python3 scripts/make_connectivity_gif.py`

## 📊 Infographics (SVG — render on GitHub)

| Infographic | What it shows | Where |
|-------------|---------------|-------|
| ![fleet](infographics/fleet_connectivity.svg) | **Fleet connectivity map** — unoq + Jetson + VPS + 3 ESP32 boards, WiFi primary, Tailscale mesh, live IPs & latency | `infographics/fleet_connectivity.svg` |
| ![hardware](infographics/hardware_inventory.svg) | **Hardware inventory** — all 12 components with product photos, locations & status | `infographics/hardware_inventory.svg` |
| ![esp32](infographics/esp32_boards.svg) | **The 3 ESP32 boards** — dual-eyes, DFRobot AI cam (flash complete!), ESP32-S3 CAM — serials, ports, status | `infographics/esp32_boards.svg` |
| ![arch](infographics/tankos_architecture.svg) | **TankOS architecture** — 5-layer stack: Shell → Core Managers → Robotics (16 ROS2 pkgs) → Jetson AI → Arduino UNO Q + peripherals | `infographics/tankos_architecture.svg` |

## 🔗 Embedded where?

- `docs/HARDWARE_DEPENDENCIES.md` §8 — photo gallery (product + build)
- `docs/FLEET_INVENTORY.md` — full device audit
- `STATUS.md` / `WIRING.md` / `images/README.md` — pointers to the above
