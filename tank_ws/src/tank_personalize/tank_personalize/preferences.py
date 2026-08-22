"""SQLite-backed preferences store.

Three sections, each gated by its own dataclass of allowed keys:

* **motion**    — kinetic limits the user dials in
* **privacy**   — what the AI may record / share / recall
* **audio**     — wake sensitivity, TTS voice, chime volume

Every read returns a *complete* payload by merging the per-section
defaults with whatever the user has overridden. That keeps the
dashboard UI rendering every slider even on a fresh device.

Persistence rule (STATUS.md §9 design rule 2): *DB-first, JSON-second*.
We only ever persist to a single SQLite file here, so the rule is
satisfied trivially — concurrent reads pass through the daemon's
``check_same_thread=False`` connect; writes are wrapped in a
single ``threading.Lock`` so a dashboard edit and a wake-word
adjustment can't race.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, Type


# --------------------------------------------------------------------------- #
# Section dataclasses
# --------------------------------------------------------------------------- #

@dataclass
class MotionPrefs:
    max_speed_mps: float = 0.4            # m/s upper bound on vx
    follow_distance_m: float = 0.80        # m — standoff while tracking
    patrol_mode: str = "random"            # off|waypoint|random
    turn_speed_radps: float = 0.8          # rad/s upper bound on wz
    obstacle_stop_distance_m: float = 0.30 # LiDAR pause threshold
    enable_chime_on_arrival: bool = True   # play short chime after tasks


@dataclass
class PrivacyPrefs:
    share_recordings: bool = False         # POST clips to remote endpoints
    telemetry_to_ai: bool = True           # battery/health into the prompt
    remember_conversations: bool = True    # write to tank_memory
    auto_delete_recordings_days: int = 7   # 0 = keep forever
    redact_faces_in_recordings: bool = True  # face-blur before save


@dataclass
class AudioPrefs:
    wake_sensitivity: float = 0.55         # 0.0–1.0 (openWakeWord threshold)
    tts_voice: str = "en_US-lessac-medium" # Piper voice id
    chime_volume: float = 0.6              # 0.0–1.0
    wake_chime: bool = True
    speech_language: str = "en-US"


# Index by section name for fast lookup.
SECTION_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "motion": asdict(MotionPrefs()),
    "privacy": asdict(PrivacyPrefs()),
    "audio": asdict(AudioPrefs()),
}

SECTION_CLASSES: Dict[str, Type[Any]] = {
    "motion": MotionPrefs,
    "privacy": PrivacyPrefs,
    "audio": AudioPrefs,
}

ALLOWED_SECTIONS = tuple(SECTION_DEFAULTS.keys())


class PrefKeyError(ValueError):
    """Raised when the caller asks for an unknown section or key."""


class PreferenceStore:
    """Atomic, thread-safe SQLite store with a per-instance write lock."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._lock = threading.Lock()
        # Ensure the parent directory exists.
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._init_schema()
        # Seed per-section defaults so a fresh device never returns
        # something half-empty.
        for section, defaults in SECTION_DEFAULTS.items():
            for k, v in defaults.items():
                self.set(section, k, v)

    # ---------- schema ----------
    def _connect(self) -> sqlite3.Connection:
        # ``check_same_thread=False`` because we may be called by the
        # FastAPI worker threads AND a long-lived ROS subscription
        # callback in production.
        return sqlite3.connect(self._path, timeout=5.0,
                               check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS prefs ("
                    "section  TEXT NOT NULL,"
                    "key      TEXT NOT NULL,"
                    "value    TEXT NOT NULL,"
                    "ts       REAL NOT NULL,"
                    "PRIMARY KEY(section, key))")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS prefs_section_idx "
                "ON prefs(section)")

    # ---------- helpers ----------
    def _validate(self, section: str, key: str) -> None:
        if section not in SECTION_DEFAULTS:
            raise PrefKeyError(
                f"unknown section {section!r}; "
                f"expected one of {ALLOWED_SECTIONS}")
        if key not in SECTION_DEFAULTS[section]:
            raise PrefKeyError(
                f"unknown key {key!r} in section {section!r}; "
                f"expected one of {tuple(SECTION_DEFAULTS[section].keys())}")

    @staticmethod
    def _coerce(value: Any, declared: Any) -> Any:
        """Best-effort coerce so PUT requests typed as JSON numbers
        still match booleans / floats declared in the dataclass."""
        # NOTE: declared can be a *value* (the default True / False /
        # 0.4 the dataclass carries) — not a type. So ``declared is bool``
        # is always False for bool instances; use isinstance.
        if isinstance(declared, bool) and isinstance(value, int) \
                and not isinstance(value, bool):
            return bool(value)
        if isinstance(declared, (int, float)) \
                and isinstance(value, (int, float)) \
                and not isinstance(value, bool):
            return float(value)
        return value

    # ---------- write ----------
    def set(self, section: str, key: str, value: Any) -> bool:
        """Atomically overwrite ``(section, key) → value``. Returns
        True if the row was updated, False if nothing changed.

        Uses ``INSERT OR REPLACE`` (not separate INSERT + UPDATE) so
        a concurrent read on a half-applied state can't see both old
        and new values, and the schema's PK constraint is respected
        when the row already exists.
        """
        self._validate(section, key)
        declared = SECTION_DEFAULTS[section][key]
        coerced = self._coerce(value, declared)
        payload = json.dumps(coerced)
        ts = time.time()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT value FROM prefs WHERE section=? AND key=?",
                (section, key))
            row = cur.fetchone()
            if row is not None and row[0] == payload:
                return False
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO prefs("
                    "section,key,value,ts) VALUES(?,?,?,?)",
                    (section, key, payload, ts))
            return True

    def patch_section(self, section: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a partial dict; returns the resulting full section."""
        if section not in SECTION_DEFAULTS:
            raise PrefKeyError(f"unknown section {section!r}")
        if not isinstance(patch, dict):
            raise PrefKeyError("patch must be a JSON object")
        for k in patch.keys():
            self._validate(section, k)
        for k, v in patch.items():
            self.set(section, k, v)
        return self.get_section(section)

    # ---------- read ----------
    def get(self, section: str, key: str) -> Any:
        self._validate(section, key)
        defaults = SECTION_DEFAULTS[section][key]
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT value FROM prefs WHERE section=? AND key=?",
                (section, key))
            row = cur.fetchone()
        if not row:
            return defaults
        try:
            return json.loads(row[0])
        except Exception:
            return defaults

    def get_section(self, section: str) -> Dict[str, Any]:
        if section not in SECTION_DEFAULTS:
            raise PrefKeyError(f"unknown section {section!r}")
        defaults = dict(SECTION_DEFAULTS[section])
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM prefs WHERE section=?",
                (section,)).fetchall()
        for k, payload in rows:
            try:
                defaults[k] = json.loads(payload)
            except Exception:
                continue
        return defaults

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        return {sec: self.get_section(sec) for sec in ALLOWED_SECTIONS}

    # ---------- reset ----------
    def reset_section(self, section: str) -> Dict[str, Any]:
        if section not in SECTION_DEFAULTS:
            raise PrefKeyError(f"unknown section {section!r}")
        with self._lock, self._connect() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM prefs WHERE section=?",
                    (section,))
        for k, v in SECTION_DEFAULTS[section].items():
            self.set(section, k, v)
        return self.get_section(section)

    def reset_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            with conn:
                conn.execute("DELETE FROM prefs")
        for section, defaults in SECTION_DEFAULTS.items():
            for k, v in defaults.items():
                self.set(section, k, v)
        return self.get_all()

    # ---------- diff ----------
    def diff_from_defaults(self, section: str) -> Dict[str, Any]:
        current = self.get_section(section)
        defaults = SECTION_DEFAULTS[section]
        return {k: {"from": defaults[k], "to": current[k]}
                for k in current.keys()
                if current[k] != defaults[k]}
