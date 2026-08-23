"""TankOS UNO Q — 3rd Perception Detection Node.

Runs YOLOv8n object detection on frames from the ESP32-S3 CAM
(USB-C, ESPHome) connected to the Arduino UNO Q board.

Architecture:
  ESP32-S3 CAM (USB-C) → WiFi HTTP → UNO Q (ARM64) → YOLOv8n → Jetson (Tailscale)

The UNO Q board (Qualcomm QRB2210 + STM32U585) has:
  - USB LTE modem (Quectel EG800AK) for cellular failover
  - USB-C ESP32-S3 CAM (ESPHome, MJPEG stream at 192.168.31.145)
  - Tailscale mesh VPN at 100.84.235.7
"""

from tank.unoq.detection.esp32cam_detector import ESP32CAMDetector

__all__ = ["ESP32CAMDetector"]
