"""Shared code used by every torrent-related plugin.

* :class:`TorrentHit`         — uniform result type across all sources.
* :func:`scrub_magnet`        — strip trackers from a magnet for safe logging.
* :func:`rank_hits`           — score + sort hits across sources.
* :func:`allowed_sources`     — load the operator-approved source allow-list.
* :func:`normalise_size`      — parse "1.4 GB" / "812 MiB" → bytes.
* :func:`dedupe_by_infohash` — de-duplicate identical torrents across
                                sources by their ``xt=urn:btih:…`` value.

Why "module-prefixed with underscore"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The package scanner in :mod:`tank_command_bridge.plugins` only treats
``torrent_search`` / ``aria2_add`` / ``aria2_progress`` as entry points;
helper modules like this are imported *by* those entry points and
therefore intentionally do not register a plugin themselves — that's
what the leading underscore signals.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Allowed sources.
# -----------------------------------------------------------------------------
DEFAULT_ALLOWED_SOURCES: Tuple[str, ...] = (
    "1337x",
    "limetorrents",
    "rarbg",
)

# Exact filename semantics: this is curated, NEVER derived from
# user input.  Operators edit it directly to disable a source.
DEFAULT_POLICY_PATH = Path("/etc/tank/torrent_policy.json")


@dataclass
class SourcePolicy:
    name: str
    enabled: bool = True
    timeout_s: float = 6.0
    http_profile: str = "cloudscraper"   # cloudscraper | httpx | static_fixtures


def load_policy(path: Optional[Path] = None) -> Dict[str, SourcePolicy]:
    """Load the per-source policy or fall back to the safe default."""
    path = path or DEFAULT_POLICY_PATH
    out: Dict[str, SourcePolicy] = {}
    for name in DEFAULT_ALLOWED_SOURCES:
        out[name] = SourcePolicy(name=name)
    if not path.exists():
        return out
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return out
    if isinstance(raw, dict):
        for key, cfg in raw.items():
            if not isinstance(cfg, dict) or "name" not in cfg:
                continue
            out[key] = SourcePolicy(
                name=cfg["name"],
                enabled=bool(cfg.get("enabled", True)),
                timeout_s=float(cfg.get("timeout_s", 6.0)),
                http_profile=str(cfg.get("http_profile", "cloudscraper")),
            )
    return out


def active_sources(policies: Dict[str, SourcePolicy]) -> List[str]:
    """Return source names that are allowed AND enabled."""
    return [p.name for p in policies.values()
            if isinstance(p, SourcePolicy) and p.enabled]


# -----------------------------------------------------------------------------
# Data model.
# -----------------------------------------------------------------------------
@dataclass
class TorrentHit:
    """A single result from any torrent source, normalised into one shape."""

    title: str
    size_bytes: int
    seeders: int
    leechers: int
    source: str
    magnet: str
    page_url: str = ""
    quality: int = 0
    uploaded: str = ""

    def score(self) -> float:
        """Higher is better.

        Seeders dominate; quality is a deadband tier reward; leechers
        subtract only by 10% so a torrent with very high seeders still
        wins over a dead one.  Ranking score, not a quality certificate.
        """
        qm = 1.0 + (self.quality >= 1080) * 0.5 + (self.quality >= 2160) * 0.3
        return ((self.seeders * 100.0) - (self.leechers * 0.1)) * qm

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["score"] = round(self.score(), 2)
        return d


def rank_hits(hits: Iterable[TorrentHit],
              take: int = 5) -> List[Dict[str, Any]]:
    """Score every hit, sort desc, return the top-N as plain dicts."""
    scored = sorted(hits, key=lambda h: h.score(), reverse=True)
    return [h.to_dict() for h in scored[:take]]


def dedupe_by_infohash(hits: Iterable[TorrentHit]) -> List[TorrentHit]:
    """Collapse hits sharing the same ``xt=urn:btih:…`` value.

    Cross-source duplicates (different site, same content) are common —
    the highest-scored entry (recomputed each pass) wins.
    """
    seen: Dict[str, TorrentHit] = {}
    for h in hits:
        ih = extract_infohash(h.magnet)
        # Use the full magnet URL as the fallback dedup key so two
        # genuinely-different torrents with the same title on the same
        # site (e.g. two unrelated "Inception 2010" remuxes) don't
        # accidentally collapse when `xt=` is missing.
        key = ih if ih else h.magnet
        existing = seen.get(key)
        if existing is None or h.score() > existing.score():
            seen[key] = h
    return list(seen.values())


def extract_infohash(magnet: str) -> str:
    """Pull ``xt=urn:btih:<HEX>`` out of a magnet. Returns "" on failure."""
    if not magnet or not magnet.startswith("magnet:"):
        return ""
    try:
        parsed = urllib.parse.urlparse(magnet)
        qs = urllib.parse.parse_qs(parsed.query)
        for xt in qs.get("xt", []):
            if xt.startswith("urn:btih:"):
                return xt[len("urn:btih:"):].lower()
    except Exception:
        return ""
    return ""


# -----------------------------------------------------------------------------
# Privacy & safety helpers.
# -----------------------------------------------------------------------------
def scrub_magnet(magnet: str) -> str:
    """Return a magnet with all trackers stripped.

    We keep the ``xt=urn:btih:<infohash>``, ``dn=Display Name``, and
    ``xl=size`` so audit logs are still actionable (did we fetch a
    specific known content? what size?) but any ``tr=`` entries are
    dropped so we don't leak active tracker hostnames into every log
    line.
    """
    if not magnet.startswith("magnet:?"):
        return magnet
    parsed = urllib.parse.urlparse(magnet)
    qs = urllib.parse.parse_qs(parsed.query)
    safe_qs = {k: v for k, v in qs.items() if k in ("xt", "dn", "xl")}
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(safe_qs, doseq=True))
    )


def magnet_is_safe(magnet_or_url: str) -> Tuple[bool, str]:
    """Return (ok, reason).  Used as a hard gate before aria2.addUri.

    * ``magnet:`` always accepted.
    * ``https://...torrent`` accepted.
    * ``http://...torrent`` **rejected** (MITM risk on trackers).
    * Empty or unknown scheme: rejected.
    """
    if not magnet_or_url:
        return False, "empty_uri"
    s = magnet_or_url.strip().lower()
    if s.startswith("magnet:?"):
        return True, "magnet"
    if s.startswith("https://") and s.endswith(".torrent"):
        return True, "https_torrent"
    if s.startswith("http://") and s.endswith(".torrent"):
        return False, "plain_http_torrent_rejected_for_mitm"
    return False, "unsupported_scheme"


# -----------------------------------------------------------------------------
# Title-parsing helpers (used by every per-site scraper).
# -----------------------------------------------------------------------------
_SIZE_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>TB|GB|MB|KB|TiB|GiB|MiB|KiB)",
    re.IGNORECASE,
)
_QUALITY_RE = re.compile(r"(?P<q>2160p?|1080p?|720p?|4k|hd|sd)", re.IGNORECASE)


def normalise_size(text: str) -> int:
    """Pull the first-sized token out of a string.  Returns 0 on failure."""
    m = _SIZE_RE.search(text or "")
    if not m:
        return 0
    n = float(m.group("num"))
    unit = m.group("unit").lower()
    factor = {"tb": 10 ** 12, "tib": 10 ** 12,
              "gb": 10 ** 9,  "gib": 10 ** 9,
              "mb": 10 ** 6,  "mib": 10 ** 6,
              "kb": 10 ** 3,  "kib": 10 ** 3}.get(unit, 1)
    return int(n * factor)


def normalise_quality(title: str) -> int:
    """Parse 720/1080/2160 from a title.  Returns 0 if unknown."""
    m = _QUALITY_RE.search(title or "")
    if not m:
        return 0
    s = m.group("q").lower()
    if "2160" in s or "4k" in s:
        return 2160
    if "1080" in s:
        return 1080
    if "720" in s:
        return 720
    if "hd" in s:
        return 720
    if "sd" in s:
        return 480
    return 0


def normalise_int(text: str) -> int:
    """Parse '1,234' / '1.2k' / '1234' → int.  Copes with commas + ``k``."""
    if text is None:
        return 0
    s = str(text).strip().replace(",", "").replace(" ", "")
    if not s:
        return 0
    m = re.match(r"^(\d+(?:\.\d+)?)(k|m)?$", s, re.IGNORECASE)
    if not m:
        return 0
    n = float(m.group(1))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        n *= 1000
    elif suffix == "m":
        n *= 1_000_000
    return int(n)
