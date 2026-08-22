"""Rclone transport for the offload daemon.

Wraps ``rclone copy`` so the rest of the package can think in terms
of "upload this file" rather than spawning a subprocess. Responsibilities:

1. **Atomic staging.** Configurable staging directory (default
   ``/var/tank/offload_staging``). Source file is :func:`shutil.move`'d
   into staging under a UUID-suffixed name, so if the daemon dies mid-
   transfer the next sweep can retry without losing the source.
2. **rclone invocation.** Calls ``rclone copy`` with ``--bwlimit``,
   ``--retries 0`` (we do our own retry counting), and the configured
   remote. Output is captured; only ``sha256(token)[:16]`` is logged.
3. **Client-side encryption.** Optional. When the
   :class:`RcloneConfig.crypt_remote` is set, copies target the crypt
   remote, which wraps an unencrypted subfolder on the WebDAV side.
4. **Exponential backoff.** ``retry_delay = min(30 * (2 ** retry_count),
   600)`` seconds. Capped at 6 retries before dead-letter.
5. **Dead-letter.** When retries are exhausted, the staged file is
   :func:`shutil.move`'d into ``/var/tank/offload_deadletter`` and the
   store row is moved to ``STATUS_DEAD_LETTER``.

We never log a raw Nextcloud password; only ``sha256(pw)[:16]`` is
written to logs (per STATUS.md design rule on redacting credentials
in operator-facing output).
"""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_LOG = logging.getLogger("tank_offload.rclone_facade")


DEFAULT_STAGING_DIR = "/var/tank/offload_staging"
DEFAULT_DEADLETTER_DIR = "/var/tank/offload_deadletter"
DEFAULT_REMOTE_ROOT = "tankcrypt:files"
DEFAULT_BWLIMIT = "5M"
MAX_RETRIES = 6
RETRY_BASE_SEC = 30.0
RETRY_CAP_SEC = 600.0
RCLONE_TIMEOUT_SEC = 1800.0   # 30 min per single rclone call


@dataclass
class RcloneConfig:
    """Connection + transport settings.

    Required: ``nextcloud_url``, ``nextcloud_user``, ``nextcloud_password``.
    Optional: ``crypt_remote_name`` (e.g. ``tankcrypt``) to enable
    client-side encryption through an rclone crypt overlay.
    """

    nextcloud_url: str = ""       # e.g. https://<vps_ip>/remote.php/dav/files/alice
    nextcloud_user: str = ""
    nextcloud_password: str = ""
    remote_root: str = DEFAULT_REMOTE_ROOT
    bwlimit: str = DEFAULT_BWLIMIT
    staging_dir: str = DEFAULT_STAGING_DIR
    deadletter_dir: str = DEFAULT_DEADLETTER_DIR
    crypt_remote_name: str = ""   # empty → no client-side encryption
    extra_args: List[str] = field(default_factory=list)

    def is_credentialed(self) -> bool:
        return (bool(self.nextcloud_url)
                and bool(self.nextcloud_user)
                and bool(self.nextcloud_password))

    def redact(self) -> Dict[str, str]:
        """Build the dict seen by loggers / dashboards. Never plaintext."""
        return {
            "nextcloud_url": self.nextcloud_url,
            "nextcloud_user_hash": _hash_secret(self.nextcloud_user),
            "nextcloud_password_hash": _hash_secret(self.nextcloud_password),
            "remote_root": self.remote_root,
            "bwlimit": self.bwlimit,
            "crypt_remote_name": self.crypt_remote_name,
            "extra_args_count": len(self.extra_args),
        }


@dataclass
class RcloneResult:
    """Per-call summary. ``ok=True`` means the rclone copy returned 0."""

    ok: bool
    returncode: int
    elapsed_sec: float
    stdout_tail: str
    stderr_tail: str
    staged_path: str = ""
    remote_path: str = ""
    error: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def _hash_secret(s: str) -> str:
    """One-way log tag \u2014 STATUS-style credential redaction."""
    if not s:
        return ""
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _ensure_dir(d: str) -> None:
    os.makedirs(d, exist_ok=True)


def rclone_env(config: RcloneConfig) -> Dict[str, str]:
    """Build the environment we'll pass to :func:`subprocess.run`.

    Setting ``RCLONE_CONFIG_*`` overrides is intentionally preferred
    over writing a real ``rclone.conf`` on disk \u2014 the password does not
    end up persisted anywhere by this daemon.
    """
    env = dict(os.environ)
    if config.is_credentialed():
        env["RCLONE_CONFIG"] = "=/dev/null"   # disable on-disk config
        env["RCLONE_CONFIG_NEXTCLOUD_TYPE"] = "webdav"
        env["RCLONE_CONFIG_NEXTCLOUD_URL"] = config.nextcloud_url
        env["RCLONE_CONFIG_NEXTCLOUD_VENDOR"] = "nextcloud"
        env["RCLONE_CONFIG_NEXTCLOUD_USER"] = config.nextcloud_user
        env["RCLONE_CONFIG_NEXTCLOUD_PASS"] = config.nextcloud_password
    return env


