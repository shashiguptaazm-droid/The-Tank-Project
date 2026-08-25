#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  UNO Q (Skullcandy) Camera Setup Script
# ═══════════════════════════════════════════════════════════════════════════
#
#  This script sets up camera streaming on the UNO Q device.
#  Run this ON the UNO Q device.
#
#  Usage:
#    chmod +x setup_unoq_camera.sh
#    ./setup_unoq_camera.sh
#
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║       UNO Q (Skullcandy) Camera Setup                   ║"
echo "  ║       Setting up Camera 2 streaming                      ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on UNO Q
if ! grep -q "unoq" /etc/hostname 2>/dev/null; then
    echo -e "${YELLOW}Warning: This script should run on UNO Q (Skullcandy)${NC}"
    echo -e "${YELLOW}Current hostname: $(hostname)${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system
echo -e "${BLUE}[1/5] Updating system...${NC}"
sudo apt update -y
sudo apt upgrade -y

# Step 2: Install camera dependencies
echo -e "${BLUE}[2/5] Installing camera dependencies...${NC}"
sudo apt install -y \
    motion \
    ffmpeg \
    python3-opencv \
    python3-pip \
    python3-serial

# Step 3: Configure motion for USB camera
echo -e "${BLUE}[3/5] Configuring motion...${NC}"

# Detect USB camera
CAMERA_DEV=$(ls /dev/video* 2>/dev/null | head -1)
if [ -z "$CAMERA_DEV" ]; then
    echo -e "${YELLOW}No /dev/video* found. Checking other devices...${NC}"
    CAMERA_DEV=$(ls /dev/video* 2>/dev/null | head -1)
fi

if [ -z "$CAMERA_DEV" ]; then
    echo -e "${YELLOW}No camera device found. Creating default config...${NC}"
    CAMERA_DEV="/dev/video0"
fi

echo -e "${GREEN}Using camera: ${CAMERA_DEV}${NC}"

# Create motion config
sudo tee /etc/motion/motion.conf > /dev/null << EOF
# Motion configuration for UNO Q Camera

# Device
videodevice ${CAMERA_DEV}
width 640
height 480
framerate 15

# Output
output_pictures best
target_dir /tmp/motion

# HTTP streaming
stream_port 8081
stream_localhost off
stream_maxrate 15
stream_authentication user:tankos

# Web control
control_port 8082
control_localhost off

# Detection
noise_level 32
minimum_motion_frames 3
EOF

# Create target directory
sudo mkdir -p /tmp/motion
sudo chmod 777 /tmp/motion

# Step 4: Create camera server script
echo -e "${BLUE}[4/5] Creating camera server...${NC}"

tee ~/camera_server.py > /dev/null << 'PYTHON'
#!/usr/bin/env python3
"""Simple camera server for UNO Q."""
import os
import sys
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CAMERA_DEV = "/dev/video0"
PORT = 8083

class CameraHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/snapshot.jpg":
            self.capture_and_send()
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "camera": CAMERA_DEV}).encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>UNO Q Camera Server</h1><p>GET /snapshot.jpg</p>")
        else:
            self.send_error(404)
    
    def capture_and_send(self):
        try:
            import cv2
            cap = cv2.VideoCapture(CAMERA_DEV)
            if not cap.isOpened():
                self.send_error(503, "Camera not available")
                return
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                self.send_error(503, "Failed to capture frame")
                return
            
            # Save as JPEG
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                cv2.imwrite(f.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                jpeg_data = Path(f.name).read_bytes()
                os.unlink(f.name)
            
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", len(jpeg_data))
            self.end_headers()
            self.wfile.write(jpeg_data)
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")

if __name__ == "__main__":
    print(f"Camera server starting on port {PORT}...")
    print(f"Camera: {CAMERA_DEV}")
    server = HTTPServer(("0.0.0.0", PORT), CameraHandler)
    print(f"Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
PYTHON

chmod +x ~/camera_server.py

# Step 5: Create systemd service
echo -e "${BLUE}[5/5] Creating systemd service...${NC}"

sudo tee /etc/systemd/system/camera-server.service > /dev/null << EOF
[Unit]
Description=UNO Q Camera Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/home/$(whoami)
ExecStart=/usr/bin/python3 /home/$(whoami)/camera_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable camera-server
sudo systemctl start camera-server

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Camera Setup Complete!                             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Camera Server:${NC}"
echo -e "  URL: http://$(hostname -I | awk '{print $1}'):8083/snapshot.jpg"
echo -e "  Health: http://$(hostname -I | awk '{print $1}'):8083/health"
echo ""
echo -e "${CYAN}Motion Streaming:${NC}"
echo -e "  Stream: http://$(hostname -I | awk '{print $1}'):8081/"
echo -e "  Control: http://$(hostname -I | awk '{print $1}'):8082/"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo -e "  sudo systemctl status camera-server"
echo -e "  sudo systemctl restart camera-server"
echo -e "  journalctl -u camera-server -f"
echo ""
