"""Typed shapes for tool definitions, calls, responses, and audit records.

Pure-data layer. No side effects. Serializes to / from JSON.
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Any


@dataclass
class ToolDefinition:
    """One tool entry as discovered from the registry.

    name:           unique dotted name ("script.sub")
    human_name:     display-facing name (same as name)
    description:    short Markdown description (one-line, ≤ 240 chars)
    script_path:    absolute path to the host-level CLI
    subcommand:     the argv[1] to invoke
    args_schema:    JSON-Schema-ish dict of arg shape (auto-derived)
    risk_tier:      "low" | "medium" | "high"
    category:       grouping metadata (download-music, vision, …)
    fids:           related F-IDs (from docstrings)
    examples:       list[dict] of usage examples (CLI form + curl form)
    """
    name: str
    human_name: str
    description: str
    script_path: str
    subcommand: str
    args_schema: dict
    risk_tier: str = "low"
    category: str = "general"
    fids: list = field(default_factory=list)
    examples: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ToolCallRequest:
    """A single LLM tool call request.

    tool_name: dotted "script.sub" name
    args:      dict of cleaned argument overrides (e.g. {"dry_run": True})
    request_id: caller-supplied UUID or auto-gen
    timeout_s:  max subprocess runtime (default 30s)
    """
    tool_name: str
    args: dict = field(default_factory=dict)
    request_id: Optional[str] = None
    timeout_s: int = 30


@dataclass
class ToolCallResponse:
    """Result of an invoke() call."""
    request_id: str
    tool_name: str
    status: str            # "ok" | "err" | "denied" | "timeout" | "unknown"
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    finished_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditRecord:
    audit_id: str
    request_id: str
    tool_name: str
    args: dict
    actor_token_hash: str
    status: str
    exit_code: int
    duration_ms: int
    ts: float


def new_request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"
