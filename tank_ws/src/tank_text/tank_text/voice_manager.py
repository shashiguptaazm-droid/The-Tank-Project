"""Voice library + download/cache manager for Piper ONNX voices.

Curated catalogue of 8 Piper voices (en / accents, F/M, calm/expressive).
Each entry has a HuggingFace URL for both ``*.onnx`` and ``*.onnx.json``
files so a fresh Pi 5 can `import` and start using new voices without
manual pip-install ceremony.

Cache layout
------------
``~/.cache/tank_voices/<voice_id>/<voice_id>.onnx``
``~/.cache/tank_voices/<voice_id>/<voice_id>.onnx.json``

Override the root with the ``TANK_VOICES_CACHE`` env var.

Adding a new voice
------------------
Append a :class:`VoiceEntry` to :data:`VOICE_LIBRARY`. Default voice is
``en_US-lessac-medium`` — matches the manifest entry the existing
``tts_node`` shipped with.

Hot-swap :class:`PiperSwapper` lets ``tts_node`` swap voice models at
runtime without restarting, when the persona dashboard changes
``voice_id``.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


CACHE_DIR = Path(
    os.environ.get("TANK_VOICES_CACHE",
                   str(Path.home() / ".cache" / "tank_voices"))
)
DEFAULT_VOICE_BASE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main"
)

ProgressCb = Callable[[str, int, int], None]


# ────────────────────────────────────────────────────────────────────────────
# Voice catalogue
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class VoiceEntry:
    """One voice's catalogue entry."""
    voice_id: str               # Piper's <lang>_<region>-<name>-<quality>
    lang: str                   # "en_US", "en_GB", …
    gender: str                 # "F" | "M"
    style: str                  # short freeform description
    quality: str                # "low" | "medium" | "high"
    onnx_url: str
    json_url: str
    onnx_sha256: str = ""
    json_sha256: str = ""
    approx_size_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VoiceEntry":
        keys = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in keys})


def _piper_url(lang_full: str, family: str,
               quality: str, filename: str) -> str:
    """Build the canonical rhasspy/piper-voices HF URL for a file."""
    lang_short = lang_full.split("_", 1)[0]
    return (f"{DEFAULT_VOICE_BASE_URL}/{lang_short}/{lang_full}/"
            f"{family}/{quality}/{filename}")


# 8 curated Piper voices. Family → URL on HF is the rhasspy layout.
VOICE_LIBRARY: List[VoiceEntry] = [
    VoiceEntry(
        voice_id="en_US-lessac-medium",
        lang="en_US", gender="F", style="Calm/Standard",
        quality="medium",
        onnx_url=_piper_url("en_US", "lessac", "medium",
                            "en_US-lessac-medium.onnx"),
        json_url=_piper_url("en_US", "lessac", "medium",
                            "en_US-lessac-medium.onnx.json"),
        approx_size_mb=15.0,
    ),
    VoiceEntry(
        voice_id="en_US-lessac-high",
        lang="en_US", gender="F", style="Clear/Warm",
        quality="high",
        onnx_url=_piper_url("en_US", "lessac", "high",
                            "en_US-lessac-high.onnx"),
        json_url=_piper_url("en_US", "lessac", "high",
                            "en_US-lessac-high.onnx.json"),
        approx_size_mb=25.0,
    ),
    VoiceEntry(
        voice_id="en_US-amy-medium",
        lang="en_US", gender="F", style="Upbeat",
        quality="medium",
        onnx_url=_piper_url("en_US", "amy", "medium",
                            "en_US-amy-medium.onnx"),
        json_url=_piper_url("en_US", "amy", "medium",
                            "en_US-amy-medium.onnx.json"),
        approx_size_mb=15.0,
    ),
    VoiceEntry(
        voice_id="en_US-ryan-high",
        lang="en_US", gender="M", style="Deep/Resonant",
        quality="high",
        onnx_url=_piper_url("en_US", "ryan", "high",
                            "en_US-ryan-high.onnx"),
        json_url=_piper_url("en_US", "ryan", "high",
                            "en_US-ryan-high.onnx.json"),
        approx_size_mb=25.0,
    ),
    VoiceEntry(
        voice_id="en_GB-alan-medium",
        lang="en_GB", gender="M", style="Soft/British",
        quality="medium",
        onnx_url=_piper_url("en_GB", "alan", "medium",
                            "en_GB-alan-medium.onnx"),
        json_url=_piper_url("en_GB", "alan", "medium",
                            "en_GB-alan-medium.onnx.json"),
        approx_size_mb=15.0,
    ),
    VoiceEntry(
        voice_id="en_GB-cori-high",
        lang="en_GB", gender="F", style="Crisp/Authority",
        quality="high",
        onnx_url=_piper_url("en_GB", "cori", "high",
                            "en_GB-cori-high.onnx"),
        json_url=_piper_url("en_GB", "cori", "high",
                            "en_GB-cori-high.onnx.json"),
        approx_size_mb=25.0,
    ),
    VoiceEntry(
        voice_id="en_US-hfc_female-medium",
        lang="en_US", gender="F", style="Expressive",
        quality="medium",
        onnx_url=_piper_url("en_US", "hfc_female", "medium",
                            "en_US-hfc_female-medium.onnx"),
        json_url=_piper_url("en_US", "hfc_female", "medium",
                            "en_US-hfc_female-medium.onnx.json"),
        approx_size_mb=15.0,
    ),
    VoiceEntry(
        voice_id="en_US-joe-medium",
        lang="en_US", gender="M", style="Playful/Child-like",
        quality="medium",
        onnx_url=_piper_url("en_US", "joe", "medium",
                            "en_US-joe-medium.onnx"),
        json_url=_piper_url("en_US", "joe", "medium",
                            "en_US-joe-medium.onnx.json"),
        approx_size_mb=15.0,
    ),
]


