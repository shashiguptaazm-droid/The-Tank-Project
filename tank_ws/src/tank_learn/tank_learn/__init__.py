"""``tank_learn`` — The Tank OS feedback loop + online learning (Phase 1).

This is the persistence layer that turns ``/intent_command`` dispatches
into (intent_text, plugin_name, confidence, reward) tuples, then feeds
those tuples into:

* :mod:`tank_iq`     — per-feature IQ scoring (Phase 2).
* :mod:`tank_os`     — global autonomy tier L0–L5 (Phase 3).
* nightly retraining of intent_router grammar weights (Phase 4).

Public surface
~~~~~~~~~~~~~~
* :class:`tank_learn.feedback_store.FeedbackStore`  — pure-Python SQLite-WAL store.
* :class:`tank_learn.feedback_node.FeedbackNode`   — ROS 2 bridge for /intent_command
  + /os/feedback + /os/iq_state.  Optional — install only needs the
  store for CI benches.

Storage layout
~~~~~~~~~~~~~~
* Default DB: ``<workspace>/tank_ws/data/os_memory.db`` (WAL mode).
* Tables:
  - ``feedback_log``           — every dispatch + reward (one row per event).
  - ``intent_grammar_weights`` — per-cid weight that drives intent_router.
  - ``iq_history``             — per-plugin IQ samples over time.

Thread safety
~~~~~~~~~~~~
The store is fully thread-safe (``threading.Lock``) and uses one
short-lived SQLite connection per call.  Mixed callers from the ROS
node pool + dashboard uvicorn pool are safe.
"""
from __future__ import annotations

from .feedback_store import (
    DEFAULT_DB_PATH,
    FeedbackRow,
    FeedbackStore,
)
from .memory_store import (
    MemoryStore,
    DEFAULT_DB_PATH as MEMORY_DEFAULT_DB_PATH,
    Episode,
    SemanticFact,
    Skill,
    FactEdge,
    ConsolidationRecord,
)

__all__ = [
    "FeedbackStore", "FeedbackRow", "DEFAULT_DB_PATH",
    "MemoryStore", "MEMORY_DEFAULT_DB_PATH",
    "Episode", "SemanticFact", "Skill", "FactEdge",
    "ConsolidationRecord",
]
