"""tank_offload — overflow-storage daemon.

When the Pi's local ``/var/tank/`` fills past a configurable threshold
the daemon pushes cold files to a Nextcloud-backed VPS via
``rclone + WebDAV``. SQLite manifests every transfer; retries with
exponential backoff; dead-letters items that exceed the retry budget;
publishes ROS events for downstream consumers.

Exposes
-------
* :class:`OffloadStore` \u2014 WAL-mode SQLite manifest API.
* :class:`OffloadPolicy` \u2014 file selection / filtering.
* :class:`RcloneFacade` \u2014 subprocess wrapper + retry / staging.
* :class:`OffloadNode` \u2014 ROS 2 watcher + worker thread.
* FastAPI on port 8085 with bearer auth (mirror of ``tank_command_bridge``).
"""
from __future__ import annotations

from .offload_store import Item, ItemStatus, OffloadStore
from .policy import OffloadPolicy, PolicyConfig
from .rclone_facade import RcloneConfig, RcloneFacade, RcloneResult

__all__ = [
    "Item",
    "ItemStatus",
    "OffloadStore",
    "OffloadPolicy",
    "PolicyConfig",
    "RcloneConfig",
    "RcloneFacade",
    "RcloneResult",
]

__version__ = "0.1.0"
