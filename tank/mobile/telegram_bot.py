"""
telegram_bot.py - Tank Telegram Bot
Instant mobile notifications + remote control via Telegram
Works over LTE — no WiFi needed
"""
import json
import time
import logging
import threading
import urllib.request
import urllib.parse
import os
from datetime import datetime

logger = logging.getLogger("tank.telegram")


class TelegramBot:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.environ.get("TANK_TELEGRAM_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TANK_TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.running = False
        self._offset = 0
        self._callbacks = {}
        self._on_message = None

    def register_command(self, command, callback):
        self._callbacks[command.lower()] = callback

    def on_message(self, callback):
        self._on_message = callback

    def _api(self, method, data=None):
        url = f"{self.base_url}/{method}"
        if data:
            data = json.dumps(data).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
            )
        else:
            req = urllib.request.Request(url)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read())
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return None

    def send_message(self, text, chat_id=None, parse_mode="HTML"):
        cid = chat_id or self.chat_id
        if not cid:
            logger.warning("No chat_id configured")
            return False
        return self._api("sendMessage", {
            "chat_id": cid,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })

    def send_photo(self, photo_path, caption="", chat_id=None):
        """Send photo to Telegram"""
        cid = chat_id or self.chat_id
        if not cid or not os.path.exists(photo_path):
            return False
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-s", "-F", f"chat_id={cid}",
                 "-F", f"caption={caption}",
                 "-F", f"photo=@{photo_path}",
                 f"{self.base_url}/sendPhoto"],
                capture_output=True, text=True, timeout=15,
            )
            return "true" in result.stdout
        except Exception as e:
            logger.error(f"Send photo error: {e}")
            return False

    def send_location(self, lat, lon, chat_id=None):
        cid = chat_id or self.chat_id
        return self._api("sendLocation", {
            "chat_id": cid,
            "latitude": lat,
            "longitude": lon,
        })

    def send_alert(self, alert_type, message, priority="normal"):
        emoji_map = {
            "threat": "🚨", "obstacle": "⚠️", "low_battery": "🔋",
            "motion": "👁️", "sound": "🔊", "info": "ℹ️",
            "camera": "📷", "system": "🤖", "emergency": "🆘",
        }
        emoji = emoji_map.get(alert_type, "📢")
        priority_map = {"low": "", "normal": "⚠️", "high": "🔴", "emergency": "🆘"}
        prefix = priority_map.get(priority, "")
        text = f"{prefix}{emoji} <b>Tank Alert</b>\n\n{message}\n\n<i>{datetime.now().strftime('%H:%M:%S')}</i>"
        return self.send_message(text)

    def send_status_update(self, status):
        text = (
            f"🤖 <b>TankOS Status</b>\n\n"
            f"Mode: {status.get('mode', 'unknown')}\n"
            f"CPU: {status.get('cpu', 0)}%\n"
            f"RAM: {status.get('ram', 0)}%\n"
            f"Battery: {status.get('battery', 0)}%\n"
            f"Signal: {status.get('signal', 'N/A')}\n"
            f"Position: {status.get('lat', 0):.4f}, {status.get('lon', 0):.4f}\n\n"
            f"<i>Updated {datetime.now().strftime('%H:%M:%S')}</i>"
        )
        return self.send_message(text)

    def start_polling(self):
        self.running = True

        def _poll():
            logger.info("Telegram bot polling started")
            while self.running:
                try:
                    resp = self._api("getUpdates", {
                        "offset": self._offset,
                        "timeout": 30,
                        "allowed_updates": ["message"],
                    })
                    if resp and resp.get("result"):
                        for update in resp["result"]:
                            self._offset = update["update_id"] + 1
                            msg = update.get("message", {})
                            text = msg.get("text", "")
                            from_chat = str(msg.get("chat", {}).get("id", ""))
                            user = msg.get("from", {}).get("first_name", "Unknown")

                            logger.info(f"TG from {user}: {text}")

                            cmd = text.strip().lower().split()[0] if text.strip() else ""
                            if cmd in self._callbacks:
                                args = text.strip()[len(cmd):].strip()
                                reply = self._callbacks[cmd](from_chat, user, args)
                                if reply:
                                    self.send_message(reply, from_chat)
                            elif self._on_message:
                                reply = self._on_message(from_chat, user, text)
                                if reply:
                                    self.send_message(reply, from_chat)
                            else:
                                self.send_message(
                                    f"🤖 TankOS received: {text}\nReply HELP for commands",
                                    from_chat,
                                )
                except Exception as e:
                    if self.running:
                        logger.error(f"Polling error: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=_poll, daemon=True)
        thread.start()
        return thread

    def stop(self):
        self.running = False
