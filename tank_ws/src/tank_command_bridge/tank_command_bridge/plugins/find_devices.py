"""``voice.find_devices`` plugin.

Passive LAN discovery.

Limitations (deliberately chosen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
We do NOT do active port scanning — no nmap, no SYN ping, no ARP
spoofing. The plugin reads:

* :file:`/proc/net/arp` — Linux ARP cache, populated by the kernel
  as the OS does its normal networking. Every IP we see is one the
  host has already talked to.
* :data:`DEFAULT_DEVICE_CACHE_PATH` — a JSON file the operator
  populates by hand or by piping ``avahi-browse --all -t`` into
  ``tank_cache_devices.py``. We never auto-write the cache.

Returns a flat list of
``{name, address, port, service, source}`` records the LLM can
filter down.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import RobotPlugin
from ._house_helpers import (
    DEFAULT_DEVICE_CACHE_PATH,
    discover_devices,
    load_device_cache,
    read_arp_table,
    reverse_dns,
)


_DEFAULT_SERVICES = ("googlecast", "airplay", "amazon", "sonos",
                     "workstation", "ssh", "http", "ipp")


class FindDevicesPlugin(RobotPlugin):
    """Discover devices on the LAN (passive only)."""

    NAME = "voice.find_devices"
    DESCRIPTION = (
        "List devices already known to the host — neighbours with ARP "
        "entries plus any mdns records the operator has cached at "
        "``/var/cache/tank/devices.json``. Never actively scans; the "
        "operator can populate the mdns cache by piping ``avahi-browse "
        "--all -t`` into a one-liner. Use this to build a list "
        "before calling ``voice.play_tv`` or ``voice.play_alexa``."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "include_arp": {"type": "boolean",
                             "description":
                                 "Read /proc/net/arp (default true).",
                             "default": True},
            "include_mdns_cache": {"type": "boolean",
                                    "description":
                                        "Read mdns cache file (default true).",
                                    "default": True},
            "service_filter": {
                "type": "array",
                "description":
                    "If non-empty, only include entries whose ``service`` "
                    "matches one of these names (googlecast, airplay, "
                    "amazon, sonos, workstation, ssh, http, ipp, etc.).",
                "items": {"type": "string"},
                "default": [],
            },
            "limit":  {"type": "integer",
                        "description": "Max records to return (default 50).",
                        "minimum": 1, "maximum": 500, "default": 50},
            "cache_path": {"type": "string",
                            "description":
                                "Override the mdns cache path.",
                            "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "devices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":     {"type": "string"},
                        "address":  {"type": "string"},
                        "port":     {"type": "integer"},
                        "service":  {"type": "string"},
                        "source":   {"type": "string"},
                    },
                },
            },
            "by_service": {
                "type": "object",
                "description": "Counts grouped by service name.",
                "additionalProperties": {"type": "integer"},
            },
            "sources_used": {
                "type": "array",
                "items": {"type": "string"},
                "description": "\"arp\" and/or \"mdns_cache\".",
            },
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "lan"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        include_arp = bool(params.get("include_arp", True))
        include_mdns = bool(params.get("include_mdns_cache", True))
        limit = int(params.get("limit", 50))
        cache_path = params.get("cache_path") or DEFAULT_DEVICE_CACHE_PATH
        wanted_services = [s.strip().lower()
                           for s in (params.get("service_filter") or [])
                           if isinstance(s, str) and s.strip()]
        sources_used: List[str] = []

        devices: List = []
        if include_arp:
            sources_used.append("arp")
            for d in read_arp_table():
                # ARP entries don't carry service names; tag them so
                # service_filter can be applied but defer final
                # labelling until mdns overlay runs.
                devices.append(d)
        if include_mdns:
            sources_used.append("mdns_cache")
            seen_addrs = {d.address for d in devices}
            from pathlib import Path
            cached = load_device_cache(Path(cache_path)) \
                if cache_path else load_device_cache()
            for d in cached:
                if d.address not in seen_addrs:
                    devices.append(d)
                else:
                    # Overlay mdns meta onto the ARP entry.
                    for existing in devices:
                        if existing.address == d.address:
                            existing.name = d.name or existing.name
                            existing.service = d.service or existing.service
                            existing.source = d.source
                            existing.port = d.port or existing.port

        # Reverse-DNS any entries still missing a friendly name.
        for d in devices:
            if not d.name and d.address:
                d.name = reverse_dns(d.address)

        # Optional service_filter.
        if wanted_services:
            devices = [d for d in devices
                       if (d.service or "").lower() in wanted_services]

        devices = devices[:limit]
        by_service: Dict[str, int] = {}
        for d in devices:
            by_service[d.service or "unknown"] = \
                by_service.get(d.service or "unknown", 0) + 1
        tts = (f"I found {len(devices)} device"
               f"{'s' if len(devices) != 1 else ''} on the LAN. "
               + (", ".join(sorted(by_service.keys())) if by_service else
                  "No service labels."))
        return {
            "_ok": True,
            "devices": [
                {"name": d.name, "address": d.address,
                 "port": d.port, "service": d.service, "source": d.source}
                for d in devices
            ],
            "by_service": by_service,
            "sources_used": sources_used,
            "tts_text": tts,
        }
