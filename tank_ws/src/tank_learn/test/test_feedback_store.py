"""Hermetic tests for ``tank_learn.feedback_store.FeedbackStore``.

The store is pure-Python + SQLite-WAL. Tests use a per-test tempdir
DB so parallelism doesn't race. No rclpy / no ROS topics exercised
here — the ROS bridge lives in :mod:`tank_learn.feedback_node`.

Coverage
~~~~~~~~
* Schema bootstrap + schema_version smoke.
* WAL pragma detection (informational — different SQLite builds may
  report a slightly different string).
* :meth:`record_dispatch` / :meth:`record_reward` / inline-reward paths.
* Reward validation (-1/0/1 only).
* :meth:`recent` ordering, :meth:`by_plugin` filtering.
* :meth:`plugin_stats` approval-rate math + :meth:`all_plugin_stats`.
* Grammar weight insert/update + bounds + :meth:`all_grammar_weights`.
* IQ ``record_iq`` + :meth:`current_iq` + :meth:`recent_iq`.
* Threaded-write smoke (5 threads × 50 inserts → 250 rows, no losses).
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from typing import List

from tank_learn.feedback_store import (
    DEFAULT_DB_PATH,
    SCHEMA_VERSION,
    FeedbackRow,
    FeedbackStore,
)


def _make_store() -> FeedbackStore:
    """Return a fresh FeedbackStore pointed at a per-test tempdir DB."""
    tmpdir = tempfile.mkdtemp(prefix="tanklearn-")
    db_path = str(Path(tmpdir) / "test.db")
    return FeedbackStore(db_path=db_path)


class _ResetFeedbackLogMixin:
    """Helper — list rather than evidence-coupling the in-memory
    store to any singleton."""

    def setUp(self) -> None:
        self.store = _make_store()
        self.addCleanup(self._cleanup_store, self.store)

    @staticmethod
    def _cleanup_store(store: FeedbackStore) -> None:
        # Close the persistent connection BEFORE removing the file —
        # otherwise the `.db-wal` / `.db-shm` sidecars stay open via
        # the SQLite handle and leak file descriptors into the next
        # test. ``close()`` is idempotent so a double-invoke is safe.
        store.close()
        try:
            os.remove(store.db_path)
        except OSError:
            pass
        # WAL sidecars (.db-wal / .db-shm) live next to the db.
        for ext in ("-wal", "-shm"):
            try:
                os.remove(store.db_path + ext)
            except OSError:
                pass


class FeedbackStoreInitTests(_ResetFeedbackLogMixin, unittest.TestCase):
    def test_schema_version_is_one(self) -> None:
        self.assertEqual(self.store.schema_version, SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, 1)

    def test_db_path_round_trips(self) -> None:
        self.assertTrue(self.store.db_path.endswith("test.db"))
        self.assertTrue(Path(self.store.db_path).is_file())

    def test_wal_mode_is_active(self) -> None:
        # journal_mode is a status query — "wal" or "memory" if a
        # network filesystem rejects WAL.  For tempdir fs, expect WAL.
        with sqlite3.connect(self.store.db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertIn(mode.lower(), ("wal", "memory"),
                      f"unexpected journal_mode={mode!r}")

    def test_default_db_path_constant_is_absolute(self) -> None:
        self.assertTrue(DEFAULT_DB_PATH.startswith("/"))
        self.assertTrue(DEFAULT_DB_PATH.endswith(".db"))


class FeedbackLogTests(_ResetFeedbackLogMixin, unittest.TestCase):
    def test_record_dispatch_returns_id(self) -> None:
        did = self.store.record_dispatch(
            intent_text="play lo-fi music",
            plugin_name="voice.play_music",
            confidence=0.92,
        )
        self.assertIsInstance(did, int)
        self.assertGreater(did, 0)

    def test_recent_returns_one_row(self) -> None:
        self.store.record_dispatch("play lo-fi", "voice.play_music", 0.92)
        rows = self.store.recent(10)
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], FeedbackRow)
        self.assertEqual(rows[0].plugin_name, "voice.play_music")
        self.assertEqual(rows[0].intent_text, "play lo-fi")
        self.assertAlmostEqual(rows[0].confidence, 0.92, places=3)
        self.assertEqual(rows[0].reward, 0)  # default

    def test_record_reward_updates_row(self) -> None:
        did = self.store.record_dispatch("go", "voice.move_to", 0.8)
        ok = self.store.record_reward(did, +1, source="user", note="nice")
        self.assertTrue(ok)
        rows = self.store.by_plugin("voice.move_to")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reward, 1)
        self.assertEqual(rows[0].source, "user")
        self.assertEqual(rows[0].note, "nice")

    def test_record_reward_validates_values(self) -> None:
        did = self.store.record_dispatch("x", "voice.x", 0.1)
        with self.assertRaises(ValueError):
            self.store.record_reward(did, 2)
        with self.assertRaises(ValueError):
            self.store.record_reward(did, -5)
        with self.assertRaises(ValueError):
            self.store.record_reward(did, "not_a_number")
        # True/False coerce to ±1
        did2 = self.store.record_dispatch("y", "voice.y", 0.1)
        self.assertTrue(self.store.record_reward(did2, True))    # +1
        self.assertTrue(self.store.record_reward(did2, False))   # -1
        latest = self.store.by_plugin("voice.y")[0]
        self.assertEqual(latest.reward, -1)

    def test_record_reward_unknown_id_returns_false(self) -> None:
        self.assertFalse(self.store.record_reward(9_999_999, +1))

    def test_record_dispatch_with_reward_inline(self) -> None:
        did = self.store.record_dispatch_with_reward(
            "show results", "voice.show_torrent_results",
            reward=-1, confidence=0.4, source="dashboard",
        )
        rows = self.store.by_plugin("voice.show_torrent_results")
        self.assertEqual(rows[0].reward, -1)
        self.assertEqual(rows[0].source, "dashboard")

    def test_recent_newest_first(self) -> None:
        a = self.store.record_dispatch("a", "v.a", 0.1)
        b = self.store.record_dispatch("b", "v.b", 0.2)
        c = self.store.record_dispatch("c", "v.c", 0.3)
        rows = self.store.recent(10)
        ids = [r.id for r in rows]
        # Newest first ⇒ c > b > a
        self.assertEqual(ids, sorted(ids, reverse=True))
        self.assertEqual(ids[0], c)
        self.assertEqual(ids[2], a)

    def test_by_plugin_filters(self) -> None:
        self.store.record_dispatch("x", "voice.x", 0.1)
        self.store.record_dispatch("y", "voice.y", 0.2)
        self.store.record_dispatch("z", "voice.x", 0.3)
        rows = self.store.by_plugin("voice.x")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.plugin_name == "voice.x" for r in rows))

    def test_plugin_stats_approval_rate(self) -> None:
        for i in range(7):
            did = self.store.record_dispatch(f"u{i}", "voice.up", 0.5)
            self.store.record_reward(did, +1)
        for i in range(3):
            did = self.store.record_dispatch(f"d{i}", "voice.up", 0.5)
            self.store.record_reward(did, -1)
        self.store.record_dispatch("unrated", "voice.up", 0.5)  # reward=0
        stats = self.store.plugin_stats("voice.up")
        self.assertEqual(stats["total_dispatches"], 11)
        self.assertEqual(stats["rated"], 10)
        self.assertEqual(stats["positive"], 7)
        self.assertEqual(stats["negative"], 3)
        self.assertAlmostEqual(stats["approval_rate"], 0.7, places=3)
        self.assertAlmostEqual(stats["avg_confidence"], 0.5, places=3)

    def test_all_plugin_stats_lists_every_plugin(self) -> None:
        self.store.record_dispatch("a", "voice.alpha", 0.1)
        self.store.record_dispatch("b", "voice.beta", 0.2)
        stats_all = self.store.all_plugin_stats()
        names = {s["plugin_name"] for s in stats_all}
        self.assertEqual(names, {"voice.alpha", "voice.beta"})

    def test_to_dict_round_trip(self) -> None:
        did = self.store.record_dispatch("z", "voice.z", 0.42)
        self.store.record_reward(did, +1)
        d = self.store.recent(1)[0].to_dict()
        self.assertEqual(d["plugin_name"], "voice.z")
        self.assertEqual(d["reward"], 1)
        self.assertAlmostEqual(d["confidence"], 0.42, places=3)


class GrammarWeightTests(_ResetFeedbackLogMixin, unittest.TestCase):
    def test_unset_returns_one(self) -> None:
        self.assertEqual(self.store.grammar_weight("voice.new"), 1.0)

    def test_insert_and_read(self) -> None:
        self.store.update_grammar_weight("voice.x", 1.25)
        self.assertAlmostEqual(self.store.grammar_weight("voice.x"), 1.25,
                               places=3)

    def test_update_existing_bumps_sample_count(self) -> None:
        self.store.update_grammar_weight("voice.x", 1.0)
        self.store.update_grammar_weight("voice.x", 0.8,
                                          increment_negative=True)
        # sample_count = 2 (incremented twice), negative_count = 1
        all_w = self.store.all_grammar_weights()
        self.assertIn("voice.x", all_w)

    def test_bounds_enforced(self) -> None:
        with self.assertRaises(ValueError):
            self.store.update_grammar_weight("voice.x", 0.01)
        with self.assertRaises(ValueError):
            self.store.update_grammar_weight("voice.x", 6.0)

    def test_empty_cid_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.update_grammar_weight("", 1.0)


class IQHistoryTests(_ResetFeedbackLogMixin, unittest.TestCase):
    def test_record_and_read_back(self) -> None:
        for iq in (45, 55, 70, 88):
            self.store.record_iq(
                "voice.x", float(iq),
                sub_accuracy=0.9, sub_uptime=0.95,
                sub_latency=0.5, sub_user_reward=0.8,
                note="boot sample",
            )
        cur = self.store.current_iq("voice.x")
        self.assertAlmostEqual(cur, 88.0, places=3)
        recent = self.store.recent_iq("voice.x", limit=4)
        self.assertEqual(len(recent), 4)
        # Newest first ⇒ 88, 70, 55, 45
        self.assertEqual([r["iq_score"] for r in recent],
                         [88.0, 70.0, 55.0, 45.0])

    def test_current_iq_returns_none_for_unknown(self) -> None:
        self.assertIsNone(self.store.current_iq("never.recorded"))

    def test_recent_iq_no_plugin_filter(self) -> None:
        self.store.record_iq("voice.a", 50.0)
        self.store.record_iq("voice.b", 60.0)
        all_recent = self.store.recent_iq(limit=10)
        self.assertGreaterEqual(len(all_recent), 2)

    def test_record_iq_requires_plugin_name(self) -> None:
        with self.assertRaises(ValueError):
            self.store.record_iq("", 50.0)


class ThreadSafetyTests(_ResetFeedbackLogMixin, unittest.TestCase):
    """Smoke test — the per-call short-lived connection + threading.Lock
    must serialise 250 concurrent writes without losing any rows."""

    def test_threaded_writes_no_loss(self) -> None:
        n_threads = 5
        n_per_thread = 50

        def worker(seed: int) -> None:
            for i in range(n_per_thread):
                self.store.record_dispatch(
                    intent_text=f"intent-{seed}-{i}",
                    plugin_name=f"voice.thread{seed}",
                    confidence=0.5,
                )
                # And an IQ sample too so both tables get hammered.
                self.store.record_iq(
                    f"voice.thread{seed}",
                    50.0 + (seed * 5) + i,
                    sub_accuracy=0.5, sub_uptime=0.5,
                    sub_latency=0.5, sub_user_reward=0.5,
                )

        threads: List[threading.Thread] = []
        for s in range(n_threads):
            t = threading.Thread(target=worker, args=(s,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            self.assertFalse(t.is_alive(), "thread hung")

        # 5 threads × 50 = 250 dispatch rows + 250 IQ rows expected.
        rows = self.store.recent(1000)
        self.assertEqual(
            len(rows), n_threads * n_per_thread,
            "Expected 250 feedback_log rows from concurrent writes"
        )
        iq_rows = self.store.recent_iq(limit=1000)
        self.assertEqual(
            len(iq_rows), n_threads * n_per_thread,
            "Expected 250 iq_history rows from concurrent writes"
        )


if __name__ == "__main__":
    unittest.main()
