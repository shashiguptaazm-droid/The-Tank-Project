#!/usr/bin/env python3
"""SMS sender — Quectel EG800AK-CN LTE modem via ModemManager.

The modem ports (ttyUSB2/ttyUSB3) are held by pppd/NetworkManager.
Use mmcli (ModemManager CLI) for SMS — it already owns the modem.
"""

from __future__ import annotations

import subprocess
import time


DEFAULT_PHONE = "+917860245819"
MODEM_INDEX = "0"


def _run(cmd: str, timeout: float = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)


def send_sms(message: str, phone: str = DEFAULT_PHONE, timeout: float = 30.0) -> dict:
    """Send an SMS via ModemManager. Returns {success, error}."""
    try:
        # Create SMS
        create_out = _run(
            f"mmcli -m {MODEM_INDEX} --messaging-create-sms=\"number='{phone}',text='{message}'\"",
            timeout=10,
        )

        # Extract SMS path — output contains formatting like '  Messaging | created sms: /org/...'
        sms_path = ""
        for line in create_out.split("\n"):
            if "/org/freedesktop/ModemManager1/SMS/" in line:
                # Extract just the path from formatted output
                for part in line.split():
                    if part.startswith("/org/"):
                        sms_path = part.strip()
                        break
                if sms_path:
                    break

        if not sms_path:
            return {"success": False, "error": f"Failed to create SMS: {create_out.strip()[:200]}"}

        # Send SMS
        send_out = _run(f"mmcli -s {sms_path} --send", timeout=timeout)

        if "successfully sent" in send_out.lower():
            return {"success": True, "error": None, "sms_path": sms_path}
        else:
            return {"success": False, "error": f"Send failed: {send_out.strip()[:200]}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def check_modem() -> dict:
    """Check modem status via ModemManager. Returns {registered, signal, error}."""
    try:
        # Get modem info
        info = _run(f"mmcli -m {MODEM_INDEX}", timeout=5)

        registered = "+CREG:" in info or "state:'registered'" in info or "registered" in info.lower()
        if not registered:
            # Try checking status differently
            status_out = _run(f"mmcli -m {MODEM_INDEX} -e", timeout=5)
            registered = "enabled" in status_out.lower()

        # Get signal strength
        signal = 0
        sig_out = _run(f"mmcli -m {MODEM_INDEX} --signal", timeout=5)
        for line in sig_out.split("\n"):
            if "strength" in line.lower():
                try:
                    signal = int(line.split(":")[1].strip().replace("%", "").strip())
                except:
                    pass

        return {"registered": registered, "signal": signal, "error": None}

    except Exception as e:
        return {"registered": False, "signal": 0, "error": str(e)}


if __name__ == "__main__":
    print("Testing SMS sender...")
    modem = check_modem()
    print(f"Modem: {modem}")

    if modem.get("registered"):
        print("Sending test SMS...")
        result = send_sms("TankOS SMS test - system working!")
        print(f"Result: {result}")
    else:
        print("Modem not registered - cannot send SMS")
