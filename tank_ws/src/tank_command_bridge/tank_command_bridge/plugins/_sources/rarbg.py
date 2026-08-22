"""rarbg.to scraper.

The site changes its DOM ~quarterly; we parse in *two passes*:

1. Pull every <tr> in the search results table.
2. Per row, find <a class="..."> values for magnet, series, size text,
   and the seeder/leechers counts.

Each row also has at least one <a href="magnet:?..."> so we use the
presence of a magnet as the row marker.  Anything that fails to
produce a magnet is dropped.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Callable, List, Optional

from .._torrent_common import TorrentHit, normalise_int, normalise_quality, normalise_size

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) TheTankTorrentFetcher/1.0"


class _RowCollector(HTMLParser):
    """Collect <tr> blocks whose HTML contains ``magnet:?``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._buf: list[str] = []
        self._capture = False
        self.rows: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._depth += 1
        if tag == "tr":
            self._buf = []
            self._capture = True
        elif self._capture:
            self._buf.append(self.get_starttag_text() or f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if self._capture and tag == "tr":
            row_html = "".join(self._buf)
            if "magnet:?" in row_html:
                self.rows.append(row_html)
            self._capture = False
            self._buf = []
        elif self._capture:
            self._buf.append(f"</{tag}>")
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)


_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def _hrefs(row: str) -> List[str]:
    return _HREF_RE.findall(row)


def parse_rarbg(html: str, query: str) -> List[TorrentHit]:
    """Pure parser.  Returns a list of :class:`TorrentHit` for the rows.

    Takes the search page HTML.  Robust against missing columns — any
    row missing size / seeders / magnet is dropped silently.
    """
    parser = _RowCollector()
    parser.feed(html)

    hits: List[TorrentHit] = []
    for row in parser.rows:
        hrefs = _hrefs(row)
        magnet = next((h for h in hrefs if h.startswith("magnet:?")), "")
        page = next((h for h in hrefs if "/torrent/" in h.lower()), "")
        if not magnet:
            continue
        # rarbg rows display Title/Size/Seeders/Leechers in four cells.
        # We split by </td> to isolate each cell.
        cells = re.split(r"</td>\s*<td[^>]*>", row)
        # First scrub HTML tags; the first marketable text becomes title.
        flat = re.sub(r"<[^>]+>", " ", " ".join(cells))
        flat = re.sub(r"\s+", " ", flat).strip()
        tokens = re.findall(r"[^\s]+", flat) or [""]
        # Heuristic: title is the longest token group preceding the
        # first size-like token ("1.4 GB" / "812 MB").
        size_match = re.search(r"(\d+(?:\.\d+)?\s*(?:TB|GB|MB|KB|TiB|GiB|MiB|KiB))",
                               flat, re.IGNORECASE)
        if not size_match:
            continue
        title = flat[:size_match.start()].strip(" -.·:")
        size_bytes = normalise_size(size_match.group(1))
        # After size: seeders and leechers are the next two ints.
        tail = flat[size_match.end():]
        nums = re.findall(r"\d{1,7}", tail)
        seeders = int(nums[0]) if len(nums) >= 1 else 0
        leechers = int(nums[1]) if len(nums) >= 2 else 0
        if not title or size_bytes <= 0:
            continue
        hits.append(TorrentHit(
            title=title,
            size_bytes=size_bytes,
            seeders=seeders,
            leechers=leechers,
            source="rarbg",
            magnet=magnet,
            page_url=page,
            quality=normalise_quality(title),
        ))
    return hits


def search_rarbg(query: str,
                 timeout_s: float = 6.0,
                 http_get: Optional[Callable[[str, float], str]] = None) -> List[TorrentHit]:
    """Search rarbg.to via HTTP.  Injection-friendly for tests."""
    http_get = http_get or _default_http_get
    q = urllib.parse.quote_plus(query.strip())
    url = f"https://rarbg.to/torrents.php?search={q}&category=movies"
    try:
        html = http_get(url, timeout_s)
    except (OSError, urllib.error.URLError):
        return []
    try:
        return parse_rarbg(html, query)
    except Exception:
        return []


def _default_http_get(url: str, timeout_s: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8", errors="replace")
