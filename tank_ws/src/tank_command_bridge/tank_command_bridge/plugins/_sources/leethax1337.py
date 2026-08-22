"""1337x.to scraper.

1337x's search results page emits rows in a table. Each row has:
  * a magnet link inside the "download" column;
  * a size cell (e.g. "1.4 GB");
  * the seeder count;
  * the leecher count.

That structure is enough for a robust parser; we still drop any row
that lacks a magnet or a parseable size.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Callable, List, Optional

from .._torrent_common import TorrentHit, normalise_quality, normalise_size

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) TheTankTorrentFetcher/1.0"


class _RowCollector(HTMLParser):
    """Collect <tr> blocks containing a magnet:"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buf: list[str] = []
        self._capture = False
        self.rows: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
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

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)


_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def parse_1337x(html: str, query: str) -> List[TorrentHit]:
    """Pure parser used by tests."""
    parser = _RowCollector()
    parser.feed(html)
    hits: List[TorrentHit] = []
    for row in parser.rows:
        hrefs = _HREF_RE.findall(row)
        magnet = next((h for h in hrefs if h.startswith("magnet:?")), "")
        page = next((h for h in hrefs if "/torrent/" in h.lower()
                                           or "1337x" in h.lower()
                                           or re.search(r"/torrent/\d+/", h)), "")
        if not magnet:
            continue
        flat = re.sub(r"<[^>]+>", " ", row)
        flat = re.sub(r"\s+", " ", flat).strip()
        size_match = re.search(
            r"(\d+(?:\.\d+)?\s*(?:TB|GB|MB|KB|TiB|GiB|MiB|KiB))",
            flat, re.IGNORECASE,
        )
        if not size_match:
            continue
        title = flat[:size_match.start()].strip(" -.·:")
        size_bytes = normalise_size(size_match.group(1))
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
            source="1337x",
            magnet=magnet,
            page_url=page,
            quality=normalise_quality(title),
        ))
    return hits


def search_1337x(query: str,
                 timeout_s: float = 6.0,
                 http_get: Optional[Callable[[str, float], str]] = None
                 ) -> List[TorrentHit]:
    """Search 1337x.to / 1337x.st / .so via HTTP.  Injection-friendly for tests."""
    http_get = http_get or _default_http_get
    q = urllib.parse.quote_plus(query.strip())
    url = f"https://1337x.to/search/{q}/1/"
    try:
        html = http_get(url, timeout_s)
    except (OSError, urllib.error.URLError):
        return []
    try:
        return parse_1337x(html, query)
    except Exception:
        return []


def _default_http_get(url: str, timeout_s: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8", errors="replace")
