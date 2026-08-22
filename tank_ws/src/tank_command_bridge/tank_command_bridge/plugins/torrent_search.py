"""``voice.torrent_search`` plugin.

The voice flow uses this as the "second" call (after the user confirmed
the movie name):

* User: "Hey Tank, find the torrent for Inception."
* LLM: "Did you mean Inception (2010, Christopher Nolan)?"
* User: "Yes."
* LLM: *calls* ``voice.torrent_search`` ``{"query": "Inception", "limit": 5}``.
* Plugin returns ranked hits across all enabled sources.
* LLM: "I found three. Top hit is 1080p, 2.4 GB, 412 seeders. Want me
  to download it? Say yes."

The plugin is read-only (no state on disk, no motors). Rate-class
``read`` matches the existing query/telemetry/chat conventions.

Privacy note
~~~~~~~~~~~~
Every hit carries ``access_uri`` (the magnet for that row). The LLM has
bearer-auth on the bridge and every action is audited, so giving it
direct access to any hit's magnet is the cleanest way to enable the
"user picks option N" flow. ``scrub_magnet`` is still used elsewhere
for audit-log writes.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import RobotPlugin
from ._sources import leethax1337, limetorrents, rarbg
from ._torrent_common import (
    DEFAULT_ALLOWED_SOURCES,
    TorrentHit,
    active_sources,
    dedupe_by_infohash,
    load_policy,
    rank_hits,
)


# Per-site registry.  Adding a source = add one line here + one entry
# in DEFAULT_ALLOWED_SOURCES + a new module under _sources/.
_SEARCH_FNS = {
    "1337x":         leethax1337.search_1337x,
    "limetorrents":  limetorrents.search_limetorrents,
    "rarbg":         rarbg.search_rarbg,
}


def _search_all(query: str,
                sources: List[str],
                timeout_s: float) -> List[TorrentHit]:
    """Run each source search with a per-source hard timeout.

    Per-source failure must NEVER tank the whole search — that's what
    makes a flaky Cloudflare-protected site tolerable.  Sequential
    keeps the failure surface simple and the bridge process predictable.
    """
    hits: List[TorrentHit] = []
    for src in sources:
        fn = _SEARCH_FNS.get(src)
        if fn is None:
            continue
        try:
            hits.extend(fn(query, timeout_s=timeout_s))
        except Exception:
            continue
    return hits


class TorrentSearchPlugin(RobotPlugin):
    """Cross-source torrent search, ranked."""

    NAME = "voice.torrent_search"
    DESCRIPTION = (
        "Search 1337x, limetorrents, and rarbg for a movie / TV / game "
        "torrent and return the top-N ranked results across all enabled "
        "sources. Results are ranked by `(seeders * 100 - leechers * 0.1) "
        "* quality_multiplier`. Every hit carries ``access_uri`` so the "
        "LLM can hand any chosen rank to ``voice.aria2_add``."
    )
    PARAMETERS_SCHEMA = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query":     {"type": "string",
                          "description": "Search term, e.g. \"Inception 2010 movie\""},
            "limit":     {"type": "integer",
                          "description": "Top-N results to return (default 5, max 20)",
                          "minimum": 1, "maximum": 20, "default": 5},
            "min_seeders": {"type": "integer",
                            "description": "Drop hits below this seeders count (default 5)",
                            "minimum": 0, "maximum": 100000, "default": 5},
            "timeout_s":   {"type": "number",
                            "description": "HTTP timeout per source (default 6.0)",
                            "minimum": 1.0, "maximum": 30.0, "default": 6.0},
            "sources":     {"type": "array",
                            "description":
                                "Override the active sources for this call "
                                "(must be a subset of the configured allow-list). "
                                "Examples: [\"1337x\"] or [\"1337x\", \"limetorrents\"].",
                            "items": {"type": "string",
                                      "enum": sorted(DEFAULT_ALLOWED_SOURCES)}},
        },
    }
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "hits": {
                "type": "array",
                "description": ("Top-N ranked hits. Each entry has title, "
                                 "size_bytes, seeders, leechers, source, "
                                 "page_url, quality, score, AND ``access_uri`` "
                                 "so the LLM can pass it to "
                                 "``voice.aria2_add`` for any chosen rank."),
                "items": {
                    "type": "object",
                    "properties": {
                        "title":     {"type": "string"},
                        "size_bytes": {"type": "integer"},
                        "seeders":    {"type": "integer"},
                        "leechers":   {"type": "integer"},
                        "source":     {"type": "string"},
                        "page_url":   {"type": "string"},
                        "quality":    {"type": "integer"},
                        "score":      {"type": "number"},
                        "access_uri": {"type": "string"},
                    },
                },
            },
            "total": {"type": "integer",
                      "description": "Hits found before limit/filter."},
            "sources_active": {"type": "array", "items": {"type": "string"}},
            "sources_failed":  {"type": "array", "items": {"type": "string"},
                                "description": "Names of sources that returned no usable rows."},
        },
    }
    TAGS = ["read", "voice", "torrent"]
    RATE_CLASS = "read"

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        query = (params.get("query") or "").strip()
        if not query:
            return {"hits": [], "total": 0,
                    "sources_active": [], "sources_failed": [],
                    "_ok": False, "_error": "missing query"}
        limit = int(params.get("limit", 5))
        min_seeders = int(params.get("min_seeders", 5))
        timeout_s = float(params.get("timeout_s", 6.0))

        policy = load_policy()
        default_sources = active_sources(policy)
        requested = list(params.get("sources") or default_sources)
        allowed = set(default_sources or list(_SEARCH_FNS.keys()))
        sources = [s for s in requested if s in allowed and s in _SEARCH_FNS]

        raw_hits = _search_all(query, sources, timeout_s)
        # Dedupe hits with the same infohash across sources.
        raw_hits = dedupe_by_infohash(raw_hits)
        # Filter min_seeders BEFORE ranking.
        filtered = [h for h in raw_hits if h.seeders >= min_seeders]

        sources_succeeded: set = set()
        for h in filtered:
            sources_succeeded.add(h.source)
        sources_failed = [s for s in sources if s not in sources_succeeded]

        # Sort by score, take top-N, attach access_uri to every returned hit
        # so the LLM can pass ANY rank to voice.aria2_add.
        filtered.sort(key=lambda h: h.score(), reverse=True)
        top = filtered[:limit]
        ranked = []
        for h in top:
            d = h.to_dict()
            d["access_uri"] = h.magnet
            ranked.append(d)

        return {
            "hits": ranked,
            "total": len(filtered),
            "sources_active": sources,
            "sources_failed": sources_failed,
            "_ok": True,
        }


# Helpers exposed for tests.
search_all = _search_all
inject_search_fns = _SEARCH_FNS
