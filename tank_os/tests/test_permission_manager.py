"""pytest suite for :mod:`tank_os.core.permission_manager`."""
from __future__ import annotations

import threading
import time

import pytest

from tank_os.core.permission_manager import (
    PERMISSION_LABELS,
    Permission,
    PermissionManager,
)


# ───────────────────────────────────────────────────────────────────────────
# Default-deny policy
# ───────────────────────────────────────────────────────────────────────────

def test_default_deny_for_every_permission():
    pm = PermissionManager()
    pm.initialize()
    for perm in Permission:
        assert pm.check(perm) is False, f"{perm.name} should default-deny"


def test_snapshot_lists_every_defined_permission():
    pm = PermissionManager()
    pm.initialize()
    snap = pm.snapshot()
    assert set(snap.keys()) == {p.name for p in Permission}
    # All False initially.
    assert not any(snap.values())


def test_permission_labels_have_human_readable_strings():
    assert PERMISSION_LABELS[Permission.CAMERA] == "Camera"
    assert PERMISSION_LABELS[Permission.MICROPHONE] == "Microphone"
    assert PERMISSION_LABELS[Permission.UPDATE_INSTALL] == "Apply Updates"


# ───────────────────────────────────────────────────────────────────────────
# Grant / revoke / check
# ───────────────────────────────────────────────────────────────────────────

def test_grant_then_check_returns_true():
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.CAMERA)
    assert pm.check(Permission.CAMERA) is True
    snap = pm.snapshot()
    assert snap["CAMERA"] is True


def test_revoke_clears_grant(event_catcher):
    catcher = event_catcher("permission_revoked")
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.NETWORK)
    pm.revoke(Permission.NETWORK)
    assert pm.check(Permission.NETWORK) is False
    assert len(catcher.of("permission_revoked")) == 1


def test_grant_revoke_publishes_events(event_catcher):
    catcher = event_catcher("permission_granted", "permission_revoked")
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.STORAGE)
    pm.revoke(Permission.STORAGE)
    assert len(catcher.of("permission_granted")) == 1
    assert len(catcher.of("permission_revoked")) == 1


def test_grant_rejects_non_enum_input():
    pm = PermissionManager()
    pm.initialize()
    with pytest.raises(TypeError):
        pm.grant("CAMERA")  # type: ignore[arg-type]


# ───────────────────────────────────────────────────────────────────────────
# Async request flow
# ───────────────────────────────────────────────────────────────────────────

def test_request_short_circuits_when_already_granted(event_catcher):
    catcher = event_catcher("permission_requested")
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.CAMERA)
    req = pm.request(Permission.CAMERA, requester="chat", reason="vision")
    # Already-granted fast-path: resolved immediately, no bus noise.
    assert req.resolved is True
    assert req.granted is True
    assert catcher.count("permission_requested") == 0


def test_request_published_when_not_granted(event_catcher):
    catcher = event_catcher("permission_requested")
    pm = PermissionManager()
    pm.initialize()
    req = pm.request(Permission.LLM_ACCESS, requester="agent",
                     reason="dispatching prompt")
    assert req.resolved is False
    assert len(catcher.of("permission_requested")) == 1
    captured = catcher.of("permission_requested")[0]
    assert captured.data["permission"] == "LLM_ACCESS"
    assert captured.data["requester"] == "agent"


def test_resolve_via_grant_unblocks_waiter(event_catcher):
    """Granting on a different thread resolves the pending future and
    emits ``permission_granted``."""
    catcher = event_catcher("permission_granted")
    pm = PermissionManager()
    pm.initialize()
    req = pm.request(Permission.UPDATE_INSTALL,
                     requester="ota",
                     reason="image pin update")
    assert req.resolved is False
    # ``done`` is set after the worker thread has fully returned from
    # grant() — only then is the bus emit guaranteed to have landed.
    done = threading.Event()
    def _grant_soon():
        try:
            time.sleep(0.05)
            pm.grant(Permission.UPDATE_INSTALL, requester="user")
        finally:
            done.set()
    worker = threading.Thread(target=_grant_soon, daemon=True)
    worker.start()
    granted = req.wait(timeout=2.0)
    assert granted is True
    assert req.granted is True
    # Block until the worker has actually finished grant() so the bus
    # emit has landed before we count captured events.
    assert done.wait(timeout=2.0), "worker thread never reported done"
    worker.join(timeout=2.0)
    assert len(catcher.of("permission_granted")) == 1


def test_cancel_pending_request_returns_false_in_wait():
    pm = PermissionManager()
    pm.initialize()
    req = pm.request(Permission.PLUGIN_INSTALL, requester="t")
    assert pm.cancel(req.id) is True
    assert req.wait(timeout=0.5) is False
    # Second cancel returns False — already resolved.
    assert pm.cancel(req.id) is False


def test_require_returns_true_when_already_granted():
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.STORAGE)
    assert pm.require(Permission.STORAGE) is True


# ───────────────────────────────────────────────────────────────────────────
# Reset / history
# ───────────────────────────────────────────────────────────────────────────

def test_reset_clears_every_grant(event_catcher):
    catcher = event_catcher("permissions_reset")
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.CAMERA)
    pm.grant(Permission.MICROPHONE)
    pm.grant(Permission.STORAGE)
    pm.reset()
    snap = pm.snapshot()
    assert all(v is False for v in snap.values())
    assert len(catcher.of("permissions_reset")) == 1


def test_history_bounded_at_max():
    pm = PermissionManager()
    pm.initialize()
    for _ in range(pm._MAX_HISTORY + 60):
        pm.grant(Permission.CAMERA)
    assert len(pm.history(limit=10_000)) <= pm._MAX_HISTORY


def test_all_grants_returns_only_true():
    pm = PermissionManager()
    pm.initialize()
    pm.grant(Permission.CAMERA)
    pm.grant(Permission.NETWORK)
    pm.grant(Permission.STORAGE)
    granted = {p.name for p in pm.all_grants()}
    assert granted == {"CAMERA", "NETWORK", "STORAGE"}


def test_request_rejects_non_enum_input():
    pm = PermissionManager()
    pm.initialize()
    with pytest.raises(TypeError):
        pm.request("CAMERA")  # type: ignore[arg-type]
