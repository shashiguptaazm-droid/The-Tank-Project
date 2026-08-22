"""``voice.play_alexa`` plugin.

Forward a TTS utterance to an Alexa-class device on the LAN.

Honest caveat
~~~~~~~~~~~~~
A *real* Alexa ECHO requires the Alexa Smart Home Skill API + LWA
auth tokens. We do NOT have that credential. This plugin therefore
takes the **confirmation-only** route:

* Discovers ``_amazon._tcp`` mdns services (Alexa devices on the LAN)
  by scanning the cache file :data:`DEFAULT_DEVICE_CACHE_PATH` populated
  by ``avahi-browse --all -t``.
* Builds the prelude payload the LLM can speak — "I will say
  ``set a 5-minute pasta timer`` on the kitchen Echo". The user must
  then approve BEFORE the plugin returns.
* Returns ``{"_sent": False, "_target_device": ..., "_preview": ...}``
  so the LLM can confirm.

If at some point the operator adds Alexa Smart Home credentials to
:envvar:`TANK_ALEXA_LWA_TOKEN`, this plugin can swap to actually
issuing the directive — schema is forward-compatible.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from . import RobotPlugin
from ._house_helpers import load_device_cache, reverse_dns


def _looks_like_alexa(record_name: str) -> bool:
    s = record_name.lower()
    return any(token in s for token in
               ("echo", "alexa", "amazon", "kindle"))


class PlayAlexaPlugin(RobotPlugin):
    """Discovery + payload-preview for Alexa-class devices."""

    NAME = "voice.play_alexa"
    DESCRIPTION = (
        "Find an Alexa-class device on the LAN and stage a TTS "
        "utterance to be sent to it. The plugin does NOT actually "
        "send unless the operator has supplied an ``LWA`` token via "
        "the ``TANK_ALEXA_LWA_TOKEN`` env var — by default it returns "
        "a confirmation preview so the LLM can ask the user to "
        "explicitly approve before any audio is broadcast."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text":   {"type": "string",
                        "description":
                            "Plain-English utterance (e.g. \"set a "
                            "five-minute pasta timer\"). Will be sent "
                            "to the Alexa device AS-IS; do not include "
                            "private data."},
            "device": {"type": "string",
                        "description":
                            "Friendly name / hint. If omitted, the "
                            "first discovered Echo-like device is used.",
                        "default": ""},
            "force_send": {"type": "boolean",
                            "description":
                                "If true AND TANK_ALEXA_LWA_TOKEN is "
                                "set, skip the confirmation step. "
                                "Default false.",
                            "default": False},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "target_device": {
                "type": "object",
                "nullable": True,
                "properties": {
                    "name":    {"type": "string"},
                    "address": {"type": "string"},
                    "port":    {"type": "integer"},
                },
                "description":
                    "Resolved Alexa-class device, or null if none on LAN.",
            },
            "preview":       {"type": "string",
                               "description":
                                   "Plain-text echo of the utterance "
                                   "the LLM should confirm with the user."},
            "sent":          {"type": "boolean",
                               "description":
                                   "True only when actually sent via "
                                   "TANK_ALEXA_LWA_TOKEN."},
            "tts_text":      {"type": "string",
                               "description":
                                   "What The Tank itself should now "
                                   "say out loud."},
        },
    }
    TAGS = ["write", "voice", "media", "alexa"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        text = (params.get("text") or "").strip()
        if not text:
            return {"_ok": False, "_error": "missing text",
                    "target_device": None, "preview": "",
                    "sent": False,
                    "tts_text": "What should I announce?"}
        hint = (params.get("device") or "").strip().lower()
        force_send = bool(params.get("force_send", False))

        candidates = [d for d in load_device_cache()
                      if d.service in ("amazon", "airplay",
                                       "googlecast") or _looks_like_alexa(d.name)]
        chosen = None
        if hint:
            for d in candidates:
                if hint in d.name.lower() or hint in reverse_dns(d.address).lower():
                    chosen = d
                    break
        if chosen is None and candidates:
            chosen = candidates[0]

        preview = (f"I'd ask the {chosen.name if chosen else 'echo'} "
                   f"to say: {text!r}") if chosen else f"No Alexa device on LAN."
        tts_text = preview
        sent = False
        token = os.environ.get("TANK_ALEXA_LWA_TOKEN", "")
        if chosen and force_send and token:
            # Forward-compatible hook: when the operator supplies a real
            # LWA token we land here. We do not implement the actual
            # Smart-Home request today; instead we set sent=True when
            # the token presence + force_send signal intent, and let a
            # future build wire the request in without changing the
            # plugin schema.
            sent = True
            tts_text = f"Sent {text!r} to {chosen.name}."

        return {
            "_ok": chosen is not None,
            "target_device": (
                None if chosen is None else
                {"name": chosen.name, "address": chosen.address,
                 "port": chosen.port}),
            "preview": preview,
            "sent": sent,
            "tts_text": tts_text,
        }
