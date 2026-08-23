"""Tests for the TankOS i18n system (language packs hosted on the VPS)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tank_os.core.i18n import (  # noqa: E402
    BUILTIN_EN, I18nManager, LANGUAGES, t, translate_widget_tree,
)


@pytest.fixture()
def mgr() -> I18nManager:
    m = I18nManager()
    m.set_language("en")
    yield m


def test_builtin_english_covers_dock() -> None:
    """The GUI works with zero network — built-in English pack is complete."""
    for key in ["Home", "Drive", "Mission", "Settings", "Safety",
                "Judge", "Human", "Evolve", "Language", "Battery"]:
        assert key in BUILTIN_EN


def test_available_languages() -> None:
    m = I18nManager()
    langs = m.available()
    assert len(langs) >= 16
    codes = [c["code"] for c in langs]
    for expect in ["en", "hi", "bn", "ta", "te", "es", "fr", "de",
                   "zh", "ja", "ko", "ar", "ru"]:
        assert expect in codes


def test_sync_fetches_from_vps_and_caches(mgr) -> None:
    """§-packs — sync downloads a pack from the VPS into the local cache."""
    result = mgr.sync("hi")
    assert result.get("hi") is True
    cached = mgr.cache_dir() / "hi.json"
    assert cached.exists()
    pack = json.loads(cached.read_text())
    assert pack.get("Home") == "होम"


def test_set_language_translates(mgr) -> None:
    mgr.set_language("es")
    assert t("Home") == "Inicio"
    assert t("Settings") == "Ajustes"
    assert t("Battery") == "Batería"
    mgr.set_language("zh")
    assert t("Home") == "主页"
    assert t("Mission") == "任务"


def test_unknown_key_falls_back_to_english(mgr) -> None:
    mgr.set_language("fr")
    assert t("TotallyUnknownString") == "TotallyUnknownString"


def test_english_is_identity(mgr) -> None:
    mgr.set_language("en")
    assert t("Home") == "Home"


def test_sync_all_languages(mgr) -> None:
    result = mgr.sync()
    assert len(result) >= 16
    assert all(result.values()), [c for c, ok in result.items() if not ok]


def test_offline_fallback_after_cache(mgr, monkeypatch) -> None:
    """Cached pack must load even if the network is unreachable."""
    mgr.sync("hi")
    # break the network mirrors
    monkeypatch.setattr("tank_os.core.i18n.VPS_BASES", ["http://127.0.0.1:1/lang"])
    monkeypatch.setattr("tank_os.core.i18n.CACHE_DIR",
                        Path(mgr.cache_dir()))
    m2 = I18nManager()
    m2.set_language("hi")
    assert m2.t("Home") == "होम"


def test_widget_tree_translation(mgr) -> None:
    """translate_widget_tree swaps exact-match labels in a Qt widget tree."""
    from PySide6.QtWidgets import (  # noqa: PLC0415
        QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    )
    app = QApplication.instance() or QApplication([])

    w = QWidget()
    lay = QVBoxLayout(w)
    lbl = QLabel("Home")
    btn = QPushButton("Drive")
    other = QLabel("Not a key")
    for x in (lbl, btn, other):
        lay.addWidget(x)

    mgr.set_language("es")
    n = translate_widget_tree(w)
    assert lbl.text() == "Inicio"
    assert btn.text() == "Conducir"
    assert other.text() == "Not a key"   # untouched, not in the pack
    assert n >= 2

    # English = no-op
    mgr.set_language("en")
    assert translate_widget_tree(w) == 0
