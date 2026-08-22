"""TerminalEngine — parse + execute + capture output, orchestrating AI + safety.

The engine never raises on bad input — every failure is captured into a
:meth:`CommandResult` dataclass that callers can inspect or print.
The :class:`Executor` is injectable so unit tests can fake the
subprocess layer without actually spawning anything.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from tank_os.core.event_bus import Event, EventBus
from tank_os.shell.terminal.ai_router import AIRouter
from tank_os.shell.terminal.history import CommandHistory
from tank_os.shell.terminal.safety import CommandSafety, SafetyClass

logger = logging.getLogger("tank_os.terminal.engine")


# ───────────────────────────────────────────────────────────────────────────
# Result dataclass
# ───────────────────────────────────────────────────────────────────────────

@dataclass
class CommandResult:
    command: str = ""
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    timed_out: bool = False
    safety_class: SafetyClass = SafetyClass.SAFE
    pending_confirmation: bool = False
    pending_explanation: str = ""
    error: str = ""
    tool_suggestion_shown: bool = False
    unrecognized: bool = False


# ───────────────────────────────────────────────────────────────────────────
# Executor abstraction — SubprocessExecutor is the sandbox-safe default.
# ───────────────────────────────────────────────────────────────────────────

class Executor:
    """Abstract executor. Tests inject a fake; production uses subprocess."""

    def execute(self, command: str, *, timeout_s: float) -> tuple:
        """Run ``command``; return ``(stdout, stderr, exit_code)``.

        Implementations must raise :class:`subprocess.TimeoutExpired`
        on real timeout — :class:`TerminalEngine` records that into
        :attr:`CommandResult.timed_out`.
        """
        raise NotImplementedError


class SubprocessExecutor(Executor):
    """Default executor using ``subprocess.Popen`` + captured pipes.

    We deliberately avoid ``pty.openpty`` here for two reasons:

    * PTY semantics are notoriously fragile on different platforms
      and CI runners.
    * Pipes keep the contract simple — output is fully captured by the
      time :meth:`execute` returns.

    Interactive programs (htop, less, password prompts) are out of
    scope. The Executor interface lets us swap in a PTY version later
    without touching the engine.
    """

    def execute(self, command: str, *, timeout_s: float) -> tuple:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            out, err = proc.communicate(timeout=timeout_s)
            return out or "", err or "", proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2.0)
            except Exception:                                   # noqa: BLE001
                pass
            raise


# ───────────────────────────────────────────────────────────────────────────
# TerminalEngine
# ───────────────────────────────────────────────────────────────────────────

class TerminalEngine:
    """Top-level AI terminal orchestrator."""

    def __init__(
        self,
        *,
        safety: Optional[CommandSafety] = None,
        history: Optional[CommandHistory] = None,
        ai: Optional[AIRouter] = None,
        executor_factory: Optional[Callable[[], Executor]] = None,
        default_timeout_s: float = 30.0,
        tool_registry: Optional[object] = None,
    ) -> None:
        self._bus = EventBus()
        self._safety = safety or CommandSafety()
        self._history = history or CommandHistory()
        self._ai = ai or AIRouter()
        self._executor_factory = executor_factory or SubprocessExecutor
        self._default_timeout_s = default_timeout_s
        self._pending: Optional[CommandResult] = None
        self._tool_registry = tool_registry

    def set_tool_registry(self, registry: object) -> None:
        """Attach a ToolRegistry instance after construction."""
        self._tool_registry = registry

    def _search_matching_tools(self, query: str, top_k: int = 5) -> list:
        """Search the ToolRegistry for tools matching the natural language query."""
        if self._tool_registry is None:
            return []
        try:
            return self._tool_registry.search(query, top_k=top_k)
        except Exception:
            return []

    # Sentinel prefix for tool suggestion messages — used by cli.py to
    # detect suggestion output (not an error, just a routing hint).
    _TOOL_SUGGESTION_PREFIX = "__TOOL_SUGGEST__"

    def _format_tool_suggestions(self, tools: list, original: str) -> str:
        """Format tool suggestions into a helpful message string.

        Uses a stable sentinel prefix so caller can detect suggestion vs.
        actual error without relying on emoji presence.
        """
        lines = [f"{self._TOOL_SUGGESTION_PREFIX} I couldn't translate that to a shell command. Try one of these tools:"]
        for t in tools[:5]:
            desc = (t.description or "").strip()[:90]
            lines.append(f"   🔧 invoke {t.name}  — {desc}")
        if len(tools) > 5:
            lines.append(f"   ... and {len(tools) - 5} more (use 'search {original[:30]}' to find)")
        lines.append(f"   📋 Or use 'tools --count' to browse all categories")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 50) -> List[str]:
        return self._history.recent_strings(limit=limit)

    def recall_history(self, query: str, limit: int = 10) -> List[str]:
        return self._history.recall(query, limit=limit)

    # ------------------------------------------------------------------
    # Parse + interpret
    # ------------------------------------------------------------------

    @staticmethod
    def parse(raw: str) -> str:
        """Strip a leading ``!`` and surrounding whitespace. ``""`` on empty."""
        s = (raw or "").strip()
        if not s:
            return ""
        if s.startswith("!"):
            return s[1:].strip()
        return s

    def interpret(self, raw: str) -> CommandResult:
        """Translate user input → a CommandResult ready to run (or confirm)."""
        line = self.parse(raw)
        if not line:
            return CommandResult(command="", error="empty input")
        sclass = self._safety.classify(line)
        if sclass is SafetyClass.BLOCKED:
            self._bus.emit(Event(
                "terminal_blocked_by_safety",
                {"command": line, "reason": "hard-blocked pattern"},
                source="terminal_engine",
            ))
            return CommandResult(
                command=line, safety_class=sclass,
                error=f"⛔ blocked: {line!r} matches a hard-blocked pattern",
            )
        # Route through AI unless the user explicitly typed !cmd.
        was_explicit = (raw or "").lstrip().startswith("!")
        interpreted = line
        ai_failed = False
        if not was_explicit:
            ai_reply = self._ai.natural_to_shell(line)
            if ai_reply is not None:
                interpreted = ai_reply.command
                self._bus.emit(Event(
                    "terminal_ai_suggested",
                    {"input": line, "command": interpreted,
                     "explanation": ai_reply.explanation},
                    source="terminal_engine",
                ))
            else:
                ai_failed = True
            if interpreted:
                # Reclassify after AI expansion — the AI may have
                # surfaced a dangerous verb we didn't see in the
                # original natural-language line.
                sclass = self._safety.classify(interpreted)
        pending = sclass in (SafetyClass.MUTATING, SafetyClass.DANGEROUS)
        result = CommandResult(
            command=interpreted, safety_class=sclass,
            pending_confirmation=pending,
            pending_explanation=(
                "This command modifies the system. Confirm before running."
                if pending else ""
            ),
        )

        # ── Tool routing: when AI fails to find a shell command,
        # search the ToolRegistry for matching tools ──
        if ai_failed or (not was_explicit and not interpreted):
            matched_tools = self._search_matching_tools(line)
            if matched_tools:
                result.error = self._format_tool_suggestions(matched_tools, line)
                result.pending_explanation = result.error
                result.command = line
                result.tool_suggestion_shown = True
                return result
            # No tools matched — flag as unrecognized natural language
            result.unrecognized = True
            result.error = f"🤔 Sorry, I couldn't understand '{line}'. Try 'help' to see available commands, or use 'search {line[:20]}' to find relevant tools."
            result.command = line
            return result

        if pending:
            self._pending = result
            self._bus.emit(Event(
                "terminal_confirmation_requested",
                {"command": interpreted, "class": sclass.name},
                source="terminal_engine",
            ))
        return result

    # ------------------------------------------------------------------
    # Confirm + run
    # ------------------------------------------------------------------

    def confirm_and_run(self, allowed: bool, *,
                        timeout_s: Optional[float] = None) -> CommandResult:
        """Run (or drop) the command waiting on operator confirmation."""
        pending = self._pending
        self._pending = None
        if pending is None:
            return CommandResult(command="", error="no command awaiting confirmation")
        self._bus.emit(Event(
            "terminal_confirmation_result",
            {"command": pending.command, "allowed": allowed},
            source="terminal_engine",
        ))
        if not allowed:
            return CommandResult(
                command=pending.command, safety_class=pending.safety_class,
                error="cancelled by operator",
            )
        return self.run(pending.command, timeout_s=timeout_s)

    # ------------------------------------------------------------------
    # Run a shell command directly (no confirmation gate)
    # ------------------------------------------------------------------

    def run(self, command: str, *,
            timeout_s: Optional[float] = None) -> CommandResult:
        cmd = (command or "").strip()
        if not cmd:
            return CommandResult(command=command, error="empty command")
        sclass = self._safety.classify(cmd)
        if sclass is SafetyClass.BLOCKED:
            self._bus.emit(Event(
                "terminal_blocked_by_safety",
                {"command": cmd, "reason": "hard-blocked pattern"},
                source="terminal_engine",
            ))
            return CommandResult(
                command=cmd, safety_class=sclass,
                error=f"⛔ blocked: {cmd!r}",
            )
        timeout = timeout_s if timeout_s is not None else self._default_timeout_s
        self._bus.emit(Event(
            "terminal_process_started",
            {"command": cmd, "timeout_s": timeout},
            source="terminal_engine",
        ))
        exe = self._executor_factory()
        start = time.time()
        try:
            out, err, rc = exe.execute(cmd, timeout_s=timeout)
            elapsed_ms = (time.time() - start) * 1000.0
            self._history.append(cmd, exit_code=rc, success=(rc == 0),
                                 stderr=err or "")
            self._bus.emit(Event(
                "terminal_command_finished",
                {"command": cmd, "exit_code": rc, "duration_ms": elapsed_ms,
                 "had_stderr": bool(err)},
                source="terminal_engine",
            ))
            return CommandResult(
                command=cmd, exit_code=rc, stdout=out, stderr=err,
                duration_ms=elapsed_ms, timed_out=False, safety_class=sclass,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.time() - start) * 1000.0
            self._history.append(cmd, exit_code=None, success=False,
                                 stderr="<timeout>")
            self._bus.emit(Event(
                "terminal_command_finished",
                {"command": cmd, "exit_code": None, "timed_out": True,
                 "duration_ms": elapsed_ms},
                source="terminal_engine",
            ))
            return CommandResult(
                command=cmd, exit_code=None, stdout="", stderr="<timeout>",
                duration_ms=elapsed_ms, timed_out=True, safety_class=sclass,
                error="execution timed out",
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            logger.warning("Executor raised for %r: %s", cmd, exc)
            return CommandResult(
                command=cmd, safety_class=sclass,
                error=f"executor failed: {exc}",
            )

    # ------------------------------------------------------------------
    # Explain the last failed command via AI
    # ------------------------------------------------------------------

    def explain_last_error(self) -> str:
        for entry in reversed(self._history.recent(limit=20)):
            if not entry.success and entry.stderr:
                explanation = self._ai.explain_error(
                    entry.command, entry.stderr,
                )
                if explanation:
                    self._bus.emit(Event(
                        "terminal_history_recalled",
                        {"kind": "explain_error",
                         "command": entry.command},
                        source="terminal_engine",
                    ))
                return explanation
        return ""
