"""Hermetic tests for tank_text.voice_manager.

The VoiceManager handles:
* The curated VOICE_LIBRARY catalogue (round-trippable).
* ensure_voice() downloads via urllib → cached path; SHA256 mismatch
  ⇒ ``VoiceDownloadError`` and partial files deleted.
* PiperSwapper.set_voice() returns a PiperVoiceHandle even when piper
  isn't installed (stub mode).

We never hit HuggingFace inside CI — ``__stream`` is monkey-patched
via ``urllib.request.urlopen``.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from tank_text.voice_manager import (
    CACHE_DIR,
    PiperSwapper,
    PiperVoiceHandle,
    VOICE_INDEX,
    VOICE_LIBRARY,
    VoiceDownloadError,
    VoiceEntry,
    download_all,
    ensure_voice,
    is_downloaded,
    list_downloaded,
    list_voices,
    pick_default_voice,
    voice_by_id,
    voice_path,
    _sha256,
)


class CatalogueTests(unittest.TestCase):

    def test_default_has_8_voices(self) -> None:
        self.assertEqual(len(VOICE_LIBRARY), 8)

    def test_all_have_valid_format(self) -> None:
        import re
        pat = re.compile(r"^[a-z]{2}_[A-Z]{2}-[a-z0-9_\-]+-(low|medium|high)$")
        for v in VOICE_LIBRARY:
            self.assertRegex(v.voice_id, pat,
                             f"bad voice_id format: {v.voice_id}")

    def test_unique_voice_ids(self) -> None:
        ids = [v.voice_id for v in VOICE_LIBRARY]
        self.assertEqual(len(set(ids)), len(ids),
                         f"duplicate voice_ids: {ids}")

    def test_voice_by_id_works(self) -> None:
        v = voice_by_id("en_US-lessac-medium")
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(v.gender, "F")

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(voice_by_id("xx_XY-bogus-low"))

    def test_voices_have_hf_urls(self) -> None:
        for v in VOICE_LIBRARY:
            self.assertIn("huggingface.co", v.onnx_url)
            self.assertIn("huggingface.co", v.json_url)
            self.assertTrue(v.onnx_url.endswith(".onnx"))
            self.assertTrue(v.json_url.endswith(".onnx.json"))

    def test_voices_are_serialisable(self) -> None:
        for v in VOICE_LIBRARY:
            d = v.to_dict()
            again = VoiceEntry.from_dict(d)
            self.assertEqual(again.voice_id, v.voice_id)
            self.assertEqual(again.gender, v.gender)

    def test_list_voices(self) -> None:
        self.assertEqual(len(list_voices()), 8)


class PickDefaultTests(unittest.TestCase):

    def test_default(self) -> None:
        self.assertEqual(pick_default_voice(), "en_US-lessac-medium")
        self.assertEqual(pick_default_voice(None), "en_US-lessac-medium")

    def test_male(self) -> None:
        self.assertEqual(pick_default_voice("M"), "en_US-ryan-high")

    def test_female(self) -> None:
        self.assertEqual(pick_default_voice("F"), "en_US-lessac-medium")


class _FakeResponse:
    """Mimics ``urllib.request.urlopen`` for streaming."""

    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)
        self.headers: Dict[str, str] = {"Content-Length": str(len(data))}

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def read(self, n: int = -1) -> bytes:
        return self._buf.read(n)


def _fake_urlopen_factory(onnx_bytes: bytes, json_bytes: bytes) -> Any:
    """Returns a function that yields _FakeResponse keyed on URL suffix.

    ``urllib.request.urlopen`` passes either a ``str`` or a
    :class:`urllib.request.Request` as its first argument; ``str(req)``
    gives us the underlying URL reliably for both.
    """

    def fake(url: Any, *a: Any, **kw: Any) -> _FakeResponse:
        url_str = str(url)
        if url_str.endswith(".onnx.json"):
            return _FakeResponse(json_bytes)
        return _FakeResponse(onnx_bytes)

    return fake


class EnsureVoiceTests(unittest.TestCase):
    """Tests for ensure_voice() using a temp cache directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="tank_voices_")
        self._cache_backup = CACHE_DIR
        import tank_text.voice_manager as vm
        vm.CACHE_DIR = Path(self._tmp)
        # Real API name on unittest.TestCase is `addCleanup` (public).
        self.addCleanup(self._restore_cache)
        self.addCleanup(lambda: shutil.rmtree(self._tmp, ignore_errors=True))

    def _restore_cache(self) -> None:
        import tank_text.voice_manager as vm
        vm.CACHE_DIR = self._cache_backup

    def test_unknown_id_raises(self) -> None:
        with self.assertRaises(VoiceDownloadError):
            ensure_voice("xx_XY-bogus-low")

    def test_download_streams_two_files(self) -> None:
        onnx_bytes = b"ONNX-FAKE" * 60
        json_bytes = json.dumps({"sample_rate": 22050}).encode("utf-8")
        progress: list = []

        def cb(name: str, so_far: int, total: int) -> None:
            progress.append((name, so_far, total))

        with patch("urllib.request.urlopen",
                    _fake_urlopen_factory(onnx_bytes, json_bytes)):
            p = ensure_voice("en_US-lessac-medium",
                              progress_cb=cb)
        self.assertTrue(p.is_file())
        self.assertEqual(p.read_bytes(), onnx_bytes)
        names = [n for (n, _, _) in progress]
        self.assertIn("en_US-lessac-medium.onnx", names)
        self.assertIn("en_US-lessac-medium.onnx.json", names)

    def test_existing_files_short_circuits(self) -> None:
        d = Path(self._tmp) / "en_US-lessac-medium"
        d.mkdir(parents=True)
        (d / "en_US-lessac-medium.onnx").write_bytes(b"x")
        (d / "en_US-lessac-medium.onnx.json").write_bytes(b"{}")
        with patch("urllib.request.urlopen") as m:
            p = ensure_voice("en_US-lessac-medium")
        self.assertEqual(p.read_bytes(), b"x")
        m.assert_not_called()

    def test_sha256_mismatch_deletes_and_raises(self) -> None:
        """Inject a sha256 mismatch via a patched catalogue entry."""
        import tank_text.voice_manager as vm
        real_entry = vm.VOICE_INDEX["en_US-lessac-medium"]
        bad_entry = VoiceEntry(
            voice_id=real_entry.voice_id,
            lang=real_entry.lang, gender=real_entry.gender,
            style=real_entry.style, quality=real_entry.quality,
            onnx_url=real_entry.onnx_url, json_url=real_entry.json_url,
            onnx_sha256="0" * 64, json_sha256=real_entry.json_sha256,
        )
        vm.VOICE_INDEX["en_US-lessac-medium"] = bad_entry
        self.addCleanup(lambda: vm.VOICE_INDEX.__setitem__(
            "en_US-lessac-medium", real_entry))
        try:
            with patch("urllib.request.urlopen",
                        _fake_urlopen_factory(b"not-real", b"{}")):
                with self.assertRaises(VoiceDownloadError):
                    ensure_voice("en_US-lessac-medium")
            self.assertFalse((Path(self._tmp) / "en_US-lessac-medium"
                              / "en_US-lessac-medium.onnx").is_file())
        finally:
            vm.VOICE_INDEX["en_US-lessac-medium"] = real_entry

    def test_list_downloaded_returns_downloaded(self) -> None:
        d = Path(self._tmp) / "en_US-lessac-medium"
        d.mkdir(parents=True)
        (d / "en_US-lessac-medium.onnx").write_bytes(b"x")
        (d / "en_US-lessac-medium.onnx.json").write_bytes(b"{}")
        out = list_downloaded()
        self.assertIn("en_US-lessac-medium", out)

    def test_is_downloaded_partial_returns_false(self) -> None:
        self.assertFalse(is_downloaded("en_US-lessac-medium"))
        d = Path(self._tmp) / "en_US-lessac-medium"
        d.mkdir(parents=True)
        (d / "en_US-lessac-medium.onnx").write_bytes(b"x")
        self.assertFalse(is_downloaded("en_US-lessac-medium"))

    def test_sha256_utility(self) -> None:
        p = Path(self._tmp) / "h.txt"
        p.write_bytes(b"hello")
        self.assertEqual(_sha256(p),
                         hashlib.sha256(b"hello").hexdigest())


