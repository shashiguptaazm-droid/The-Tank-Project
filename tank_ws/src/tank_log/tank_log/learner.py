"""Periodic *learner* — takes the topic_logs stream and emits rollup
summaries plus simple anomaly alerts.

Design
------
We don't try to be clever. The learner:

1.  Every ``window_sec`` seconds (default 60), counts how many messages
    per topic landed in the last window.
2.  Picks the busiest topic and persists a row in ``topic_summary``.
3.  Reports simple anomaly patterns (priority-ordered, safety first):

    * ``estop_stuck``                       — /estop True has persisted for >= 30 s
                                               (always wins — it's a safety lock).
    * ``dock_charging_but_health_not_ok``   — /dock/charge_cmd True near a /health/ok False
                                               (charging despite BMS warning).
    * ``wake_no_intent``                    — wake fired but no /intent_text within 5 s
                                               (UX hiccup — last in priority order).

Locking
-------
No ``Learner._lock``. We rely on the per-store ``LogStore._lock`` for
atomicity over sqlite — there is no outer mutex that could nest inside
the store's lock and produce an inversion.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from .log_store import LogStore


# Default thresholds — all settable via constructor.
DEFAULT_WINDOW_SEC     = 60.0
DEFAULT_LOOKBACK_SEC   = 60.0
WAKE_NO_INTENT_SEC     = 5.0
DOCK_HEALTH_WINDOW_SEC = 5.0
ESTOP_STUCK_SEC        = 30.0
# Lookback for stuck-state window checks — must be >= ESTOP_STUCK_SEC so a
# continuous pulse can be observed end-to-end.
ESTOP_STUCK_LOOKBACK_SEC = 120.0


def _is_truthy(payload: str) -> bool:
    return (payload or "").strip().lower() in ("true", "1")


class Learner:
    """Pure-Python periodic learner. No ROS dependency."""

    def __init__(self, store: LogStore,
                 window_sec: float = DEFAULT_WINDOW_SEC,
                 lookback_sec: float = DEFAULT_LOOKBACK_SEC) -> None:
        self._store = store
        self._window = float(window_sec)
        self._lookback = float(lookback_sec)
        # No mutex — single dict, write-then-publish. ingest callers are
        # serial; downstream tolerates a stale read for one tick.
        self._last_run_ts: float = 0.0
        self._last_summary: Dict = {}

    def tick(self) -> Dict:
        """Run one learner pass; return the summary payload that was persisted."""
        now = time.time()
        counts = self._store.counts_per_topic(since_sec=self._lookback)
        anomaly = self._detect_anomaly(now)
        top_topic = max(counts, key=counts.get) if counts else "(none)"
        top_count = counts.get(top_topic, 0)
        summary_id = self._store.record_summary(
            ts=now, window_sec=self._window,
            top_topic=top_topic, top_count=top_count,
            anomaly=anomaly, counts=counts,
        )
        self._last_run_ts = now
        self._last_summary = {
            "id":         summary_id,
            "ts":         now,
            "window_sec": self._window,
            "top_topic":  top_topic,
            "top_count":  top_count,
            "anomaly":    anomaly,
            "counts":     counts,
        }
        return self._last_summary

    # ---------------- anomaly rules (priority order) -----------------
    def _detect_anomaly(self, now: float) -> Optional[str]:
        if self._check_estop_stuck():
            return "estop_stuck"
        if self._check_dock_health_mismatch():
            return "dock_charging_but_health_not_ok"
        if self._check_wake_no_intent(now):
            return "wake_no_intent"
        return None

    def _check_estop_stuck(self) -> bool:
        """True if /estop has been True continuously for >= ESTOP_STUCK_SEC.

        Uses a *time-window* query (topic_rows_since) NOT a row-limit query,
        so high-rate publishers (>=2 Hz) don't compress the apparent span
        and silently disable the rule.
        """
        rows = self._store.topic_rows_since("/estop", ESTOP_STUCK_LOOKBACK_SEC)
        if not rows:
            return False
        if not _is_truthy(rows[0].payload):
            return False
        if (rows[0].ts - rows[-1].ts) < ESTOP_STUCK_SEC:
            return False
        return all(_is_truthy(r.payload) for r in rows)

    def _check_dock_health_mismatch(self) -> bool:
        dock_rows = self._store.topic_rows_since("/dock/charge_cmd",
                                                 DOCK_HEALTH_WINDOW_SEC * 2)
        if not dock_rows or not _is_truthy(dock_rows[0].payload):
            return False
        health_rows = self._store.topic_rows_since("/health/ok",
                                                    DOCK_HEALTH_WINDOW_SEC * 2)
        for h in health_rows:
            if abs(h.ts - dock_rows[0].ts) < DOCK_HEALTH_WINDOW_SEC \
                    and not _is_truthy(h.payload):
                return True
        return False

    def _check_wake_no_intent(self, now: float) -> bool:
        wake_rows = self._store.topic_rows_since("/wake_detected",
                                                  WAKE_NO_INTENT_SEC)
        recent_wake = [r for r in wake_rows if _is_truthy(r.payload)]
        if not recent_wake:
            return False
        intent_rows = self._store.topic_rows_since("/intent_text",
                                                    WAKE_NO_INTENT_SEC * 4)
        if not intent_rows:
            return True
        for w in recent_wake:
            for ir in intent_rows:
                if w.ts <= ir.ts <= w.ts + WAKE_NO_INTENT_SEC:
                    return False
        return True

    @property
    def last_summary(self) -> Dict:
        return dict(self._last_summary)
