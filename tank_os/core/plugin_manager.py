"""
TankOS Plugin Manager — dynamic plugin loading from ``tank_os/plugins/``.

Every plugin ships a ``manifest.json`` + ``plugin.py`` with an optional
``assets/`` and ``settings/`` directory.  The PluginManager discovers,
loads, initialises, and tracks every plugin at startup.

Plugin API (defined in :mod:`tank_os.core.plugin_api`)::

    class MyPlugin(Plugin):
        def initialize(self): ...
        def shutdown(self): ...
        def widget(self, parent=None): ...
        def settings(self): ...
        def commands(self): ...
        def events(self): ...
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tank_os.core.event_bus import Event, EventBus

logger = logging.getLogger("tank_os.plugin_manager")

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


@dataclass
class PluginManifest:
    """Deserialised ``manifest.json`` for a plugin."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    entry: str = "plugin.py"
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    settings_schema: Dict[str, Any] = field(default_factory=dict)
    commands: List[Dict[str, Any]] = field(default_factory=list)
    events: List[str] = field(default_factory=list)


@dataclass
class PluginInfo:
    """Runtime record for a loaded plugin."""
    manifest: PluginManifest
    path: Path
    instance: Any  # Plugin instance
    enabled: bool = True
    error: Optional[str] = None


class PluginManager:
    """Singleton that discovers, loads, and manages plugins."""

    _instance: Optional["PluginManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "PluginManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._plugins: Dict[str, PluginInfo] = {}
                cls._instance._manifest_lock = threading.Lock()
                cls._instance._bus = EventBus()
            return cls._instance

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> List[PluginManifest]:
        """Walk ``plugins/`` and parse every ``manifest.json``."""
        manifests: List[PluginManifest] = []
        if not PLUGINS_DIR.exists():
            PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
            return manifests

        for entry in sorted(PLUGINS_DIR.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.exists():
                logger.debug("Skipping %s (no manifest.json)", entry.name)
                continue
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = PluginManifest(
                    name=raw.get("name", entry.name),
                    version=raw.get("version", "1.0.0"),
                    description=raw.get("description", ""),
                    author=raw.get("author", ""),
                    entry=raw.get("entry", "plugin.py"),
                    dependencies=raw.get("dependencies", []),
                    permissions=raw.get("permissions", []),
                    tags=raw.get("tags", []),
                    settings_schema=raw.get("settings_schema", {}),
                    commands=raw.get("commands", []),
                    events=raw.get("events", []),
                )
                manifests.append(manifest)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to parse manifest for %s: %s",
                               entry.name, exc)
        return manifests

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_plugin(self, manifest: PluginManifest) -> Optional[PluginInfo]:
        """Load a single plugin by its manifest.

        Imports ``plugin.py`` from the plugin directory, instantiates
        the ``Plugin`` subclass, and calls ``initialize()``.
        """
        plugin_dir = PLUGINS_DIR / manifest.name
        entry_path = plugin_dir / manifest.entry

        if not entry_path.exists():
            err = f"Entry file {entry_path} not found"
            logger.error(err)
            pi = PluginInfo(manifest=manifest, path=plugin_dir,
                            instance=None, enabled=False, error=err)
            self._plugins[manifest.name] = pi
            return pi

        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"tank_os.plugins.{manifest.name}.plugin",
                entry_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load {entry_path}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Find Plugin subclass
            plugin_cls = None
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and attr.__name__ != "Plugin":
                    from tank_os.core.plugin_api import Plugin
                    if issubclass(attr, Plugin):
                        plugin_cls = attr
                        break

            if plugin_cls is None:
                raise ImportError(
                    f"No Plugin subclass found in {entry_path}"
                )

            instance = plugin_cls()
            instance._manifest = manifest
            instance._plugin_dir = plugin_dir
            instance.initialize()

            pi = PluginInfo(manifest=manifest, path=plugin_dir,
                            instance=instance)
            self._plugins[manifest.name] = pi

            self._bus.emit(Event("plugin_loaded", {
                "name": manifest.name,
                "version": manifest.version,
            }, source="plugin_manager"))

            logger.info("Loaded plugin: %s v%s", manifest.name,
                        manifest.version)
            return pi

        except Exception as exc:
            err = f"Failed to load {manifest.name}: {exc}"
            logger.exception(err)
            pi = PluginInfo(manifest=manifest, path=plugin_dir,
                            instance=None, enabled=False, error=err)
            self._plugins[manifest.name] = pi
            return pi

    def load_all(self) -> List[PluginInfo]:
        """Discover and load every available plugin."""
        results: List[PluginInfo] = []
        for manifest in self.discover():
            pi = self.load_plugin(manifest)
            if pi:
                results.append(pi)
        self._bus.emit(Event("plugins_loaded", {
            "count": len(results),
            "names": list(self._plugins.keys()),
        }, source="plugin_manager"))
        return results

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown_all(self) -> None:
        """Call ``shutdown()`` on every loaded plugin."""
        for name, pi in list(self._plugins.items()):
            if pi.instance and pi.enabled:
                try:
                    pi.instance.shutdown()
                except Exception as exc:
                    logger.error("Error shutting down %s: %s", name, exc)
        self._plugins.clear()
        self._bus.emit(Event("plugins_shutdown", {}, source="plugin_manager"))

    def reload(self, name: str) -> Optional[PluginInfo]:
        """Reload a single plugin by name."""
        self.unload(name)
        manifest = PluginManifest(name=name)
        return self.load_plugin(manifest)

    def unload(self, name: str) -> bool:
        """Unload a plugin, calling shutdown if needed."""
        pi = self._plugins.pop(name, None)
        if pi and pi.instance:
            try:
                pi.instance.shutdown()
            except Exception as exc:
                logger.error("Error unloading %s: %s", name, exc)
            return True
        return False

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[PluginInfo]:
        return self._plugins.get(name)

    def all(self) -> Dict[str, PluginInfo]:
        return dict(self._plugins)

    def enabled(self) -> List[PluginInfo]:
        return [p for p in self._plugins.values() if p.enabled]

    def widgets(self, parent=None) -> List[Any]:
        """Collect all plugin widgets for assembly into the dashboard."""
        widgets = []
        for pi in self._plugins.values():
            if pi.instance and pi.enabled:
                try:
                    w = pi.instance.widget(parent=parent)
                    if w is not None:
                        widgets.append(w)
                except Exception:
                    logger.exception("widget() failed for %s",
                                     pi.manifest.name)
        return widgets
