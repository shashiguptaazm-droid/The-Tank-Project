"""Smoke tests for the evolution system (Phase 4 minimal).

Verifies:
- All evolution modules import without error.
- KeyRegistry resolves in the documented order (project_env > systemd env).
- All 14 providers register correctly.
- RotationOrchestrator retries on failure.
- Programming errors (KeyError) propagate; only httpx.HTTPError is caught.

Network-free: all provider calls are mocked.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# httpx is only required by tests that exercise the orchestrator's
# HTTP-error retry path. Other tests (registry, breaker, token bucket,
# provider registry) run without it. Tests that need it call
# ``pytest.importorskip("httpx")`` inline so the rest of the file
# stays runnable in lean environments.
httpx = None  # populated lazily by tests that need it


# ── Path setup (same as the other test file) ──────────────────────────────
_HERE = Path(__file__).resolve()
_SRC_PARENT = _HERE.parents[2]    # tank_ws/src/
if str(_SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(_SRC_PARENT))


# ── 1. Import sanity ─────────────────────────────────────────────────────

def test_evolution_package_imports():
    """Every public symbol in evolution/__init__.py is importable."""
    from tank_assistant import evolution
    expected = [
        "KeyRegistry", "key_registry", "get_key",
        "CircuitBreaker", "TokenBucket", "HealthMonitor",
        "health_monitor", "CircuitState",
        "BaseHttpProvider", "OpenAIMixin", "CustomJsonMixin",
        "OpenAIProvider", "AnthropicProvider", "FreebuffProvider",
        "OpenRouterProvider", "GroqProvider", "GeminiProvider",
        "MistralProvider", "CloudflareProvider", "CerebrasProvider",
        "CohereProvider", "ReplicateProvider", "HuggingFaceProvider",
        "EndpointAIProvider", "DeepSeekProvider",
        "register_provider", "all_providers", "get_provider_class",
        "BaseOrchestrator", "OrchestratorResult",
        "RotationOrchestrator",
    ]
    for name in expected:
        assert hasattr(evolution, name), f"missing public symbol: {name}"


# ── 2. KeyRegistry chain-of-trust ────────────────────────────────────────

def test_key_registry_resolves_in_chain_order(tmp_path, monkeypatch):
    """Project .env > systemd env > os.environ.

    With no system keys available, ``key_registry.get()`` should fall
    through to the project .env.
    """
    from tank_assistant.evolution import KeyRegistry, key_registry, parse_dotenv_text

    # Parse sanity check.
    parsed = parse_dotenv_text(
        'FOO="bar"\n# comment\nBAZ = qux\nexport X=1\n')
    assert parsed == {"FOO": "bar", "BAZ": "qux", "X": "1"}

    # Create a tmp .env file and register it with a fresh registry.
    env_file = tmp_path / "test.env"
    env_file.write_text("PROJECT_TEST_KEY=project_value\n")

    reg = KeyRegistry(
        project_env=env_file,
        systemd_env_files=[],   # disable edulabs env for the test
    )
    # Make sure os.environ doesn't have it.
    monkeypatch.delenv("PROJECT_TEST_KEY", raising=False)
    assert reg.get("PROJECT_TEST_KEY") == "project_value"
    # Stats reflect project_env hits.
    stats = reg.stats()
    assert stats["by_backend"]["project_env"] >= 1


def test_key_registry_falls_back_to_os_environ(monkeypatch):
    """When .env and systemd env don't have the key, os.environ wins."""
    from tank_assistant.evolution import KeyRegistry
    reg = KeyRegistry(
        project_env=Path("/nonexistent/.env"),
        systemd_env_files=[],
    )
    monkeypatch.setenv("FROM_OS_ENVIRON", "yes")
    assert reg.get("FROM_OS_ENVIRON") == "yes"


def test_key_registry_returns_default_when_missing(monkeypatch):
    from tank_assistant.evolution import KeyRegistry
    reg = KeyRegistry(
        project_env=Path("/nonexistent/.env"),
        systemd_env_files=[],
    )
    monkeypatch.delenv("DEFINITELY_NOT_THERE", raising=False)
    assert reg.get("DEFINITELY_NOT_THERE") is None
    assert reg.get("DEFINITELY_NOT_THERE", "fallback") == "fallback"


def test_key_registry_never_leaks_values_in_repr():
    """``__repr__`` must not expose any actual key values."""
    from tank_assistant.evolution import key_registry
    r = repr(key_registry)
    assert "sk-" not in r
    assert "gsk-" not in r
    assert "secret" not in r.lower()


# ── 3. Provider registry ─────────────────────────────────────────────────

def test_all_14_providers_registered():
    """Every expected provider name appears in the registry."""
    from tank_assistant.evolution import PROVIDERS, all_providers
    expected_names = {
        "openai", "anthropic", "freebuff",
        "openrouter", "groq", "gemini", "mistral",
        "cloudflare", "cerebras", "cohere",
        "replicate", "huggingface", "endpointai", "deepseek",
    }
    registered = set(PROVIDERS.keys())
    missing = expected_names - registered
    assert not missing, f"missing providers: {missing}"
    assert len(PROVIDERS) >= 14, (
        f"expected ≥14 providers, got {len(PROVIDERS)}")


def test_provider_classes_have_key_names():
    from tank_assistant.evolution import PROVIDERS
    for name, (cls, key_name) in PROVIDERS.items():
        assert key_name, f"{name} has no KEY_NAME"
        assert cls.KEY_NAME == key_name, (
            f"{name}: registry KEY_NAME {key_name!r} != class KEY_NAME {cls.KEY_NAME!r}")