VOICE_INDEX: Dict[str, VoiceEntry] = {v.voice_id: v for v in VOICE_LIBRARY}


def voice_by_id(voice_id: str) -> Optional[VoiceEntry]:
    return VOICE_INDEX.get(voice_id)


def list_voices() -> List[Dict[str, Any]]:
    return [v.to_dict() for v in VOICE_LIBRARY]


# ────────────────────────────────────────────────────────────────────────────
# Downloader + checksum
# ────────────────────────────────────────────────────────────────────────────

class VoiceDownloadError(RuntimeError):
    pass


def voice_path(voice_id: str, kind: str = "onnx") -> Path:
    """Local cached path for a voice's ONNX or JSON file."""
    suffix = ".onnx" if kind == "onnx" else ".onnx.json"
    return CACHE_DIR / voice_id / f"{voice_id}{suffix}"


def is_downloaded(voice_id: str) -> bool:
    return (voice_path(voice_id, "onnx").is_file()
            and voice_path(voice_id, "json").is_file())


def list_downloaded() -> List[str]:
    if not CACHE_DIR.is_dir():
        return []
    out = []
    for p in sorted(CACHE_DIR.iterdir()):
        if p.is_dir() and is_downloaded(p.name):
            out.append(p.name)
    return out


def __stream(url: str, dest: Path,
             progress_cb: Optional[ProgressCb]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TankBot/1.0 (Piper voice loader)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", "0") or 0)
            so_far = 0
            tmp = dest.with_suffix(dest.suffix + ".part")
            with tmp.open("wb") as fh:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    so_far += len(chunk)
                    if progress_cb and total > 0:
                        try:
                            progress_cb(dest.name, so_far, total)
                        except Exception:
                            pass
            tmp.replace(dest)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise VoiceDownloadError(f"{url}: {exc}") from exc


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_voice(voice_id: str,
                 progress_cb: Optional[ProgressCb] = None) -> Path:
    """Download a voice if missing. Returns the ONNX path.

    Raises :class:`VoiceDownloadError` if the id is unknown, the
    network fails, or a checksum mismatches.
    """
    entry = voice_by_id(voice_id)
    if entry is None:
        raise VoiceDownloadError(f"unknown voice_id {voice_id!r}")
    onnx = voice_path(voice_id, "onnx")
    js = voice_path(voice_id, "json")
    if onnx.is_file() and js.is_file():
        return onnx
    __stream(entry.onnx_url, onnx, progress_cb)
    __stream(entry.json_url, js, progress_cb)
    if entry.onnx_sha256 and _sha256(onnx) != entry.onnx_sha256:
        onnx.unlink(missing_ok=True)
        raise VoiceDownloadError(
            f"{voice_id}: ONNX sha256 mismatch")
    if entry.json_sha256 and _sha256(js) != entry.json_sha256:
        js.unlink(missing_ok=True)
        raise VoiceDownloadError(
            f"{voice_id}: JSON sha256 mismatch")
    return onnx


def download_all(progress_cb: Optional[ProgressCb] = None) -> List[str]:
    """Download every entry in :data:`VOICE_LIBRARY`. Returns the list of
    successfully downloaded ids (errors logged to stderr; catalogue
    still goes through)."""
    out: List[str] = []
    for v in VOICE_LIBRARY:
        try:
            ensure_voice(v.voice_id, progress_cb)
            out.append(v.voice_id)
        except Exception as exc:
            print(f"[voice_manager] {v.voice_id}: {exc}",
                  file=sys.stderr)
    return out


# ────────────────────────────────────────────────────────────────────────────
# Hot-swap façade for tts_node
# ────────────────────────────────────────────────────────────────────────────

class PiperVoiceHandle:
    """Holds a loaded ``piper.PiperVoice`` and a sample-rate.

    Tests inject ``._voice`` to None (or to a fake) to keep the suite
    hermetic. Production loads the model from the cache dir.
    """

    def __init__(self, voice_id: str,
                 onnx_path: Optional[Path] = None,
                 json_path: Optional[Path] = None,
                 sample_rate: int = 22050) -> None:
        self.voice_id = voice_id
        self._voice: Any = None
        self._sample_rate = sample_rate
        self._onnx_path = onnx_path
        self._json_path = json_path

    @property
    def loaded(self) -> bool:
        return self._voice is not None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def load(self) -> None:
        """Eagerly load the voice. No-op when paths are missing (stub)."""
        try:
            from piper import PiperVoice                      # noqa: WPS433
        except Exception:
            self._voice = None
            return
        if not self._onnx_path or not self._json_path:
            self._voice = None
            return
        if not self._onnx_path.is_file() or not self._json_path.is_file():
            self._voice = None
            return
        try:
            self._voice = PiperVoice.load(
                str(self._onnx_path), str(self._json_path))
        except Exception:
            self._voice = None          # leave in stub mode on failure

    def synth(self, text: str) -> bytes:
        if self._voice is None:
            return b"\x00\x00" * int(0.5 * self._sample_rate)
        audio = self._voice.synthesize(text)
        if hasattr(audio, "audio_int16_array"):
            raw = audio.audio_int16_array
        else:
            raw = audio.audio
        import numpy as np
        return np.asarray(raw, dtype=np.int16).tobytes()

    def to_dict(self) -> Dict[str, Any]:
        return {"voice_id": self.voice_id,
                "loaded":   self.loaded,
                "sample_rate": self._sample_rate}


class PiperSwapper:
    """Hot-swap façade. ``set_voice(id)`` returns the bound handle.

    Pattern for ``tts_node``::

        self._swapper = PiperSwapper()
        self._swapper.set_voice("en_US-lessac-medium")     # initial
        # ... later, on /tts/voice_id message:
        self._swapper.set_voice(new_voice_id)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handle: Optional[PiperVoiceHandle] = None

    @property
    def current(self) -> Optional[PiperVoiceHandle]:
        return self._handle

    def set_voice(self, voice_id: str) -> PiperVoiceHandle:
        """Resolve voice (downloading if missing), bind, return handle."""
        with self._lock:
            try:
                onnx = ensure_voice(voice_id)
                js = voice_path(voice_id, "json")
            except VoiceDownloadError:
                # Stub handle — TTS keeps emitting silence but doesn't crash.
                h = PiperVoiceHandle(voice_id)
            else:
                h = PiperVoiceHandle(voice_id, onnx_path=onnx, json_path=js)
            h.load()
            self._handle = h
            return h

    def synth(self, text: str) -> bytes:
        with self._lock:
            h = self._handle
        if h is None:
            return b""
        return h.synth(text)


def pick_default_voice(persona_gender: Optional[str] = None) -> str:
    """Pick a sensible default voice for a new user.

    ``persona_gender`` ∈ {"F", "M"} or None. Returns a known voice_id.
    """
    if persona_gender and persona_gender.upper() == "M":
        return "en_US-ryan-high"
    if persona_gender and persona_gender.upper() == "F":
        return "en_US-lessac-medium"
    return "en_US-lessac-medium"


__all__ = [
    "VoiceEntry", "VOICE_LIBRARY", "VOICE_INDEX",
    "voice_by_id", "list_voices",
    "ensure_voice", "is_downloaded", "list_downloaded", "download_all",
    "voice_path", "VoiceDownloadError",
    "PiperVoiceHandle", "PiperSwapper", "pick_default_voice",
]
