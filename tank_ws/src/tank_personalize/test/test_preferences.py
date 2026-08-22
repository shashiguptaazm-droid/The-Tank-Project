"""Tests for tank_personalize.preferences."""
from __future__ import annotations

import os
import tempfile

import pytest

from tank_personalize.preferences import (
    ALLOWED_SECTIONS,
    AudioPrefs,
    MotionPrefs,
    PrefKeyError,
    PreferenceStore,
    PrivacyPrefs,
)


@pytest.fixture
def store(tmp_path) -> PreferenceStore:
    db_path = str(tmp_path / "prefs.db")
    p = PreferenceStore(db_path)
    return p


def test_seed_returns_defaults(store: PreferenceStore):
    for section in ALLOWED_SECTIONS:
        sec = store.get_section(section)
        assert isinstance(sec, dict) and sec, section
        # Every declared key should be present.
        if section == "motion":
            assert set(sec) == set(MotionPrefs().__dict__)
        elif section == "privacy":
            assert set(sec) == set(PrivacyPrefs().__dict__)
        elif section == "audio":
            assert set(sec) == set(AudioPrefs().__dict__)


def test_set_returns_false_for_same_value(store: PreferenceStore):
    changed_a = store.set("motion", "max_speed_mps", 0.4)
    assert changed_a is False  # seed already set it to 0.4
    store.set("motion", "max_speed_mps", 0.5)
    changed_b = store.set("motion", "max_speed_mps", 0.5)
    assert changed_b is False
    changed_c = store.set("motion", "max_speed_mps", 0.6)
    assert changed_c is True


def test_unknown_section_rejected(store: PreferenceStore):
    with pytest.raises(PrefKeyError):
        store.set("bogus", "x", 1)
    with pytest.raises(PrefKeyError):
        store.get_section("bogus")


def test_unknown_key_rejected(store: PreferenceStore):
    with pytest.raises(PrefKeyError):
        store.set("motion", "turbo_boost", True)


def test_patch_section_returns_full(store: PreferenceStore):
    result = store.patch_section("motion", {"max_speed_mps": 0.55})
    assert result["max_speed_mps"] == 0.55
    # Other keys still default.
    assert "patrol_mode" in result


def test_patch_rejects_non_dict(store: PreferenceStore):
    with pytest.raises(PrefKeyError):
        store.patch_section("audio", "not a dict")  # type: ignore[arg-type]


def test_reset_section(store: PreferenceStore):
    store.set("audio", "wake_sensitivity", 0.9)
    res = store.reset_section("audio")
    assert res["wake_sensitivity"] == 0.55  # back to default
    # Other sections untouched.
    assert store.get_section("motion")["max_speed_mps"] == 0.4


def test_reset_all(store: PreferenceStore):
    store.set("audio", "wake_sensitivity", 0.93)
    store.set("motion", "max_speed_mps", 0.77)
    res = store.reset_all()
    assert res["audio"]["wake_sensitivity"] == 0.55
    assert res["motion"]["max_speed_mps"] == 0.4


def test_diff_from_defaults(store: PreferenceStore):
    assert store.diff_from_defaults("audio") == {}
    store.set("audio", "wake_sensitivity", 0.92)
    diff = store.diff_from_defaults("audio")
    assert "wake_sensitivity" in diff
    assert diff["wake_sensitivity"]["from"] == 0.55
    assert diff["wake_sensitivity"]["to"] == 0.92


def test_bool_coercion_from_int(store: PreferenceStore):
    # JSON PUTs come in as ints; store set as 1 should be persisted
    # as a boolean.
    store.set("audio", "wake_chime", 1)
    assert store.get("audio", "wake_chime") is True