class PiperSwapperTests(unittest.TestCase):

    def test_set_voice_returns_handle(self) -> None:
        s = PiperSwapper()
        h = s.set_voice("en_US-lessac-medium")
        self.assertEqual(h.voice_id, "en_US-lessac-medium")
        self.assertIsInstance(h, PiperVoiceHandle)

    def test_set_voice_unknown_creates_stub(self) -> None:
        s = PiperSwapper()
        h = s.set_voice("xx_XY-bogus-low")
        self.assertFalse(h.loaded)

    def test_synth_returns_bytes_when_no_handle(self) -> None:
        s = PiperSwapper()
        out = s.synth("hello")
        self.assertEqual(out, b"")

    def test_synth_after_set_voice_returns_bytes(self) -> None:
        s = PiperSwapper()
        s.set_voice("en_US-lessac-medium")
        out = s.synth("hello")
        self.assertIsInstance(out, bytes)


class VoicePathTests(unittest.TestCase):

    def test_onnx_path(self) -> None:
        p = voice_path("en_US-lessac-medium", "onnx")
        self.assertEqual(p.name, "en_US-lessac-medium.onnx")

    def test_json_path(self) -> None:
        p = voice_path("en_US-lessac-medium", "json")
        self.assertEqual(p.name, "en_US-lessac-medium.onnx.json")


if __name__ == "__main__":
    unittest.main()
