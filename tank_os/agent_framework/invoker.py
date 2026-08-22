"""ToolInvoker — runs a single host-level CLI script via subprocess.

Bounded subprocess runtime; stdio captured; audit-friendly response.
Same single-process pattern used by every host-level CLI in scripts/.
"""
from __future__ import annotations
import os
import subprocess
import sys
import time
from pathlib import Path

from .schemas import ToolDefinition, ToolCallRequest, ToolCallResponse, new_request_id


# Server-side safety bounds. LLMs can request huge timeout_s values;
# we clamp so a single call cannot pin a worker for hours/days.
DEFAULT_TIMEOUT_S = 30
MAX_TIMEOUT_S = 300  # 5 min hard cap per tool call


def _clamp_timeout(requested_s: int) -> int:
    """Clamp a caller-supplied timeout_s into [1, MAX_TIMEOUT_S]."""
    try:
        n = int(requested_s)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_S
    return max(1, min(n, MAX_TIMEOUT_S))


# Subprocess env allow-list: child argv comes from an LLM, so we strip
# tokens / SSH keys / cloud creds from os.environ before handing it the
# shell PATH. Anything not on this list is not propagated.
_SAFE_ENV_KEYS = frozenset({
    # shell / locale
    "PATH", "LANG", "LANGUAGE", "LC_ALL",
    "LC_CTYPE", "LC_NUMERIC", "LC_MESSAGES", "LC_COLLATE", "LC_MONETARY",
    "LC_TIME", "LC_PAPER", "LC_NAME", "LC_ADDRESS", "LC_TELEPHONE",
    "LC_MEASUREMENT", "LC_IDENTIFICATION",
    "TZ",
    # user / fs
    "HOME", "USER", "TMPDIR", "SHELL", "LOGNAME",
    # python
    "PYTHONPATH",
    # TLS for https to private CAs
    "SSL_CERT_FILE", "SSL_CERT_DIR",
})


def _safe_env(extra: dict) -> dict:
    """Return a copy of os.environ filtered through _SAFE_ENV_KEYS + extra."""
    base = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}
    if extra:
        base.update(extra)
    return base


# One-time observability: if TANK_AGENT_VERBOSE=1, log how many custom
# env vars we will strip. Helps an on-call figure out why a downstream
# tool "suddenly doesn't see TANK_API_KEY" after upgrading the framework.
# Off by default so test/CI imports stay clean.
if os.environ.get("TANK_AGENT_VERBOSE", "").strip() == "1":
    _stripped = sum(1 for k in os.environ if k not in _SAFE_ENV_KEYS)
    if _stripped:
        _samples = ", ".join(
            sorted({k.split("_", 1)[0] + "_***" for k in os.environ if k not in _SAFE_ENV_KEYS})[:5]
        )
        print(
            f"[agent_framework] safe_env will strip {_stripped} non-allow-listed "
            f"env vars before LLM-driven child processes (sample prefixes: {_samples})",
            file=sys.stderr,
        )


class ToolInvoker:
    """Dispatches LLM tool calls to host-level CLI scripts."""
    def __init__(self, registry):
        self.registry = registry

    def invoke(self, request: ToolCallRequest) -> ToolCallResponse:
        tool = self.registry.get(request.tool_name)
        rid = request.request_id or new_request_id()

        if tool is None:
            return ToolCallResponse(
                request_id=rid,
                tool_name=request.tool_name,
                status="unknown",
                exit_code=2,
                stdout="",
                stderr=f"unknown tool: {request.tool_name}",
                duration_ms=0,
            )

        cmd = self._build_cmd(tool, request.args)
        start = time.monotonic()
        timeout_s = _clamp_timeout(request.timeout_s)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(Path(tool.script_path).resolve().parent.parent),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=_safe_env({"TANK_AGENT_RID": rid, "TANK_AGENT_NAME": tool.name}),
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolCallResponse(
                request_id=rid,
                tool_name=tool.name,
                status="ok" if proc.returncode == 0 else "err",
                exit_code=proc.returncode,
                stdout=proc.stdout[:8192],
                stderr=proc.stderr[:4096],
                duration_ms=duration_ms,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return ToolCallResponse(
                request_id=rid,
                tool_name=tool.name,
                status="timeout",
                exit_code=124,
                stdout="",
                stderr=f"timed out after {timeout_s}s",
                duration_ms=duration_ms,
            )

    def _build_cmd(self, tool: ToolDefinition, args: dict) -> list:
        cmd = ["python3", tool.script_path, tool.subcommand]
        for k, v in (args or {}).items():
            if v is None:
                continue
            flag = f"--{k.replace('_', '-')}"
            if isinstance(v, bool):
                if v:
                    cmd.append(flag)
            else:
                cmd.extend([flag, str(v)])
        return cmd
