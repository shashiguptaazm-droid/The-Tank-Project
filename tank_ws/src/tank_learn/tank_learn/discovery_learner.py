"""tank_learn.discovery_learner — overnight AI-module discovery orchestrator.

Runs each source fetcher, applies the static capability rules, upserts
discoveries into :class:`DiscoveryStore`, and writes a single run-summary
row at the end. Failure budget is per-source so a hung PyPI scrape does NOT
block HuggingFace from being harvested.

Two layers of window gating:

1. **In-process clock guard.** Operators can run the CLI outside the
   03:00-08:00 window for testing / manual triggering by passing ``--force``.
   The window state (``window_open=False``) is still recorded in the
   summary so the dashboard knows the difference between "scheduled run"
   and "operator manual run".
2. **systemd timer** (see ``tank_learn/systemd/tank-learn-discovery.timer``)
   fires at 03:00 daily with 600-second jitter, invoking the CLI's
   ``run`` subcommand.

The orchestrator NEVER partial-leaves the DB: every run writes a summary
row, even if all sources failed.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .discovery_store import (
    DEFAULT_DB_PATH,
    DiscoveryStore,
    DiscoverySummary,
    ModuleRecord,
)
from ._sources import (
    extract_capabilities,
    fetch_pypi,
    fetch_hf,
    fetch_github,
    default_http_get,
)


# Window in local time (the VPS uses UTC for systemd, but the operator
# spec was 03:00-08:00 local — we use datetimetime.now() which picks up
# whatever the host thinks "local" is).
WINDOW_START_HOUR = 3     # inclusive
WINDOW_END_HOUR = 8       # exclusive (matches user spec "between 3 and 8")
DEFAULT_SLOW_TIMEOUT_S = 300.0  # bail any source after 5 minutes


def is_window_open(now: Optional[datetime] = None) -> bool:
    """True iff local hour is in ``[WINDOW_START_HOUR, WINDOW_END_HOUR)``."""
    n = now if now is not None else datetime.now()
    return WINDOW_START_HOUR <= n.hour < WINDOW_END_HOUR


def run_discovery(
    *,
    store: Optional[DiscoveryStore] = None,
    http_get: Callable[..., str] = default_http_get,
    since_days: int = 1,
    sources: Optional[List[str]] = None,
    force: bool = False,
    slow_timeout_s: float = DEFAULT_SLOW_TIMEOUT_S,
    clock: Callable[[], datetime] = datetime.now,
) -> DiscoverySummary:
    """Run a discovery sweep, upsert into the store, return + persist summary.

    Parameters
    ----------
    store        : DiscoveryStore — defaults to a fresh store at DEFAULT_DB_PATH.
    http_get     : injectable HTTP callable — tests pass a stub, production
                   uses ``urllib.request.urlopen``.
    since_days   : integer age filter; records newer than this are accepted.
                   ``0`` disables the filter.
    sources      : one or more of ``["pypi", "hf", "github"]``;
                   ``None`` runs all three.
    force        : bypass the 3-8 in-process clock guard. The summary still
                   records ``window_open=False``.
    slow_timeout : per-source wall-clock budget in seconds.
    clock        : injectable clock for tests; defaults to ``datetime.now``.
    """
    started = time.time()
    window_open = is_window_open(clock())
    if not window_open and not force:
        s = DiscoverySummary(
            started_ts=started, finished_ts=time.time(),
            new_modules=0, updated_modules=0, new_capabilities=0,
            sources_succeeded=[], sources_failed={},
            window_open=False,
        )
        if store is not None:
            store.write_summary(s)
        return s

    if store is None:
        store = DiscoveryStore()

    sources = sources or ["pypi", "hf", "github"]
    succeeded: List[str] = []
    failed: Dict[str, str] = {}
    new_mods = 0
    upd_mods = 0
    new_caps = 0

    fetchers: Dict[str, Callable[[], List[ModuleRecord]]] = {
        "pypi":   (lambda: fetch_pypi(http_get=http_get, since_days=since_days)),
        "hf":     (lambda: fetch_hf(http_get=http_get, since_days=since_days)),
        "github": (lambda: fetch_github(
            http_get=http_get, since_days=since_days)),
    }

    for source in sources:
        if source not in fetchers:
            failed[source] = "unknown_source"
            continue
        try:
            t0 = time.monotonic()
            records = fetchers[source]()
            elapsed = time.monotonic() - t0
            if elapsed > slow_timeout_s:
                failed[source] = f"source_slow:{elapsed:.1f}s"
                continue
        except Exception as exc:
            failed[source] = f"{type(exc).__name__}:{exc}"
            continue
        succeeded.append(source)
        for rec in records:
            # Belt-and-suspenders: rules dict might miss something; let
            # the source-specific pass through fill in capabilities.
            if not rec.capabilities:
                rec.capabilities = extract_capabilities(rec.name, rec.summary)
            try:
                was_new, _existed = store.upsert_module(rec)
                if was_new:
                    new_mods += 1
                else:
                    upd_mods += 1
            except Exception as exc:
                # Don't blow up the whole batch on one row failure.
                failed[source] = (
                    f"upsert_failed:{type(exc).__name__}:{exc}"
                )
                continue
            for cap in rec.capabilities:
                try:
                    if store.add_capability(rec.source, rec.name, cap):
                        new_caps += 1
                except Exception:
                    # Capability ledger is non-critical; skip on error.
                    pass

    finished = time.time()
    summary = DiscoverySummary(
        started_ts=started, finished_ts=finished,
        new_modules=new_mods, updated_modules=upd_mods,
        new_capabilities=new_caps,
        sources_succeeded=succeeded,
        sources_failed=failed,
        window_open=window_open,
    )
    store.write_summary(summary)
    return summary


__all__ = [
    "WINDOW_START_HOUR", "WINDOW_END_HOUR", "DEFAULT_SLOW_TIMEOUT_S",
    "is_window_open", "run_discovery",
]
