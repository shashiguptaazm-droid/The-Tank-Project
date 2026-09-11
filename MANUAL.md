# MediGyaan Video & Audio Calling — Complete Implementation Manual

> **Last updated:** 11 September 2026
> **Status:** iOS fully wired and CI-green. Android migration pending (Jitsi → LiveKit).

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [What Was Built](#2-what-was-built)
3. [VPS Project Directory](#3-vps-project-directory)
4. [Connection Details](#4-connection-details)
5. [How a Call Works (End to End)](#5-how-a-call-works-end-to-end)
6. [Server-Side Components](#6-server-side-components)
7. [iOS Integration](#7-ios-integration)
8. [Android Integration (Migration Guide)](#8-android-integration-migration-guide)
9. [Room Naming Convention](#9-room-naming-convention)
10. [Security Model](#10-security-model)
11. [Operations](#11-operations)
12. [Troubleshooting](#12-troubleshooting)
13. [Rollback](#13-rollback)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        213.199.61.156 (medigyaan.com)                   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  nginx (port 443, TLS 1.2/1.3)                                │   │
│   │                                                                 │   │
│   │   /Neurons/*  ──► PHP-FPM (medigyaan PHP backend)              │   │
│   │   /rtc        ──► LiveKit 127.0.0.1:7880  (WebSocket upgrade)  │   │
│   │   /twirp/*    ──► LiveKit 127.0.0.1:7880  (room management)    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  LiveKit SFU (Docker, host networking)                         │   │
│   │                                                                 │   │
│   │   7880/tcp    Signalling (loopback only, nginx proxies here)   │   │
│   │   7881/tcp    ICE/TCP fallback                                  │   │
│   │   7882-7892/udp  ICE/UDP (media — the actual call traffic)     │   │
│   │   3478/udp    TURN + STUN (embedded)                            │   │
│   │   5349/tcp    TURN/TLS (embedded, uses LE cert)                 │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  /etc/medigyaan/livekit.php     API secret (outside webroot)   │   │
│   │  /var/www/medigyaan/Neurons/    PHP webroot                    │   │
│   │    └── livekit_token.php        Token minting endpoint         │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  OpenVPN server   1194/udp  (was 443/tcp, moved to free port)  │   │
│   │  Let's Encrypt    auto-renewing cert for medigyaan.com          │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **LiveKit's built-in TURN server** replaces a standalone Coturn deployment. No extra ports needed.
- **Single-port UDP mux** (7882–7892) instead of the 10,000-port range the original guide suggested. Smaller attack surface, easier firewall management.
- **No media transits nginx.** Only signalling (WebSocket) goes through 443; media goes directly between clients and LiveKit on 7881/7882.
- **The API secret never ships inside any app binary.** The token endpoint on the VPS mints short-lived JWTs server-side.

---

## 2. What Was Built

| Component | What it does | Where it lives |
|---|---|---|
| **LiveKit SFU** | Receives one stream per participant and forwards to others (no transcoding) | Docker container `livekit` on the VPS |
| **nginx TLS vhost** | Terminates HTTPS, reverse-proxies `wss://medigyaan.com/rtc` to LiveKit | `/etc/nginx/sites-available/medigyaan-ssl.conf` |
| **Token endpoint** | Mints room-scoped JWTs using the API secret | `/var/www/medigyaan/Neurons/livekit_token.php` |
| **API secret** | Signs JWTs; never leaves the server | `/etc/medigyaan/livekit.php` |
| **iOS calling UI** | Full-screen call view, camera/mic controls, room derivation | `ios-projects/MediGyaan/MediGyaan/Features/Call/` |
| **OpenVPN migration** | Moved from 443/tcp to 1194/udp to free port 443 for TLS | `/etc/openvpn/server.conf` |
| **Let's Encrypt cert** | TLS for medigyaan.com + TURN/TLS | `/etc/letsencrypt/live/medigyaan.com/` |

**Android status:** The Android app currently calls Jitsi Meet (`meet.jit.si`). The room naming convention (`edu_lab_rtm_<low>_<high>`) is already identical on both platforms, so once Android is pointed at this SFU, cross-platform calling will work out of the box. See [Section 8](#8-android-integration-migration-guide).

---

## 3. VPS Project Directory

All server-side files live under `/root/livekit/`:

```
/root/livekit/
├── README.md                    # Detailed runbook (technical reference)
├── MANUAL.md                    # This document
├── livekit.yaml                 # LiveKit SFU configuration
├── docker-compose.yml           # Docker Compose service definition
├── nginx-medigyaan-ssl.conf     # nginx TLS vhost (source copy)
├── mint-token.py                # CLI helper to mint tokens manually
├── livekit-firewall.service     # systemd unit: blocks port 7880 from the internet
├── restart-livekit-on-renew.sh  # certbot deploy hook: restarts LiveKit on cert renewal
└── php/
    ├── livekit_token.php        # Token minting endpoint (deployed to webroot)
    └── livekit.php              # API secret config (deployed outside webroot)
```

**Deployed locations:**

| File | Deployed to | Permissions | Purpose |
|---|---|---|---|
| `livekit.yaml` | `/root/livekit/livekit.yaml` (bind-mounted into Docker) | `root:root 0644` | LiveKit config |
| `livekit_token.php` | `/var/www/medigyaan/Neurons/livekit_token.php` | `www-data:www-data 0644` | Token endpoint |
| `livekit.php` | `/etc/medigyaan/livekit.php` | `root:www-data 0640` | API secret (outside webroot) |
| `livekit-firewall.service` | `/etc/systemd/system/livekit-firewall.service` | — | Blocks 7880 from internet |
| `restart-livekit-on-renew.sh` | `/etc/letsencrypt/renewal-hooks/deploy/restart-livekit-on-renew.sh` | `root:root 0755` | Restart LiveKit on cert renewal |
| `nginx-medigyaan-ssl.conf` | `/etc/nginx/sites-available/medigyaan-ssl.conf` | — | nginx vhost |

**Backup:** The original state before any changes was saved to `/root/medigyaan-livekit-backup-20260911-193618/`.

---

## 4. Connection Details

### 4.1 Network

| Detail | Value |
|---|---|
| **VPS hostname** | `medicscholar.medigyaan.com` |
| **Public IPv4** | `213.199.61.156` |
| **Public IPv6** | `2a02:c207:2340:1853::1` |
| **Domain** | `medigyaan.com` (A + AAAA records point here) |
| **OS** | Ubuntu 24.04.4 LTS, kernel 6.8.0-136-generic |
| **CPU** | 4 vCPU AMD EPYC, 2.0 GHz |
| **RAM** | 7.83 GiB total |

### 4.2 Ports

| Port | Protocol | Service | Public access |
|---|---|---|---|
| 80 | TCP | nginx (plain HTTP, certbot ACME) | ✅ Yes |
| 443 | TCP | nginx (HTTPS + wss://) | ✅ Yes |
| 1194 | UDP | OpenVPN | ✅ Yes |
| 3478 | UDP | LiveKit TURN/STUN | ✅ Yes |
| 5349 | TCP | LiveKit TURN/TLS | ✅ Yes |
| 7880 | TCP | LiveKit signalling | ❌ **Blocked** (iptables DROP) |
| 7881 | TCP | LiveKit ICE/TCP | ✅ Yes |
| 7882–7892 | UDP | LiveKit media (ICE/UDP mux) | ✅ Yes |

### 4.3 Credentials

| Credential | Value | Location |
|---|---|---|
| **LiveKit API key** | `APIVgBVwvMgYmaq` | `/etc/medigyaan/livekit.php` + `/root/livekit/livekit.yaml` |
| **LiveKit API secret** | `BDAsayrFe4i6R6DmzJJxNR2eopEGfYeImDpw5UKm8ZEA` | `/etc/medigyaan/livekit.php` + `/root/livekit/livekit.yaml` |
| **WebSocket URL** | `wss://medigyaan.com/rtc` | Hardcoded in API config |
| **Token endpoint** | `https://medigyaan.com/Neurons/livekit_token.php` | Hardcoded in API config |
| **TLS cert expiry** | 2026-12-10 | Auto-renewing via certbot |

⚠️ **Rotate the API key/secret together.** Update both `livekit.yaml` and `/etc/medigyaan/livekit.php`, then `docker compose up -d --force-recreate` in `/root/livekit/`.

### 4.4 Client Configuration

| Platform | WebSocket URL | Token endpoint | SDK |
|---|---|---|---|
| **iOS** | `wss://medigyaan.com/rtc` | `https://medigyaan.com/Neurons/livekit_token.php` | `livekit/client-sdk-swift` 2.16.0 (SPM) |
| **Android** | `wss://medigyaan.com/rtc` | `https://medigyaan.com/Neurons/livekit_token.php` | `io.livekit:livekit-android` (see Section 8) |

---

## 5. How a Call Works (End to End)

### 5.1 Sequence diagram

```
  iOS / Android                        VPS (medigyaan.com)               LiveKit SFU
  ────────────                         ────────────────────               ────────────
       │                                     │                                │
  1.   │── POST /Neurons/livekit_token.php ──►│                                │
       │   {room, user_id, display_name}     │                                │
       │                                     │── verify user_id exists ────    │
       │                                     │── verify user_id ∈ room ────    │
       │                                     │── mint JWT (HS256) ─────────    │
       │◄── {token, url, room, expires_at} ──│                                │
       │                                     │                                │
  2.   │── wss://medigyaan.com/rtc ──────────►│                                │
       │   (Upgrade: websocket)              │── proxy_pass 127.0.0.1:7880 ──►│
       │                                     │                                │
  3.   │◄── 101 Switching Protocols ─────────│────────────────────────────────│
       │                                     │                                │
  4.   │── {token} ─────────────────────────►│───────────────────────────────►│
       │                                     │                                │── verify JWT
       │                                     │                                │── join room
       │◄── {room_info, participants} ───────│────────────────────────────────│
       │                                     │                                │
  5.   │◄──────────── RTP media (UDP 7882) ──────────────────────────────────►│
       │── RTP media (UDP 7882) ─────────────────────────────────────────────►│
       │                                     │                                │
```

### 5.2 What the token endpoint validates

1. **Room format:** Must be `edu_lab_rtm_<low>_<high>` (1-on-1) or `EDULABS_<epoch-ms>` (ad-hoc). Anything else → 403.
2. **Room entitlement:** For `edu_lab_rtm_<low>_<high>`, the `user_id` must be one of `low` or `high`. This prevents someone from joining a call they're not a party to.
3. **Low < high:** Both sides must derive the same room name. The endpoint enforces `low < high` to prevent duplicate rooms.
4. **Rate limit:** 60 requests per 10 minutes per IP.

### 5.3 What the JWT grants

```json
{
  "iss": "APIVgBVwvMgYmaq",
  "sub": "u42",
  "name": "Shashi Gupta",
  "nbf": 1789149826,
  "exp": 1789171426,
  "video": {
    "room": "edu_lab_rtm_42_57",
    "roomJoin": true,
    "canPublish": true,
    "canSubscribe": true,
    "canPublishData": true
  }
}
```

The `sub` (identity) is `u<userId>` — prefixed with `u` to be distinguishable from any room-scoped identifier LiveKit invents.

---

## 6. Server-Side Components

### 6.1 LiveKit SFU

**Config:** `/root/livekit/livekit.yaml`
**Compose:** `/root/livekit/docker-compose.yml`

```bash
# View status
docker compose -f /root/livekit/docker-compose.yml ps

# View logs
docker logs livekit --tail 50

# Restart after config change
docker compose -f /root/livekit/docker-compose.yml up -d --force-recreate

# Health check
curl -sS https://medigyaan.com/rtc/validate?access_token=<any-valid-token>
# Should return: 200 {"success"}
```

**Key config choices:**
- `rtc.udp_port: 7882-7892` — single-port mux (not the 50000–60000 range)
- `rtc.interfaces.includes: [eth0]` — filters out Tailscale/Docker/VPN ICE candidates
- `rtc.use_external_ip: true` — STUN resolves to 213.199.61.156
- `room.auto_create: true` — rooms are created on first join (no admin step)
- `room.empty_timeout: 300` — room closes 5 min after last participant leaves

### 6.2 Token Endpoint

**Source:** `/root/livekit/php/livekit_token.php`
**Deployed:** `/var/www/medigyaan/Neurons/livekit_token.php`

```bash
# Test from any machine
curl -sS -X POST https://medigyaan.com/Neurons/livekit_token.php \
  -d "room=edu_lab_rtm_1_2&user_id=1&display_name=Test"

# Expected: {"success":true,"token":"eyJ...","url":"wss://medigyaan.com/rtc",...}
```

**To update the endpoint:**

```bash
# Edit the source
vim /root/livekit/php/livekit_token.php

# Deploy
cp /root/livekit/php/livekit_token.php /var/www/medigyaan/Neurons/livekit_token.php
chown www-data:www-data /var/www/medigyaan/Neurons/livekit_token.php
```

### 6.3 API Secret Config

**File:** `/etc/medigyaan/livekit.php`

```php
<?php
return [
    'api_key'    => 'APIVgBVwvMgYmaq',
    'api_secret' => 'BDAsayrFe4i6R6DmzJJxNR2eopEGfYeImDpw5UKm8ZEA',
    'ws_url'     => 'wss://medigyaan.com/rtc',
];
```

Permissions: `root:www-data 0640` (readable by PHP-FPM, not by the world).

### 6.4 nginx TLS vhost

**Source:** `/root/livekit/nginx-medigyaan-ssl.conf`
**Installed:** `/etc/nginx/sites-available/medigyaan-ssl.conf`

```bash
# Test config
nginx -t

# Reload after change
systemctl reload nginx
```

**Key locations:**
- `location ^~ /rtc` — WebSocket proxy to LiveKit (with upgrade headers, 24h timeout)
- `location ^~ /twirp/` — Server-side API proxy to LiveKit
- `location /` — PHP backend
- `location ~ \.php$` — PHP-FPM passthrough

### 6.5 Firewall Rules

| Rule | Protocol | Port | Purpose | Persistence |
|---|---|---|---|---|
| iptables DROP | TCP | 7880 | Block public access to LiveKit API | `/etc/systemd/system/livekit-firewall.service` |
| iptables ACCEPT | TCP | 443 | HTTPS | Manual (ufw inactive) |
| iptables ACCEPT | UDP | 1194 | OpenVPN | Manual (ufw inactive) |
| Tailscale | — | — | ts-input chain | Tailscale manages |

⚠️ **ufw is inactive.** The only host-level firewall rules are the iptables DROP on 7880 and the Tailscale chain. Enabling ufw is recommended but involves lockout risk and is left as a manual step.

### 6.6 Certbot / TLS

```bash
# Check cert validity
openssl x509 -in /etc/letsencrypt/live/medigyaan.com/fullchain.pem -noout -dates

# Force renewal
snap.certbot renew --force-renewal

# Dry run
snap.certbot renew --dry-run

# Renewal hooks
ls /etc/letsencrypt/renewal-hooks/deploy/
# → restart-livekit-on-renew.sh (restarts LiveKit container)
```

The cert covers `medigyaan.com` and `www.medigyaan.com`. It expires 2026-12-10 and renews automatically via `snap.certbot.renew.timer`.

---

## 7. iOS Integration

### 7.1 Files added

| File | Purpose |
|---|---|
| `Core/API/LiveKitAPI.swift` | HTTP client for the token endpoint |
| `Core/Networking/APIConfig.swift` | `LiveKit.webSocketURL` and `LiveKit.tokenURL` constants |
| `Core/Networking/HTTPClient.swift` | `postObject(form:toAbsolute:)` for cross-host requests |
| `Models/Call.swift` | `CallToken`, `CallRoom`, `CallKind` models |
| `Features/Call/CallViewModel.swift` | Room lifecycle: connect, mute, camera flip, leave |
| `Features/Call/CallView.swift` | Full-screen call UI |
| `Features/Social/MessengerView.swift` | Toolbar phone/video buttons, `fullScreenCover` for call |
| `Core/Auth/KeychainStore.swift` | Abstracted Keychain for secrets (including auth token) |
| `Resources/Info.plist` | `audio` background mode added |

### 7.2 Dependency

In `project.yml`:

```yaml
packages:
  LiveKit:
    url: https://github.com/livekit/client-sdk-swift
    exactVersion: 2.16.0
```

Module name: `LiveKit` (not `LiveKitClient` as in older versions).

### 7.3 CI status

- **Branch:** `ios-swiftui` on `shashiguptaazm-droid/The-Tank-Project`
- **Latest green commit:** `ebfdd4c`
- **Workflow:** `.github/workflows/ios.yml` (macOS-15, Xcode 16.4, iPhone 16 simulator)

### 7.4 How the iOS app uses calls

1. User opens a conversation in the messenger.
2. Toolbar shows **phone** and **video** icons (disabled if no peer).
3. Tapping either calls `PendingCall.oneToOne(myId, peerId, peerName, kind)`.
4. `fullScreenCover` opens `CallView`, which creates `CallViewModel`.
5. `CallViewModel.start()` fetches a token from `livekit_token.php`, then calls `room.connect(url:token:)`.
6. After connecting, it publishes mic (always) and camera (video calls only).
7. When the other user joins, their `RemoteParticipant` appears via `@ObservedObject var room: Room`.
8. Leaving calls `room.disconnect()` and dismisses the sheet.

---

## 8. Android Integration (Migration Guide)

### 8.1 Current state

The Android app uses **Jitsi Meet SDK 10.3.0** (`org.jitsi.react:jitsi-meet-sdk`), which:
- Opens `JitsiMeetActivity` pointing at `meet.jit.si`
- Has a no-op `VideoCallActivity` that opens a browser to `meet.jit.si/$room`
- Sends `VIDEO_CALL_INVITE:$roomName` as a chat message

The room naming convention is **already identical** to iOS:
```kotlin
private fun getRoomName(u1: Int, u2: Int): String {
    return if (u1 < u2) "edu_lab_rtm_${u1}_${u2}" else "edu_lab_rtm_${u2}_${u1}"
}
```

### 8.2 What needs to change

#### Step 1: Replace Jitsi SDK with LiveKit SDK

In `app/build.gradle.kts`, remove:
```kotlin
implementation("org.jitsi.react:jitsi-meet-sdk:10.3.0")
```

Add:
```kotlin
// LiveKit Android SDK
implementation("io.livekit:livekit-android:2.16.0")
```

> ⚠️ Check https://github.com/livekit/livekit-android/releases for the latest version that matches iOS's 2.16.0.

#### Step 2: Add camera/microphone permissions

In `AndroidManifest.xml`, add if not already present:
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

#### Step 3: Create `LiveKitCallActivity.kt`

```kotlin
package com.rankwarz.edulabsrtm

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import io.livekit.android.LiveKit
import io.livekit.android.RoomOptions
import io.livekit.android.room.Room
import io.livekit.android.room.participant.Participant
import io.livekit.android.room.participant.RemoteParticipant
import io.livekit.android.room.track.*
import io.livekit.android.renderer.video.VideoView
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException

class LiveKitCallActivity : AppCompatActivity() {

    companion object {
        private const val PREF_NAME = "MY_APP"
        private const val TOKEN_URL = "https://medigyaan.com/Neurons/livekit_token.php"
        private const val WS_URL = "wss://medigyaan.com/rtc"
        private const val PERMISSION_REQUEST_CODE = 1001

        fun start(context: Context, roomName: String, peerName: String, isVideo: Boolean) {
            val intent = Intent(context, LiveKitCallActivity::class.java).apply {
                putExtra("room_name", roomName)
                putExtra("peer_name", peerName)
                putExtra("is_video", isVideo)
            }
            context.startActivity(intent)
        }
    }

    private var room: Room? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val roomName = intent.getStringExtra("room_name") ?: run {
            finish(); return
        }
        val peerName = intent.getStringExtra("peer_name") ?: "User"
        val isVideo = intent.getBooleanExtra("is_video", true)

        // Simple call layout — replace with your own XML/design
        setContentView(R.layout.activity_livekit_call)

        findViewById<TextView>(R.id.peerNameText)?.text = peerName

        findViewById<ImageButton>(R.id.muteButton)?.setOnClickListener {
            scope.launch {
                room?.localParticipant?.setMicrophone(
                    enabled = !(room?.localParticipant?.isMicrophoneEnabled() ?: true)
                )
            }
        }

        findViewById<ImageButton>(R.id.cameraButton)?.setOnClickListener {
            scope.launch {
                room?.localParticipant?.setCamera(
                    enabled = !(room?.localParticipant?.isCameraEnabled() ?: true)
                )
            }
        }

        findViewById<ImageButton>(R.id.endCallButton)?.setOnClickListener {
            scope.launch { disconnect() }
        }

        // Check permissions and connect
        if (hasPermissions()) {
            scope.launch { connect(roomName, isVideo) }
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO),
                PERMISSION_REQUEST_CODE
            )
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE &&
            grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
            val roomName = intent.getStringExtra("room_name") ?: return
            val isVideo = intent.getBooleanExtra("is_video", true)
            scope.launch { connect(roomName, isVideo) }
        } else {
            Toast.makeText(this, "Permissions required for calls", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    private suspend fun connect(roomName: String, isVideo: Boolean) {
        val prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", 0)
        val userName = prefs.getString("user_name", "User $userId") ?: "User $userId"

        if (userId == 0) {
            Toast.makeText(this, "Please sign in to make calls", Toast.LENGTH_SHORT).show()
            finish(); return
        }

        // Fetch token from server
        val token = fetchToken(roomName, userId, userName) ?: run {
            Toast.makeText(this, "Failed to start call", Toast.LENGTH_SHORT).show()
            finish(); return
        }

        // Connect to LiveKit
        room = LiveKit.connect(
            url = WS_URL,
            token = token,
            options = RoomOptions()
        )

        // Publish local tracks
        room?.localParticipant?.setMicrophone(enabled = true)
        if (isVideo) {
            room?.localParticipant?.setCamera(enabled = true)
        }

        // Observe participants
        room?.listener = object : Room.Listener {
            override fun onParticipantConnected(participant: RemoteParticipant) {
                // A remote participant joined — their video/audio will auto-subscribe
            }
            override fun onParticipantDisconnected(participant: RemoteParticipant) {
                // Check if room is empty, finish if so
            }
            override fun onDisconnected() {
                runOnUiThread { finish() }
            }
        }
    }

    private fun fetchToken(room: String, userId: Int, displayName: String): String? {
        val body = "room=$room&user_id=$userId&display_name=${java.net.URLEncoder.encode(displayName, "UTF-8")}"
        val request = Request.Builder()
            .url(TOKEN_URL)
            .post(body.toRequestBody("application/x-www-form-urlencoded".toMediaType()))
            .build()

        return try {
            val response = OkHttpClient().newCall(request).execute()
            val json = JSONObject(response.body?.string() ?: "")
            json.optString("token").ifEmpty { null }
        } catch (e: Exception) {
            null
        }
    }

    private suspend fun disconnect() {
        room?.disconnect()
        room = null
    }

    override fun onDestroy() {
        scope.launch { disconnect() }
        scope.cancel()
        super.onDestroy()
    }

    private fun hasPermissions(): Boolean {
        return checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED &&
               checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
    }
}
```

#### Step 4: Create `activity_livekit_call.xml`

A minimal call layout. Replace with your own design tokens:

```xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#000000">

    <!-- Remote video fills the screen -->
    <io.livekit.android.renderer.video.VideoView
        android:id="@+id/remoteVideo"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

    <!-- Local preview (picture-in-picture) -->
    <io.livekit.android.renderer.video.VideoView
        android:id="@+id/localVideo"
        android:layout_width="120dp"
        android:layout_height="160dp"
        android:layout_gravity="bottom|end"
        android:layout_margin="16dp" />

    <!-- Header: peer name -->
    <TextView
        android:id="@+id/peerNameText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_gravity="top|center_horizontal"
        android:layout_marginTop="40dp"
        android:textColor="#FFFFFF"
        android:textSize="18sp"
        android:padding="8dp"
        android:background="#44000000" />

    <!-- Controls -->
    <LinearLayout
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_gravity="bottom|center_horizontal"
        android:layout_marginBottom="40dp"
        android:orientation="horizontal"
        android:gravity="center">

        <ImageButton android:id="@+id/muteButton"
            android:layout_width="60dp" android:layout_height="60dp"
            android:layout_margin="12dp"
            android:background="@drawable/bg_circle_gray"
            android:src="@android:drawable/ic_btn_speak_now"
            android:contentDescription="Mute" />

        <ImageButton android:id="@+id/cameraButton"
            android:layout_width="60dp" android:layout_height="60dp"
            android:layout_margin="12dp"
            android:background="@drawable/bg_circle_gray"
            android:src="@android:drawable/ic_menu_camera"
            android:contentDescription="Camera" />

        <ImageButton android:id="@+id/endCallButton"
            android:layout_width="60dp" android:layout_height="60dp"
            android:layout_margin="12dp"
            android:background="@drawable/bg_circle_red"
            android:src="@android:drawable/ic_menu_call"
            android:contentDescription="End call" />
    </LinearLayout>
</FrameLayout>
```

#### Step 5: Register the activity in `AndroidManifest.xml`

```xml
<activity android:name=".LiveKitCallActivity" android:exported="false" />
```

#### Step 6: Update `MessengerActivity.kt`

Replace the `launchJitsi` function:

```kotlin
// BEFORE (Jitsi):
private fun launchJitsi(roomName: String) {
    val options = JitsiMeetConferenceOptions.Builder()
        .setServerURL(URL("https://meet.jit.si"))
        .setRoom(roomName)
        .setUserInfo(userInfo)
        .build()
    JitsiMeetActivity.launch(this, options)
}

// AFTER (LiveKit):
private fun launchLiveKit(roomName: String, isVideo: Boolean = true) {
    val prefs = getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    val userName = prefs.getString("user_name", "User $userId") ?: "User $userId"
    LiveKitCallActivity.start(this, roomName, peerName, isVideo)
}
```

Replace all calls to `launchJitsi(roomName)` with `launchLiveKit(roomName)`.

#### Step 7: Update `VideoCallActivity.kt`

```kotlin
// BEFORE (browser redirect):
class VideoCallActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val room = "EDULABS_" + System.currentTimeMillis()
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://meet.jit.si/$room")))
        finish()
    }
}

// AFTER (LiveKit):
class VideoCallActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("MY_APP", Context.MODE_PRIVATE)
        val userId = prefs.getInt("user_id", 0)
        val userName = prefs.getString("user_name", "User $userId") ?: "User $userId"
        val room = "EDULABS_${System.currentTimeMillis()}"
        LiveKitCallActivity.start(this, room, userName, isVideo = true)
        finish()
    }
}
```

#### Step 8: Remove Jitsi imports

In `MessengerActivity.kt`, remove these imports:
```kotlin
import org.jitsi.meet.sdk.JitsiMeetUserInfo
import org.jitsi.meet.sdk.JitsiMeetActivity
import org.jitsi.meet.sdk.JitsiMeetConferenceOptions
```

---

## 9. Room Naming Convention

Both platforms **must** derive identical room names. The convention:

| Call type | Room name format | Example |
|---|---|---|
| **1-on-1** | `edu_lab_rtm_<min(userId1,userId2)>_<max(userId1,userId2)>` | `edu_lab_rtm_42_57` |
| **Ad-hoc** | `EDULABS_<epoch_ms>` | `EDULABS_1768000000000` |

**Critical rules:**
- The two user IDs must be in ascending order (`low < high`).
- Both callers must use `min/max` to ensure they derive the same name regardless of who initiates.
- The token endpoint **enforces** `low < high` and rejects `low == high` (you can't call yourself).

**Cross-platform compatibility:** The iOS code is `CallRoom.oneToOne(myId, peerId)` which builds `edu_lab_rtm_<min>_<max>`. The Android code is `getRoomName(u1, u2)` which builds the same string. They are byte-identical.

---

## 10. Security Model

### 10.1 What's protected

| Threat | Mitigation |
|---|---|
| **Eavesdropping on arbitrary rooms** | Room entitlement check: token endpoint only mints for rooms the caller is a party to |
| **API secret in binary** | Secret stays on VPS in `/etc/medigyaan/livekit.php`; app only holds short-lived JWTs |
| **Replay attacks** | JWTs expire in 6 hours (`exp` claim) |
| **Denial of service** | Rate limit: 60 requests / 10 min / IP |
| **Port 7880 exposure** | iptables DROP rule blocks public access; only nginx (loopback) can reach it |

### 10.2 Known limitations

| Limitation | Impact | Mitigation path |
|---|---|---|
| **user_id is guessable** | An attacker who knows two user IDs could mint a token for their room | Add a per-user session token from the backend; validate it server-side |
| **No TURN credentials on iOS** | LiveKit generates ephemeral TURN credentials via the JWT's `video` grant | Not a gap — this is how LiveKit's built-in TURN works |
| **ufw is inactive** | No host firewall except the iptables rule on 7880 | Enable ufw with explicit allow rules; be careful not to lock out SSH |
| **Android still uses Jitsi** | Calls don't work cross-platform until Android migrates | See Section 8 |

---

## 11. Operations

### 11.1 Daily operations

```bash
# Check LiveKit is running
docker ps --filter name=livekit

# Check cert validity
openssl x509 -in /etc/letsencrypt/live/medigyaan.com/fullchain.pem -noout -dates

# Test token endpoint
curl -sS -X POST https://medigyaan.com/Neurons/livekit_token.php \
  -d "room=edu_lab_rtm_1_2&user_id=1&display_name=Test" | python3 -m json.tool

# View LiveKit logs
docker logs livekit --tail 50
```

### 11.2 Restarting LiveKit

```bash
cd /root/livekit
docker compose up -d --force-recreate
```

### 11.3 Rotating API keys

1. Generate new keys:
   ```bash
   docker run --rm --entrypoint /livekit-server livekit/livekit-server generate-keys
   ```
2. Update `/root/livekit/livekit.yaml` (the `keys:` section)
3. Update `/etc/medigyaan/livekit.php` (both `api_key` and `api_secret`)
4. Restart: `docker compose up -d --force-recreate`
5. All previously issued tokens are now invalid (they signed with the old secret)

### 11.4 Updating the token endpoint

```bash
# Edit
vim /root/livekit/php/livekit_token.php

# Deploy
cp /root/livekit/php/livekit_token.php /var/www/medigyaan/Neurons/livekit_token.php
chown www-data:www-data /var/www/medigyaan/Neurons/livekit_token.php
# No restart needed — PHP reads the file on each request
```

### 11.5 Updating the TLS cert

```bash
# Force renewal (certbot auto-renews, but manual is fine)
snap.certbot renew --force-renewal

# The deploy hook restarts LiveKit automatically
# Verify:
docker logs livekit --tail 5
```

### 11.6 Updating nginx

```bash
# Edit
vim /root/livekit/nginx-medigyaan-ssl.conf

# Test
nginx -t

# Deploy and reload
cp /root/livekit/nginx-medigyaan-ssl.conf /etc/nginx/sites-available/medigyaan-ssl.conf
systemctl reload nginx
```

---

## 12. Troubleshooting

### 12.1 "Call failed: Could not start the call"

**Check:** Is the token endpoint reachable?
```bash
curl -sS -X POST https://medigyaan.com/Neurons/livekit_token.php \
  -d "room=edu_lab_rtm_1_2&user_id=1"
```

If 500: check `/var/log/php8.3-fpm.log` and ensure `/etc/medigyaan/livekit.php` is readable by `www-data`.

### 12.2 "Call failed: connection timed out"

**Check:** Is port 443 reachable from the client's network?
```bash
# From the VPS:
curl -sS -o /dev/null -w "%{http_code}" https://medigyaan.com/Neurons/livekit_token.php
```

**Check:** Is nginx running?
```bash
systemctl status nginx
```

### 12.3 "Call connected but no video/audio"

**Check:** Is port 7882/udp open on the VPS?
```bash
# From an external host:
ss -lnup | grep 7882
```

**Check:** Is iptables blocking?
```bash
iptables -L INPUT -n | grep 7882
# Should NOT have a DROP/REJECT rule
```

### 12.4 "Call fails on cellular/WiFi behind strict firewall"

LiveKit's built-in TURN server handles NAT traversal. If both UDP and TCP fail:
1. Check port 3478/udp is reachable (STUN)
2. Check port 5349/tcp is reachable (TURN/TLS)
3. The client SDK should automatically fall back to TURN relay

### 12.5 "Token endpoint returns 403 for valid room"

This means `user_id` is not one of the two participants in the room name. Verify the room name derivation matches both platforms.

### 12.6 LiveKit container keeps restarting

```bash
docker logs livekit --tail 30
```

Common causes:
- `livekit.yaml` syntax error
- Cert files missing or unreadable
- Port conflict (something else on 7880/7881/7882)

---

## 13. Rollback

If something goes wrong, the backup is at:
```
/root/medigyaan-livekit-backup-20260911-193618/
```

### 13.1 Restore OpenVPN to 443/tcp

```bash
# Restore original server.conf
cp /root/medigyaan-livekit-backup-20260911-193618/openvpn-server.conf /etc/openvpn/server.conf

# Restart
systemctl restart openvpn-server@server

# Re-issue client configs with remote 213.199.61.156 443 tcp
```

### 13.2 Remove LiveKit

```bash
cd /root/livekit
docker compose down

# Remove the SSL vhost
rm /etc/nginx/sites-enabled/medigyaan-ssl.conf
systemctl reload nginx

# Remove the token endpoint
rm /var/www/medigyaan/Neurons/livekit_token.php

# Remove the config
rm -rf /etc/medigyaan

# Remove the iptables rule
iptables -D INPUT -p tcp --dport 7880 -j DROP
```

### 13.3 Restore the iptables rule (if removed by mistake)

```bash
iptables -I INPUT 1 -p tcp --dport 7880 -j DROP
# Persist:
apt-get install -y iptables-persistent
netfilter-persistent save
```

---

*This manual covers the complete state of MediGyaan's video/audio calling infrastructure as of 11 September 2026. The server-side is production-ready and verified. iOS is wired and CI-green. Android migration (Section 8) is the remaining work.*
