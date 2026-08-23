#!/usr/bin/env python3
"""UNO Q — Lightweight 3rd Perception Relay.

Runs on the UNO Q board (Qualcomm QRB2210, ARM64).
Captures frames from the ESP32-S3 CAM via USB-C serial,
sends raw JPEG to the Jetson over Tailscale for YOLO detection.

NO OpenCV, NO ultralytics, NO torch — pure Python stdlib.

Architecture:
  ESP32-S3 CAM (USB-C serial) → UNO Q relay → Jetson YOLO via Tailscale

Usage:
  python3 unoq_perception_relay.py
"""
import json
import os
import socket
import struct
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────
ESP32_SERIAL_PORT = "/dev/ttyACM0"
ESP32_BAUD = 115200
JETSON_URL = "http://100.122.31.46:8085"
VPS_URL = "http://100.71.127.19:8888"
RELAY_INTERVAL_S = 3  # seconds between frame captures
TIMEOUT_S = 10

# ESP32-S3 CAM endpoints (if on WiFi)
ESP32_WIFI_HOST = "192.168.31.145"
ESP32_CAPTURE_URL = f"http://{ESP32_WIFI_HOST}/capture"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def capture_from_wifi():
    """Try to grab a JPEG frame from ESP32-S3 CAM over WiFi."""
    try:
        req = urllib.request.urlopen(ESP32_CAPTURE_URL, timeout=TIMEOUT_S)
        jpeg = req.read()
        ct = req.headers.get("Content-Type", "")
        if jpeg and ("image" in ct or len(jpeg) > 1000):
            return jpeg
    except Exception:
        pass
    return None


def capture_from_serial():
    """Try to grab a JPEG frame from ESP32-S3 CAM via USB serial."""
    try:
        import serial as pyserial
        s = pyserial.Serial(ESP32_SERIAL_PORT, ESP32_BAUD, timeout=5)
        time.sleep(0.3)
        s.read(s.in_waiting)
        s.write(b"SNAP\n")

        header = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            c = s.read(1)
            if c:
                header += c
                if c == b"\n":
                    break

        h = header.decode("utf-8", errors="replace").strip()
        if not h.startswith("FRAME:"):
            s.close()
            return None

        parts = h.split(":")
        expected = int(parts[3])
        jpeg = b""
        dl = time.time() + 10
        while len(jpeg) < expected and time.time() < dl:
            chunk = s.read(min(expected - len(jpeg), 16384))
            if chunk:
                jpeg += chunk
                dl = time.time() + 2
        s.read(1)
        s.close()

        if len(jpeg) > 100:
            return jpeg
    except ImportError:
        pass
    except Exception as e:
        log(f"Serial capture error: {e}")
    return None


def send_to_jetson(jpeg_bytes):
    """POST the JPEG frame to the Jetson for YOLO detection."""
    targets = [JETSON_URL, VPS_URL]

    payload = {
        "source": "unoq_esp32cam",
        "node": "unoq",
        "tailscale_ip": "100.84.235.7",
        "timestamp": time.time(),
        "frame_size": len(jpeg_bytes),
    }

    for target in targets:
        try:
            url = f"{target}/api/perception/frame"

            # Build multipart form data
            boundary = "----TankBoundary"
            body = b""
            # JSON part
            body += f"--{boundary}\r\n".encode()
            body += b'Content-Disposition: form-data; name="meta"\r\n'
            body += b"Content-Type: application/json\r\n\r\n"
            body += json.dumps(payload).encode() + b"\r\n"
            # JPEG part
            body += f"--{boundary}\r\n".encode()
            body += b'Content-Disposition: form-data; name="frame"; filename="frame.jpg"\r\n'
            body += b"Content-Type: image/jpeg\r\n\r\n"
            body += jpeg_bytes + b"\r\n"
            body += f"--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read().decode())
            return True, result

        except Exception as e:
            log(f"Report to {target} failed: {e}")
            continue

    return False, {}


def send_to_jetson_simple(jpeg_bytes):
    """Fallback: POST raw JPEG to Jetson (simpler endpoint)."""
    targets = [JETSON_URL, VPS_URL]

    for target in targets:
        try:
            url = f"{target}/api/detections"
            payload = json.dumps({
                "source": "unoq_esp32cam",
                "node": "unoq",
                "tailscale_ip": "100.84.235.7",
                "timestamp": time.time(),
                "frame_size": len(jpeg_bytes),
                "frame_b64": __import__("base64").b64encode(jpeg_bytes).decode()[:1000],
            }).encode()

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            continue
    return False


def main():
    log("🔭 UNO Q 3rd Perception Relay starting...")
    log(f"   ESP32-S3 CAM serial: {ESP32_SERIAL_PORT}")
    log(f"   ESP32-S3 CAM WiFi: {ESP32_WIFI_HOST}")
    log(f"   Jetson target: {JETSON_URL}")
    log(f"   VPS fallback: {VPS_URL}")
    log(f"   Interval: {RELAY_INTERVAL_S}s")

    frame_count = 0
    success_count = 0
    fail_count = 0

    while True:
        try:
            t0 = time.time()

            # Try WiFi first (faster), then serial
            jpeg = capture_from_wifi()
            source = "wifi"
            if jpeg is None:
                jpeg = capture_from_serial()
                source = "serial"

            if jpeg:
                frame_count += 1
                ok, result = send_to_jetson(jpeg)
                if ok:
                    success_count += 1
                    det_count = result.get("detection_count", "?")
                    log(f"✅ Frame #{frame_count} ({source}, {len(jpeg)}B) → {det_count} detections")
                else:
                    fail_count += 1
                    log(f"⚠️ Frame #{frame_count} captured but report failed")
            else:
                fail_count += 1
                if fail_count % 5 == 0:
                    log(f"❌ No frame for {fail_count} attempts — check ESP32-S3 CAM")

            # Stats every 10 frames
            if frame_count % 10 == 0 and frame_count > 0:
                log(f"📊 Stats: {frame_count} frames, {success_count} sent, {fail_count} failed")

            elapsed = time.time() - t0
            sleep_time = max(0.1, RELAY_INTERVAL_S - elapsed)
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            log("🛑 Stopped by user")
            break
        except Exception as e:
            log(f"❌ Relay error: {e}")
            time.sleep(5)

    log(f"📊 Final: {frame_count} frames, {success_count} sent, {fail_count} failed")


if __name__ == "__main__":
    main()
