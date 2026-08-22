"""Command manifest — the machine-readable command surface that any AI
assistant can introspect at ``GET /api/cmd/manifest``.

Each command entry has:

  * ``description``         free-text, surfaces to LLMs as the tool description.
  * ``parameters``          OpenAI-compatible JSON Schema (subset of
                            Draft 2020-12 — ``type``, ``properties``,
                            ``required``).
  * ``response``            JSON Schema for the response body.
  * ``example``             ready-to-send curl-friendly example.
  * ``tags``                coarse role: ``["write"]`` vs ``["read"]``.
  * ``rate_class``          ``"write"`` -> write-quota; ``"read"`` -> read-quota.

Stays static + human-editable so we can hand-tune tool descriptions
without writing Python. Keep it small.
"""
from __future__ import annotations

from typing import Dict, List


def _schema(name: str, t: str,
            description: str = "",
            enum: List[str] = None,
            minimum: float = None,
            maximum: float = None,
            default: object = None,
            _has_default: bool = False) -> Dict:
    s: Dict = {"type": t, "description": description}
    if enum is not None:
        s["enum"] = enum
    if minimum is not None:
        s["minimum"] = minimum
    if maximum is not None:
        s["maximum"] = maximum
    if _has_default:
        s["default"] = default
    s["title"] = name
    return s


COMMANDS: Dict[str, Dict] = {
    "estop": {
        "description": (
            "Latched or release the hardware e-stop. ``true`` halts all "
            "motors and refuses further write commands; ``false`` releases "
            "after a recent operator heartbeat."
        ),
        "tags": ["write", "safety"],
        "rate_class": "write",
        "parameters": {
            "type": "object",
            "required": ["state"],
            "properties": {
                "state": _schema("state", "boolean",
                                  "true = latch motors off, false = release"),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "latched": {"type": "boolean"},
                "ts":      {"type": "number"},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"state": True},
        },
    },
    "move": {
        "description": (
            "Drive the skid-steer base for a bounded duration. Linear "
            "velocity clamp 0.5 m/s, angular clamp 1.5 rad/s, "
            "duration cap 5 s. After ``duration_s`` seconds the commander "
            "publishes a zero Twist so the watchdog stops the motors."
        ),
        "tags": ["write", "motion"],
        "rate_class": "write",
        "parameters": {
            "type": "object",
            "required": ["vx", "wz", "duration_s"],
            "properties": {
                "vx": _schema("vx", "number", "linear m/s", minimum=-0.5,
                              maximum=0.5),
                "wz": _schema("wz", "number", "angular rad/s",
                              minimum=-1.5, maximum=1.5),
                "duration_s": _schema("duration_s", "number",
                                       "seconds to publish Twist",
                                       minimum=0.1, maximum=5.0),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "vx_eff": {"type": "number"},
                "wz_eff": {"type": "number"},
                "duration_s_eff": {"type": "number"},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"vx": 0.2, "wz": 0.0, "duration_s": 2.0},
        },
    },
    "patrol": {
        "description": (
            "Start/pause autonomous patrolling. ``mode`` selects the "
            "patrol_node mode and the rest of the pipeline follows it."
        ),
        "tags": ["write", "autonomy"],
        "rate_class": "write",
        "parameters": {
            "type": "object",
            "required": ["mode"],
            "properties": {
                "mode": _schema("mode", "string", "patrol mode",
                                enum=["waypoint", "random", "pause",
                                      "stop"]),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "accepted": {"type": "boolean"},
                "mode":   {"type": "string"},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"mode": "waypoint"},
        },
    },
    "dock": {
        "description": (
            "Toggle AprilTag auto-docking. ``enable=true`` arms the dock "
            "node (it will start chasing the dock tag if visible)."
        ),
        "tags": ["write"],
        "rate_class": "write",
        "parameters": {
            "type": "object",
            "required": ["enable"],
            "properties": {
                "enable": _schema("enable", "boolean",
                                   "true = arm dock node"),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "armed": {"type": "boolean"},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"enable": True},
        },
    },
    "capture": {
        "description": (
            "Snap the latest camera frame as a data: URL (base64 JPEG). "
            "Returns a downsampled 640x480 image so the assistant can "
            "carry it without blowing out the context window."
        ),
        "tags": ["read", "vision"],
        "rate_class": "read",
        "parameters": {
            "type": "object",
            "properties": {
                "max_px": _schema("max_px", "integer",
                                   "longest edge cap (default 640)",
                                   minimum=160, maximum=1920),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "ts":     {"type": "number"},
                "width":  {"type": "integer"},
                "height": {"type": "integer"},
                "data_url": {"type": "string",
                              "description": "data:image/jpeg;base64,..."},
            },
        },
        "example": {"audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
                    "params": {"max_px": 640}},
    },
    "telemetry": {
        "description": (
            "Aggregate read of /battery/state, /health/state, "
            "/estop, /cmd_vel latency, and the latest /emotion/state. "
            "Useful as a one-shot ping to see if the system is healthy."
        ),
        "tags": ["read", "telemetry"],
        "rate_class": "read",
        "parameters": {"type": "object"},
        "response": {
            "type": "object",
            "properties": {
                "ok":          {"type": "boolean"},
                "battery_v":   {"type": "number"},
                "battery_pct": {"type": "number"},
                "cpu_c":       {"type": "number"},
                "estop":       {"type": "boolean"},
                "emotion":     {"type": "string"},
                "cmd_age_ms":  {"type": "number"},
            },
        },
        "example": {"audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
                    "params": {}},
    },
    "query": {
        "description": (
            "Forward a structured memory / meta query to ``tank_meta``. "
            "Returns top-k hits from the requested index. Kinds: "
            "``code``, ``hardware``, ``decisions``, ``knowledge``."
        ),
        "tags": ["read", "meta"],
        "rate_class": "read",
        "parameters": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": _schema("kind", "string", "index to query",
                                enum=["code", "hardware", "decisions",
                                      "knowledge"]),
                "text": _schema("text", "string",
                                 "query string (or component name for "
                                 "kind=hardware)"),
                "k": _schema("k", "integer",
                              "top-k (default 3)", minimum=1, maximum=20),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "hits": {"type": "array", "items": {"type": "object"}},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"kind": "decisions", "text": "pwm frequency",
                        "k": 3},
        },
    },
    "chat": {
        "description": (
            "Send a free-form message to The Tank's local assistant. "
            "Routes through whatever chat backend is configured. Returns "
            "the assistant's reply text + current emotion. Useful for "
            "interactive debugging from a coding assistant."
        ),
        "tags": ["read", "chat"],
        "rate_class": "read",
        "parameters": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": _schema("text", "string", "utterance"),
                "use_external_llm": _schema(
                    "use_external_llm", "boolean",
                    "if true, also call external LLM providers "
                    "(Freebuff/OpenAI/Anthropic) and merge",
                    default=False, _has_default=True),
            },
        },
        "response": {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "emotion": {"type": "string"},
                "external_pieces": {"type": "array", "items": {"type": "string"}},
            },
        },
        "example": {
            "audit_id": "0c7e1d3c-1234-5678-9abc-def012345678",
            "params": {"text": "what is your current battery level?",
                        "use_external_llm": False},
        },
    },
}


