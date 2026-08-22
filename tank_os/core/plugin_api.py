"""
TankOS Plugin API — base class for all plugins.

Every plugin in ``tank_os/plugins/<name>/`` must have a ``plugin.py``
that defines a subclass of ``Plugin``::

    from tank_os.core.plugin_api import Plugin

    class MyPlugin(Plugin):
        name = "my_plugin"
        version = "1.0"

        def initialize(self):
            self.log.info("MyPlugin started")

        def widget(self, parent=None):
            from PySide6.QtWidgets import QLabel
            return QLabel("Hello from MyPlugin", parent=parent)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tank_os.core.event_bus import EventBus


class Plugin:
    """Base class for all TankOS plugins.

    Subclasses MUST override ``initialize()`` and MAY override any of the
    lifecycle hooks.  The plugin manager sets ``_manifest`` and
    ``_plugin_dir`` before calling ``initialize()``.
    """

    name: str = ""
    """Plugin identifier (auto-filled from manifest)."""

    version: str = "1.0.0"
    """Semantic version (auto-filled from manifest)."""

    # Set by PluginManager before initialize()
    _manifest: Any = None
    _plugin_dir: Path = Path()

    def __init__(self) -> None:
        self.log = logging.getLogger(f"tank_os.plugin.{self.name or '?'}")
        self.bus = EventBus()

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Called after the plugin is imported and instantiated.

        Set up resources, register event handlers, start threads.
        Must not block for long — use background threads.
        """
        raise NotImplementedError(
            f"{type(self).__name__}.initialize() must be overridden"
        )

    def shutdown(self) -> None:
        """Called when the plugin is unloaded or TankOS shuts down.

        Release resources, stop threads, disconnect hardware.
        """
        pass

    # ------------------------------------------------------------------
    # GUI hooks
    # ------------------------------------------------------------------

    def widget(self, parent: Any = None) -> Optional[Any]:
        """Return a Qt widget for inclusion in the dashboard or settings.

        Return ``None`` if this plugin has no persistent GUI.
        """
        return None

    def settings(self) -> Optional[Any]:
        """Return a Qt widget for the Settings > Plugins panel.

        Return ``None`` if this plugin has no configurable settings.
        """
        return None

    # ------------------------------------------------------------------
    # Integration hooks
    # ------------------------------------------------------------------

    def commands(self) -> List[Dict[str, Any]]:
        """Return a list of command descriptors for the command registry.

        Each entry::

            {
                "name": "my_command",
                "description": "...",
                "parameters": {...},
            }
        """
        return []

    def events(self) -> List[str]:
        """Return a list of event types this plugin emits or subscribes to.

        Used by the event bus inspector in Developer Mode.
        """
        return []
