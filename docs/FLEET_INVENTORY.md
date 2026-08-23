# Tank Fleet — Device Inventory & Connectivity Map

> Live-audited **2026-08-23** across all devices (unoq, Jetson, VPS, ESP32 boards).
> This is the authoritative record of every device, its interfaces, usage,
> connections, and requirements. Photo gallery: [`../docs/hardware_photos/`](hardware_photos/PHOTOS_README.md).

---

## 1. Fleet overview

| # | Node | Role | Tailscale IP | LAN IP | OS / arch |
|---|------|------|--------------|--------|-----------|
| 1 | **unoq** (host `skullcandy`) | Arduino UNO Q real-time controller + TankOS terminal | `100.84.235.7` | `192.168.31.72` | Debian 13 (trixie), aarch64 |
| 2 | **shashi** | NVIDIA Jetson Orin Nano Super — tank brain | `100.122.31.46` | `192.168.31.74` | JetPack Ubuntu, aarch64 |
| 3 | **medicscholar** (medigyaan.com) | Cloud VPS — API, Nextcloud, webdav, torrent cloud | `100.71.127.19` | `213.199.61.156` | Ubuntu, x86_64 |
| 4 | **shashis-z-flip6** | Operator phone (Tailscale app) | `100.91.134.103` | — | Android |
| 5 | ESP32-S3 CAM | ESPHome camera | — | `192.168.31.145` | ESPHome |
| 6 | ESP32-S3 Dual-eyes | Round-eye display driver (via Jetson USB) | — | — | ESP32-S3 |
| 7 | DFRobot ESP32-S3 AI Cam | Vision + IMU (via Jetson USB) | — | — | ESP32-S3 |

**Offline nodes (not currently reachable):** `openwrt` (100.72.169.107, 22d), `openwrt-pi-storage` (100.106.250.6, 51d), `raspberrypi` (100.85.16.126, 11d), `transformer` (100.125.165.27, 2d).

---

## 2. unoq (this board — Arduino UNO Q)

### 2.1 Network interfaces

| Interface | State | Address | Purpose |
|-----------|-------|---------|---------|
| `wlan0` | UP | `192.168.31.72/24` + IPv6 | **Primary** — WiFi `AirFiber-X9nxU1` (autoconnect) |
| `tailscale0` | UP | `100.84.235.7` | **Fallback** — mesh (boot-enabled) |
| `tun0` | UP | `10.8.0.4/24` | OpenVPN client (`0.0.0.0/1 via 10.8.0.1` — routes VPN traffic) |
| `enx9c7f64e08587` | DOWN | — | USB 10/100 LAN adapter (hub port 5, no cable) |
| `docker0` | UP | `172.17.0.1/16` | Docker bridge |

### 2.2 USB devices

| Device | VID:PID | Where | Purpose |
|--------|---------|-------|---------|
| ESP32-S3 CAM (JTAG/serial) | `303a:1001` | `/dev/ttyACM0` | ESPHome camera — serial `14:C1:9F:C1:2C:24` |
| QinHeng USB2.0 HUB | `1a86:809d` | hub | 6-port hub (ports 1,2,4,6 empty) |
| QinHeng USB 10/100 LAN | `1a86:5394` | `enx9c7f64e08587` | LAN adapter (unused) |

### 2.3 Usage & services

- **Disk:** 6.1G / 9.8G (67%) · **RAM:** 2.3G / 3.6G · **Load:** ~2.0
- **Docker:** `influxdb` (2.7), `ariang`, `aria2`, `torrent_cloud_db` (mariadb 11)
- **Systemd:** `docker`, `tailscaled`, `tankos-web-embed` (localhost terminal), `tankos-web` (ttyd web terminal), `x11vnc` (display :0)
- **Display:** XFCE on `:0` via x11vnc — USB Devices GUI launcher present

---

## 3. Jetson (shashi — tank brain)

### 3.1 Network interfaces

| Interface | State | Address | Purpose |
|-----------|-------|---------|---------|
| `wlP1p1s0` | UP | `192.168.31.74/24` + IPv6 | **Primary** — WiFi `AirFiber-X9nxU1` (autoconnect) |
| `tailscale0` | UP | `100.122.31.46` | **Fallback** — mesh (boot-enabled, SSH works) |
| `enxae0c29a39b6d` | UP* | link-local | Realtek RTL8152 USB LAN (no DHCP) |
| `can0`, `enP8p1s0`, `usb0`, `usb1`, `l4tbr0`, `enx00e04c360b2c` | DOWN | — | Unused (CAN, ethernet, USB gadget) |

### 3.2 USB devices

| Device | VID:PID | Port | Purpose |
|--------|---------|------|---------|
| **DFRobot ESP32-S3 AI Cam** | `303a:1001` | `/dev/ttyACM0` | Vision + IMU — serial `28:84:85:4C:84:04` — **now streaming video frames** (flash complete) |
| **ESP32-S3 Dual-eyes** | `303a:1001` | `/dev/ttyACM1` | Round-eye driver — serial `A0:F2:62:E3:DF:F4` — JSON commands over UART |
| Silicon Labs CP210x (LiDAR) | `10c4:ea60` | `/dev/ttyUSB0` | LDROBOT LD19 LiDAR |
| Quectel **EG800AK-CN** 4G LTE | `2c7c:6002` | `/dev/ttyUSB1-3` | Cellular backup — registered, 64% signal (AT / data / PPP) |
| WD My Passport | `1058:25e1` | — | Storage (WD20NMVW) |
| Realtek 4-port USB 2.0/3.0 hubs | `0bda:5489` / `0bda:0489` | — | USB expansion |
| Huasheng USB2.0 hubs | `214b:7260` ×2 | — | USB expansion |
| IMC Bluetooth | `13d3:3549` | — | Bluetooth |
| CASUE USB keyboard | `2a7a:9005` | — | Input |

