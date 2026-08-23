# 📺 UNO Q — Android TV Connection

The **Arduino UNO Q** board doubles as the tank's **home media hub + Android TV
controller**. It runs the **UNO Q TV** cloud-stack — a Node.js app that serves a
full-screen TV kiosk, a torrent media library, and an **ADB-based Android TV
remote** — all branded **"UNO Q TV"**.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Arduino UNO Q  (unoq)                        │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │   cloud-stack (Node.js server, port 8200)                │   │
│   │   ┌────────────┐  ┌───────────────┐  ┌────────────────┐  │   │
│   │   │  UNO Q TV  │  │  Media Hub    │  │  TV Remote     │  │   │
│   │   │  kiosk UI  │  │  torrents →   │  │  (ADB control) │  │   │
│   │   │  (Chromium │  │  download →   │  │  power / volume │  │   │
│   │   │   fullscreen)│  │  stream/watch │  │  channels / cast │  │   │
│   │   └────────────┘  └───────────────┘  └────────────────┘  │   │
│   └──────────────────────────────────────────────────────────┘   │
│                    │  ADB :5555 (WiFi)                           │
└────────────────────┼─────────────────────────────────────────────┘
                     ▼
        ┌───────────────────────────┐
        │    Android TV / Jio STB   │
        │  (remote control, cast,   │
        │   app launch, channel zap)│
        └───────────────────────────┘
```

- **UNO Q → TV link:** ADB over WiFi (`adb connect <tv-ip>:5555`), driven by the
  remote page's keyevents / intents.
- **Kiosk display:** Chromium fullscreen on the UNO Q's display shows the "UNO Q TV"
  brand page (the `app-settings.json` brand is served on `:8200`).
- **Media:** torrent search → aria2 download → stream/watch in the browser.

## Components

| File | Purpose |
|------|---------|
| `cloud-stack/server.js` | The full UNO Q TV app — kiosk UI, media hub, ADB TV remote API |
| `cloud-stack/tv-settings.json` | Android TV connection settings (IP, ADB port `5555`, MAC, cast app, channel list) |
| `cloud-stack/app-settings.json` | Branding — `"brandName": "UNO Q TV"` |
| `cloud-stack/package.json` | Node deps (torrent-search-api, cheerio, mysql2, …) |
| `cloud-stack/config/aria2/` | aria2 download config for the media hub |

## Android TV Remote (the interesting part)

The `/remote` page (also the desktop **"TV Remote"** launcher →
`http://192.168.31.72:8200/remote`) controls a real Android TV via ADB:

- `adb connect <tv-ip>:5555` — pairs with the TV over WiFi
- **Power / volume / navigation** — `input keyevent` codes
- **Text input** — `input text`
- **Cast** — `am start` intent with `-d <url>` (YouTube by default, per `castApp`)
- **Channel zapping** — saved channel list (Star Plus 501, Sony MAX 502…)
- **Device info** — `getprop ro.product.model` / `ro.build.version.release`

## Screenshots (captured live from the running app)

| Screen | What it shows |
|--------|---------------|
| [Home / kiosk](screenshots/tv/31_unoq_tv_home.png) | "UNO Q TV" brand page (fullscreen kiosk on the UNO Q display) |
| [TV Remote](screenshots/tv/32_unoq_tv_remote.png) | Android TV remote control card |
| [Media Hub](screenshots/tv/33_unoq_tv_media.png) | Torrent media library |
| [Settings](screenshots/tv/34_unoq_tv_settings.png) | TV connection settings (IP, ADB port) |
| [Login](screenshots/tv/35_unoq_tv_login.png) | Access gate |

## Related

- Fleet node: `unoq` — see [`FLEET_INVENTORY.md`](FLEET_INVENTORY.md#2-unoq-this-board--arduino-uno-q)
- The board itself: [`docs/hardware_photos/2_arduino_uno_q.jpg`](hardware_photos/2_arduino_uno_q.jpg)
- Desktop launcher: `~/Desktop/TV Remote.desktop` → `http://192.168.31.72:8200/remote`
