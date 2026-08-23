#!/usr/bin/env python3
"""Perception Daemon — crash-proof, async triggers.

LiDAR polls every 200ms. On trigger → camera + YOLO + LLM → SMS.
Runs in separate thread so daemon stays alive.

Phone: +917860245819
"""

import sys
import time
import threading
import logging
import traceback
from pathlib import Path

LOG_FILE = Path("/tmp/perception_daemon.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("perception")

PROJECT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT))


def run_trigger(motion, lidar_dist, phone):
    """Thread: capture → YOLO → LLM → SMS."""
    try:
        log.info("Pipeline: camera capture...")
        yolo_result = ""
        try:
            from tank_os.shell.terminal.agent_chat import _capture_frame, _run_yolo
            frame = _capture_frame()
            if frame:
                yolo_result = _run_yolo(frame)
                log.info(f"YOLO: {yolo_result}")
            else:
                log.warning("Camera capture returned None")
        except Exception as e:
            yolo_result = f"Camera error: {e}"
            log.error(f"Camera: {traceback.format_exc()}")

        log.info("Pipeline: AI interpretation...")
        lidar_info = f"LiDAR: {lidar_dist/1000:.2f}m" if lidar_dist > 0 else "N/A"
        ai_text = "AI unavailable"
        try:
            from tank_os.shell.terminal.agent_chat import _rotate_chat
            msgs = [
                {"role": "system", "content": "Security AI. Interpret concisely in 1-2 sentences. Plain text."},
                {"role": "user", "content": f"Alert at {time.strftime('%H:%M:%S')}. Motion: {motion:.3f} | {lidar_info} | Camera: {yolo_result}"},
            ]
            ai_text = _rotate_chat(msgs)
            log.info(f"AI: {ai_text}")
        except Exception as e:
            ai_text = f"AI error: {e}"
            log.error(f"AI: {traceback.format_exc()}")

        log.info("Pipeline: sending SMS...")
        sms_text = f"TankOS Alert [{time.strftime('%H:%M:%S')}]\n\n{ai_text}\n\n{lidar_info}"
        try:
            from tank_os.shell.terminal.sms_sender import send_sms
            result = send_sms(sms_text, phone=phone)
            if result.get("success"):
                log.info(f"SMS SENT ✅")
            else:
                log.error(f"SMS FAILED ❌: {result.get('error')}")
        except Exception as e:
            log.error(f"SMS: {traceback.format_exc()}")

        log.info("Pipeline complete ✅")

    except Exception as e:
        log.error(f"Trigger thread CRASHED: {traceback.format_exc()}")


def main():
    phone = "+917860245819"
    LIDAR_THRESHOLD = 3000   # mm
    COOLDOWN = 30            # seconds

    log.info("=" * 50)
    log.info("Perception Daemon v2 starting...")
    log.info(f"LiDAR < {LIDAR_THRESHOLD}mm | Cooldown: {COOLDOWN}s | Phone: {phone}")

    last_trigger = 0.0

    try:
        from tank_os.shell.terminal.lidar_reader import read_lidar
        log.info("LiDAR import OK, starting poll...")
    except Exception as e:
        log.error(f"LiDAR import failed: {e}")
        return

    while True:
        try:
            scan = read_lidar(timeout_s=1.0)
            if scan and scan.min_distance > 0 and scan.min_distance < LIDAR_THRESHOLD:
                now = time.time()
                if now - last_trigger >= COOLDOWN:
                    last_trigger = now
                    log.info(f"TRIGGER: {scan.min_distance}mm {scan.nearest_object}")
                    t = threading.Thread(target=run_trigger, args=(0.0, scan.min_distance, phone), daemon=True)
                    t.start()
        except Exception as e:
            log.error(f"LiDAR poll error: {e}")

        time.sleep(0.2)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            log.error(f"Daemon crashed, restarting in 5s: {traceback.format_exc()}")
            time.sleep(5)
