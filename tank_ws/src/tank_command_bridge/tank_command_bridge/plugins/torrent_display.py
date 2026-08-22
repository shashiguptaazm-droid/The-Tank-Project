"""``voice.torrent_pick`` / ``voice.torrent_cancel`` / ``voice.show_torrent_results``.

Three plugins that close the loop between ``voice.torrent_search`` and
the dashboard's "asking" UI. Picking and cancelling operate on the
shared :class:`RecentResultsStore` + :class:`ActiveDownloadsStore`
from :mod:`_torrent_display`. ``show_torrent_results`` is a read-class
hint that asks the dashboard to surface the latest results as cards.

Wire flow
---------
user:  "search torrent lo-fi"
       ─► torrent_search fills RECENT_RESULTS via _torrent_common
user:  "show me the results"
       ─► show_torrent_results pushes a /dashboard/event payload
user:  "download the second one"
       ─► torrent_pick(ordinal=2) emits voice.aria2_add intent
user:  "cancel it"
       ─► torrent_cancel by GID or magnet
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

from . import RobotPlugin
# `_aria2_common` only exports `Aria2Error` (plus raw RPC `add_uri`,
# `tell_status`, etc. as functions). The plugin needs a CLIENT object
# interface (so ctx.aria2 can be set to a fake for tests), hence we
# define `NullAria2Client` / `_derive_safe_options` / `_scrub_magnet`
# locally below. This guarantees module-level Aria2Error identity is
# the production class (no shadow stub class to mismatch `except`).
from ._aria2_common import Aria2Error
from ._torrent_display import (
    ACTIVE_DOWNLOADS,
    RECENT_RESULTS,
)


# ────────────────────────────────────────────────────────────────────────────
# Local client + helpers. ``_aria2_common`` is the JSON-RPC transport but
# it ships FUNCTIONS not an object — so the plugin speaks to aria2 via a
# thin client interface that any object exposing ``add_uri(magnet,
# options=…)`` can fulfil.  The dashboard, an aria2c shell-out, or a
# test fake all drop into the same slot.
# ────────────────────────────────────────────────────────────────────────────
class NullAria2Client:
    """No-op aria2 client. ``add_uri`` returns a deterministic stub gid,
    ``remove`` returns ``"ok"``. Used by tests AND by the plugin when
    ``ctx.aria2`` is not provided."""

    def __init__(self) -> None:
        self._seq = 0

    def _next_gid(self) -> str:
        self._seq += 1
        return f"stub-gid-{self._seq}"

    def add_uri(self, magnet: str, options: Optional[Dict[str, Any]] = None) -> str:
        return self._next_gid()

    def remove(self, gid: str) -> str:
        return "ok"


def _scrub_magnet(magnet: str) -> str:
    """Light magnet sanitiser.  Today: passthrough.  Future: strip
    trackers, pin the btih, validate the URI schema. Defined here so
    it's overridable in one place."""
    if not isinstance(magnet, str):
        return ""
    return magnet.strip()


def _derive_safe_options(filename: Optional[str] = None) -> Dict[str, Any]:
    """Translate the plugin's human-readable ``title`` into aria2's
    ``out=`` option so files land in a clean directory with the
    operator's preferred name. Today: empty options dict (the caller
    sets ``dir`` upstream)."""
    out: Dict[str, Any] = {}
    if filename:
        # Cap at 120 chars + strip dangerous chars — matches what the
        # previous lazy shim did so no behaviour change.
        safe = "".join(c for c in filename[:120]
                       if c.isalnum() or c in (" ", ".", "_", "-")).strip()
        if safe:
            out["out"] = safe
    return out