def test_get_provider_class_returns_class_or_none():
    from tank_assistant.evolution import get_provider_class
    assert get_provider_class("groq") is not None
    assert get_provider_class("does_not_exist") is None


# ── 4. RotationOrchestrator retries on failure ──────────────────────────

def _make_mock_provider(name, *, fail_with=None, reply_text="OK"):
    """Build a BaseHttpProvider-shaped mock."""
    p = mock.Mock()
    p.name = name
    p.is_configured = True
    if fail_with is not None:
        p.prompt.side_effect = fail_with
    else:
        p.prompt.return_value = {"text": reply_text, "tool_calls": []}
    return p


def _require_httpx():
    """Helper — skip the calling test if httpx isn't installed."""
    return pytest.importorskip("httpx")


def test_rotation_retries_then_succeeds():
    """First provider throws an ``httpx.HTTPError`` → orchestrator records
    failure → second succeeds. The new ``_call_provider`` only catches
    ``httpx.HTTPError`` (transient), so we use that exception type here.
    """
    from tank_assistant.evolution import RotationOrchestrator
    from tank_assistant.evolution.health import health_monitor

    httpx = _require_httpx()
    p1 = _make_mock_provider(
        "groq", fail_with=httpx.HTTPError("HTTP 429 (rate limit)"))
    p2 = _make_mock_provider("cerebras", reply_text="the answer")
    orch = RotationOrchestrator(providers=[p1, p2], max_attempts=3)
    # Reset breaker state for both.
    health_monitor.record_success("groq")   # reset to HEALTHY
    health_monitor.record_success("cerebras")

    result = orch.run("system", "user")
    assert result.error is None, f"unexpected error: {result.error}"
    assert result.text == "the answer"
    assert "cerebras" in result.providers_used
    assert p1.prompt.call_count == 1
    assert p2.prompt.call_count == 1


def test_rotation_returns_error_when_all_fail():
    from tank_assistant.evolution import RotationOrchestrator
    from tank_assistant.evolution.health import health_monitor

    httpx = _require_httpx()
    p1 = _make_mock_provider(
        "groq", fail_with=httpx.HTTPError("HTTP 429 (rate limit)"))
    p2 = _make_mock_provider(
        "cerebras", fail_with=httpx.HTTPError("HTTP 500 (server error)"))
    orch = RotationOrchestrator(providers=[p1, p2], max_attempts=2)
    health_monitor.record_success("groq")
    health_monitor.record_success("cerebras")

    result = orch.run("system", "user")
    assert result.error is not None
    assert "all providers failed" in result.error or "HTTP" in result.error


def test_rotation_respects_max_attempts():
    """With max_attempts=1, only the first provider is tried even if more exist."""
    from tank_assistant.evolution import RotationOrchestrator
    from tank_assistant.evolution.health import health_monitor

    httpx = _require_httpx()
    p1 = _make_mock_provider(
        "groq", fail_with=httpx.HTTPError("HTTP 429 (rate limit)"))
    p2 = _make_mock_provider("cerebras", reply_text="never called")
    orch = RotationOrchestrator(providers=[p1, p2], max_attempts=1)
    health_monitor.record_success("groq")
    health_monitor.record_success("cerebras")

    result = orch.run("system", "user")
    assert result.error is not None
    assert p2.prompt.call_count == 0, (
        "max_attempts=1 must NOT call p2 after p1 fails")


def test_call_provider_re_raises_non_http_errors():
    """Programming errors (KeyError) must propagate, not be swallowed."""
    from tank_assistant.evolution.orchestrators.base import BaseOrchestrator

    orch = BaseOrchestrator()
    p = _make_mock_provider("groq", fail_with=KeyError("provider bug"))
    with pytest.raises(KeyError):
        orch._call_provider(p, "system", "user", None, None, "auto")

    # httpx.HTTPError is the transient exception class — must be caught
    # and returned as a result with error set, not re-raised.
    httpx = _require_httpx()
    p2 = _make_mock_provider(
        "cerebras", fail_with=httpx.HTTPError("transient"))
    result = orch._call_provider(p2, "system", "user", None, None, "auto")
    assert result.error is not None
    assert "http" in result.error.lower()


# ── 5. Circuit breaker state transitions ─────────────────────────────────

def test_circuit_breaker_degrades_then_dead():
    from tank_assistant.evolution import CircuitBreaker, CircuitState
    cb = CircuitBreaker(name="t", failure_threshold=3, failure_window_s=60)
    # 1st failure: HEALTHY → DEGRADED.
    cb.record_failure(now=100.0)
    assert cb.state == CircuitState.DEGRADED
    # 2 more failures: → DEAD.
    cb.record_failure(now=101.0)
    cb.record_failure(now=102.0)
    assert cb.state == CircuitState.DEAD
    # Cooldown respected.
    assert cb.can_attempt(now=102.0 + 60) is False
    assert cb.can_attempt(now=102.0 + 600) is True


def test_token_bucket_consumes_and_refills():
    from tank_assistant.evolution import TokenBucket
    b = TokenBucket(capacity=2, refill_per_s=2)
    assert b.acquire() is True
    assert b.acquire() is True
    assert b.acquire() is False    # empty
    # Refill after 1 second.
    import time as _t
    b.last_refill_ts = _t.monotonic() - 1.0
    assert b.acquire() is True
