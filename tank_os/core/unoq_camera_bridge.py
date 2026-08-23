#!/usr/bin/env python3
"""ESP32 CAM Network Bridge — serves camera frames over HTTP for remote AI nodes.

Runs on UNO Q (100.84.235.7). Jetson and other nodes pull frames via HTTP.
Endpoints:
  GET /snapshot.jpg  — latest JPEG frame (single shot)
  GET /stream        — MJPEG stream (for cv2.VideoCapture)
  GET /status        — JSON: {connected, resolution, fps}
"""

import http.server
import json
import logging
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

from tank_os.core.unoq_camera import ESP32CameraDriver

PORT = 8080
STREAM_FPS = 8
MAX_CLIENTS = 5

logger = logging.getLogger("tank.unoq.cam_bridge")

_last_jpeg: bytes = b""
_last_jpeg_time: float = 0
_lock = threading.Lock()
_stream_clients: list = []
_camera: Optional[ESP32CameraDriver] = None


def _capture_loop():
    """Background thread: continuously capture frames from ESP32 camera."""
    global _last_jpeg, _last_jpeg_time, _camera
    _camera = ESP32CameraDriver()
    while True:
        try:
            path = _camera.capture()
            if path and path.stat().st_size > 500:
                data = path.read_bytes()
                with _lock:
                    _last_jpeg = data
                    _last_jpeg_time = time.time()
            time.sleep(1.0 / STREAM_FPS)
        except Exception as e:
            logger.debug("Capture error: %s", e)
            time.sleep(1)


class CameraHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # quiet

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/snapshot.jpg":
            self._serve_jpeg()
        elif path == "/stream":
            self._serve_stream()
        elif path == "/status":
            self._serve_status()
        elif path == "/":
            self._serve_html()
        else:
            self.send_error(404)

    def _serve_jpeg(self):
        with _lock:
            jpeg = _last_jpeg
        if not jpeg:
            self.send_error(503, "No frame yet")
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(jpeg)

    def _serve_stream(self):
        """MJPEG stream — cv2.VideoCapture compatible."""
        self.send_response(200)
        self.send_header("Content-Type",
                         "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        client_id = id(self)
        _stream_clients.append(client_id)
        try:
            last_sent = b""
            while client_id in _stream_clients:
                with _lock:
                    jpeg = _last_jpeg
                if jpeg and jpeg != last_sent:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    last_sent = jpeg
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if client_id in _stream_clients:
                _stream_clients.remove(client_id)

    def _serve_status(self):
        with _lock:
            has_frame = len(_last_jpeg) > 0
            last = _last_jpeg_time
        status = {
            "camera_connected": _camera is not None and _camera.connected,
            "has_frame": has_frame,
            "last_frame_ts": last,
            "fps": STREAM_FPS,
            "clients": len(_stream_clients),
        }
        body = json.dumps(status).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html = (
            "<html><head><title>UNO Q Camera</title></head>"
            "<body style='text-align:center;background:#111;color:#fff'>"
            "<h2>ESP32-S3 CAM — OV3660 320x240</h2>"
            "<img src='/stream' style='max-width:100%'/>"
            "<p><a href='/snapshot.jpg'>Snapshot</a> | "
            "<a href='/status'>Status</a></p>"
            "</body></html>"
        )
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    print(f"🚀 UNO Q Camera Bridge → http://0.0.0.0:{PORT}")
    print(f"   Snapshot: http://100.84.235.7:{PORT}/snapshot.jpg")
    print(f"   Stream:   http://100.84.235.7:{PORT}/stream")

    capture_thread = threading.Thread(target=_capture_loop, daemon=True)
    capture_thread.start()

    time.sleep(2)  # wait for first frame

    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), CameraHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()