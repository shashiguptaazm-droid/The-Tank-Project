"""Tests for tank_offload.offload_store."""
from __future__ import annotations

import time

import pytest

from tank_offload.offload_store import (
    STATUS_DEAD_LETTER,
    STATUS_PENDING,
    STATUS_STAGING,
    STATUS_UPLOADED,
    Item,
    OffloadStore,
    new_uuid,
)


@pytest.fixture
def store(tmp_path) -> OffloadStore:
    return OffloadStore(str(tmp_path / "manifest.db"))


def test_new_uuid_is_short_unique():
    ids = {new_uuid() for _ in range(64)}
    assert len(ids) == 64
    for u in ids:
        assert 8 <= len(u) <= 16


def test_enqueue_creates_pending_row(store: OffloadStore):
    item = store.enqueue("/var/tank/recordings/a.avi",
                          size_bytes=4096, kind="recording")
    assert item.status == STATUS_PENDING
    assert item.retry_count == 0
    assert item.size_bytes == 4096
    again = store.get(item.uuid)
    assert again is not None
    assert again.original_path == "/var/tank/recordings/a.avi"


def test_validate_transition_table():
    # pending can move to staging / uploaded / dead_letter
    assert OffloadStore.validate_transition(STATUS_PENDING, STATUS_STAGING)
    assert OffloadStore.validate_transition(STATUS_PENDING, STATUS_UPLOADED)
    assert OffloadStore.validate_transition(STATUS_PENDING, STATUS_DEAD_LETTER)
    # uploading can't escape
    assert not OffloadStore.validate_transition(STATUS_UPLOADED, STATUS_PENDING)
    assert not OffloadStore.validate_transition(STATUS_UPLOADED, STATUS_STAGING)
    assert not OffloadStore.validate_transition(STATUS_DEAD_LETTER, STATUS_UPLOADED)
    # Unknown state
    assert not OffloadStore.validate_transition("weird", STATUS_UPLOADED)


def test_transition_rejects_illegal(store: OffloadStore):
    item = store.enqueue("/p1", size_bytes=1, kind="recording")
    # First promote to uploaded (terminal)
    store.transition(item.uuid, to_status=STATUS_UPLOADED,
                      remote_path="by-uuid/p1__a.avi")
    # Now any further move must raise.
    with pytest.raises(ValueError):
        store.transition(item.uuid, to_status=STATUS_STAGING,
                          staged_path="/tmp/x")


def test_record_retry_increments_count_and_sets_next_ts(store: OffloadStore):
    item = store.enqueue("/p2", size_bytes=10, kind="log")
    updated = store.record_retry(item.uuid, "boom", next_delay_sec=60.0)
    assert updated.retry_count == 1
    assert updated.next_retry_ts > time.time() - 1.0
    assert updated.status == STATUS_PENDING


def test_due_for_retry_respects_next_retry_ts(store: OffloadStore):
    item = store.enqueue("/p3", size_bytes=1, kind="recording")
    store.record_retry(item.uuid, "boom", next_delay_sec=120.0)
    assert store.due_for_retry(now=time.time()) == []
    # Once we hit the next_retry_ts window, the row pops up.
    due_later = store.due_for_retry(now=item.updated_at + 999)
    assert any(it.uuid == item.uuid for it in due_later)


def test_counts_count_each_status(store: OffloadStore):
    a = store.enqueue("/a", size_bytes=1, kind="recording")
    b = store.enqueue("/b", size_bytes=1, kind="log")
    store.transition(a.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    c = store.enqueue("/c", size_bytes=1, kind="db_snapshot")
    store.transition(c.uuid, to_status=STATUS_DEAD_LETTER,
                      last_error="exhausted")
    counts = store.counts()
    assert counts[STATUS_UPLOADED] == 1
    assert counts[STATUS_PENDING] == 1   # b is still pending
    assert counts[STATUS_DEAD_LETTER] == 1


def test_list_uploads_and_deadletter(store: OffloadStore):
    a = store.enqueue("/a", size_bytes=1, kind="recording")
    store.transition(a.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    c = store.enqueue("/c", size_bytes=1, kind="db_snapshot")
    store.transition(c.uuid, to_status=STATUS_DEAD_LETTER,
                      last_error="x")
    uploads = store.list_uploads(limit=5)
    assert {it.uuid for it in uploads} == {a.uuid}
    dead = store.list_by_status(STATUS_DEAD_LETTER, limit=5)
    assert {it.uuid for it in dead} == {c.uuid}


def test_get_by_path_returns_latest(store: OffloadStore):
    a = store.enqueue("/var/p", size_bytes=1, kind="recording")
    store.transition(a.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    # An updated upload of the same path.
    b = store.enqueue("/var/p", size_bytes=2, kind="recording")
    assert b.uuid != a.uuid
    found = store.get_by_path("/var/p")
    assert found is not None
    assert found.uuid == b.uuid
    assert found.size_bytes == 2


def test_oldest_uploaded_at_and_total_bytes(store: OffloadStore):
    assert store.oldest_uploaded_at() is None
    assert store.total_uploaded_bytes() == 0
    a = store.enqueue("/a", size_bytes=1000, kind="recording")
    store.transition(a.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    b = store.enqueue("/b", size_bytes=4000, kind="log")
    time.sleep(0.01)   # ensure b.created_at > a.created_at
    store.transition(b.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    assert store.total_uploaded_bytes() == 5000
    assert store.oldest_uploaded_at() is not None


def test_truncate_removes_rows(store: OffloadStore):
    a = store.enqueue("/a", size_bytes=1, kind="recording")
    store.transition(a.uuid, to_status=STATUS_UPLOADED,
                      remote_path="x")
    n = store.truncate([STATUS_UPLOADED, STATUS_DEAD_LETTER])
    assert n == 1   # only one row matches
    assert store.counts()[STATUS_UPLOADED] == 0


def test_delete_round_trip(store: OffloadStore):
    a = store.enqueue("/a", size_bytes=1, kind="recording")
    assert store.delete(a.uuid) is True
    assert store.get(a.uuid) is None
    assert store.delete(a.uuid) is False
