"""User-memory store.

Small durable snapshot of what The Tank has *learned* about its
owner — the user's preferred name, last time they interacted,
moods the AI has labelled them with, and free-form facts they
asked the robot to remember. Persisted in SQLite so it survives
reboots, exposed through the dashboard and read by the assistant
to compose the system prompt.

Design rules followed (per STATUS.md §9):
* DB-first. We only ever write one place, but writes go through a
  named mutex so dashboard PUTs and a "remember this" voice intent
  don't race.
* String slicing: every free-form fact is trimmed and capped before
  it lands in SQLite and again before it lands in the prompt.
* ID format: there's no public ID here — the user is the implicit
  single owner (single-tenant dashboard per the user's answer).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Bounded lengths — every fact / name has a cap so a runaway voice
# intent can't dump a 200 KB blob into the system prompt.
NAME_MAX = 80
FACT_MAX = 240
FACT_HARD_CAP = 12      # only the last FACT_HARD_CAP facts feed the prompt
MOOD_KEY_MAX = 24


@dataclass
class UserMemory:
    """What The Tank remembers about the owner."""

    remembered_name: Optional[str] = None
    last_seen_ts: float = 0.0
    moods_seen: Dict[str, int] = field(default_factory=dict)
    custom_facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "remembered_name": self.remembered_name,
            "last_seen_ts": self.last_seen_ts,
            "moods_seen": dict(self.moods_seen),
            "custom_facts": list(self.custom_facts),
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "UserMemory":
        if not d:
            return cls()
        m = cls()
        if isinstance(d.get("remembered_name"), str):
            m.remembered_name = d["remembered_name"].strip()[:NAME_MAX] \
                or None
        if isinstance(d.get("last_seen_ts"), (int, float)):
            m.last_seen_ts = float(d["last_seen_ts"])
        if isinstance(d.get("moods_seen"), dict):
            m.moods_seen = {
                str(k).strip()[:MOOD_KEY_MAX]: int(v)
                for k, v in d["moods_seen"].items()
                if int(v) >= 0
            }
        if isinstance(d.get("custom_facts"), list):
            clean: List[str] = []
            for f in d["custom_facts"]:
                if not isinstance(f, str):
                    continue
                trimmed = f.strip()[:FACT_MAX]
                if trimmed and trimmed not in clean:
                    clean.append(trimmed)
            m.custom_facts = clean[-FACT_HARD_CAP:]
        return m


class MemoryStore:
    """Single-row store; row id is always 1 (single-tenant dashboard)."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._init_schema()
        # Make sure at least the default row exists.
        if self.read() is None:
            self._write(UserMemory())

    # ---------- schema ----------
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0,
                               check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS memory ("
                    "id         INTEGER PRIMARY KEY CHECK(id = 1),"
                    "name       TEXT,"
                    "last_seen  REAL,"
                    "moods_json TEXT,"
                    "facts_json TEXT,"
                    "ts         REAL)")

    # ---------- internals ----------
    def _write(self, m: UserMemory) -> None:
        with self._lock, self._connect() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory("
                    "id, name, last_seen, moods_json, facts_json, ts) "
                    "VALUES(1,?,?,?,?,?)",
                    (m.remembered_name,
                     float(m.last_seen_ts),
                     json.dumps(m.moods_seen or {}),
                     json.dumps(m.custom_facts or []),
                     time.time()))

    # ---------- read ----------
    def read(self) -> Optional[UserMemory]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT name, last_seen, moods_json, facts_json "
                "FROM memory WHERE id=1")
            row = cur.fetchone()
        if row is None:
            return None
        try:
            moods = json.loads(row[2] or "{}")
        except Exception:
            moods = {}
        try:
            facts = json.loads(row[3] or "[]")
        except Exception:
            facts = []
        if not isinstance(moods, dict):
            moods = {}
        if not isinstance(facts, list):
            facts = []
        return UserMemory(
            remembered_name=(row[0] or None) and str(row[0]).strip() or None,
            last_seen_ts=float(row[1] or 0.0),
            moods_seen={str(k)[:MOOD_KEY_MAX]: int(v)
                        for k, v in moods.items()
                        if isinstance(v, (int, float))},
            custom_facts=[str(f)[:FACT_MAX] for f in facts
                          if isinstance(f, str) and str(f).strip()],
        )

    # ---------- mutations ----------
    def update(self, **kwargs: Any) -> UserMemory:
        """Set arbitrary valid fields in one go; bumps ``last_seen_ts``.

        Unknown keys raise ``ValueError`` so an API typo can't silently
        create a typo'd column.
        """
        m = self.read() or UserMemory()
        valid_keys = {"remembered_name", "last_seen_ts",
                      "moods_seen", "custom_facts"}
        for k, v in kwargs.items():
            if k not in valid_keys:
                raise ValueError(f"unknown memory field {k!r}")
            setattr(m, k, v)
        m.last_seen_ts = time.time()
        # Re-clamp defensively so a stray API call can't bypass the
        # field-level caps.
        m = UserMemory.from_dict(m.to_dict())
        self._write(m)
        return m

    def set_name(self, name: str) -> UserMemory:
        return self.update(remembered_name=name)

    def clear_name(self) -> UserMemory:
        return self.update(remembered_name=None)

    def touch(self) -> UserMemory:
        return self.update(last_seen_ts=time.time())

    def bump_mood(self, mood: str) -> UserMemory:
        m = self.read() or UserMemory()
        key = (mood or "").strip().lower()[:MOOD_KEY_MAX]
        if not key:
            return m
        m.moods_seen[key] = int(m.moods_seen.get(key, 0)) + 1
        m.last_seen_ts = time.time()
        self._write(m)
        return m

    def add_fact(self, fact: str) -> UserMemory:
        m = self.read() or UserMemory()
        cleaned = (fact or "").strip()[:FACT_MAX]
        if cleaned and cleaned not in m.custom_facts:
            m.custom_facts.append(cleaned)
        # Trim to hard cap.
        m.custom_facts = m.custom_facts[-FACT_HARD_CAP:]
        m.last_seen_ts = time.time()
        self._write(m)
        return m

    def remove_fact(self, fact: str) -> UserMemory:
        m = self.read() or UserMemory()
        target = (fact or "").strip()[:FACT_MAX]
        m.custom_facts = [f for f in m.custom_facts if f != target]
        m.last_seen_ts = time.time()
        self._write(m)
        return m

    def clear_facts(self) -> UserMemory:
        return self.update(custom_facts=[])

    def clear_all(self) -> UserMemory:
        return self.update(remembered_name=None,
                           moods_seen={},
                           custom_facts=[])
