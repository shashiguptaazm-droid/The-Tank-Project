"""Plays an :class:`Animation` through any HAL object that exposes
``write_json(payload)``.

Three flavours:

* :class:`StubPlayer`     — records what it would have sent.
* :class:`SerialPlayer`   — calls the HAL on every frame.
* :class:`AsyncPlayer`     — runs in a daemon thread (non-blocking).

Used by ``eye_lcd_bridge``'s ``/eye/animation_play`` subscriber so an
animation over ``/eye/animation_play`` flows through the same UART
channel as the existing single-expression ``/eye_expression``.

Frame timing
------------
For each frame:
* a ``delay`` command consumes its own ``ms`` parameter.
* any other command paints one frame worth (= ``1 / anim.fps`` seconds)

This caps UART pressure: a 12 fps animation is ~12 small JSON writes
per second into the eye HAL — well under 115 200 bps' budget.

AsyncPlayer lifecycle
--------------------
The previous daemon thread is ``.join()``ed synchronously before a
new one starts. That avoids two animations racing on the same HAL
(the eyes would visually jitter) and prevents unbounded thread
accumulation if /eye/animation_play arrives in a tight loop.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

from .animations import Animation


class StubPlayer:
    """Records the wire JSON the player would have emitted.

    Default for tests + benches; the existing ``NullEyeSerialHal`` keeps
    using it via this adapter so the eye bridge still works without
    a real UART.
    """

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self.last_animation: Optional[str] = None
        self.frames_played: int = 0
        self.reset_called: int = 0

    def write_json(self, payload: Dict[str, Any]) -> None:
        self.events.append({"payload": dict(payload),
                            "ts": time.time()})
        if "anim" in payload:
            self.last_animation = payload["anim"]
        if payload.get("frame", {}).get("cmd") == "reset":
            self.reset_called += 1

    def play(self, anim: Animation, blocking: bool = True) -> int:
        frame_dt = 1.0 / max(1, anim.fps)
        for f in anim.frames:
            self.write_json({"anim": anim.name, "frame": f.to_dict()})
            self.frames_played += 1
            ms = 0
            if f.cmd == "delay":
                ms = int((f.args or {}).get("ms",
                    int(frame_dt * 1000)))
            if blocking and ms > 0:
                time.sleep(ms / 1000.0)
            elif blocking:
                time.sleep(frame_dt)
        return len(anim.frames)

    def clear(self) -> None:
        self.events.clear()
        self.last_animation = None
        self.frames_played = 0
        self.reset_called = 0


class SerialPlayer:
    """Forwards an Animation onto a real HAL (e.g. pyserial UART)."""

    def __init__(self, hal: Any) -> None:
        self._hal = hal

    def play(self, anim: Animation, blocking: bool = True) -> int:
        frame_dt = 1.0 / max(1, anim.fps)
        for f in anim.frames:
            payload = {"anim": anim.name, "frame": f.to_dict()}
            try:
                self._hal.write_json(payload)
            except Exception:
                # Untrusted HAL — keep going so a single bad frame can't
                # strand the whole animation. Logging is the caller's job.
                pass
            ms = 0
            if f.cmd == "delay":
                ms = int((f.args or {}).get("ms",
                    int(frame_dt * 1000)))
            if blocking and ms > 0:
                time.sleep(ms / 1000.0)
            elif blocking:
                time.sleep(frame_dt)
        return len(anim.frames)


class AsyncPlayer:
    """Run playback in a daemon thread so the ROS callback returns fast.

    Lifecycle:
      * :meth:`play_async` synchronously joins any previously-running
        playback thread *before* starting a new one, so two animations
        never race on the same HAL and we don't accumulate orphan
        daemon threads if /eye/animation_play is fired in a tight loop.
      * :meth:`join` is exposed for explicit shutdown.

    The synchronously-joined wait is intentional: callers are ROS
    callbacks which can absorb a one-second block here without
    starving other subscribers (this is the *single* long-running
    callback in the bridge node).
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._thread: Optional[threading.Thread] = None
        self._frames_target: int = 0

    def play_async(self, anim: Animation) -> None:
        if self._thread and self._thread.is_alive():
            # serial → no race condition possible; the eyes have time to
            # finish their blink before the new animation takes over.
            self._thread.join()
        self._frames_target = len(anim.frames)
        self._thread = threading.Thread(
            target=self._inner.play, args=(anim, False), daemon=True,
        )
        self._thread.start()

    def join(self, timeout: Optional[float] = None) -> bool:
        if not self._thread:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())


__all__ = ["StubPlayer", "SerialPlayer", "AsyncPlayer"]
