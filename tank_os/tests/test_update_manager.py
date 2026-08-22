"""pytest suite for :mod:`tank_os.core.update_manager`."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from tank_os.core.update_manager import (
    LocalManifestProvider,
    ScriptsOTAProvider,
    UpdateInfo,
    UpdateManager,
    UpdateProvider,
    UpdateSnapshot,
)


# ───────────────────────────────────────────────────────────────────────────
# Bundled providers
# ───────────────────────────────────────────────────────────────────────────

def test_bundled_providers_present_at_init():
    um = UpdateManager()
    assert "local-manifest" in um.list_providers()
    assert "tank-ota" in um.list_providers()


def test_register_provider_rejects_non_subclass():
    um = UpdateManager()
    with pytest.raises(TypeError):
        um.register_provider(object())  # type: ignore[arg-type]


# ───────────────────────────────────────────────────────────────────────────
# LocalManifestProvider
# ───────────────────────────────────────────────────────────────────────────

def test_local_manifest_provider_parses_valid_entries(tmp_path: Path):
    manifest = tmp_path / "update_manifest.json"
    manifest.write_text(json.dumps([
        {"id": "u1", "source": "local",
         "version_from": "1.0", "version_to": "1.1",
         "summary": "fix bug"},
        {"id": "u2", "source": "local",
         "version_from": "2.0", "version_to": "2.1",
         "summary": "new feature", "size_bytes": 4096,
         "requires_reboot": True},
    ]), encoding="utf-8")
    prov = LocalManifestProvider(manifest_path=manifest)
    updates = prov.check()
    assert len(updates) == 2
    [u1, u2] = updates
    assert u1.id == "u1"
    assert u1.version_from == "1.0"
    assert u1.version_to == "1.1"
    assert u2.requires_reboot is True
    assert u2.size_bytes == 4096


def test_local_manifest_provider_handles_missing_file(tmp_path: Path):
    prov = LocalManifestProvider(manifest_path=tmp_path / "missing.json")
    assert prov.check() == []


def test_local_manifest_provider_per_entry_try_except(tmp_path: Path):
    """Each manifest entry is parsed under ``try / except`` so a single
    entry that fails coercion (e.g. ``size_bytes`` not an int) is
    silently skipped while well-formed entries still load."""
    manifest = tmp_path / "update_manifest.json"
    manifest.write_text(json.dumps([
        {"id": "good", "source": "local",
         "version_from": "1", "version_to": "2"},
        # `size_bytes` fails coercion (int("not_an_int") raises) →
        # entry skipped, well-formed neighbours still survive.
        {"id": "bad", "source": "local",
         "version_from": "1", "version_to": "2",
         "size_bytes": "not_an_int"},
        {"id": "good2", "source": "local",
         "version_from": "x", "version_to": "y"},
    ]), encoding="utf-8")
    prov = LocalManifestProvider(manifest_path=manifest)
    updates = prov.check()
    assert {u.id for u in updates} == {"good", "good2"}


def test_local_manifest_provider_handles_corrupt_json(tmp_path: Path):
    manifest = tmp_path / "update_manifest.json"
    manifest.write_text("not json{", encoding="utf-8")
    prov = LocalManifestProvider(manifest_path=manifest)
    assert prov.check() == []


# ───────────────────────────────────────────────────────────────────────────
# ScriptsOTAProvider
# ───────────────────────────────────────────────────────────────────────────

def test_scripts_ota_provider_heartbeat(tmp_path: Path):
    # Mirror the repo's real scripts/ota.py location so the provider
    # detects it; otherwise it should just report "unavailable".
    repo_root = Path(__file__).resolve().parents[2]
    ota = repo_root / "scripts" / "ota.py"
    if not ota.is_file():
        pytest.skip("scripts/ota.py not present in this checkout")
    prov = ScriptsOTAProvider()
    assert prov.is_available() is True
    updates = prov.check()
    assert any(u.id == "ota-heartbeat" for u in updates)


def test_scripts_ota_provider_dry_run_apply_succeeds(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    if not (repo_root / "scripts" / "ota.py").is_file():
        pytest.skip("scripts/ota.py not present in this checkout")
    prov = ScriptsOTAProvider()
    target = UpdateInfo(id="x", source="tank-ota",
                        version_from="a", version_to="b")
    assert prov.apply(target, dry_run=True) is True


# ───────────────────────────────────────────────────────────────────────────
# UpdateManager.check
# ───────────────────────────────────────────────────────────────────────────

def test_check_emits_started_and_completed_events(event_catcher):
    catcher = event_catcher("update_check_started",
                            "update_check_completed",
                            "update_available")
    um = UpdateManager()
    um.initialize()
    # Replace providers with a deterministic one for the test.
    class _Fixed(UpdateProvider):
        def __init__(self):
            super().__init__("fixed")
        def check(self) -> List[UpdateInfo]:
            return [UpdateInfo(id="x", source="fixed",
                               version_from="1", version_to="2",
                               summary="deterministic")]
    um._providers = {"fixed": _Fixed()}
    found = um.check()
    assert len(found) == 1
    assert found[0].id == "x"
    assert um.last_checked() > 0
    assert len(catcher.of("update_check_started")) == 1
    [completed] = catcher.of("update_check_completed")
    assert completed.data["count"] == 1
    assert len(catcher.of("update_available")) == 1


def test_check_swallows_provider_exception(event_catcher):
    catcher = event_catcher("update_check_completed")
    um = UpdateManager()
    um.initialize()

    class _Boom(UpdateProvider):
        def __init__(self):
            super().__init__("boom")
        def check(self):
            raise RuntimeError("provider crashed")

    class _Good(UpdateProvider):
        def __init__(self):
            super().__init__("good")
        def check(self):
            return [UpdateInfo(id="g", source="good",
                               version_from="1", version_to="2")]

    um._providers = {"boom": _Boom(), "good": _Good()}
    found = um.check()
    assert [u.id for u in found] == ["g"]
    [completed] = catcher.of("update_check_completed")
    assert completed.data["count"] == 1


# ───────────────────────────────────────────────────────────────────────────
# UpdateManager.apply / rollback
# ───────────────────────────────────────────────────────────────────────────

def test_apply_dry_run_with_default_provider_returns_true():
    um = UpdateManager()
    um.initialize()

    class _DefaultApply(UpdateProvider):
        def __init__(self):
            super().__init__("default-apply")
        def check(self):
            return []

    um._providers = {"default-apply": _DefaultApply()}
    um._available = [UpdateInfo(
        id="u1", source="default-apply",
        version_from="1", version_to="2", summary="x",
    )]
    # Base-class apply returns dry_run bool → True on dry-run.
    assert um.apply("u1", dry_run=True) is True


def test_apply_unknown_update_id_returns_false():
    um = UpdateManager()
    um.initialize()
    assert um.apply("missing-id", dry_run=False) is False
    assert um.apply("missing-id", dry_run=True) is False


def test_apply_calls_provider_with_real_run(event_catcher):
    catcher = event_catcher("update_applying", "update_completed")
    um = UpdateManager()
    um.initialize()

    class _DoIt(UpdateProvider):
        def __init__(self):
            super().__init__("doit")
        def check(self):
            return []
        def apply(self, update, *, dry_run=False):
            return True

    um._providers = {"doit": _DoIt()}
    um._available = [UpdateInfo(
        id="u1", source="doit",
        version_from="1", version_to="2", summary="x",
    )]
    assert um.apply("u1", dry_run=False) is True
    assert len(catcher.of("update_applying")) == 1
    assert len(catcher.of("update_completed")) == 1
    # Check duration is recorded in history.
    assert um.history(limit=10)[-1]["ok"] is True


def test_rollback_unknown_snapshot_returns_false():
    um = UpdateManager()
    um.initialize()
    assert um.rollback("nope", dry_run=False) is False


def test_rollback_missing_provider_returns_false():
    um = UpdateManager()
    um.initialize()
    snap = UpdateSnapshot(id="s1", captured_at=0.0, source="missing",
                          version_from="a", version_to="b")
    um._snapshots["s1"] = snap
    assert um.rollback("s1", dry_run=False) is False


# ───────────────────────────────────────────────────────────────────────────
# Snapshot capture + history bounds
# ───────────────────────────────────────────────────────────────────────────

def test_capture_snapshot_returns_record_with_id_and_source():
    um = UpdateManager()
    um.initialize()
    target = UpdateInfo(id="u1", source="local",
                        version_from="1", version_to="2")
    snap = um._capture_snapshot(target)
    assert snap.id.startswith("snap_")
    assert snap.source == "local"
    assert snap.version_from == "1"
    assert snap.version_to == "2"
    assert snap.notes == "auto-captured for rollback"


def test_available_returns_copy_of_internal_list():
    um = UpdateManager()
    um.initialize()
    um._available = [UpdateInfo(id="x", source="local",
                                version_from="1", version_to="2")]
    snap = um.available()
    assert len(snap) == 1
    # Mutating the snapshot must not affect internal state.
    snap.clear()
    assert len(um._available) == 1
