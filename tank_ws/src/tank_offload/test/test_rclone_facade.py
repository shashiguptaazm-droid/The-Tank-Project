"""Tests for tank_offload.rclone_facade.

``subprocess.run`` is patched via ``unittest.mock`` so the tests never
invoke rclone. We assert on (a) the cmd line shape, (b) the env
pass-through, and (c) retry / dead-letter helpers.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from tank_offload.rclone_facade import (
    DEFAULT_BWLIMIT,
    MAX_RETRIES,
    RcloneConfig,
    RcloneFacade,
    RcloneResult,
    _hash_secret,
    build_copy_cmd,
    rclone_env,
)


@pytest.fixture
def cfg(tmp_path) -> RcloneConfig:
    return RcloneConfig(
        nextcloud_url="https://vps.example/remote.php/dav/files/alice",
        nextcloud_user="alice",
        nextcloud_password="hunter2-secret-NEVER-LOG",
        staging_dir=str(tmp_path / "staging"),
        deadletter_dir=str(tmp_path / "deadletter"),
        bwlimit="2M",
    )


def test_hash_secret_redacts_to_stable_tag():
    assert _hash_secret("hunter2") == _hash_secret("hunter2")
    assert _hash_secret("hunter2") != _hash_secret("hunter3")
    assert _hash_secret("") == ""
    assert _hash_secret("hunter2").startswith("sha256:")


def test_redact_omits_plaintext_password(cfg: RcloneConfig):
    out = cfg.redact()
    assert "hunter2-secret-NEVER-LOG" not in str(out)
    assert out["nextcloud_password_hash"].startswith("sha256:")
    assert out["nextcloud_url"] == cfg.nextcloud_url


def test_is_credentialed_requires_url_user_password():
    bare = RcloneConfig()
    assert not bare.is_credentialed()
    partial = RcloneConfig(nextcloud_url="x")
    assert not partial.is_credentialed()
    full = RcloneConfig(nextcloud_url="x", nextcloud_user="y",
                          nextcloud_password="z")
    assert full.is_credentialed()


def test_rclone_env_sets_overrides_without_writing_disk(cfg: RcloneConfig):
    env = rclone_env(cfg)
    # Override mode \u2014 no RCLONE_CONFIG file pointed at.
    assert env["RCLONE_CONFIG"] == "=/dev/null"
    assert env["RCLONE_CONFIG_NEXTCLOUD_URL"] == cfg.nextcloud_url
    assert env["RCLONE_CONFIG_NEXTCLOUD_USER"] == cfg.nextcloud_user
    assert env["RCLONE_CONFIG_NEXTCLOUD_PASS"] == cfg.nextcloud_password
    assert env["RCLONE_CONFIG_NEXTCLOUD_TYPE"] == "webdav"
    assert env["RCLONE_CONFIG_NEXTCLOUD_VENDOR"] == "nextcloud"
    # Important: the plaintext password is in env, but only the
    # ``subprocess.run`` call reads it; nothing persists to disk.
    assert "hunter2-secret-NEVER-LOG" in env["RCLONE_CONFIG_NEXTCLOUD_PASS"]


def test_build_copy_cmd_has_required_flags(cfg: RcloneConfig):
    cmd = build_copy_cmd(cfg, "/tmp/x.avi", "by-uuid/x.avi")
    assert cmd[0] == "rclone"
    assert cmd[1] == "copy"
    assert "--retries" in cmd
    assert "--bwlimit" in cmd
    assert "2M" in cmd
    assert "by-uuid/x.avi" in cmd[-1]


def test_build_copy_cmd_with_crypt_overlay(tmp_path):
    cfg = RcloneConfig(
        nextcloud_url="https://x", nextcloud_user="u",
        nextcloud_password="p",
        crypt_remote_name="tankcrypt",
        staging_dir=str(tmp_path / "s"),
        deadletter_dir=str(tmp_path / "d"),
    )
    cmd = build_copy_cmd(cfg, "/tmp/x.avi", "/")
    assert cmd[-1].startswith("tankcrypt:")


# ----- facade: stage / unstage / deadletter / copy_once -----

def test_stage_moves_file_to_staging(cfg: RcloneConfig, tmp_path):
    facade = RcloneFacade(cfg)
    src = tmp_path / "src.avi"
    src.write_bytes(b"X" * 1024)
    stage = facade.stage(str(src), "deadbeef")
    assert not os.path.isfile(str(src))
    assert os.path.isfile(stage.staged_path)
    assert stage.staged_path.startswith(cfg.staging_dir)
    assert stage.remote_path == "by-uuid/deadbeef__src.avi"


def test_stage_is_idempotent_on_repeat(cfg: RcloneConfig, tmp_path):
    facade = RcloneFacade(cfg)
    src = tmp_path / "dup.avi"
    src.write_bytes(b"X")
    stage1 = facade.stage(str(src), "abc")
    # Staged path now exists; second call must reuse it (no exception).
    stage2 = facade.stage(str(src), "abc")
    assert stage1.staged_path == stage2.staged_path


def test_unstage_removes_file(cfg: RcloneConfig, tmp_path):
    facade = RcloneFacade(cfg)
    src = tmp_path / "gone.avi"
    src.write_bytes(b"Y")
    stage = facade.stage(str(src), "u1")
    facade.unstage(stage.staged_path)
    assert not os.path.isfile(stage.staged_path)


def test_deadletter_moves_into_dl_dir(cfg: RcloneConfig, tmp_path):
    facade = RcloneFacade(cfg)
    src = tmp_path / "boom.avi"
    src.write_bytes(b"Z")
    stage = facade.stage(str(src), "u2")
    dl = facade.deadletter(stage.staged_path, "u2")
    assert dl.startswith(cfg.deadletter_dir)
    assert os.path.isfile(dl)
    assert not os.path.isfile(stage.staged_path)


# ----- copy_once (mocked subprocess) -----

def _ok_proc(stdout="", stderr=""):
    p = MagicMock()
    p.returncode = 0
    p.stdout = stdout
    p.stderr = stderr
    return p


def _fail_proc(returncode=1, stderr="boom"):
    p = MagicMock()
    p.returncode = returncode
    p.stdout = ""
    p.stderr = stderr
    return p


def test_copy_once_success(cfg: RcloneConfig, tmp_path):
    facade = RcloneFacade(cfg)
    with patch("subprocess.run",
               return_value=_ok_proc("done", "")) as pr:
        res = facade.copy_once("/tmp/x", "by-uuid/x")
    assert res.ok is True
    assert res.returncode == 0
    assert res.error == ""
    # Last arg to subprocess.run should be a list
    args, kwargs = pr.call_args
    cmd = args[0]
    assert cmd[0] == "rclone"
    assert cmd[1] == "copy"


def test_copy_once_failure_captures_stderr_tail(cfg: RcloneConfig):
    facade = RcloneFacade(cfg)
    with patch("subprocess.run",
               return_value=_fail_proc(13, "fatal: rate-limited")):
        res = facade.copy_once("/tmp/x", "by-uuid/x")
    assert res.ok is False
    assert res.returncode == 13
    assert "rate-limited" in res.stderr_tail
    assert "exit 13" in res.error


def test_copy_once_timeout(cfg: RcloneConfig):
    facade = RcloneFacade(cfg)
    with patch("subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd="rclone", timeout=1800)):
        res = facade.copy_once("/tmp/x", "by-uuid/x")
    assert res.ok is False
    assert "timeout" in res.error


def test_copy_once_missing_rclone(cfg: RcloneConfig):
    facade = RcloneFacade(cfg)
    with patch("subprocess.run",
               side_effect=FileNotFoundError("no such file: rclone")):
        res = facade.copy_once("/tmp/x", "by-uuid/x")
    assert res.ok is False
    assert "rclone missing" in res.error


# ----- retry helpers -----

def test_compute_retry_delay_grows_but_caps():
    facade = RcloneFacade(RcloneConfig())
    assert facade.compute_retry_delay(0) == 30.0
    assert facade.compute_retry_delay(1) == 60.0
    assert facade.compute_retry_delay(2) == 120.0
    # Cap at 600s forever, even with huge retry counts.
    assert facade.compute_retry_delay(20) == 600.0


def test_exhausted_threshold():
    facade = RcloneFacade(RcloneConfig())
    assert not facade.exhausted(0)
    assert not facade.exhausted(MAX_RETRIES - 1)
    assert facade.exhausted(MAX_RETRIES)
    assert facade.exhausted(MAX_RETRIES + 1)


def test_dry_run_returns_cmd_shape(cfg: RcloneConfig):
    facade = RcloneFacade(cfg)
    out = facade.dry_run("/tmp/src.avi", "u3")
    assert out["would_copy"] == "/tmp/src.avi"
    assert out["cmd"][0] == "rclone"
    assert out["credentialed"] is True
    assert out["bwlimit"] == "2M"
