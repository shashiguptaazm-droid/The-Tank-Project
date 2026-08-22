"""Provider health + circuit breaker + token bucket.

Used by :class:`RotationOrchestrator` (and the higher orchestrators) to
detect failures, demote providers temporarily, and recover them via
health-check pings.

Concepts
--------
- :class:`CircuitState` — ``HEALTHY`` / ``DEGRADED`` / ``DEAD``.
- :class:`CircuitBreaker` — per-provider state machine. Each ``record_*``
  call can transition the state per the documented rules. ``can_attempt``
  returns ``False`` when the breaker is ``DEAD`` and the cooldown has not
  elapsed.
- :class:`TokenBucket` — modest rate-limit heuristic. Each call to
  ``acquire()`` refills based on elapsed time; returns ``True`` if a
  token is available, decrements it, then ``False`` if exhausted.
- :class:`HealthMonitor` — registry of breakers keyed by provider name.
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Circuit breaker ───────────────────────────────────────────────────────

class CircuitState(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DEAD = "dead"


@dataclass
class CircuitBreaker:
    """Per-provider breaker. Failures transition toward DEAD; successes
    in DEGRADED or DEAD recover toward HEALTHY.

    Defaults: 3 strikes in 60s pushes to DEAD for 5 minutes;
    a single failure in HEALTHY pushes to DEGRADED for 30s.
    """
    name: str
    state: CircuitState = CircuitState.HEALTHY
    failures: int = 0
    successes: int = 0
    last_failure_ts: float = 0.0
    last_state_change_ts: float = field(default_factory=time.monotonic)
    degraded_cooldown_s: float = 30.0
    dead_cooldown_s: float = 300.0
    failure_threshold: int = 3
    failure_window_s: float = 60.0

    def can_attempt(self, now: Optional[float] = None) -> bool:
        """True if we should make a call right now."""
        now = now or time.monotonic()
        if self.state == CircuitState.HEALTHY:
            return True
        elapsed = now - self.last_state_change_ts
        if self.state == CircuitState.DEGRADED:
            return elapsed >= self.degraded_cooldown_s
        if self.state == CircuitState.DEAD:
            return elapsed >= self.dead_cooldown_s
        return True

    def record_success(self, now: Optional[float] = None) -> None:
        now = now or time.monotonic()
        self.successes += 1
        if self.state in (CircuitState.DEGRADED, CircuitState.DEAD):
            # Single success in DEAD recovers to DEGRADED.
            # Two consecutive successes in DEGRADED → HEALTHY.
            if (
                self.state == CircuitState.DEAD
                or self.successes >= 2
            ):
                self._transition(CircuitState.HEALTHY, now)
                self.failures = 0

    def record_failure(self, now: Optional[float] = None) -> None:
        now = now or time.monotonic()
        self.failures += 1
        self.last_failure_ts = now
        # Reset success streak.
        self.successes = 0
        if self.state == CircuitState.HEALTHY:
            # One failure → DEGRADED.
            self._transition(CircuitState.DEGRADED, now)
            return
        if self.state == CircuitState.DEGRADED:
            # 3 strikes (within window) → DEAD.
            if self.failures >= self.failure_threshold:
                self._transition(CircuitState.DEAD, now)
            return
        # Already DEAD — extend the cooldown.
        self.last_state_change_ts = now - self.dead_cooldown_s

    def _transition(self, new: CircuitState, now: float) -> None:
        self.state = new
        self.last_state_change_ts = now

    def snapshot(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "last_failure_age_s": (
                time.monotonic() - self.last_failure_ts
                if self.last_failure_ts else None),
            "age_in_state_s": (
                time.monotonic() - self.last_state_change_ts),
        }


# ── Token bucket ──────────────────────────────────────────────────────────

@dataclass
class TokenBucket:
    """Simple time-based bucket. Optional layer on top of the breaker."""
    capacity: float = 60.0           # burst size
    refill_per_s: float = 1.0        # sustained rate
    tokens: float = 60.0
    last_refill_ts: float = field(default_factory=time.monotonic)

    def acquire(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill_ts
        if elapsed > 0:
            self.tokens = min(
                self.capacity, self.tokens + elapsed * self.refill_per_s)
            self.last_refill_ts = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


# ── HealthMonitor — registry of per-provider breakers ─────────────────────

class HealthMonitor:
    """Singleton-ish. Maintains one :class:`CircuitBreaker` per provider
    name and exposes a single ``can_attempt(name)`` plus
    ``record_success/failure`` API for orchestrators.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._breakers: Dict[str, CircuitBreaker] = {}

    def breaker_for(self, name: str) -> CircuitBreaker:
        with self._lock:
            b = self._breakers.get(name)
            if b is None:
                b = CircuitBreaker(name=name)
                self._breakers[name] = b
            return b

    def can_attempt(self, name: str) -> bool:
        return self.breaker_for(name).can_attempt()

    def record_success(self, name: str) -> None:
        self.breaker_for(name).record_success()

    def record_failure(self, name: str) -> None:
        self.breaker_for(name).record_failure()

    def available_providers(self, names: List[str]) -> List[str]:
        """Return subset of ``names`` whose breakers permit an attempt now."""
        return [n for n in names if self.can_attempt(n)]

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            return {name: b.snapshot() for name, b in self._breakers.items()}


health_monitor = HealthMonitor()
