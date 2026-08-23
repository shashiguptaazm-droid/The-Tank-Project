"""Tank — Camera drivers.

1. USBCamera    — V4L2 USB webcam (Jetson, /dev/video0)
2. ESP32CAMDriver — ESPHome ESP32-S3 CAM (UNO Q, WiFi @ 192.168.31.145)
3. OrbbecCamera — Orbbec Astra/Gemini depth
4. LuxonisCamera — Luxonis OAK-D stereo
"""
from tank.perception.cameras.esp32cam import ESP32CAMDriver
