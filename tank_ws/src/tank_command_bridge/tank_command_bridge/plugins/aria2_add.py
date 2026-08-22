"""``voice.aria2_add`` plugin.

The voice flow uses this as the "third" call: after the user selected a
specific hit from ``voice.torrent_search``.

* User: "Yes — top hit."
* LLM: *calls* ``voice.aria2_add`` ``{"magnet": "<magnet:?xt=...>"}``.
* Plugin validates the magnet (scheme + length), then queues it into
  aria2 via JSON-RPC, forwarding any ``filename`` / ``dir`` overrides
  to aria2's options dict.
* Plugin returns ``{"gid": "...", "status": "added"}`` so the LLM can
  say "Download queued" and remember the gid for the next progress call.

Hard safety
~~~~~~~~~~~~
We refuse to add anything that isn't ``magnet:?`` or an ``https://...
.torrent`` URL.  Plain HTTP is blocked because trackers/download-portal
URLs without TLS are a MITM surface.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import RobotPlugin
from ._aria2_common import Aria2Error, add_uri, warn_if_no_token
from ._torrent_common import magnet_is_safe


class Aria2AddPlugin(RobotPlugin):
    """Add a torrent URI to aria2 via JSON-RPC."""

    NAME = "voice.aria2_add"
    DESCRIPTION = (
        "Queue a single torrent URI (magnet:? or https://...torrent) in "
        "the local aria2 instance via its JSON-RPC interface. Plain HTTP "
        "torrent URLs are rejected for MITM reasons. The downloaded "
        "file lands in the directory configured by aria2.conf "
        "(``dir=/downloads`` by default). Returns the aria2 gid for "
        "downstream progress polling."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["magnet"],
        "properties": {
            "magnet":   {"type": "string",
                         "description": ("But really any URI. Must start with "
                                         "'magnet:?' or 'https://' + "
                                         "'.torrent' extension.")},
            "filename": {"type": "string",
                         "description":
                             "Optional aria2 ``out`` filename override. "
                             "If omitted, aria2 picks from the infohash dn=",
                         "default": ""},
            "dir":      {"type": "string",
                         "description": "Optional aria2 ``dir`` override",
                         "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "gid":             {"type": "string"},
            "status":          {"type": "string"},
            "validation_note": {"type": "string"},
            "options_sent":    {"type": "object",
                                "description": "Snapshot of the aria2 options "
                                               "dict that was forwarded on the wire."},
        },
    }
    TAGS = ["write", "voice", "aria2"]
    RATE_CLASS = "write"     # mutates aria2 queue

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        uri = (params.get("magnet") or "").strip()
        if not uri:
            return {"gid": "", "status": "rejected",
                    "validation_note": "missing uri",
                    "options_sent": {},
                    "_ok": False}
        ok, why = magnet_is_safe(uri)
        if not ok:
            return {"gid": "", "status": "rejected",
                    "validation_note": f"validation_failed:{why}",
                    "options_sent": {},
                    "_ok": False}
        warn_if_no_token()

        # Build aria2 options from filename / dir overrides.
        options: Dict[str, Any] = {}
        if params.get("filename"):
            options["out"] = str(params["filename"])
        if params.get("dir"):
            options["dir"] = str(params["dir"])
        try:
            gid = add_uri(uri, options=options or None, timeout=6.0)
        except Aria2Error as exc:
            return {"gid": "", "status": "error",
                    "validation_note": f"aria2_error:{exc}",
                    "options_sent": options,
                    "_ok": False}
        return {"gid": gid, "status": "added",
                "validation_note": why,
                "options_sent": options,
                "_ok": True}
