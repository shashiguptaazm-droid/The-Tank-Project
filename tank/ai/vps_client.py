"""Tank — VPS AI Client.

Robust HTTPS client with auth, retries, backoff, health checks.
Falls back to OFFLINE_MODE if VPS unavailable — never crashes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("tank.vps")


class VPSClient:
    def __init__(self, url: str, api_key: str, timeout: float = 30.0,
                 retries: int = 3, backoff_base: float = 1.0) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._retries = retries
        self._backoff_base = backoff_base
        self._healthy = False
        self._last_check = 0.0
        self._check_interval = 30.0
        self._request_count = 0
        self._error_count = 0

    def is_healthy(self) -> bool:
        now = time.time()
        if now - self._last_check < self._check_interval:
            return self._healthy
        self._last_check = now
        try:
            resp = self._request("/health")
            self._healthy = resp is not None
        except Exception:
            self._healthy = False
        return self._healthy

    def detect(self, frame_data: bytes) -> Dict[str, Any]:
        return self._call("/detect", {"frame": frame_data.hex()})

    def classify(self, label: str) -> Dict[str, Any]:
        return self._call("/classify", {"label": label})

    def reason(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._call("/reason", context)

    def _call(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        for attempt in range(self._retries):
            try:
                resp = requests.post(
                    f"{self._url}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=self._timeout,
                )
                self._request_count += 1
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                self._error_count += 1
                wait = self._backoff_base * (2 ** attempt)
                logger.warning(f"VPS call {path} attempt {attempt+1} failed: {e}, retry in {wait}s")
                time.sleep(wait)
        logger.error(f"VPS call {path} failed after {self._retries} attempts")
        return {"error": "vps_unavailable", "offline_mode": True}

    def _request(self, path: str) -> Optional[Dict]:
        import requests
        resp = requests.get(f"{self._url}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()

    @property
    def stats(self) -> Dict[str, Any]:
        return {"healthy": self._healthy, "requests": self._request_count, "errors": self._error_count}
