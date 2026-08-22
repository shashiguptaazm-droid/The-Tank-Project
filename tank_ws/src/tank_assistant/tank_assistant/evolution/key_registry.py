"""Key registry — by-name API key access without ever storing values in code.

Backends (lookup chain, in order)
---------------------------------
1. **OS keyring** — ``keyring.get_password("tank_llm", KEY_NAME)``. Requires
   the optional ``keyring`` package; skipped silently when unavailable.
2. **Systemd env file** — ``/etc/edulabs-thesis-worker/worker.env`` (and any
   additional paths in :data:`SYSTEMD_ENV_FILES`). Parsed at runtime by a
   lightweight dotenv reader; this file is owned by the edulabs services
   and we never write to it.
3. **Project ``.env``** — ``/root/the tank project/.env`` (or whatever
   ``PROJECT_ROOT`` resolves to). Per-key fallback for local dev.
4. **Process ``os.environ``** — used as final fallback; under systemd the
   ``EnvironmentFile=`` directive will already have populated these.

Security
--------
- Key VALUES are never logged, repr'd, or echoed to stdout.
- The :class:`KeyRegistry` class overrides ``__repr__`` to show only the
  lookup stats, not the values.
- The :meth:`get` method return value should be passed directly to provider
  constructor ``api_key=`` and never persisted.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional


_LOG = logging.getLogger("tank_assistant.evolution.key_registry")

# ── Configuration ─────────────────────────────────────────────────────────

PROJECT_ROOT = Path(os.environ.get(
    "TANK_PROJECT_ROOT", "/root/the tank project"))

PROJECT_ENV_FILE = Path(os.environ.get(
    "TANK_PROJECT_ENV", PROJECT_ROOT / ".env"))

# Systemd EnvironmentFile paths — read at runtime, never written to.
SYSTEMD_ENV_FILES: List[Path] = [
    Path(p) for p in os.environ.get(
        "TANK_SYSTEMD_ENV_FILES",
        "/etc/edulabs-thesis-worker/worker.env",
    ).split(":") if p.strip()
]

# Optional service-name label used as the keyring namespace.
KEYRING_SERVICE = os.environ.get("TANK_KEYRING_SERVICE", "tank_llm")


# ── Lightweight dotenv parser (no `python-dotenv` dep required) ──────────

def parse_dotenv_text(text: str) -> Dict[str, str]:
    """Parse ``KEY=value`` lines, ignoring comments and blank lines.

    Quotes around the value are stripped. ``\\#`` is treated as a literal
    ``#`` (escape for ``#`` in values). Backslash-newlines are joined.
    """
    out: Dict[str, str] = {}
    line_iter = iter(text.splitlines())
    pending_key: Optional[str] = None
    pending_val: str = ""
    for raw in line_iter:
        if pending_key is not None:
            # Continuation of multi-line value.
            stripped = raw.rstrip()
            if stripped.endswith("\\"):
                pending_val += stripped[:-1] + "\n"
                continue
            pending_val += stripped
            out[pending_key] = pending_val.strip().strip('"').strip("'")
            pending_key = None
            pending_val = ""
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Strip inline comments (not preceded by backslash).
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # Strip optional "export" prefix (shell .env files)
        if key.startswith("export "):
            key = key[7:].strip()
        val = val.strip().strip('"').strip("'")
        if val.endswith("\\"):
            # Multi-line value follows.
            pending_key = key
            pending_val = val[:-1] + "\n"
        else:
            out[key] = val
    if pending_key is not None:
        out[pending_key] = pending_val.strip().strip('"').strip("'")
    return out


# ── Caching layer ─────────────────────────────────────────────────────────

class KeyRegistry:
    """Singleton-ish key accessor.

    Created once at module import; share across the process via
    :data:`key_registry`. Reads ``.env`` files lazily on first lookup
    and caches parsed content. Cache invalidates when file mtime changes.
    """

    def __init__(self, *,
                 project_env: Optional[Path] = None,
                 systemd_env_files: Optional[List[Path]] = None) -> None:
        self.project_env = Path(project_env) if project_env else PROJECT_ENV_FILE
        self.systemd_env_files = (
            list(systemd_env_files) if systemd_env_files is not None
            else SYSTEMD_ENV_FILES[:])
        self._lock = RLock()
        self._project_cache: Dict[str, str] = {}
        self._project_mtime: float = 0.0
        self._systemd_cache: Dict[str, Dict[str, str]] = {}  # path -> env
        self._stats = {"hits": 0, "misses": 0, "by_backend": {
            "keyring": 0, "systemd": 0, "project_env": 0, "os_environ": 0,
        }}

    # ── Internal: parse + cache the project .env ─────────────────────────

    def _load_project_env(self, force: bool = False) -> Dict[str, str]:
        with self._lock:
            try:
                mtime = self.project_env.stat().st_mtime
            except FileNotFoundError:
                self._project_cache = {}
                self._project_mtime = 0.0
                return {}
            if force or mtime > self._project_mtime or not self._project_cache:
                try:
                    text = self.project_env.read_text(encoding="utf-8")
                    self._project_cache = parse_dotenv_text(text)
                except Exception as exc:
                    _LOG.debug("project env read failed: %s", exc)
                    self._project_cache = {}
                self._project_mtime = mtime
            return self._project_cache

    # ── Internal: parse + cache each systemd env file ───────────────────

    def _load_systemd_env(self, path: Path,
                          force: bool = False) -> Dict[str, str]:
        with self._lock:
            cache = self._systemd_cache.setdefault(str(path), {})
            try:
                mtime = path.stat().st_mtime
            except FileNotFoundError:
                cache.clear()
                return {}
            cache_mtime = cache.get("__mtime__", 0.0)
            if force or mtime > cache_mtime or not cache:
                try:
                    text = path.read_text(encoding="utf-8")
                    parsed = parse_dotenv_text(text)
                    parsed["__mtime__"] = mtime
                    self._systemd_cache[str(path)] = parsed
                    return parsed
                except Exception as exc:
                    _LOG.debug("systemd env %s read failed: %s", path, exc)
                    return {}
            return cache

    # ── Public: lookup chain ────────────────────────────────────────────

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Return the key value for ``name`` following the lookup chain.

        Returns ``default`` (defaulting to ``None``) if no backend has the
        key. NEVER logs the value.
        """
        if not name:
            return default

        # 1) OS keyring.
        try:
            import keyring  # type: ignore
            v = keyring.get_password(KEYRING_SERVICE, name)
            if v:
                self._stats["by_backend"]["keyring"] += 1
                self._stats["hits"] += 1
                return v
        except Exception:
            pass

        # 2) Systemd env file(s) (first wins).
        for path in self.systemd_env_files:
            env = self._load_systemd_env(path)
            if name in env:
                self._stats["by_backend"]["systemd"] += 1
                self._stats["hits"] += 1
                return env[name]

        # 3) Project .env.
        env = self._load_project_env()
        if name in env:
            self._stats["by_backend"]["project_env"] += 1
            self._stats["hits"] += 1
            return env[name]

        # 4) os.environ (final fallback; systemd populates this under
        #    EnvironmentFile=).
        v = os.environ.get(name)
        if v:
            self._stats["by_backend"]["os_environ"] += 1
            self._stats["hits"] += 1
            return v

        self._stats["misses"] += 1
        return default

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def available_keys(self) -> List[str]:
        """Return sorted list of all key NAMES (not values) known to any
        backend. Used by the orchestrator to advertise capability.

        Order of preference: systemd env, project .env, os.environ,
        then any keyring entries (requires keyring lib walk).
        """
        out: set[str] = set()
        for path in self.systemd_env_files:
            out.update(self._load_systemd_env(path).keys())
            out.discard("__mtime__")
        out.update(self._load_project_env().keys())
        # Avoid scanning all of os.environ — only the ones we ask for.
        return sorted(out)

    def stats(self) -> Dict[str, object]:
        return dict(self._stats)

    def __repr__(self) -> str:
        # NEVER expose values — only stats.
        return (
            f"KeyRegistry(project_env={self.project_env!s}, "
            f"systemd={len(self.systemd_env_files)} file(s), "
            f"stats={self._stats})"
        )


# ── Module-level singletons ───────────────────────────────────────────────

key_registry = KeyRegistry()


def get_key(name: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience wrapper around :data:`key_registry`."""
    return key_registry.get(name, default)
