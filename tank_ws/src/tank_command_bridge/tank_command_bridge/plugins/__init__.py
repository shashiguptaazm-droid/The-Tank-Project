"""Voice-command plugin registry for The Tank Project.

How it works
------------
A "voice command plugin" is a :class:`RobotPlugin` subclass that declares
its name, JSON-Schema for params, JSON-Schema for response, rate-class,
and a ``run(params, ctx=None) -> dict`` method.

We do **not** modify :mod:`tank_command_bridge.commands` /
:mod:`tank_command_bridge.manifest` to know about any individual plugin.
Instead, both files run a tiny end-of-module line::

    from .plugins import _register_voice_plugins          # in commands.py
    from .plugins import _register_voice_plugins_manifest # in manifest.py

Those helpers import each module listed in :data:`PLUGIN_PATHS`,
instantiate the named class, and update the bridge's own dispatch /
manifest dicts **in place** so the existing FastAPI layer keeps working
unchanged.

Why this shape
~~~~~~~~~~~~~~
* Drop-in extensibility: adding a new voice command is "write one file
  + add one line to PLUGIN_PATHS".
* Zero changes to ``app.py`` (auth + rate limits still apply, audit_id
  still flows).
* Zero changes to ``manifest.py`` schema — LLM tool calls work because
  ``/api/cmd/manifest`` now contains our merged declarations.
* Lazy via stdlib ``importlib``; missing optional deps in a plugin
  produce a clear :class:`PluginLoadError` with the offending module
  name, not a chain of cryptic Tracebacks.

Public API
~~~~~~~~~~
* :class:`RobotPlugin`           — base class.
* :data:`PLUGIN_PATHS`           — add new plugins here.
* :func:`_register_voice_plugins`  — invoked by ``commands.py``.
* :func:`_register_voice_plugins_manifest` — invoked by ``manifest.py``.
* :class:`PluginLoadError`        — raised when a plugin cannot load.
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List, Tuple


class PluginLoadError(RuntimeError):
    """Raised when a plugin cannot be imported or instantiated."""


class RobotPlugin:
    """Base class for every voice-command plugin.

    Subclass and set the class-level constants; implement :meth:`run`.
    The discovery layer will pick up the subclass automatically.
    """

    NAME: str = ""
    DESCRIPTION: str = ""
    PARAMETERS_SCHEMA: Dict[str, Any] = {}
    RESPONSE_SCHEMA: Dict[str, Any] = {}
    RATE_CLASS: str = "read"     # "read" | "write"
    TAGS: List[str] = ["read", "voice"]

    def run(self, params: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        raise NotImplementedError("RobotPlugin subclasses must implement run()")


# -----------------------------------------------------------------------------
# Plugin entry points.  Add new (module_path, class_name) tuples here.
# 29 plugins total:  3 torrent/aria2 + 8 house/cast + 4 vision/AI
#                  + 11 chassis + 3 torrent-display + 3 vpn/wireguard.
# -----------------------------------------------------------------------------
PLUGIN_PATHS: List[Tuple[str, str]] = [
    # --- audio / search / download --------------------------------------
    ("tank_command_bridge.plugins.torrent_search",
     "TorrentSearchPlugin"),
    ("tank_command_bridge.plugins.aria2_add",
     "Aria2AddPlugin"),
    ("tank_command_bridge.plugins.aria2_progress",
     "Aria2ProgressPlugin"),
    # --- house / cast ----------------------------------------------------
    ("tank_command_bridge.plugins.play_music",
     "PlayMusicPlugin"),
    ("tank_command_bridge.plugins.play_youtube",
     "PlayYouTubePlugin"),
    ("tank_command_bridge.plugins.play_tv",
     "PlayTvPlugin"),
    ("tank_command_bridge.plugins.play_alexa",
     "PlayAlexaPlugin"),
    ("tank_command_bridge.plugins.find_devices",
     "FindDevicesPlugin"),
    ("tank_command_bridge.plugins.power",
     "PowerPlugin"),
    ("tank_command_bridge.plugins.move_to",
     "MoveToPlugin"),
    ("tank_command_bridge.plugins.whereami",
     "WhereAmIPlugin"),
    # --- vision / AI -----------------------------------------------------
    ("tank_command_bridge.plugins.vision_detect",
     "VoiceDetectPersonsPlugin"),
    ("tank_command_bridge.plugins.vision_detect",
     "VoiceDetectFacesPlugin"),
    ("tank_command_bridge.plugins.vision_security",
     "VoiceDetectIntruderPlugin"),
    ("tank_command_bridge.plugins.vision_security",
     "VoiceAlertIntruderPlugin"),
    # --- chassis motion (5 modules — 11 plugins) -----------------------
    ("tank_command_bridge.plugins.chassis_drive",
     "DriveForwardPlugin"),
    ("tank_command_bridge.plugins.chassis_drive",
     "DriveBackwardPlugin"),
    ("tank_command_bridge.plugins.chassis_drive",
     "BrakeMotionPlugin"),
    ("tank_command_bridge.plugins.chassis_turn",
     "TurnLeftPlugin"),
    ("tank_command_bridge.plugins.chassis_turn",
     "TurnRightPlugin"),
    ("tank_command_bridge.plugins.chassis_turn",
     "SpinPlugin"),
    ("tank_command_bridge.plugins.chassis_speed",
     "SetMaxSpeedPlugin"),
    ("tank_command_bridge.plugins.chassis_speed",
     "SetCruiseModePlugin"),
    ("tank_command_bridge.plugins.chassis_follow",
     "FollowMePlugin"),
    ("tank_command_bridge.plugins.chassis_follow",
     "StopFollowMePlugin"),
    ("tank_command_bridge.plugins.chassis_follow",
     "PausePatrolPlugin"),
    ("tank_command_bridge.plugins.chassis_follow",
     "ResumePatrolPlugin"),    # --- torrent display (the "Asking" trio) ---------------------------
    ("tank_command_bridge.plugins.torrent_display",
     "TorrentPickPlugin"),
    ("tank_command_bridge.plugins.torrent_display",
     "TorrentCancelPlugin"),
    ("tank_command_bridge.plugins.torrent_display",
     "ShowTorrentResultsPlugin"),
    # --- vpn / wireguard (connect / disconnect / status trio) ---------
    ("tank_command_bridge.plugins.vpn",
     "VpnConnectPlugin"),
    ("tank_command_bridge.plugins.vpn",
     "VpnDisconnectPlugin"),
    ("tank_command_bridge.plugins.vpn",
     "VpnStatusPlugin"),
]	


# -----------------------------------------------------------------------------
# Discovery.
# -----------------------------------------------------------------------------
def _discover_plugins() -> List[RobotPlugin]:
    return _discover_plugins_with(PLUGIN_PATHS)


def _discover_plugins_with(paths: List[Tuple[str, str]]) -> List[RobotPlugin]:
    out: List[RobotPlugin] = []
    for mod_path, cls_name in paths:
        try:
            mod = importlib.import_module(mod_path)
        except ImportError as exc:
            raise PluginLoadError(
                f"failed to import plugin module {mod_path!r}: {exc}"
            ) from exc
        try:
            cls = getattr(mod, cls_name)
        except AttributeError as exc:
            raise PluginLoadError(
                f"plugin module {mod_path!r} has no class {cls_name!r}: {exc}"
            ) from exc
        if not isinstance(cls, type) or not issubclass(cls, RobotPlugin):
            raise PluginLoadError(
                f"{mod_path}.{cls_name} is not a RobotPlugin subclass"
            )
        try:
            inst = cls()
        except Exception as exc:
            raise PluginLoadError(
                f"could not instantiate {mod_path}.{cls_name}: {exc}"
            ) from exc
        if not inst.NAME:
            raise PluginLoadError(
                f"{mod_path}.{cls_name} has empty NAME — refusing to register"
            )
        out.append(inst)
    return out


# -----------------------------------------------------------------------------
# Inject into the bridge's dispatch / manifest dicts *in place*.
# -----------------------------------------------------------------------------
def _register_voice_plugins(
    dispatch: Dict[str, Any], rate_class: Dict[str, str]
) -> List[str]:
    registered: List[str] = []
    for plugin in _discover_plugins():
        dispatch[plugin.NAME] = (lambda p, _p=plugin: _p.run(p))
        rate_class[plugin.NAME] = plugin.RATE_CLASS
        registered.append(plugin.NAME)
    return registered


def _make_example_params(schema: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, prop in (schema.get("properties") or {}).items():
        t = prop.get("type", "string")
        if t == "string":
            out[name] = ""
        elif t == "integer":
            out[name] = 0
        elif t == "number":
            out[name] = 0.0
        elif t == "boolean":
            out[name] = False
        elif t == "array":
            out[name] = []
        elif t == "object":
            out[name] = {}
    return out


def _register_voice_plugins_manifest(commands: Dict[str, Dict[str, Any]]) -> List[str]:
    registered: List[str] = []
    for plugin in _discover_plugins():
        commands[plugin.NAME] = {
            "description": plugin.DESCRIPTION,
            "tags": list(plugin.TAGS),
            "rate_class": plugin.RATE_CLASS,
            "parameters": plugin.PARAMETERS_SCHEMA,
            "response":    plugin.RESPONSE_SCHEMA,
            "example": {
                "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
                "params": _make_example_params(plugin.PARAMETERS_SCHEMA),
            },
        }
        registered.append(plugin.NAME)
    return registered