def build_copy_cmd(config: RcloneConfig, source: str, dest: str) -> List[str]:
    """Compose the rclone copy command line. Used both for real copy
    and for the dry-run path so reviewers can diff the two easily."""
    target_remote = config.remote_root
    if config.crypt_remote_name:
        target_remote = f"{config.crypt_remote_name}:tank"
    cmd = [
        "rclone", "copy",
        "--retries", "0",   # we do our own retry counting
        "--bwlimit", config.bwlimit,
        "--stats-one-line",
        "--stats", "5s",
        "--no-check-certificate",  # VPS uses self-signed in dev
        source,
        f"{target_remote}/{dest.lstrip('/')}",
    ]
    cmd.extend(config.extra_args)
    return cmd


@dataclass
class _Stage:
    staged_path: str
    remote_path: str


class RcloneFacade:
    """Transport wrapper. Mostly stateless except for the directories."""

    def __init__(self, config: RcloneConfig) -> None:
        self.config = config
        _ensure_dir(self.config.staging_dir)
        _ensure_dir(self.config.deadletter_dir)

    # ----- staging -----
    def stage(self, original: str, item_uuid: str) -> _Stage:
        """Move ``original`` into the staging dir under a UUID name.

        Returns the staged absolute path + remote-relative path. If
        ``staged_path`` already exists for an earlier attempt, it's
        reused (we don't double-copy what we already moved).
        """
        base = os.path.basename(original)
        staged = os.path.join(self.config.staging_dir,
                              f"{item_uuid}__{base}")
        if not os.path.isfile(staged):
            try:
                shutil.move(original, staged)
            except OSError as exc:
                _LOG.warning("stage move failed: %s -> %s (%s)",
                              original, staged, exc)
                raise
        remote_path = f"by-uuid/{item_uuid}__{base}"
        return _Stage(staged_path=staged, remote_path=remote_path)

    def unstage(self, staged_path: str) -> None:
        """Best-effort delete of the staged copy after successful upload."""
        try:
            os.remove(staged_path)
        except OSError as exc:
            _LOG.warning("unstage delete failed: %s (%s)",
                          staged_path, exc)

    def deadletter(self, staged_path: str, item_uuid: str) -> str:
        """Move the staged file into the dead-letter dir. Returns new path."""
        base = os.path.basename(staged_path)
        target = os.path.join(self.config.deadletter_dir,
                               f"{item_uuid}__{base}")
        try:
            shutil.move(staged_path, target)
        except OSError:
            # If move failed (cross-mount), fallback to copy+remove.
            shutil.copy2(staged_path, target)
            try:
                os.remove(staged_path)
            except OSError:
                pass
        return target

    # ----- retry orchestration -----
    def compute_retry_delay(self, retry_count: int) -> float:
        """Exponential backoff with cap \u2014 mirrors the blueprint."""
        return min(RETRY_BASE_SEC * (2 ** max(0, int(retry_count))),
                    RETRY_CAP_SEC)

    @staticmethod
    def exhausted(retry_count: int) -> bool:
        return int(retry_count) >= MAX_RETRIES

    # ----- the actual copy -----
    def copy_once(self, staged_path: str, remote_path: str) -> RcloneResult:
        """Single shot \u2014 no internal retries. The caller decides."""
        cmd = build_copy_cmd(self.config, staged_path, remote_path)
        env = rclone_env(self.config)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, env=env,
                capture_output=True, text=True,
                timeout=RCLONE_TIMEOUT_SEC,
                check=False,
            )
            elapsed = time.monotonic() - start
            return RcloneResult(
                ok=(proc.returncode == 0),
                returncode=proc.returncode,
                elapsed_sec=elapsed,
                stdout_tail=(proc.stdout or "")[-400:],
                stderr_tail=(proc.stderr or "")[-400:],
                staged_path=staged_path,
                remote_path=remote_path,
                error="" if proc.returncode == 0
                       else f"rclone exit {proc.returncode}",
            )
        except subprocess.TimeoutExpired as exc:
            return RcloneResult(
                ok=False, returncode=-1,
                elapsed_sec=time.monotonic() - start,
                stdout_tail="",
                stderr_tail="timeout",
                staged_path=staged_path,
                remote_path=remote_path,
                error=f"timeout after {RCLONE_TIMEOUT_SEC}s",
            )
        except FileNotFoundError as exc:
            return RcloneResult(
                ok=False, returncode=-1,
                elapsed_sec=time.monotonic() - start,
                stdout_tail="", stderr_tail="",
                staged_path=staged_path,
                remote_path=remote_path,
                error=f"rclone missing: {exc}",
            )

    def dry_run(self, original: str, item_uuid: str) -> Dict[str, Any]:
        """Show what *would* be transferred, without staging or copying."""
        cmd = build_copy_cmd(self.config, original,
                              f"by-uuid/{item_uuid}__{os.path.basename(original)}")
        return {
            "would_copy": original,
            "cmd": cmd,
            "remote_target": self.config.remote_root,
            "bwlimit": self.config.bwlimit,
            "credentialed": self.config.is_credentialed(),
        }
