# Simple Internet universal downloader - Software & Python dependencies

This document is the canonical dependency map for the Simple Internet application layer. It covers everything from core async HTTP to media processing, torrenting, search, and UI.

## System-level dependencies

These must be installed via your OS package manager (`apt`, `brew`, etc.) before Python packages that wrap them will work.

| Package | Purpose |
|---------|---------|
| ffmpeg | Audio/video conversion, streaming, analysis, metadata |
| libtorrent-rasterbar | C++ torrent library (needed by python-libtorrent) |
| 7zip / p7zip-full | Archive extraction (7z, RAR, etc.) |
| mkvtoolnix | MKV multiplexing, chapter editing |
| atomicparsley | Embedding metadata into MP4 files |
| rtmpdump | Legacy RTMP stream downloading |
| phantomjs / chromium (headless) | JavaScript-heavy site scraping (optional) |
| openssl | TLS/SSL (usually pre-installed) |
| sqlite3 | Default database (pre-installed on most systems) |
| redis | Optional message broker for task queues |

### Install on Debian/Ubuntu (Raspberry Pi)

```bash
sudo apt update
sudo apt install ffmpeg libtorrent-rasterbar-dev p7zip-full mkvtoolnix atomicparsley rtmpdump redis
```

### Install on macOS

```bash
brew install ffmpeg libtorrent-rasterbar p7zip mkvtoolnix atomicparsley
```

## Python dependencies (pip)

Grouped by function so you can install only what you need.

### 1. Core async & networking

| Package | Description |
|---------|-------------|
| aiohttp | Async HTTP client/server, backbone of high-speed downloading |
| httpx | Sync/async HTTP client with HTTP/2 support |
| aiofiles | Async file operations for non-blocking disk I/O |
| urllib3 | Underlying HTTP library |
| requests | Synchronous HTTP for simpler tasks, API calls |
| websockets | Real-time progress over WebSocket |
| python-socketio | Higher-level WebSocket with rooms (web UI) |
| socksio / PySocks | SOCKS proxy support for aiohttp/httpx |

### 2. Download engines & extractors

| Package | Description |
|---------|-------------|
| yt-dlp | The ultimate media extractor - supports 1800+ sites |
| python-libtorrent | Bindings for libtorrent |
| libtorrent | pip-installable wheel (often the same) |
| nzbfriends / pynzb | Parse NZB files for Usenet |
| py3-nzb | Alternative NZB parser |
| sabyenc3 | yEnc decoder for Usenet binaries |
| ipfshttpclient | Talk to a local IPFS daemon |
| hls-downloader (optional) | Dedicated HLS stream downloader |

### 3. Media post-processing

| Package | Description |
|---------|-------------|
| ffmpeg-python | Pythonic wrapper around FFmpeg |
| mutagen | Read/write audio metadata (ID3, FLAC tags) |
| Pillow | Image processing, thumbnails, format conversion |
| exiftool (subprocess) | Read/write EXIF/IPTC for images/video |
| pycaption | Subtitle parsing and conversion (SRT, WebVTT) |
| subliminal | Automatic subtitle downloader by hash |
| babelfish | Language code conversion (subliminal dep) |
| pysubs2 | Advanced subtitle editing |

### 4. Archive handling

| Package | Description |
|---------|-------------|
| patool | Unifies archive formats via external programs |
| py7zr | Pure-Python 7z extractor |
| rarfile | RAR extraction (requires unrar binary) |
| zipfile (stdlib) | Built-in ZIP handling |

### 5. Metadata, tagging & MusicBrainz

| Package | Description |
|---------|-------------|
| musicbrainzngs | MusicBrainz API bindings |
| discogs-client | Discogs API for metadata |
| beets (optional) | Advanced music library manager |
| mediafile | Audio metadata wrapper (used by beets) |
| acoustid | Audio fingerprinting (needs chromaprint) |
| pyacoustid | Python binding for Chromaprint |
| chromaprint | System library (`libchromaprint-dev`) |

### 6. Database & storage

| Package | Description |
|---------|-------------|
| sqlalchemy | ORM for SQLite/PostgreSQL |
| alembic | Database migrations |
| sqlcipher3 (optional) | Encrypted SQLite |
| redis | Redis client (task queues & caching) |
| diskcache | Disk-based cache alternative to Redis |