### 3.3 Usage & services

- **Disk:** 39G / 95G (43%) · **RAM:** 1.5G / 7.3G · **Load:** ~0.3 · **GPU:** Orin (nvgpu)
- **Systemd:** `docker`, `edulabs-torrent-cloud` (TankOS Torrent Cloud), `tailscaled`, `tank-network` (WiFi→LTE→Hotspot failover), `tankos-web-embed`
- **Processes:** `tank_os.shell.terminal.tcp_entry` (terminal), `tank-network start` ×5
- **Desktop:** TankCamera + TankDashboard launchers, updated `TANK_RUNBOOK.md`

---

## 4. VPS (medicscholar.medigyaan.com)

### 4.1 Network interfaces

| Interface | State | Address | Purpose |
|-----------|-------|---------|---------|
| `eth0` | UP | `213.199.61.156/20` + IPv6 | Public internet |
| `tailscale0` | UP | `100.71.127.19` | **Fallback** — mesh, offers exit node |
| `tun0` | UP | `10.8.0.1/24` | OpenVPN server (VPN gateway for fleet) |
| `br-adf5ddf43d80` | UP | `172.18.0.1/16` | Docker bridge (Nextcloud/webdav stack) |

### 4.2 Services & usage

- **Disk:** 173G / 290G (60%) · **RAM:** 2.6G / 7.8G
- **Systemd:** `docker`, `nginx`, `tailscaled`, `tank-vps` (API server)
- **Listening:** `:8888` tank-vps API · `:80` nginx · `:443` OpenVPN · `:8080` docker · `3306` mariadb
- **Docker:** `nextcloud`, `nextcloud_db`, `webdav`, `ariang`, `aria2`, `torrent_cloud_db`
- **tank-vps API** (`/api/status`): state `OBSERVING`, sensors on **mock** data (real hardware not wired to VPS yet)

---

## 5. ESP32 boards (the 3)

| Board | MAC serial | Connection | Status 2026-08-23 |
|-------|-----------|------------|-------------------|
| **ESP32-S3 CAM** (ESPHome) | `14:C1:9F:C1:2C:24` | unoq USB `/dev/ttyACM0` + WiFi `.145` | ✅ ARP-reachable; HTTP sleeps in power-save (normal) |
| **ESP32-S3 Dual-eyes** | `A0:F2:62:E3:DF:F4` | Jetson USB `/dev/ttyACM1` | ✅ Present; JSON `{cmd}` protocol (`happy`/`alert`/`blink`/`gaze`) |
| **DFRobot AI Camera** (SEN0611) | `28:84:85:4C:84:04` | Jetson USB `/dev/ttyACM0` | ✅ **Flashing COMPLETE** — streams `[FRAME] 640x480` (CamWebServer) |

> ⚠️ **DFRobot camera updated:** previously "factory IMU-only", now flashing `CamWebServer.ino`
> (`~/The-Tank-Project/firmware/dfrobot_camera/CamWebServer.ino.bin`). Desktop config YAML is stale —
> update `firmware:` and `camera_stream:` fields.

---

## 6. Connectivity matrix (verified live)

| Path | How | Latency | Status |
|------|-----|---------|--------|
| unoq → Jetson | Tailscale direct (LAN) | **3 ms** | ✅ active |
| unoq → VPS | Tailscale (internet, exit node) | **188–224 ms** | ✅ active |
| unoq → ESP32 CAM | WiFi `.145` | — | ✅ ARP REACHABLE |
| Jetson → eyes | USB ttyACM1 | — | ✅ |
| Jetson → DFRobot cam | USB ttyACM0 | — | ✅ streaming frames |
| Jetson → LiDAR | USB ttyUSB0 | — | ✅ |
| Jetson → 4G modem | USB ttyUSB1-3 | — | ✅ registered 64% |

**Fallback hierarchy:** WiFi (`AirFiber-X9nxU1`, both Linux boxes autoconnect) → LTE (EG800AK-CN on Jetson) → Hotspot (`tank-network` manager) → Tailscale mesh (boot-enabled on all 3 Linux nodes).

---

## 7. Requirements checklist

| Requirement | unoq | Jetson | VPS | ESP32s |
|-------------|------|--------|-----|--------|
| Boot-persistent Tailscale | ✅ enabled | ✅ enabled | ✅ enabled | n/a (WiFi-only) |
| WiFi autoconnect | ✅ | ✅ | n/a (eth0) | ✅ CAM on `.145` |
| SSH access | ✅ local | ✅ `100.122.31.46` | ✅ `100.71.127.19` | n/a |
| tank-vps API | client | client | ✅ `:8888` systemd | n/a |
| Torrent cloud | ✅ aria2 | ✅ edulabs | ✅ aria2 | n/a |
| Monitoring | influxdb | — | nextcloud/webdav | — |
| Real-time controller | ✅ (this board) | commands via USB | — | — |

---

*Source of truth for wiring/pins: `WIRING.md` · software mapping: `docs/HARDWARE_DEPENDENCIES.md` · photos: `docs/hardware_photos/` + `images/build/`.*