def manifest_json() -> dict:
    """Top-level manifest. Tool descriptions drop into an OpenAI /
    Anthropic ``tools=[...]`` list one-to-one. Top-level ``body``
    schema documents that ``audit_id`` lives at the POST body root,
    NOT inside ``params`` \u2014 this is the most common AI integration
    mistake."""
    tools = []
    for name, c in COMMANDS.items():
        tools.append({
            "name": name,
            "description": c["description"],
            "request_body": {
                "type": "object",
                "required": ["audit_id", "params"],
                "properties": {
                    "audit_id": {"type": "string", "format": "uuid",
                                  "description":
                                      "client-generated UUIDv4 for "
                                      "audit log"},
                    "params": c["parameters"],
                },
            },
            "parameters": c["parameters"],
            "response": c["response"],
            "rate_class": c["rate_class"],
        })
    return {
        "version": "1",
        "auth": {
            "scheme": "Bearer",
            "header": "Authorization",
            "env_var_hint": "TANK_API_KEYS (JSON) or TANK_API_KEY",
        },
        "body_envelope": {
            "type": "object",
            "required": ["audit_id", "params"],
            "properties": {
                "audit_id": {"type": "string", "format": "uuid"},
                "params":   {"type": "object"},
            },
        },
        "tools": tools,
        "examples": {name: c["example"] for name, c in COMMANDS.items()},
        "notes": [
            "Every command requires Authorization: Bearer <TANK_API_KEY>",
            "Every command requires audit_id (uuidv4) at the body "
            "ROOT, not inside params.",
            "Write commands are subject to a software latch after estop.",
            "Move clamps vx/wz/duration before publishing.",
        ],
    }


# =============================================================================
# Voice-command plugin auto-discovery.
#
# Drop new plugins in ``plugins/`` and add their entry-point to
# ``plugins.PLUGIN_PATHS``.  They register themselves into COMMANDS above so
# the LLM tool introspection surface (``/api/cmd/manifest``) sees them
# without any extra plumbing.
# =============================================================================
from .plugins import _register_voice_plugins_manifest  # noqa: E402
_PLUGIN_NAMES = _register_voice_plugins_manifest(COMMANDS)