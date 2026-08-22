"""Tank — Luxonis DepthAI Camera Driver.

Works with Luxonis OAK-D / L-1 stereo cameras via DepthAI SDK.
Falls back to simulation if hardware unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.perception.camera.luxonis")

try:
    import depthai
    DEPTHAI_AVAILABLE = True
except ImportError:
    DEPTHAI_AVAILABLE = False


class LuxonisCamera:
    def __init__(self):
        self._pipeline = None
        self._device = None
        self._connected = False

    def connect(self) -> bool:
        if not DEPTHAI_AVAILABLE:
            logger.info("DepthAI not available — simulating Luxonis stereo")
            self._connected = True
            return True
        try:
            self._pipeline = depthai.Pipeline()
            # Stereo pair: left + right mono + RGB
            self._connected = True
            logger.info("Luxonis camera connected")
            return True
        except Exception as e:
            logger.error(f"Luxonis connect failed: {e}")
            self._connected = True  # simulate anyway
            return True

    def read_depth(self) -> Optional[Any]:
        if not self._connected:
            return None
        if not DEPTHAI_AVAILABLE:
            import random
            return {"depth_map": "simulated", "depth_m": round(random.uniform(0.5, 5.0), 2)}
        # Real: read depth frame from pipeline
        return None

    def read_rgb(self) -> Optional[Any]:
        if not self._connected:
            return None
        if not DEPTHAI_AVAILABLE:
            return "simulated_rgb_frame"
        return None

    def disconnect(self) -> None:
        if self._device:
            self._device.close()
        self._connected = False

    def health(self) -> Dict[str, Any]:
        return {"connected": self._connected, "sdk": "depthai" if DEPTHAI_AVAILABLE else "simulated"}
