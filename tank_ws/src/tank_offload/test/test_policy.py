"""Tests for tank_offload.policy."""
from __future__ import annotations

import os
import time

import pytest

from tank_offload.policy import (
    EXCLUDED_PREFIXES,
    KIND_DB_SNAPSHOT,
    KIND_LOG,
    KIND_RECORDING,
    ALL_KINDS,
    OffloadPolicy,
    PolicyConfig,
    _is_excluded,
)


# -------------------- _is_excluded --------------------

def test_is_excluded_dev_sys_proc():
    for prefix in ("/dev", "/sys", "/proc", "/tmp"):
        assert _is_excluded(prefix) is not None
        assert _is_excluded(os.path.join(prefix, "anything")) is not None


def test_is_excluded_wal_shm():
    assert _is_excluded("/var/tank/data/memory.db-wal") is not None
    assert _is_excluded("/var/tank/data/memory.db-shm") is not None


def test_is_excluded_accepts_avi_recording(tmp_path):
    f = tmp_path / "normal.avi"
    f.write_bytes(b"\x00\x00")
    assert _is_excluded(str(f)) is None


# -------------------- PolicyConfig defaults --------------------

def test_policy_config_defaults_are_sane():
    cfg = PolicyConfig()
    assert cfg.recording_max_age_days > 0
    assert cfg.db_snapshot_max_age_days > 0
    assert cfg.log_min_bytes > 0
    assert cfg.max_per_kind > 0


# -------------------- candidates() --------------------

@pytest.fixture
def media_layout(tmp_path):
    """Stand up a tiny /var/tank-like layout under ``tmp_path`` so the
    OffloadPolicy can walk it deterministically."""
    base = tmp_path
    recordings = base / "recordings"
    logs = base / "logs"
    data = base / "data"
    for d in (recordings, logs, data):
        d.mkdir()

    # recording 1 \u2014 40 days old
    r1 = recordings / "a_old.avi"
    r1.write_bytes(b"A" * 1024)
    os.utime(r1, (time.time() - 40 * 86400, time.time() - 40 * 86400))

    # recording 2 \u2014 5 days old (above threshold, should NOT be picked)
    r2 = recordings / "b_fresh.avi"
    r2.write_bytes(b"B" * 1024)
    os.utime(r2, (time.time() - 5 * 86400, time.time() - 5 * 86400))

    # log rotated \u2014 1 MB (below default, should NOT be picked)
    l1 = logs / "small.log"
    l1.write_bytes(b"X" * (1024 * 1024))

    # DB snapshot \u2014 14 days old
    db1 = data / "memory-20240901.tar.gz"
    db1.write_bytes(b"Z" * 1024)
    os.utime(db1, (time.time() - 14 * 86400, time.time() - 14 * 86400))

    # DB snapshot \u2014 2 days old (above 7d default, should NOT be picked)
    db2 = data / "memory-fresh.tar.gz"
    db2.write_bytes(b"Y" * 1024)
    os.utime(db2, (time.time() - 2 * 86400, time.time() - 2 * 86400))

    return {
        "recordings": str(recordings),
        "logs": str(logs),
        "data": str(data),
        "base": str(base),
        "r1": str(r1), "r2": str(r2),
        "l1": str(l1),
        "db1": str(db1), "db2": str(db2),
    }


def _cfg(media):
    return PolicyConfig(
        recordings_glob=os.path.join(media["recordings"], "*.avi"),
        logs_glob=os.path.join(media["logs"], "*.log"),
        db_snapshot_glob=os.path.join(media["data"], "*.tar.gz"),
        recording_max_age_days=30.0,
        db_snapshot_max_age_days=7.0,
        log_min_bytes=50 * 1024 * 1024,   # 50 MB
    )


def test_candidates_recording_age_filter(media_layout):
    cfg = _cfg(media_layout)
    policy = OffloadPolicy(cfg)
    rec_only = policy.candidates([KIND_RECORDING])
    paths = {c.path for c in rec_only}
    assert media_layout["r1"] in paths
    assert media_layout["r2"] not in paths


def test_candidates_log_size_filter(media_layout):
    cfg = _cfg(media_layout)
    # Lower the log threshold so the 1MB file passes.
    cfg.log_min_bytes = 512 * 1024
    policy = OffloadPolicy(cfg)
    log_only = policy.candidates([KIND_LOG])
    paths = {c.path for c in log_only}
    assert media_layout["l1"] in paths


def test_candidates_db_snapshot_age_filter(media_layout):
    cfg = _cfg(media_layout)
    policy = OffloadPolicy(cfg)
    db_only = policy.candidates([KIND_DB_SNAPSHOT])
    paths = {c.path for c in db_only}
    assert media_layout["db1"] in paths
    assert media_layout["db2"] not in paths


def test_candidates_union_with_max_per_kind(media_layout):
    cfg = _cfg(media_layout)
    cfg.max_per_kind = 1
    policy = OffloadPolicy(cfg)
    candidates = policy.candidates(ALL_KINDS)
    # max 1 per kind + cross-kind largest-first cap
    counts: Dict[str, int] = {}
    for c in candidates:
        counts[c.kind] = counts.get(c.kind, 0) + 1
    for k, v in counts.items():
        assert v <= 1, f"{k} should be capped at 1; got {v}"


def test_candidates_excludes_wal_shm(tmp_path):
    # Even if a .db-wal sits in the db_snapshot dir because of a
    # shell-quoting bug, the policy should skip it.
    data = tmp_path / "data"
    data.mkdir()
    wal = data / "memory.db-wal"
    wal.write_bytes(b"X" * 1024)
    os.utime(wal, (time.time() - 14 * 86400, time.time() - 14 * 86400))
    cfg = PolicyConfig(
        db_snapshot_glob=str(data / "*.tar.gz"),
        db_snapshot_max_age_days=7.0,
    )
    policy = OffloadPolicy(cfg)
    out = policy.candidates([KIND_DB_SNAPSHOT])
    assert all("db-wal" not in c.path for c in out)


def test_dry_run_returns_each_kind_bucket(media_layout):
    cfg = _cfg(media_layout)
    cfg.log_min_bytes = 512 * 1024
    policy = OffloadPolicy(cfg)
    out = policy.dry_run()
    assert set(out) == set(ALL_KINDS)
    assert any(c.path == media_layout["r1"] for c in out[KIND_RECORDING])


def test_explain_handles_missing_file(tmp_path):
    cfg = _cfg({**{
        "recordings": str(tmp_path),
        "logs": str(tmp_path),
        "data": str(tmp_path),
        "base": str(tmp_path),
        "r1": str(tmp_path / "ghost.avi"),
        "r2": str(tmp_path / "ghost.avi"),
        "l1": str(tmp_path / "ghost.log"),
        "db1": str(tmp_path / "ghost.tar.gz"),
        "db2": str(tmp_path / "ghost.tar.gz"),
    }})
    policy = OffloadPolicy(cfg)
    msg = policy.explain("/no/such/file.avi")
    assert "not found" in msg or "stat" in msg or "size=" not in msg
