"""Workspace-level pytest bootstrap for The Tank Project.

ROS Python packages use the ``<pkg>/<pkg>/`` layout: the *inner*
``<pkg>/`` directory contains ``__init__.py`` and is the actual Python
package, while the *outer* ``<pkg>/`` is the ROS package root
(``package.xml`` + ``setup.py`` + the inner module of the same name).

That means absolute imports like
``from tank_command_bridge.plugins._chassis_helpers import X`` only
resolve when the INNER package directory is on :data:`sys.path`,
NOT the workspace root (``tank_ws/src/``).

This conftest adds every package's inner directory to ``sys.path`` at
pytest session start so the existing test suite (and every future
test we add) is hermetic without an external PYTHONPATH dance.

Discovery is auto — we scan ``tank_ws/src/`` for ``<pkg>/<pkg>/__init__.py``
and insert each one — so a brand-new ROS package added to the workspace
becomes importable in tests without modifying this file. A small
hardcoded fallback list runs only if the auto-scan yields zero hits
(offline / read-only mirror scenarios).

Usage::

    # Inside the workspace, just run pytest — no setup needed.
    pytest the\ tank\ project/tank_ws/src

    # Or, if you must use unittest without pytest:
    PYTHONPATH='/root/the tank project/tank_ws/src/tank_command_bridge:/root/the tank project/tank_ws/src/tank_speech' python3 -m unittest ...
"""
import sys
from pathlib import Path

# This file lives at <workspace>/tank_ws/src/conftest.py. The inner
# Python package directories are at <workspace>/tank_ws/src/<pkg>/<pkg>/.
_HERE = Path(__file__).resolve().parent           # tank_ws/src/

# Fallback list — only used if the auto-discover pass below finds no
# inner packages (defensive, not the primary path).
_PKG_NAMES_FALLBACK = (
    "tank_command_bridge",
    "tank_speech",
    "tank_text",
    "tank_vision",
    "tank_dashboard",
    "tank_motion",
)


def _discover_inner_pkg_dirs(workspace_src: Path) -> list:
    """Find every ``<pkg>/<pkg>/__init__.py`` under ``workspace_src``."""
    found = []
    if not workspace_src.is_dir():
        return found
    for child in sorted(workspace_src.iterdir()):
        if not child.is_dir():
            continue
        inner = child / child.name
        if (inner / "__init__.py").is_file():
            found.append(inner)
    return found


def _bootstrap_sys_path() -> None:
    """Insert the inner ``<pkg>/`` directory of every known ROS package
    onto :data:`sys.path` (in front of system paths) so tests can
    ``from <pkg>.X import Y`` directly."""
    inner_dirs = _discover_inner_pkg_dirs(_HERE)
    if not inner_dirs:
        # Fallback when ``_HERE`` is read-only or empty (CI sandbox).
        for pkg in _PKG_NAMES_FALLBACK:
            inner_dirs.append(_HERE / pkg / pkg)
    for inner in inner_dirs:
        s = str(inner)
        if inner.is_dir() and s not in sys.path:
            sys.path.insert(0, s)


_bootstrap_sys_path()