### 7. Task scheduling & automation

| Package | Description |
|---------|-------------|
| APScheduler | Advanced cron-like job scheduling |
| celery | Distributed task queue (scale-out) |
| arq | Async task queue (Redis-backed, simpler) |
| watchdog | Filesystem monitor for new `.torrent` files |
| feedparser | RSS/Atom feed parser for auto-downloads |

### 8. Search & scraping

| Package | Description |
|---------|-------------|
| beautifulsoup4 | HTML parsing |
| lxml | Fast HTML/XML parser |
| html5lib | Lenient HTML parser |
| requests-html | JavaScript-rendered page scraping |
| selenium (optional) | Full browser automation |
| duckduckgo-search | DuckDuckGo search API wrapper |
| google-api-python-client | Google Custom Search API |
| wikipedia | Wikipedia API for data grabs |
| imdbpy | IMDb movie database access |

### 9. UI frameworks

| Package | Description |
|---------|-------------|
| PySide6 / PyQt6 | Native desktop GUI (Qt) |
| Flask / FastAPI | Web backends (FastAPI recommended for async) |
| uvicorn | ASGI server for FastAPI/Starlette |
| Jinja2 | Templating (if using Flask) |
| python-socketio | Real-time updates to web UI |
| Vue.js / React (not pip) | Frontend framework (static build) |
| flask-socketio | Flask WebSocket |
| flask-cors | Cross-origin requests handling |

### 10. Cloud & remote

| Package | Description |
|---------|-------------|
| boto3 | AWS S3 upload/download |
| google-cloud-storage | GCS integration |
| dropbox | Dropbox API |
| webdavclient3 | WebDAV client (Nextcloud/ownCloud) |
| python-telegram-bot | Telegram bot interface |
| smtplib (stdlib) | Email notifications |
| imbox / imapclient | IMAP for fetching attachments |
| paramiko | SSH/SFTP for remote seedbox management |

### 11. Security & privacy

| Package | Description |
|---------|-------------|
| cryptography | Encrypt/decrypt files, keys |
| keyring | Store passwords in OS keychain |
| bcrypt | Password hashing |
| pyOpenSSL | TLS certs |
| clamd | ClamAV virus scanning integration |

### 12. Developer & testing

| Package | Description |
|---------|-------------|
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| black | Code formatter |
| flake8 | Linter |
| mypy | Type checking |
| pre-commit | Git hooks |
| docker (Python SDK) | Container builds |

## Quick installs

```bash
# Core + Download + Media
pip install aiohttp httpx aiofiles yt-dlp python-libtorrent ffmpeg-python \
            mutagen Pillow patool py7zr rarfile subliminal pysubs2 \
            sqlalchemy apscheduler watchdog feedparser beautifulsoup4 lxml \
            duckduckgo-search fastapi uvicorn python-socketio Flask-SocketIO \
            cryptography keyring boto3 dropbox python-telegram-bot paramiko

# Desktop GUI (optional, pick one)
pip install PySide6
# OR
# pip install PyQt6

# Web UI dev (optional)
pip install jinja2
```

## Raspberry Pi / TankOS add-ons

```bash
# Codecs FFmpeg may need on a Pi
sudo apt install libmp3lame-dev libx264-dev libx265-dev libvpx-dev \
                 libfdk-aac-dev libopus-dev libvorbis-dev libass-dev

# Hardware acceleration (H.265 hw decode on Pi 5)
sudo apt install ffmpeg rpi-eeprom
```

## How this maps to the host-level CLIs

The Simple Internet host-level CLIs in `scripts/download_*.py` -
- Round 1: `download_{music,video,data,torrent,scheduled,deepweb}.py` covering F717-F916
- Round 2: `download_{music,video,data,torrent,scheduled,deepweb,images,software,ebooks,misc}_2.py` covering F917-F1116
- Round 3: `download_{cloud,ai,power,community}_3.py` covering F1117-F1166

- intentionally stub the heavy lifting. Each `cmd_<sub>` handler returns synthetic JSON and persists a record under `tank_ws/data/<prefix>/`. A real implementation would call into a downloader service backed by the libraries listed in sections 1-11 above. See `docs/SIMPLE_INTERNET_ARCH.md` for the module-by-module architecture.
