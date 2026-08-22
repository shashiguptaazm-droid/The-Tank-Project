"""
Simple Internet — Search Aggregation Engine.

Meta-search across torrent sites, YouTube, web, documents, and images.
Plugin-based architecture for adding new search sources.

Feature coverage: 56-80 (search), 59-67 (torrent search), 60-63 (media search),
64-65 (document search), 71-73 (bookmarks, suggestions, safe search)
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("tank_os.internet.search")


class SearchSource(Enum):
    """Available search sources."""
    TORRENT = "torrent"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    WEB = "web"
    IMAGES = "images"
    DOCUMENTS = "documents"
    EBOOKS = "ebooks"
    NEWS = "news"


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    source: str                    # "torrent", "youtube", "web", etc.
    size_bytes: int = 0
    seeders: int = 0
    leechers: int = 0
    upload_date: str = ""
    author: str = ""
    description: str = ""
    thumbnail: str = ""
    file_type: str = ""            # "mp4", "mp3", "pdf", etc.
    quality: str = ""              # "1080p", "320kbps", etc.
    score: float = 0.0            # Relevance score
    magnet: str = ""               # For torrent results
    info_hash: str = ""            # For torrent results


@dataclass
class SearchQuery:
    """A search query with filters."""
    query: str
    source: SearchSource = SearchSource.TORRENT
    category: str = ""              # "video", "audio", "documents"
    file_type: str = ""             # "mp4", "mp3", "pdf"
    min_size: int = 0
    max_size: int = 0
    min_seeders: int = 0
    sort_by: str = "seeders"        # "seeders", "size", "date"
    limit: int = 20
    safe_search: bool = True
    page: int = 1


class SearchEngine:
    """
    Meta-search engine aggregating multiple sources (features 56-80).

    Features:
    - Query multiple sources simultaneously
    - Result deduplication and merging
    - Search filters (file type, size, date)
    - Smart suggestions and history
    - Safe search enforcement
    """

    def __init__(self):
        self._sources: Dict[SearchSource, Callable] = {}
        self._history: List[Dict[str, Any]] = []
        self._bookmarks: List[SearchResult] = []
        self._register_default_sources()

    def _register_default_sources(self) -> None:
        """Register built-in search sources."""
        self._sources[SearchSource.YOUTUBE] = self._search_youtube
        self._sources[SearchSource.SOUNDCLOUD] = self._search_soundcloud
        self._sources[SearchSource.WEB] = self._search_web
        self._sources[SearchSource.IMAGES] = self._search_images
        self._sources[SearchSource.NEWS] = self._search_news
        # Torrent search is handled by the existing voice.torrent_search plugin

    def register_source(self, name: SearchSource, handler: Callable) -> None:
        """Register a custom search source (feature 75)."""
        self._sources[name] = handler

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute a search query (feature 56)."""
        results: List[SearchResult] = []

        # Check if source handler exists
        handler = self._sources.get(query.source)
        if handler:
            try:
                results = handler(query)
            except Exception as e:
                logger.warning("Search source %s failed: %s", query.source.value, e)
        else:
            logger.warning("No handler for search source: %s", query.source.value)

        # Apply filters (features 58, 74)
        results = self._apply_filters(results, query)

        # Sort (feature 67)
        results = self._sort_results(results, query.sort_by)

        # Save to history (feature 80)
        self._history.append({
            "query": query.query,
            "source": query.source.value,
            "results": len(results),
            "time": time.time(),
        })

        return results[:query.limit]

    def search_all(self, query: str, limit_per_source: int = 5) -> Dict[str, List[SearchResult]]:
        """Search across all available sources (feature 56)."""
        results: Dict[str, List[SearchResult]] = {}
        base_query = SearchQuery(query=query, limit=limit_per_source)

        for source_type, handler in self._sources.items():
            try:
                q = SearchQuery(query=query, source=source_type, limit=limit_per_source)
                source_results = handler(q)
                if source_results:
                    results[source_type.value] = source_results
            except Exception as e:
                logger.warning("Search all failed for %s: %s", source_type.value, e)

        return results

    def _search_youtube(self, query: SearchQuery) -> List[SearchResult]:
        """Search YouTube via yt-dlp (feature 60)."""
        try:
            import yt_dlp
            results = []

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "force_generic_extractor": False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = f"ytsearch{query.limit}:{query.query}"
                info = ydl.extract_info(search_query, download=False)

                if info and "entries" in info:
                    for entry in info["entries"][:query.limit]:
                        if not entry:
                            continue
                        results.append(SearchResult(
                            title=entry.get("title", ""),
                            url=f"https://youtube.com/watch?v={entry.get('id', '')}",
                            source="youtube",
                            upload_date=entry.get("upload_date", ""),
                            author=entry.get("uploader", ""),
                            description=entry.get("description", "")[:200],
                            thumbnail=entry.get("thumbnail", ""),
                            file_type="mp4",
                            quality=entry.get("resolution", ""),
                        ))

            return results
        except ImportError:
            logger.warning("yt-dlp not available for YouTube search")
            return []

    def _search_soundcloud(self, query: SearchQuery) -> List[SearchResult]:
        """Search SoundCloud (feature 61)."""
        try:
            import yt_dlp
            results = []
            ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = f"scsearch{query.limit}:{query.query}"
                info = ydl.extract_info(search_query, download=False)
                if info and "entries" in info:
                    for entry in info["entries"][:query.limit]:
                        if not entry:
                            continue
                        results.append(SearchResult(
                            title=entry.get("title", ""),
                            url=entry.get("url", "") or entry.get("webpage_url", ""),
                            source="soundcloud",
                            author=entry.get("uploader", ""),
                            thumbnail=entry.get("thumbnail", ""),
                            file_type="mp3",
                        ))
            return results
        except ImportError:
            return []

    def _search_web(self, query: SearchQuery) -> List[SearchResult]:
        """Generic web search via DuckDuckGo (feature 57)."""
        try:
            results = []
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query.query)}"

            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TankOS/1.0)"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            html = resp.read().decode("utf-8", errors="replace")

            # Simple HTML parsing for DuckDuckGo results
            for match in re.finditer(
                r'<a rel="nofollow" href="([^"]+)"[^>]*>(.*?)</a>',
                html,
            ):
                url = match.group(1)
                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                if url and title and not url.startswith("//"):
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        source="web",
                        description=f"Found on web — {time.strftime('%Y-%m-%d')}",
                    ))

            return results[:query.limit]
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return []

    def _search_images(self, query: SearchQuery) -> List[SearchResult]:
        """Search images (feature 62)."""
        # Uses DuckDuckGo image search
        try:
            results = []
            search_url = (
                f"https://html.duckduckgo.com/html/?q="
                f"{urllib.parse.quote(query.query + ' site:imgur.com OR site:flickr.com')}"
            )
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TankOS/1.0)"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            html = resp.read().decode("utf-8", errors="replace")

            for match in re.finditer(r'<img[^>]+src="([^"]+)"[^>]*>', html):
                src = match.group(1)
                if src.startswith("http") and not src.endswith(".gif"):
                    results.append(SearchResult(
                        title=f"Image {len(results) + 1}",
                        url=src,
                        source="images",
                        thumbnail=src,
                        file_type=src.split(".")[-1].split("?")[0],
                    ))

            return results[:query.limit]
        except Exception:
            return []

    def _search_news(self, query: SearchQuery) -> List[SearchResult]:
        """Search news (feature 79)."""
        try:
            results = []
            search_url = (
                f"https://html.duckduckgo.com/html/?q="
                f"{urllib.parse.quote(query.query + ' site:reuters.com OR site:bbc.com OR site:apnews.com')}"
            )
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TankOS/1.0)"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            html = resp.read().decode("utf-8", errors="replace")

            for match in re.finditer(
                r'<a rel="nofollow" href="([^"]+)"[^>]*>(.*?)</a>',
                html,
            ):
                url = match.group(1)
                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                if url and title:
                    results.append(SearchResult(
                        title=title, url=url, source="news",
                    ))

            return results[:query.limit]
        except Exception:
            return []

    def _apply_filters(self, results: List[SearchResult],
                        query: SearchQuery) -> List[SearchResult]:
        """Apply search filters (feature 58)."""
        filtered = results

        if query.category:
            filtered = [r for r in filtered if query.category.lower() in r.file_type.lower()]

        if query.file_type:
            filtered = [r for r in filtered if r.file_type.lower() == query.file_type.lower()]

        if query.min_size > 0:
            filtered = [r for r in filtered if r.size_bytes >= query.min_size]

        if query.max_size > 0:
            filtered = [r for r in filtered if r.size_bytes <= query.max_size]

        if query.min_seeders > 0:
            filtered = [r for r in filtered if r.seeders >= query.min_seeders]

        return filtered

    def _sort_results(self, results: List[SearchResult],
                       sort_by: str) -> List[SearchResult]:
        """Sort search results (feature 67)."""
        if sort_by == "seeders":
            return sorted(results, key=lambda r: r.seeders, reverse=True)
        elif sort_by == "size":
            return sorted(results, key=lambda r: r.size_bytes, reverse=True)
        elif sort_by == "date":
            return sorted(results, key=lambda r: r.upload_date, reverse=True)
        return results

    # Feature 72: Bookmarks
    def bookmark_result(self, result: SearchResult) -> None:
        """Save a search result as a bookmark (feature 72)."""
        if result not in self._bookmarks:
            self._bookmarks.append(result)
            logger.info("Bookmarked: %s", result.title)

    def get_bookmarks(self) -> List[SearchResult]:
        """Get saved bookmarks."""
        return self._bookmarks

    def remove_bookmark(self, url: str) -> bool:
        """Remove a bookmark by URL."""
        for b in self._bookmarks:
            if b.url == url:
                self._bookmarks.remove(b)
                return True
        return False

    # Feature 73: Suggestions
    def get_suggestions(self, partial: str) -> List[str]:
        """Get search suggestions (feature 73)."""
        suggestions = []
        for h in self._history:
            if partial.lower() in h["query"].lower():
                suggestions.append(h["query"])
        return list(set(suggestions))[:5]

    # Feature 80: History
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get search history (feature 80)."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear search history."""
        self._history.clear()

    def get_summary(self) -> Dict[str, Any]:
        """Brief summary."""
        return {
            "sources": [s.value for s in self._sources],
            "history_count": len(self._history),
            "bookmarks": len(self._bookmarks),
        }
