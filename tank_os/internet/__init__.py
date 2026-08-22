"""
Simple Internet — Universal Downloader & Search Tool for TankOS.

Turns the entire web into a local library — safely, swiftly, and under your control.
Integrates aria2, yt-dlp, FFmpeg, torrent search, and the TankOS voice plugins
into a unified download experience.

Features:
- Multi-protocol downloads (HTTP, FTP, BitTorrent, Magnet, YouTube, etc.)
- Search aggregation across torrent sites, YouTube, documents
- Download queue with priority management
- Automatic categorization and metadata tagging
- Library management with search and filtering
- Voice control via existing TankOS plugins
"""

from tank_os.internet.downloader import (
    DownloadEngine,
    DownloadTask,
    DownloadStatus,
    DownloadCategory,
)
from tank_os.internet.search import (
    SearchEngine,
    SearchResult,
    SearchQuery,
    SearchSource,
)
from tank_os.internet.manager import (
    InternetManager,
)

__all__ = [
    "DownloadEngine", "DownloadTask", "DownloadStatus", "DownloadCategory",
    "SearchEngine", "SearchResult", "SearchQuery", "SearchSource",
    "InternetManager",
]
