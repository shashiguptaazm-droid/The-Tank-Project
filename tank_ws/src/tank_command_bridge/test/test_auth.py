"""Tests for tank_command_bridge.auth.

Covers:
* missing/malformed Authorization header (401)
* invalid token (401)
* valid token + role
* write-class rate-limit triggers 429 after the quota is hit
"""
from __future__ import annotations

import os
import pytest

from tank_command_bridge.auth import (
    AuthError,
    RateLimiter,
    _load_keys,
    authenticate,
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    # Use a deterministic key set per test.
    monkeypatch.setenv("TANK_API_KEYS", '{"goodkey":"admin","reader":"guest"}')
    monkeypatch.delenv("TANK_API_KEY", raising=False)
    yield


def test_auth_missing_header_returns_401():
    with pytest.raises(AuthError) as exc:
        authenticate("")
    assert exc.value.code == 401


def test_auth_invalid_token_returns_401():
    with pytest.raises(AuthError) as exc:
        authenticate("Bearer not-a-real-key")
    assert exc.value.code == 401


def test_auth_valid_returns_token_hash_and_role():
    h, role = authenticate("Bearer goodkey")
    assert role == "admin"
    assert h.startswith("sha256:")
    h2, role2 = authenticate("Bearer reader")
    assert role2 == "guest"


def test_rate_limit_writes_throttle_after_quota():
    now_values = iter([0.0 + i * 0.001 for i in range(15)])
    rl = RateLimiter(write_quota=3, window_sec=60.0,
                      now_fn=lambda: next(now_values))
    h, _ = authenticate("Bearer goodkey")
    rl.check(h, "admin", is_write=True)
    rl.check(h, "admin", is_write=True)
    rl.check(h, "admin", is_write=True)
    with pytest.raises(AuthError) as exc:
        rl.check(h, "admin", is_write=True)
    assert exc.value.code == 429


def test_load_keys_fallback_to_single_env(monkeypatch):
    monkeypatch.delenv("TANK_API_KEYS", raising=False)
    monkeypatch.setenv("TANK_API_KEY", "singlekey")
    keys = _load_keys()
    assert keys == {"singlekey": "admin"}


def test_load_keys_returns_empty_dict_when_unset(monkeypatch):
    monkeypatch.delenv("TANK_API_KEYS", raising=False)
    monkeypatch.delenv("TANK_API_KEY", raising=False)
    assert _load_keys() == {}