# ────────────────────────────────────────────────────────────────────────────
# Confirm-before-act buffer for staged picks (the dashboard hits
# POST /api/torrent/pick?auto_confirm=false to inspect before queueing).
# ────────────────────────────────────────────────────────────────────────────
class _PickStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: Optional[Dict[str, Any]] = None

    def push(self, row: Dict[str, Any]) -> None:
        with self._lock:
            self._pending = dict(row)

    def consume(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self._pending
            self._pending = None
            return p

    def peek(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._pending) if self._pending else None


PENDING_PICK = _PickStore()


def _resolve_client(ctx: Any) -> Any:
    """Return ``ctx.aria2`` if it's set, else a fresh ``NullAria2Client``.

    Defensive — preserves ``ctx is not None AND hasattr(ctx, "aria2") AND ctx.aria2 is not None``
    so plugins that pass ``ctx=None`` or a stub ctx-without-aria2 don't crash.
    """
    if ctx is not None and hasattr(ctx, "aria2") and ctx.aria2 is not None:
        return ctx.aria2
    return NullAria2Client()


# ────────────────────────────────────────────────────────────────────────────
# Plugins
# ────────────────────────────────────────────────────────────────────────────
class TorrentPickPlugin(RobotPlugin):
    """Pick one of the most recent search results and queue it for download."""
    NAME = "voice.torrent_pick"
    DESCRIPTION = (
        "Pick one of the most recent search results by ordinal "
        "('the second one' → ordinal=2). Stages the row, optionally "
        "auto-confirms via ``voice.aria2_add``, and updates "
        "ACTIVE_DOWNLOADS so the dashboard shows progress. Use "
        "``voice.show_torrent_results`` to surface the cards first."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "ordinal": {"type": "integer",
                        "description": "1-based ordinal — 'first' = 1, "
                                       "'third' = 3, etc.",
                        "minimum": 1, "default": 1},
            "ordinal_word": {"type": "string",
                              "enum": ["first", "second", "third",
                                       "fourth", "fifth", "sixth",
                                       "last"],
                              "default": ""},
            "auto_confirm": {"type": "boolean",
                              "description": "Skip dashboard confirm "
                                              "and queue the aria2 add "
                                              "immediately.",
                              "default": True},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "picked": {"type": "object"},
            "queued_for_aria2": {"type": "boolean"},
            "ordinal": {"type": "integer"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "torrent", "display"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        ord_word = (params.get("ordinal_word") or "").strip().lower()
        word_to_n = {"first": 1, "second": 2, "third": 3,
                     "fourth": 4, "fifth": 5, "sixth": 6}
        try:
            n = int(params.get("ordinal", 1) or 1)
        except (TypeError, ValueError):
            n = 1
        if ord_word in word_to_n:
            n = word_to_n[ord_word]
        elif ord_word == "last":
            n = max(1, len(RECENT_RESULTS.list()))
        items = RECENT_RESULTS.list()
        if not items:
            return {"_ok": False, "ordinal": n,
                    "tts_text":
                        "There are no recent torrent results to pick."}
        idx = max(0, min(n - 1, len(items) - 1))
        row = items[idx]
        PENDING_PICK.push(row)
        queued = False
        aria2_resp: Dict[str, Any] = {}
        auto_confirm = bool(params.get("auto_confirm", True))
        if auto_confirm and row.get("magnet"):
            client = _resolve_client(ctx)
            magnet = _scrub_magnet(row["magnet"])
            if magnet:
                title = row.get("title", "torrent")[:120]
                options = _derive_safe_options(filename=title)
                try:
                    gid = client.add_uri(magnet, options=options)
                    ACTIVE_DOWNLOADS.mark_active(gid, {
                        "title": title,
                        "source": row.get("source", ""),
                        "magnet": magnet,
                    })
                    queued = True
                    aria2_resp = {"gid": gid}
                except Aria2Error as exc:
                    aria2_resp = {"error": str(exc)[:200]}
        title = row.get("title", "result")
        return {"_ok": True,
                "picked": row,
                "queued_for_aria2": queued,
                "ordinal": idx + 1,
                "aria2": aria2_resp,
                "tts_text": (
                    f"Staged {title}. "
                    + ("Downloading now." if queued else
                       "Open the dashboard to confirm."))}


class TorrentCancelPlugin(RobotPlugin):
    """Cancel a running torrent by GID or by magnet. Mark it done."""
    NAME = "voice.torrent_cancel"
    DESCRIPTION = (
        "Cancel an active torrent by its GID (from a previous "
        "voice.aria2_progress response) or by magnet URI. Marks it "
        "done in ACTIVE_DOWNLOADS so the dashboard row updates."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "gid": {"type": "string", "default": ""},
            "magnet": {"type": "string", "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "cancelled": {"type": "boolean"},
            "matched_gid": {"type": "string"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["write", "voice", "torrent", "display"]
    RATE_CLASS = "write"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        gid = (params.get("gid") or "").strip()
        magnet = (params.get("magnet") or "").strip()
        client = _resolve_client(ctx)
        if not gid:
            for entry in ACTIVE_DOWNLOADS.list():
                if magnet and (magnet in (entry.get("magnet", "") or "")):
                    gid = entry["gid"]
                    break
        if not gid or not ACTIVE_DOWNLOADS.contains(gid):
            return {"_ok": False, "cancelled": False,
                    "tts_text":
                        "Couldn't find that download to cancel."}
        try:
            client.remove(gid)
        except Aria2Error as exc:
            return {"_ok": False, "cancelled": False,
                    "matched_gid": gid,
                    "_hint": str(exc)[:200],
                    "tts_text": "Cancel failed."}
        ACTIVE_DOWNLOADS.mark_done(gid)
        return {"_ok": True, "cancelled": True, "matched_gid": gid,
                "tts_text": "Download cancelled."}


class ShowTorrentResultsPlugin(RobotPlugin):
    """Tell the dashboard to surface the most recent torrent results as cards."""
    NAME = "voice.show_torrent_results"
    DESCRIPTION = (
        "Mark the current RECENT_RESULTS for display. The dashboard's "
        "/api/torrent/results endpoint picks the same store up, so the "
        "card list becomes visible to the operator."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "default": ""},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "shown": {"type": "integer"},
            "query": {"type": "string"},
            "active": {"type": "integer"},
            "tts_text": {"type": "string"},
        },
    }
    TAGS = ["read", "voice", "torrent", "display"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        items = RECENT_RESULTS.list()
        active = ACTIVE_DOWNLOADS.list()
        title = (params.get("query") or RECENT_RESULTS.last_query()).strip()
        shown = len(items)
        if not items:
            tts = ("There are no recent torrent results. "
                   "Try 'search torrent <movie>'.")
        else:
            tts = (f"Showing {shown} "
                   f"{'result' if shown == 1 else 'results'}"
                   f" for {title!r}. Pick by ordinal or open the dashboard.")
        if ctx is not None and hasattr(ctx, "bus_event"):
            try:
                ctx.bus_event("torrent_results_shown",
                              {"items": items, "query": title})
            except Exception:
                pass
        return {"_ok": True, "shown": shown, "query": title,
                "active": len(active), "tts_text": tts}


__all__ = [
    "NullAria2Client",
    "PENDING_PICK",
    "TorrentPickPlugin",
    "TorrentCancelPlugin",
    "ShowTorrentResultsPlugin",
]
