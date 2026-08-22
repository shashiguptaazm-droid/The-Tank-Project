"""TankOS Agent Framework — unified surface for AI LLM plugins + features.

Exposes every host-level CLI subcommand (1,166 today, plus plugin slots
for future features) as a structured tool that any AI LLM can call.

Layered above:
  - tank_command_bridge (:8082, 9 robot commands, bearer auth)
  - tank_meta (decision/code/hardware search on :8083)
  - tank_personalize (preferences dashboard on :8084)
  - 40 host-level CLI scripts in scripts/*.py (1,166 subcommands total)

The framework adds:
  - auto-generated OpenAI/Anthropic/raw-JSON manifests
  - a uniform `POST /invoke` dispatch surface
  - bearer-auth, per-token rate-limit, audit log
  - plugin-slot discovery so future features self-register

Public surface (this __init__):
    from tank_os.agent_framework import (
        ToolRegistry, ToolInvoker, Manifest, AuditLog,
        openai_manifest, anthropic_manifest, raw_manifest,
    )
"""

from .registry import ToolRegistry
from .invoker import ToolInvoker
from .manifest import Manifest, openai_manifest, anthropic_manifest, raw_manifest, RISK_TIERS
from .audit import AuditLog, AuditRecord
from .schemas import ToolDefinition, ToolCallRequest, ToolCallResponse

__all__ = [
    "ToolRegistry",
    "ToolInvoker",
    "Manifest",
    "openai_manifest",
    "anthropic_manifest",
    "raw_manifest",
    "RISK_TIERS",
    "AuditLog",
    "AuditRecord",
    "ToolDefinition",
    "ToolCallRequest",
    "ToolCallResponse",
]

__version__ = "0.1.0"
__author__ = "TankOS Agent Framework"
