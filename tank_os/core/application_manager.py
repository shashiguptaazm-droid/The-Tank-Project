"""TankOS Application Manager — discover, register, lifecycle-manage apps.

Apps are full-screen/focused UX surfaces, distinct from background
plugins. The ApplicationManager walks conventional discovery roots
(``tank_os/windows/``, ``tank_os/services/``, ``tank_os/widgets/``)
plus a user-configured ``tank_os/applications/`` fallback, parses any
``app_manifest.json`` it finds, and exposes a uniform registry that the
shell + dashboards can drive.

Apps that fail import or have no manifest are placed in a
*degraded* registry entry so the dashboard can surface the reason.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.app_manager")

# Built-in discovery roots. A custom ``tank_os/applications/`` folder is
# also scanned if present.
_BASE_DIR = Path(__file__).resolve().parent.parent
_DISCOVERY_ROOTS: List[Path] = [
    _BASE_DIR / "windows",
    _BASE_DIR / "services",
    _BASE_DIR / "widgets",
    _BASE_DIR / "applications",
]


# ───────────────────────────────────────────────────────────────────────────
# AppInfo dataclass — backward-compatible with the old stub.
# ───────────────────────────────────────────────────────────────────────────

@dataclass
class AppInfo:
    """Runtime record for one registered application."""

    name: str
    version: str = "1.0"
    description: str = ""
    icon: str = ""
    category: str = ""
    entry: str = "app.py"
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    # Runtime fields
    instance: Any = None
    path: Optional[Path] = None
    enabled: bool = True
    running: bool = False
    error: Optional[str] = None
    discovered_at: float = field(default_factory=time.time)


# ───────────────────────────────────────────────────────────────────────────
# ApplicationManager
# ───────────────────────────────────────────────────────────────────────────


class ApplicationManager:
    """Singleton registry of installed TankOS apps."""

    _instance: Optional["ApplicationManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ApplicationManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.apps: Dict[str, AppInfo] = {}
                cls._instance._bus = EventBus()
                cls._instance._registry_lock = threading.Lock()
                cls._instance._lifecycle_hooks: Dict[str, List[Callable]] = {
                    "on_start": [],
                    "on_pause": [],
                    "on_resume": [],
                    "on_stop": [],
                }
            return cls._instance

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def initialize(self, auto_discover: bool = True) -> None:
        """Initialise registry, optionally scanning discovery roots."""
        try:
            from tank_os.core.permission_manager import PermissionManager
            self._permission_manager = PermissionManager()
        except Exception:  # pragma: no cover - defensive
            self._permission_manager = None
        if auto_discover:
            self.discover()
        logger.info(
            "ApplicationManager initialized — %d apps registered",
            len(self.apps),
        )

    @staticmethod
    def discovery_roots() -> List[Path]:
        return [p for p in _DISCOVERY_ROOTS if p.exists()]

    def discover(self) -> List[AppInfo]:
        """Scan every discovery root, parse manifests, register apps.

        Apps without a manifest but with an ``app.py`` entry are still
        registered with defaults.
        """
        roots = self.discovery_roots()
        registered: List[AppInfo] = []
        seen: set[str] = set()
        for root in roots:
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir()):
                if not entry.is_dir() or entry.name.startswith(("_", ".")):
                    continue
                if entry.name in seen:
                    continue
                seen.add(entry.name)
                info = self._register_from_directory(entry, source=str(root))
                if info is not None:
                    registered.append(info)
        self._bus.emit(Event(
            "applications_discovered",
            {"count": len(registered), "total": len(self.apps)},
            source="application_manager",
        ))
        return registered

    # ------------------------------------------------------------------
    # Manual registration
    # ------------------------------------------------------------------

    def register(self, app: AppInfo) -> None:
        """Add an ``AppInfo`` to the registry without instantiating."""
        with self._registry_lock:
            self.apps[app.name] = app
        self._bus.emit(Event(
            "app_registered",
            {"name": app.name, "version": app.version, "category": app.category},
            source="application_manager",
        ))

    def unregister(self, name: str) -> bool:
        """Remove an app entry; calling ``stop`` first if running."""
        with self._registry_lock:
            info = self.apps.get(name)
            if info is None:
                return False
            if info.running:
                try:
                    self.stop(name)
                except Exception:
                    logger.exception("stop() during unregister failed for %s",
                                     name)
            self.apps.pop(name, None)
        self._bus.emit(Event("app_unregistered", {"name": name},
                             source="application_manager"))
        return True

    def get(self, name: str) -> Optional[AppInfo]:
        return self.apps.get(name)

    def all(self) -> List[AppInfo]:
        return list(self.apps.values())

    def by_category(self, category: str) -> List[AppInfo]:
        return [a for a in self.apps.values() if a.category == category]

    def running(self) -> List[AppInfo]:
        return [a for a in self.apps.values() if a.running]

    def search(self, query: str) -> List[AppInfo]:
        """Case-insensitive substring match against name/description/tag."""
        q = (query or "").strip().lower()
        if not q:
            return self.all()
        out: List[AppInfo] = []
        for a in self.apps.values():
            haystacks = [a.name.lower(), a.description.lower()]
            haystacks.extend(t.lower() for t in a.tags)
            if any(q in s for s in haystacks):
                out.append(a)
        return out

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, name: str, *args: Any, **kwargs: Any) -> bool:
        """Load (if needed), instantiate, and call ``on_start``.

        The full transition (resolve app → check running → load
        instance → request perms → invoke lifecycle → flip running
        flag → emit event) is performed under ``_registry_lock`` so
        concurrent ``start(name)`` calls cannot double-fire
        ``on_start``.
        """
        with self._registry_lock:
            info = self.apps.get(name)
            if info is None:
                logger.warning("start() unknown app: %s", name)
                return False
            if info.running:
                logger.debug("start() noop — already running: %s", name)
                return True
        self._ensure_instance(info)
        # Permission gate — apps may declare required permissions
        if info.permissions and self._permission_manager is not None:
            from tank_os.core.permission_manager import Permission
            for pname in info.permissions:
                try:
                    perm = Permission[pname]
                except KeyError:
                    logger.debug("App %s declares unknown permission %s",
                                 name, pname)
                    continue
                if not self._permission_manager.check(perm):
                    logger.info("App %s needs %s, requesting", name, pname)
                    req = self._permission_manager.request(
                        perm, requester=f"app:{name}",
                        reason=f"App {name} requires {pname}",
                    )
                    if not req.wait(timeout=5.0):
                        logger.warning(
                            "App %s start denied: missing %s", name, pname
                        )
                        return False
        # Re-acquire the lock while we flip ``running`` so concurrent
        # callers can't race past the ``running`` check above.
        with self._registry_lock:
            if info.running:
                return True
            ok = self._invoke_lifecycle(info, "on_start", *args, **kwargs)
            if ok:
                info.running = True
                self._bus.emit(Event(
                    "app_started", {"name": name},
                    source="application_manager"))
            return ok

    def pause(self, name: str) -> bool:
        with self._registry_lock:
            info = self.apps.get(name)
            if info is None or not info.running:
                return False
        ok = self._invoke_lifecycle(info, "on_pause")
        if ok:
            self._bus.emit(Event("app_paused", {"name": name},
                                 source="application_manager"))
        return ok

    def resume(self, name: str) -> bool:
        with self._registry_lock:
            info = self.apps.get(name)
            if info is None or not info.running:
                return False
        ok = self._invoke_lifecycle(info, "on_resume")
        if ok:
            self._bus.emit(Event("app_resumed", {"name": name},
                                 source="application_manager"))
        return ok

    def stop(self, name: str) -> bool:
        with self._registry_lock:
            info = self.apps.get(name)
            if info is None or not info.running:
                return True
        ok = self._invoke_lifecycle(info, "on_stop")
        info.running = False
        self._bus.emit(Event("app_stopped", {"name": name},
                             source="application_manager"))
        return ok

    def stop_all(self) -> None:
        for name in [a.name for a in self.running()]:
            try:
                self.stop(name)
            except Exception:
                logger.exception("stop_all failed for %s", name)

    # ------------------------------------------------------------------
    # Lifecycle hook registry (system-wide handlers)
    # ------------------------------------------------------------------

    def on(self, hook: str, callback: Callable) -> bool:
        """Register a system-wide lifecycle handler.

        Valid hooks: on_start, on_pause, on_resume, on_stop.
        """
        if hook not in self._lifecycle_hooks:
            return False
        self._lifecycle_hooks[hook].append(callback)
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _register_from_directory(self, app_dir: Path,
                                 source: str) -> Optional[AppInfo]:
        manifest_path = app_dir / "app_manifest.json"
        if manifest_path.is_file():
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                info = AppInfo(
                    name=raw.get("name", app_dir.name),
                    version=raw.get("version", "1.0"),
                    description=raw.get("description", ""),
                    icon=raw.get("icon", ""),
                    category=raw.get("category", ""),
                    entry=raw.get("entry", "app.py"),
                    permissions=list(raw.get("permissions", []) or []),
                    tags=list(raw.get("tags", []) or []),
                    dependencies=list(raw.get("dependencies", []) or []),
                    path=app_dir,
                )
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to parse %s: %s — registering degraded entry",
                    manifest_path, exc,
                )
                info = AppInfo(
                    name=app_dir.name, path=app_dir, enabled=False,
                    error=f"manifest invalid: {exc}",
                )
        else:
            entry_path = app_dir / "app.py"
            info = AppInfo(
                name=app_dir.name,
                description="(no manifest)",
                enabled=entry_path.is_file(),
                error=None if entry_path.is_file() else "no app.py",
                path=app_dir,
            )
        # Tag the source for diagnostics
        info.tags = list(info.tags) + [f"root:{Path(source).name}"]
        self.register(info)
        return info

    def _ensure_instance(self, info: AppInfo) -> None:
        """Lazy-load the app's ``entry`` module and cache instance."""
        if info.instance is not None or info.path is None:
            return
        entry_path = info.path / info.entry
        if not entry_path.is_file():
            info.error = f"entry module missing: {entry_path}"
            info.enabled = False
            return
        try:
            spec = importlib.util.spec_from_file_location(
                f"tank_os.apps.{info.name}.{info.entry[:-3]}",
                entry_path,
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"spec invalid for {entry_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            info.instance = module
            info.error = None
        except Exception as exc:
            info.error = f"import failed: {exc}"
            info.enabled = False
            logger.warning("Could not load app %s: %s", info.name, exc)

    def _invoke_lifecycle(self, info: AppInfo, hook: str,
                          *args: Any, **kwargs: Any) -> bool:
        """Invoke a lifecycle method on the app instance, fallback to
        no-ops. Also fires the system-wide hook handlers."""
        ok = True
        if info.instance is not None:
            method = getattr(info.instance, hook, None)
            if callable(method):
                try:
                    method(*args, **kwargs)
                except Exception:
                    ok = False
                    logger.exception(
                        "App %s hook %s raised", info.name, hook
                    )
        for cb in self._lifecycle_hooks.get(hook, []):
            try:
                cb(info, *args, **kwargs)
            except Exception:
                logger.exception("system hook %s raised", hook)
        return ok
