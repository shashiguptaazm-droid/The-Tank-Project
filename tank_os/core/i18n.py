"""TankOS i18n — lightweight language support, packs hosted on the VPS.

Design:
- Translation packs (JSON: English source string -> localized string) live on
  the VPS at ``/lang/{code}.json`` and are **fetched on demand**, then cached
  locally under ``~/.cache/tankos/lang/`` — the device stays light, and the
  system works **offline-first** (last known pack is always available).
- A small built-in English pack means the GUI never depends on the network.
- ``translate_widget_tree()`` walks a Qt widget tree and swaps exact-match
  English labels for the current language — so existing screens get localized
  without being rewritten, and screens can opt into ``t()`` for finer control.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("tank_os.core.i18n")

#: VPS base URLs — tailnet IP first, public IP as fallback.
VPS_BASES = [
    "http://100.71.127.19/lang",     # medicscholar tailnet
    "http://213.199.61.156/lang",    # medicscholar public
]

CACHE_DIR = Path(os.path.expanduser("~/.cache/tankos/lang"))

#: Built-in English pack — the GUI works with zero network dependency.
BUILTIN_EN: Dict[str, str] = {
    "Home": "Home", "Drive": "Drive", "Mission": "Mission", "Map": "Map",
    "Vision": "Vision", "AI": "AI", "Health": "Health", "ESP32": "ESP32",
    "Jetson": "Jetson", "Compete": "Compete", "Events": "Events",
    "Sensors": "Sensors", "Topology": "Topology", "Tests": "Tests",
    "Power": "Power", "Analytics": "Analytics", "Security": "Security",
    "TV": "TV", "Chat": "Chat", "Settings": "Settings", "AI Cmd": "AI Cmd",
    "Safety": "Safety", "Judge": "Judge", "Dist AI": "Dist AI",
    "Human": "Human", "Const": "Const", "Know Map": "Know Map",
    "Tools": "Tools", "System": "System", "Evolve": "Evolve",
    "AI Core": "AI Core",
    "Network": "Network", "Audio": "Audio", "Voice": "Voice",
    "Display": "Display", "Privacy": "Privacy", "Developer": "Developer",
    "Language": "Language", "Save All Settings": "Save All Settings",
    "⚙️ Settings": "⚙️ Settings",
    "Connected": "Connected", "Disconnected": "Disconnected",
    "Online": "Online", "Offline": "Offline", "Battery": "Battery",
}

#: Language metadata (code, native name, English name, flag).
LANGUAGES: List[Dict[str, str]] = [
    {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "flag": "🇮🇳"},
    {"code": "bn", "name": "Bengali", "native": "বাংলা", "flag": "🇧🇩"},
    {"code": "ta", "name": "Tamil", "native": "தமிழ்", "flag": "🇮🇳"},
    {"code": "te", "name": "Telugu", "native": "తెలుగు", "flag": "🇮🇳"},
    {"code": "mr", "name": "Marathi", "native": "मराठी", "flag": "🇮🇳"},
    {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "flag": "🇮🇳"},
    {"code": "es", "name": "Spanish", "native": "Español", "flag": "🇪🇸"},
    {"code": "fr", "name": "French", "native": "Français", "flag": "🇫🇷"},
    {"code": "de", "name": "German", "native": "Deutsch", "flag": "🇩🇪"},
    {"code": "it", "name": "Italian", "native": "Italiano", "flag": "🇮🇹"},
    {"code": "pt", "name": "Portuguese", "native": "Português", "flag": "🇵🇹"},
    {"code": "ru", "name": "Russian", "native": "Русский", "flag": "🇷🇺"},
    {"code": "zh", "name": "Chinese", "native": "中文", "flag": "🇨🇳"},
    {"code": "ja", "name": "Japanese", "native": "日本語", "flag": "🇯🇵"},
    {"code": "ko", "name": "Korean", "native": "한국어", "flag": "🇰🇷"},
    {"code": "ar", "name": "Arabic", "native": "العربية", "flag": "🇸🇦"},
]


class I18nManager:
    """Translate TankOS UI strings; packs are fetched from the VPS and cached."""

    _instance: Optional["I18nManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "I18nManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._current = "en"
        self._packs: Dict[str, Dict[str, str]] = {"en": dict(BUILTIN_EN)}
        self._loaded: set = {"en"}
        self._dirty = True

    # ------------------------------------------------------------------ api
    @property
    def language(self) -> str:
        return self._current

    def set_language(self, code: str) -> bool:
        """Switch the active language; returns False if the pack is unknown."""
        code = (code or "en").lower()
        if code == self._current and code in self._loaded:
            return True
        pack = self._load_pack(code)
        if pack is None and code != "en":
            logger.warning("i18n: no pack for %r — falling back to English", code)
            code = "en"
        self._current = code
        self._packs.setdefault(code, dict(BUILTIN_EN))
        self._loaded.add(code)
        self._dirty = True
        logger.info("i18n: language -> %s", code)
        return True

    def t(self, key: str, default: Optional[str] = None) -> str:
        """Translate an English source string into the current language."""
        if not key:
            return key
        if self._current == "en":
            return key
        pack = self._packs.get(self._current) or {}
        out = pack.get(key)
        if out:
            return out
        return default if default is not None else key

    def has(self, code: str) -> bool:
        return code in self._loaded or (CACHE_DIR / f"{code}.json").exists()

    def available(self) -> List[Dict[str, str]]:
        return list(LANGUAGES)

    def cache_dir(self) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return CACHE_DIR

    # -------------------------------------------------------------- network
    def _fetch(self, path: str, timeout: float = 8.0) -> Optional[bytes]:
        last_err: Optional[Exception] = None
        for base in VPS_BASES:
            url = f"{base}/{path}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "TankOS-i18n/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except Exception as exc:  # noqa: BLE001 — try next mirror
                last_err = exc
        if last_err is not None:
            logger.debug("i18n: fetch %s failed: %s", path, last_err)
        return None

    def sync(self, code: Optional[str] = None, timeout: float = 8.0) -> Dict[str, bool]:
        """Download pack(s) from the VPS into the local cache.

        Returns {code: success}. ``code=None`` syncs every known language.
        """
        codes = [code] if code else [c["code"] for c in LANGUAGES]
        result: Dict[str, bool] = {}
        for c in codes:
            if c == "en":
                result[c] = True
                continue
            data = self._fetch(f"{c}.json", timeout=timeout)
            if data is None:
                result[c] = False
                continue
            try:
                pack = json.loads(data)
                if not isinstance(pack, dict):
                    raise ValueError("pack must be a JSON object")
                self.cache_dir().mkdir(parents=True, exist_ok=True)
                (CACHE_DIR / f"{c}.json").write_bytes(data)
                self._packs[c] = pack
                self._loaded.add(c)
                result[c] = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("i18n: bad pack %r: %s", c, exc)
                result[c] = False
        return result

    def sync_async(self, code: Optional[str] = None) -> None:
        """Fire-and-forget sync in a background thread (non-blocking GUI)."""
        threading.Thread(target=self.sync, args=(code,), daemon=True).start()

    # --------------------------------------------------------------- cache
    def _load_pack(self, code: str) -> Optional[Dict[str, str]]:
        """Load a pack: cache file first, then network, then fall back."""
        if code in self._loaded and code != "en":
            return self._packs.get(code)
        cached = CACHE_DIR / f"{code}.json"
        if cached.exists():
            try:
                pack = json.loads(cached.read_text())
                self._packs[code] = pack
                self._loaded.add(code)
                return pack
            except Exception as exc:  # noqa: BLE001
                logger.warning("i18n: cached pack %r unreadable: %s", code, exc)
        data = self._fetch(f"{code}.json")
        if data is not None:
            try:
                pack = json.loads(data)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(data)
                self._packs[code] = pack
                self._loaded.add(code)
                return pack
            except Exception as exc:  # noqa: BLE001
                logger.warning("i18n: fetched pack %r invalid: %s", code, exc)
        return None

    def status(self) -> Dict[str, Any]:
        cached = [p.name[:-5] for p in CACHE_DIR.glob("*.json")] if CACHE_DIR.exists() else []
        return {
            "language": self._current,
            "cached": sorted(set(cached) | self._loaded),
            "available": [c["code"] for c in LANGUAGES],
            "cache_dir": str(CACHE_DIR),
            "mirrors": list(VPS_BASES),
        }


# ---------------------------------------------------------------------------
# Convenience singleton helpers
# ---------------------------------------------------------------------------
def i18n() -> I18nManager:
    return I18nManager()


def t(key: str, default: Optional[str] = None) -> str:
    """Module-level translate helper (English source -> current language)."""
    return I18nManager().t(key, default)


def translate_widget_tree(widget: Any, mgr: Optional[I18nManager] = None) -> int:
    """Walk a Qt widget tree and translate exact-match English labels.

    QLabel / QPushButton / QCheckBox / QGroupBox / QDockWidget texts are
    looked up in the active pack and replaced when a translation exists.
    Returns the number of widgets translated. Best-effort: never raises.
    """
    mgr = mgr or I18nManager()
    if mgr.language == "en":
        return 0
    translated = 0
    try:
        from PySide6.QtWidgets import (  # noqa: PLC0415
            QCheckBox, QDockWidget, QGroupBox, QLabel, QPushButton,
        )
        widgets: List[Any] = []
        for tgt in (QLabel, QPushButton, QCheckBox, QGroupBox, QDockWidget):
            widgets.extend(widget.findChildren(tgt))
            if isinstance(widget, tgt):
                widgets.append(widget)
    except Exception:  # noqa: BLE001 — no Qt available
        return 0

    for w in widgets:
        try:
            text = w.text()
            if not text:
                continue
            new = mgr.t(text)
            if new != text:
                w.setText(new)
                translated += 1
        except Exception:  # noqa: BLE001 — best-effort per widget
            continue
    return translated
