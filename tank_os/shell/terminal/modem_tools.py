#!/usr/bin/env python3
"""Modem Tools — contacts, SMS, calls via ModemManager.

The AI agent uses these to interact with the LTE modem naturally:
  send_sms("Hi!", to="mom")
  send_sms("Running late", to="+917860245819")
  call_number("+917860245819")
  call_number("dad")
  list_contacts()
  add_contact("Shashi", "+917860245819")
  get_modem_status()
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


CONTACTS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "contacts.json"
MODEM_INDEX = "0"
DEFAULT_PHONE = "+917860245819"


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _run(cmd: str, timeout: float = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)


# ═══════════════════════════════════════════════════════════════════════════
#  Contacts
# ═══════════════════════════════════════════════════════════════════════════

def _load_contacts() -> Dict[str, str]:
    """Load contacts from JSON file."""
    if CONTACTS_FILE.exists():
        try:
            return json.loads(CONTACTS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_contacts(contacts: Dict[str, str]):
    """Save contacts to JSON file."""
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_FILE.write_text(json.dumps(contacts, indent=2))


def add_contact(name: str, phone: str) -> str:
    """Add a contact. Name is case-insensitive for lookup."""
    contacts = _load_contacts()
    contacts[name.lower()] = phone
    _save_contacts(contacts)
    return f"Saved contact: {name} → {phone}"


def remove_contact(name: str) -> str:
    """Remove a contact by name."""
    contacts = _load_contacts()
    key = name.lower()
    if key in contacts:
        del contacts[key]
        _save_contacts(contacts)
        return f"Removed contact: {name}"
    return f"Contact '{name}' not found"


def list_contacts() -> str:
    """List all saved contacts."""
    contacts = _load_contacts()
    if not contacts:
        return "No contacts saved. Use add_contact(name, phone) to add."
    lines = []
    for name, phone in sorted(contacts.items()):
        lines.append(f"  {name.title()} → {phone}")
    return f"Contacts ({len(contacts)}):\n" + "\n".join(lines)


def resolve_number(name_or_number: str) -> str:
    """Resolve a name to a phone number. If already a number, return as-is."""
    # Already a phone number?
    if name_or_number.startswith("+") or name_or_number.replace("-", "").replace(" ", "").isdigit():
        return name_or_number

    # Try contacts lookup
    contacts = _load_contacts()
    key = name_or_number.lower().strip()
    if key in contacts:
        return contacts[key]

    # Try partial match
    matches = [(n, p) for n, p in contacts.items() if key in n]
    if len(matches) == 1:
        return matches[0][1]
    elif len(matches) > 1:
        names = ", ".join(m[0].title() for m in matches)
        return f"AMBIGUOUS:{names}"

    return f"NOT_FOUND:{name_or_number}"


# ═══════════════════════════════════════════════════════════════════════════
#  SMS
# ═══════════════════════════════════════════════════════════════════════════

def send_sms(message: str, to: str = DEFAULT_PHONE) -> str:
    """Send SMS to a phone number or contact name.

    Examples:
        send_sms("Hi!", to="mom")
        send_sms("Running late", to="+917860245819")
    """
    # Resolve name to number
    phone = resolve_number(to)
    if phone.startswith("NOT_FOUND:"):
        return f"Contact '{to}' not found. Add it first with add_contact('{to}', '<phone>')"
    if phone.startswith("AMBIGUOUS:"):
        return f"Multiple matches for '{to}': {phone.split(':')[1]}. Be more specific."

    # Create and send SMS via ModemManager
    # Escape single quotes in message
    safe_msg = message.replace("'", "'\\''")
    safe_phone = phone.replace("'", "'\\''")

    create_out = _run(
        f"mmcli -m {MODEM_INDEX} --messaging-create-sms=\"number='{safe_phone}',text='{safe_msg}'\"",
        timeout=10,
    )

    # Extract SMS path
    sms_path = ""
    for line in create_out.split("\n"):
        for part in line.split():
            if part.startswith("/org/"):
                sms_path = part.strip()
                break
        if sms_path:
            break

    if not sms_path:
        return f"Failed to create SMS: {create_out[:200]}"

    send_out = _run(f"mmcli -s {sms_path} --send", timeout=15)

    if "successfully sent" in send_out.lower():
        return f"SMS sent to {phone}: '{message[:50]}{'...' if len(message) > 50 else ''}'"
    else:
        return f"SMS send failed: {send_out[:200]}"


def get_sms_messages(direction: str = "all", limit: int = 5) -> str:
    """Read recent SMS messages.

    Args:
        direction: 'received', 'sent', or 'all'
        limit: max messages to show
    """
    out = _run(f"mmcli -m {MODEM_INDEX} --messaging-list-sms", timeout=10)

    sms_paths = []
    for line in out.split("\n"):
        for part in line.split():
            if part.startswith("/org/"):
                sms_paths.append(part.strip())

    if not sms_paths:
        return "No SMS messages on modem"

    messages = []
    for path in sms_paths[-limit:]:
        detail = _run(f"mmcli -s {path}", timeout=5)
        # Parse fields
        number = text = state = ""
        for line in detail.split("\n"):
            if "number:" in line:
                number = line.split(":")[1].strip()
            elif "text:" in line:
                text = line.split(":", 1)[1].strip()
            elif "state:" in line:
                state = line.split(":")[1].strip()

        if direction != "all" and direction not in state:
            continue

        messages.append(f"  [{state}] {number}: {text[:100]}")

    return f"SMS messages ({len(messages)}):\n" + "\n".join(messages) if messages else "No matching messages"


# ═══════════════════════════════════════════════════════════════════════════
#  Voice Calls (AT commands via primary port)
# ═══════════════════════════════════════════════════════════════════════════

def call_number(number_or_name: str) -> str:
    """Initiate a voice call to a phone number or contact name.

    Examples:
        call_number("dad")
        call_number("+917860245819")
    """
    phone = resolve_number(number_or_name)
    if phone.startswith("NOT_FOUND:"):
        return f"Contact '{number_or_name}' not found."
    if phone.startswith("AMBIGUOUS:"):
        return f"Multiple matches for '{number_or_name}': {phone.split(':')[1]}"

    # Use ModemManager to send AT command for voice call
    # DTMF拨号 via ATD
    out = _run(f"mmcli -m {MODEM_INDEX} --command='ATD{phone};'", timeout=15)
    if "OK" in out or "error" not in out.lower():
        return f"Calling {phone}... (dial initiated)"
    else:
        return f"Call failed: {out[:200]}"


def hangup_call() -> str:
    """Hang up the current call."""
    out = _run(f"mmcli -m {MODEM_INDEX} --command='ATH'", timeout=5)
    return "Call hung up" if "OK" in out else f"Hangup failed: {out[:100]}"


def answer_call() -> str:
    """Answer an incoming call."""
    out = _run(f"mmcli -m {MODEM_INDEX} --command='ATA'", timeout=5)
    return "Call answered" if "OK" in out else f"Answer failed: {out[:100]}"


# ═══════════════════════════════════════════════════════════════════════════
#  Modem Status
# ═══════════════════════════════════════════════════════════════════════════

def get_modem_status() -> str:
    """Get modem status: registration, signal, SIM info."""
    info = _run(f"mmcli -m {MODEM_INDEX}", timeout=5)
    if not info or "error" in info.lower():
        return "Modem not found"

    lines = {}
    for line in info.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if key and val:
                lines[key] = val

    status_parts = []
    status_parts.append(f"Model: {lines.get('model', 'unknown')}")
    status_parts.append(f"Firmware: {lines.get('firmware revision', 'unknown')}")

    # Check registration
    creg = _run(f"mmcli -m {MODEM_INDEX} --command='AT+CREG?'", timeout=5)
    if "+CREG:" in creg:
        reg_val = creg.split("+CREG:")[1].split("\n")[0].strip()
        status_parts.append(f"Network: {reg_val}")

    # Signal
    sig = _run(f"mmcli -m {MODEM_INDEX} --signal", timeout=5)
    for line in sig.split("\n"):
        if "strength" in line.lower():
            status_parts.append(f"Signal: {line.split(':')[1].strip()}")

    # SIM
    for line in info.split("\n"):
        if "own:" in line:
            status_parts.append(f"SIM number: {line.split(':')[1].strip()}")

    return "Modem status:\n  " + "\n  ".join(status_parts)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI interface for direct testing
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 modem_tools.py status")
        print("  python3 modem_tools.py contacts")
        print("  python3 modem_tools.py add <name> <phone>")
        print("  python3 modem_tools.py sms <to> <message>")
        print("  python3 modem_tools.py read [limit]")
        print("  python3 modem_tools.py call <number>")
        print("  python3 modem_tools.py hangup")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "status":
        print(get_modem_status())
    elif cmd == "contacts":
        print(list_contacts())
    elif cmd == "add" and len(sys.argv) >= 4:
        print(add_contact(sys.argv[2], sys.argv[3]))
    elif cmd == "sms" and len(sys.argv) >= 4:
        msg = " ".join(sys.argv[3:])
        print(send_sms(msg, to=sys.argv[2]))
    elif cmd == "read":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(get_sms_messages(limit=limit))
    elif cmd == "call" and len(sys.argv) >= 3:
        print(call_number(sys.argv[2]))
    elif cmd == "hangup":
        print(hangup_call())
    else:
        print(f"Unknown command: {cmd}")
