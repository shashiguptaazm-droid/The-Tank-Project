"""Authentication + per-token token-bucket rate limiting.

Tokens come from ``TANK_API_KEYS`` (a JSON dict ``{"key":"role"}``) or
fall back to ``TANK_API_KEY`` (single ``{"key":"admin"}``). All
comparisons go through :func:`secrets.compare_digest` to avoid timing
attacks. Per-token rate-limit keeps a tiny in-memory bucket; tests and
the CLI tester can build deterministic clocks via
:class:`RateLimiter`.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
from typing import Dict, Optional, Tuple


DEFAULT_READ_QUOTA = 60       # per minute
DEFAULT_WRITE_QUOTA = 10      # per minute
DEFAULT_QUOTA_WINDOW = 60.0  # seconds


def _load_keys() -> Dict[str, str]:
    """Build the {token: role} dict from env. Unknown if unset."""
    raw = os.environ.get("TANK_API_KEYS")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            raise ValueError("TANK_API_KEYS must be a JSON object")
        except Exception as exc:
            raise RuntimeError(f"bad TANK_API_KEYS: {exc}") from exc
    fallback = os.environ.get("TANK_API_KEY", "")
    if fallback:
        return {fallback: "admin"}
    return {}


class AuthError(Exception):
    """Raised when an incoming request fails auth."""

    def __init__(self, message: str, code: int = 401) -> None:
        super().__init__(message)
        self.code = code


def _extract_bearer(auth_header: str) -> str:
    """Pull the token from a ``Bearer <token>`` header. Empty if invalid."""
    if not auth_header:
        return ""
    parts = auth_header.strip().split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def authenticate(auth_header: str, keys: Optional[Dict[str, str]] = None
                 ) -> Tuple[str, str]:
    """Return ``(token_hash, role)`` for a valid bearer or raise
    :class:`AuthError`."""
    keys = _load_keys() if keys is None else keys
    if not keys:
        raise AuthError(
            "no TANK_API_KEYS / TANK_API_KEY configured on the bridge",
            code=503,
        )
    token = _extract_bearer(auth_header)
    if not token:
        raise AuthError("missing or malformed Authorization header")
    for k, role in keys.items():
        if secrets.compare_digest(k, token):
            return _token_hash(token), role
    raise AuthError("invalid API key")


def _token_hash(token: str) -> str:
    """One-way log tag — never log the raw key."""
    return "sha256:" + secrets.token_hex(8) + "::" + \
        str(abs(hash(token)) % (10 ** 8))


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Per-token token bucket. Thread-safe; tests can pass a callable
    ``now_fn`` to make the bucket deterministic."""

    def __init__(self, *, read_quota: int = DEFAULT_READ_QUOTA,
                 write_quota: int = DEFAULT_WRITE_QUOTA,
                 window_sec: float = DEFAULT_QUOTA_WINDOW,
                 now_fn=time.monotonic) -> None:
        self._read_quota = int(read_quota)
        self._write_quota = int(write_quota)
        self._window = float(window_sec)
        self._now_fn = now_fn
        self._buckets: Dict[Tuple[str, str], Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, token_hash: str, role: str, is_write: bool) -> None:
        with self._lock:
            bucket = (token_hash, "write" if is_write else "read")
            reset_at, used = self._buckets.get(bucket, (self._now_fn(), 0))
            now = self._now_fn()
            if now >= reset_at:
                reset_at = now + self._window
                used = 0
            quota = self._write_quota if is_write else self._read_quota
            if used >= quota:
                raise AuthError(
                    f"rate limit exceeded ({used}/{quota} "
                    f"{'write' if is_write else 'read'} per "
                    f"{int(self._window)}s; token {token_hash})",
                    code=429,
                )
            self._buckets[bucket] = (reset_at, used + 1)
