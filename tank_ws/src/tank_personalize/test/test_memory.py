"""Tests for tank_personalize.memory."""
from __future__ import annotations

import pytest

from tank_personalize.memory import FACT_HARD_CAP, MemoryStore, UserMemory


@pytest.fixture
def store(tmp_path) -> MemoryStore:
    return MemoryStore(str(tmp_path / "mem.db"))


def test_defaults_empty(store: MemoryStore):
    m = store.read()
    assert m.remembered_name is None
    assert m.moods_seen == {}
    assert m.custom_facts == []
    assert m.last_seen_ts == 0.0


def test_set_name(store: MemoryStore):
    store.set_name("Aisha")
    m = store.read()
    assert m.remembered_name == "Aisha"
    assert m.last_seen_ts > 0.0


def test_set_name_trims_and_caps(store: MemoryStore):
    long = "x" * 1000
    store.update(remembered_name=long)  # goes through from_dict
    m = store.read()
    assert m.remembered_name is not None
    assert len(m.remembered_name) <= 80


def test_clear_name(store: MemoryStore):
    store.set_name("Sam")
    store.clear_name()
    assert store.read().remembered_name is None


def test_add_fact_dedupes(store: MemoryStore):
    store.add_fact("likes dark mode")
    store.add_fact("likes dark mode")
    store.add_fact("  likes dark mode  ")
    assert store.read().custom_facts == ["likes dark mode"]


def test_add_fact_caps(store: MemoryStore):
    for i in range(FACT_HARD_CAP + 8):
        store.add_fact(f"fact {i}")
    facts = store.read().custom_facts
    assert len(facts) == FACT_HARD_CAP
    # The earliest facts must have fallen off (LRU eviction by append).
    assert facts[0] == f"fact 8"


def test_remove_fact(store: MemoryStore):
    store.add_fact("tea")
    store.add_fact("coffee")
    store.remove_fact("tea")
    assert store.read().custom_facts == ["coffee"]


def test_remove_fact_missing(store: MemoryStore):
    store.add_fact("tea")
    res = store.remove_fact("water")
    assert res.custom_facts == ["tea"]


def test_bump_mood(store: MemoryStore):
    store.bump_mood("happy")
    store.bump_mood("happy")
    store.bump_mood("tired")
    moods = store.read().moods_seen
    assert moods["happy"] == 2
    assert moods["tired"] == 1


def test_bump_mood_lowercases_key(store: MemoryStore):
    store.bump_mood("HAPPY")
    assert store.read().moods_seen == {"happy": 1}


def test_clear_facts_mood_intact(store: MemoryStore):
    store.add_fact("a")
    store.add_fact("b")
    store.bump_mood("calm")
    store.clear_facts()
    m = store.read()
    assert m.custom_facts == []
    assert m.moods_seen == {"calm": 1}


def test_clear_all(store: MemoryStore):
    store.set_name("Lee")
    store.add_fact("a")
    store.bump_mood("glad")
    store.clear_all()
    m = store.read()
    assert m.remembered_name is None
    assert m.custom_facts == []
    assert m.moods_seen == {}


def test_update_rejects_unknown_fields(store: MemoryStore):
    with pytest.raises(ValueError):
        store.update(telephone="555-1212")


def test_touch_bumps_only_last_seen(store: MemoryStore):
    store.set_name("Ana")
    store.add_fact("hi")
    state = store.read()
    state_last = state.last_seen_ts
    # Touch should not change facts/name but should bump ts.
    new = store.touch().to_dict()
    assert new["remembered_name"] == "Ana"
    # Trimming float precision is risky — just compare >=
    assert new["last_seen_ts"] >= state_last
