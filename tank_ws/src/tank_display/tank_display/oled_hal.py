"""OLED hardware abstraction layer.

Two implementations:

* :class:`NullOledHal` keeps an in-memory snapshot of every rendered
  frame (a copy of the PIL image + mood tag). Used in tests and on
  benches without the 1.3\" SH1106 panel attached.

* :class:`LumaOledHal` drives the panel over I²C using ``luma.oled``.
  Address ``0x70`` (matches WIRING.md Phase 2 OLED reservation) and a
  ``SH1106`` 128 × 64 controller.
"""
from __future__ import annotations

import collections
import math  # noqa: F401  — kept for diagnostic logging downstream
from typing import Optional

# 128 × 64 — native SH1106 resolution at I²C 0x70.
DEFAULT_WIDTH = 128
DEFAULT_HEIGHT = 64

# Cap the NullHal frame log so a long-running live node can't OOM.
_NULLHAL_FRAME_LOG_CAP = 64


class NullOledHal:
    """Test/bench HAL — stores every rendered frame as a copy of the PIL
    image plus the mood it was rendered for. Capped at
    ``_NULLHAL_FRAME_LOG_CAP`` entries so a long-running live node
    doesn't OOM."""

    _PIL_OK = None

    def __init__(self, width: int = DEFAULT_WIDTH,
                 height: int = DEFAULT_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.frames: collections.deque = collections.deque(
            maxlen=_NULLHAL_FRAME_LOG_CAP
        )

    @property
    def last_frame(self) -> Optional[dict]:
        return self.frames[-1] if self.frames else None

    def display(self, image, mood: str = "") -> None:
        # Always copy so later mutations of the caller's buffer don't
        # affect us (and so tests can compare images without aliasing).
        try:
            snapshot = image.copy()
        except Exception:
            snapshot = image
        self.frames.append({"mood": mood, "image": snapshot})

    def clear(self) -> None:
        pass

    def close(self) -> None:
        pass


class LumaOledHal:
    """luma.oled-backed HAL — speaks to the SH1106 panel over I²C.

    All luma imports are lazy so this module loads cleanly on benches
    that never have luma installed (NullHal is the default)."""

    def __init__(self, port: int = 1, address: int = 0x70,
                 width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
        try:
            from luma.core.interface.serial import i2c    # type: ignore
            from luma.oled.device import sh1106          # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "luma.oled is not installed but use_luma=True. "
                "Run `pip install luma.oled` on the Pi 5, or set "
                "`use_luma: false` in tank_display.yaml for bench mode."
            ) from exc
        self.width = width
        self.height = height
        self._device = sh1106(i2c(port=port, address=address))

    def display(self, image, mood: str = "") -> None:
        # sh1106 exposes display(image) on current luma. We never need
        # the legacy context-manager / paste path.
        self._device.display(image)

    def clear(self) -> None:
        try:
            self._device.clear()
            self._device.show()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._device.cleanup()  # type: ignore[attr-defined]
        except Exception:
            pass


def open_hal(use_luma: bool, *, port: int = 1, address: int = 0x70,
             width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
    """Build a HAL.  If ``use_luma`` is False (the bench default), return
    a :class:`NullOledHal` so tests don't need a panel attached."""
    if not use_luma:
        return NullOledHal(width=width, height=height)
    return LumaOledHal(port=port, address=address, width=width, height=height)
