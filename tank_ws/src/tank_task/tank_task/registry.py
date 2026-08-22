"""Auto-importing registry side-effect.

Importing :mod:`tank_task.registry` registers all the built-in tasks
into :data:`tank_task.base.TaskRegistry`. External callers (notably
``tank_command_bridge.manifest``) should ``import tank_task.registry``
before reading the bridge manifest so their /api/cmd/manifest
auto-contains every task the user added.
"""
from __future__ import annotations

import importlib
import logging

from . import base
from .base import TaskRegistry  # noqa: F401  — re-export

_log = logging.getLogger("tank_task")

_BUILTIN_TASK_MODULES = (
    "tank_task.tasks.come_to_owner",
    "tank_task.tasks.follow_me",
    "tank_task.tasks.go_to_room",
    "tank_task.tasks.return_to_dock",
    "tank_task.tasks.status_report",
    "tank_task.tasks.pick_up_trash_in_room",
    "tank_task.tasks.fetch_named_object",
    "tank_task.tasks.find_owner",
    "tank_task.tasks.list_tasks",
)


def import_all_tasks() -> int:
    """Side-effect import every task module. Returns count registered."""
    before = set(t.name for t in TaskRegistry().all())
    for mod_name in _BUILTIN_TASK_MODULES:
        try:
            importlib.import_module(mod_name)
        except Exception as exc:                              # pragma: no cover
            # Don't fail the registry if one task module is missing
            # (e.g., bench without rclpy). Log via the package logger
            # if it is configured.
            _log.warning("tank_task: failed to import %s (%s)",
                         mod_name, exc)
    after = set(t.name for t in TaskRegistry().all())
    return max(0, len(after) - len(before))


def manifest_envelope() -> dict:
    """Return the per-task manifest envelope for the bridge."""
    return {
        "version": "1",
        "source": "tank_task",
        "tasks": [
            {
                "name": t.name,
                "description": t.description,
                "tags": t.tags,
                "parameters": t.parameters_schema,
            }
            for t in TaskRegistry().all()
        ],
    }
