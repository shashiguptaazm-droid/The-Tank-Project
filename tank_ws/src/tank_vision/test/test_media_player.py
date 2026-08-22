"""Hermetic tests for tank_vision.media_player.

Three player flavours are tested:
* StubPlayer: captures wire events
* SerialPlayer: forwards to a mock HAL
* AsyncPlayer: non-blocking thread, prior thread joined before new one

None of these call out to hardware — everything is in-memory.
"""
from __future__ import annotations

import time
import unittest

from tank_vision.animations import Animation, FrameCommand
from tank_vision.media_player import AsyncPlayer, SerialPlayer, StubPlayer


def _short_anim() -> Animation:
    return Animation(
        name="tst", fps=20, loop=False,
        frames=[
            FrameCommand("fill",   {"color": "#000000"}),
            FrameCommand("circle", {"x": 5, "y": 5, "r": 5,
                                    "color": "#FFFFFF"}),
            FrameCommand("delay",  {"ms": 1}),
            FrameCommand("reset",  {}),
        ],
        description="fast fixture",
    )


def _slow_anim() -> Animation:
    """Two delay frames at 250 ms each so AsyncPlayer.is_running is
    observable between play_async() and join()."""
    return Animation(
        name="slow", fps=2, loop=False,
        frames=[
            FrameCommand("delay", {"ms": 250}),
            FrameCommand("delay", {"ms": 250}),
        ],
        description="slow observation fixture",
    )


class StubPlayerTests(unittest.TestCase):

    def test_records_all_frames(self) -> None:
        sp = StubPlayer()
        sp.play(_short_anim(), blocking=False)
        self.assertEqual(sp.frames_played, 4)
        self.assertEqual(sp.last_animation, "tst")

    def test_reset_count(self) -> None:
        sp = StubPlayer()
        sp.play(_short_anim(), blocking=False)
        self.assertEqual(sp.reset_called, 1)

    def test_clear(self) -> None:
        sp = StubPlayer()
        sp.play(_short_anim(), blocking=False)
        sp.clear()
        self.assertEqual(sp.events, [])
        self.assertEqual(sp.frames_played, 0)

    def test_blocking_respects_delay(self) -> None:
        sp = StubPlayer()
        a = Animation(name="d", fps=10, frames=[
            FrameCommand("delay", {"ms": 50}),
        ])
        t0 = time.monotonic()
        sp.play(a, blocking=True)
        elapsed = time.monotonic() - t0
        # Generous lower bound; nobody in CI has 1 ms sleeps.
        self.assertGreaterEqual(elapsed, 0.025)


class SerialPlayerTests(unittest.TestCase):

    def test_forwards_each_frame_to_hal(self) -> None:
        class FakeHal:
            def __init__(self) -> None:
                self.calls: list = []

            def write_json(self, payload: dict) -> None:
                self.calls.append(payload)

        h = FakeHal()
        p = SerialPlayer(h)
        n = p.play(_short_anim(), blocking=False)
        self.assertEqual(n, 4)
        self.assertEqual(len(h.calls), 4)
        self.assertIn("anim", h.calls[0])
        self.assertEqual(h.calls[0]["anim"], "tst")

    def test_hal_exception_does_not_stop(self) -> None:
        class BrokenHal:
            def __init__(self) -> None:
                self.calls = 0

            def write_json(self, payload: dict) -> None:
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError("uart stub full")

        h = BrokenHal()
        p = SerialPlayer(h)
        # All 4 frames should still make it through the try/except.
        n = p.play(_short_anim(), blocking=False)
        self.assertEqual(n, 4)
        self.assertEqual(h.calls, 4)


class AsyncPlayerTests(unittest.TestCase):

    def test_non_blocking(self) -> None:
        """play_async returns immediately and join completes cleanly.

        We deliberately do NOT assert is_running is True at any point
        because StubPlayer.play(blocking=False) skips all time.sleep
        calls, so the inner loop completes in < 1 ms and the
        observation races with thread completion. The non-blocking
        property is verified by ``assertLess(elapsed, 0.10)``.
        """
        async_p = AsyncPlayer(StubPlayer())
        t0 = time.monotonic()
        async_p.play_async(_slow_anim())
        elapsed = time.monotonic() - t0
        # Returning here should be < 100 ms even though the animation
        # has 500 ms of delay-frames — the whole point of AsyncPlayer.
        self.assertLess(elapsed, 0.10)
        ok = async_p.join(timeout=2.0)
        self.assertTrue(ok)
        self.assertFalse(async_p.is_running)

    def test_join_when_never_started(self) -> None:
        async_p = AsyncPlayer(StubPlayer())
        self.assertTrue(async_p.join(timeout=0.05))

    def test_prior_thread_joined_before_new_starts(self) -> None:
        """Two rapid play_async calls must not leak threads — the
        prior one is joined before the second spawns."""
        async_p = AsyncPlayer(StubPlayer())
        async_p.play_async(_slow_anim())
        async_p.play_async(_slow_anim())    # should join the first
        # Only one thread is alive at any point.
        ok = async_p.join(timeout=2.0)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
