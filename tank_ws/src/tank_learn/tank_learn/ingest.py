"""tank_learn.ingest — bridge from DiscoveryStore to MemoryStore.

Consumes the overnight AI-module discoveries harvested by
:mod:`tank_learn.discovery_learner` and emits MEMORY entries so the
brain learns them:

  * one **episode** per new module (dedupe_key="discovery.<source>:<name>"
    so re-ingest is a no-op);
  * one **episode** per new capability (dedupe_key="discovery.capability:<cap>"
    by default — overlapping across sources is counted as separate
    episodic events but the *semantic* fact rolls them up);
  * one **semantic_fact** row per recurring capability token (the
    ingest promotes on the first sighting, then :mod:`consolidation`
    decides whether to deepen confidence);
  * one **skill** row per new ability with ``alpha=2``, ``beta=1`` so
    proficiency starts at ``0.667`` (rather than the floor) — once
    the AI uses it successfully, the Beta posterior pulls it toward 1.0.

Designed to be called by the consolidation routine OR the operator CLI.
``since_ts`` lets the caller ingest only newly-discovered rows since
the last sleep cycle.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .discovery_store import DiscoveryStore, ModuleRecord
from .memory_store import (
    CONFIDENCE_FLOOR, MemoryStore, SemanticFact, Skill,
)


@dataclass
class IngestResult:
    """Counts emitted by :func:`ingest_discovery_summary`."""
    episodes_added: int = 0
    facts_added: int = 0
    skills_added: int = 0
    modules_seen: int = 0
    capabilities_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episodes_added":    self.episodes_added,
            "facts_added":       self.facts_added,
            "skills_added":      self.skills_added,
            "modules_seen":      self.modules_seen,
            "capabilities_seen": self.capabilities_seen,
        }


# Initial proficiency for a freshly learned ABILITY = alpha/(alpha+beta)
# with alpha=2, beta=1 → 0.667 — "I have a strong prior but I haven't
# used it yet."  Once the AI actually invokes it, update_skill(success=True)
# pushes alpha → 3 and proficiency's mean shifts to 0.75.
_NEW_SKILL_ALPHA_PRIOR = 2
_NEW_SKILL_BETA_PRIOR = 1


def ingest_discovery_summary(
    mem: MemoryStore,
    discovery: DiscoveryStore,
    *,
    since_ts: Optional[float] = None,
    now_ts: Optional[float] = None,
    source_label: str = "discovery",
) -> IngestResult:
    """Pull new discoveries and convert them into episodic/semantic/procedural
    memory rows. Safe to call repeatedly: ``dedupe_key`` on episodes and
    the ``UNIQUE`` constraints on facts/skills make re-runs idempotent.
    """
    now = float(now_ts if now_ts is not None else time.time())
    result = IngestResult()

    # ── 1. Pull new (or all) module rows ──────────────────────────────────
    modules: List[Dict[str, Any]] = discovery.modules(
        since_ts=since_ts, limit=2000,
    )

    # ── 1a. Pre-fetch capabilities join ──────────────────────────────────
    # The DiscoveryStore ``model_registry`` table only carries source + name
    # + url + summary + timestamps. Per-module capabilities are in a
    # separate ``capability_ledger`` table keyed by (source, module_name).
    # We do one bulk pull and join in Python so the module loop is O(1).
    all_caps = discovery.capabilities(since_ts=since_ts, limit=2000)
    caps_by_module: Dict[Any, List[str]] = {}
    for c in all_caps:
        key = (str(c.get("source", "")), str(c.get("module_name", "")))
        cap = str(c.get("capability", "") or "").strip().lower()
        if cap:
            caps_by_module.setdefault(key, []).append(cap)

    for m in modules:
        result.modules_seen += 1
        src = str(m.get("source", ""))
        name = str(m.get("name", ""))
        # Episode: "Discovery: <name> from <src>"
        ep_content = (
            f"Discovered module {name} from {src}. "
            f"{(m.get('summary','') or '')[:140]}".strip()
        )
        ep_id = mem.record_episode(
            source=source_label, content=ep_content,
            ts=now, dedupe_key=f"discovery.module:{src}:{name}",
            metadata={"url": m.get("url", ""), "kind": "module"},
        )
        if ep_id:
            result.episodes_added += 1

        # Per-capability episodes + facts + skills
        caps = caps_by_module.get((src, name), [])
        for cap in caps:
            cap_norm = (cap or "").strip().lower()
            if not cap_norm:
                continue
            result.capabilities_seen += 1

            # 1a. Capability episode (one per capability, idempotent on cap).
            cap_ep = mem.record_episode(
                source=source_label,
                content=f"Capability observed: {cap_norm} (from {src}:{name})",
                ts=now,
                dedupe_key=f"discovery.capability:{src}:{cap_norm}",
                metadata={"module": name, "source": src, "kind": "capability"},
            )
            if cap_ep:
                result.episodes_added += 1

            # 1b. Semantic fact row for the capability token.
            definition = (
                f"AI capability class observed in module {name} "
                f"(source={src})."
            )
            try:
                fid = mem.upsert_fact(
                    cap_norm, definition,
                    confidence=max(CONFIDENCE_FLOOR, 0.30), ts=now,
                )
                if fid:
                    result.facts_added += 1
            except ValueError:
                # token sanitation rejected; skip silently.
                continue

            # 1c. Procedural memory — one skill per capability, prior=alpha=2
            # beta=1 → starting proficiency 0.667 ("I have a strong prior
            # but I haven't used it yet").
            sid = _upsert_skill_at(mem, cap_norm,
                                    alpha_prior=_NEW_SKILL_ALPHA_PRIOR,
                                    beta_prior=_NEW_SKILL_BETA_PRIOR,
                                    ts=now)
            if sid:
                result.skills_added += 1
    return result


def _upsert_skill_at(
    mem: MemoryStore, ability: str,
    *, alpha_prior: int, beta_prior: int, ts: float,
) -> Optional[int]:
    """Insert-or-touch a skill row only if the ability is new; otherwise
    refresh ``last_use_ts`` so the consolidation milestones recognise it.

    Returns the row id, or ``None`` if the ability already existed
    (``skills_added`` counter stays at 0 for re-ingest of an already-
    known capability).

    Implementation note: we DO NOT rely on ``Cursor.lastrowid`` after
    ``INSERT OR IGNORE`` because the truthiness check
    (``int(cur.lastrowid or 0) if cur.lastrowid else None``) silently
    returns ``None`` for some platforms when the prior connection-level
    lastrowid is stale. Instead we INSERT OR IGNORE and then explicit
    ``SELECT id WHERE ability_name = ?`` to find the id deterministically.
    """
    ability_norm = (ability or "").strip().lower()
    existing_rows = mem.skills(min_proficiency=0.0, limit=10_000)
    for sk in existing_rows:
        if sk.ability_name == ability_norm:
            # Touch last_use_ts; no proficiency change.
            mem.update_skill(ability_norm, success=True, ts=ts)
            return None
    # Insert with custom priors via raw SQL path (we don't expose a
    # "set_priors=True" flag to keep update_skill's signature clean).
    with mem._lock:  # type: ignore[attr-defined]
        mem._conn.execute(  # type: ignore[attr-defined]
            "INSERT OR IGNORE INTO skills"
            " (ability_name, proficiency, alpha, beta, last_use_ts, use_count)"
            " VALUES (?, ?, ?, ?, ?, 0)",
            (
                ability_norm,
                alpha_prior / (alpha_prior + beta_prior),
                alpha_prior, beta_prior, ts,
            ),
        )
        # Bulletproof id resolution: explicit SELECT by ability_name.
        # Beats Cursor.lastrowid which can be stale across autocommit
        # boundaries on some Python/SQLite builds.
        cur = mem._conn.execute(  # type: ignore[attr-defined]
            "SELECT id FROM skills WHERE ability_name = ?",
            (ability_norm,),
        )
        row = cur.fetchone()
    if row is None:
        # INSERT OR IGNORE landed but the SELECT after couldn't see it.
        # That SHOULD never happen with WAL + autocommit but if it
        # does we return None so the caller treats it as "no new skill".
        return None
    return int(row[0])


def ingest_module(
    mem: MemoryStore,
    rec: ModuleRecord,
    *,
    now_ts: Optional[float] = None,
    source_label: str = "discovery",
) -> IngestResult:
    """Ingest a single :class:`ModuleRecord` (e.g., from operator feed).

    Useful for the CLI ``teach.py`` shape ``--module-name foo`` — same
    shape as a discovery, minus the registry lookup.
    """
    now = float(now_ts if now_ts is not None else time.time())
    discovery = DiscoveryStore()  # transient; we don't write to it here
    try:
        source = rec.source or "user_teach"
        ep = mem.record_episode(
            source=source_label,
            content=(
                f"Manually taught module {rec.name} from {source}. "
                f"{(rec.summary or '')[:140]}".strip()
            ),
            ts=now,
            dedupe_key=f"teach.module:{source}:{rec.name}",
            metadata={"kind": "module", "source": source, "url": rec.url},
        )
        result = IngestResult(episodes_added=1 if ep else 0,
                              modules_seen=1, capabilities_seen=0,
                              facts_added=0, skills_added=0)
        for cap in (rec.capabilities or []):
            cap_norm = (cap or "").strip().lower()
            if not cap_norm:
                continue
            result.capabilities_seen += 1
            mem.record_episode(
                source=source_label,
                content=f"Capability: {cap_norm} (taught from {source})",
                ts=now,
                dedupe_key=f"teach.capability:{source}:{cap_norm}",
                metadata={"kind": "capability", "source": source},
            )
            result.episodes_added += 1
            try:
                mem.upsert_fact(
                    cap_norm,
                    f"Manually taught capability from {source}:{rec.name}.",
                    confidence=max(CONFIDENCE_FLOOR, 0.30), ts=now,
                )
                result.facts_added += 1
            except ValueError:
                continue
            sid = _upsert_skill_at(
                mem, cap_norm,
                alpha_prior=_NEW_SKILL_ALPHA_PRIOR,
                beta_prior=_NEW_SKILL_BETA_PRIOR,
                ts=now,
            )
            if sid:
                result.skills_added += 1
        return result
    finally:
        discovery.close()


__all__ = [
    "IngestResult",
    "ingest_discovery_summary", "ingest_module",
]
