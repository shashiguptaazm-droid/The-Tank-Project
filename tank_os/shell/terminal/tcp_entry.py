#!/usr/bin/env python3
"""TankOS TCP Terminal Entry Point — direct TCP access to TerminalREPL.

Usage (systemd socket-activated):
    /usr/local/bin/tankos-terminal

Or run directly for testing:
    python3 -m tank_os.shell.terminal.tcp_entry

Listens on stdin/stdout (piped by systemd socket activation) and
runs the full TankOS TerminalREPL with all AI engines, agent framework,
and system commands.
"""

from __future__ import annotations

import os
import sys
import traceback

# Ensure we can import from the project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main() -> None:
    """Bootstrap TankOS TerminalREPL for TCP connections."""
    print("TankOS AI Terminal v2.0 — Connected via TCP", flush=True)
    print(f"PID: {os.getpid()}", flush=True)

    try:
        # ── Initialize AIManager ──
        try:
            from tank_os.core.ai_manager import AIManager
            ai = AIManager()
            ai.initialize()
            print(f"AI: {ai.default_provider} ({len(ai.list_providers())} providers)", flush=True)
        except Exception as e:
            print(f"AI: local-stub (init error: {e})", flush=True)

        # ── Evolution Bridge ──
        try:
            from tank_os.core.evolution_bridge import init_evolution_providers
            n = init_evolution_providers(
                discover_models=True,
                register_local=True,
                register_rotation=True,
                set_rotation_default=True,
            )
            print(f"Evolution: {n} providers registered", flush=True)
        except ImportError:
            print("Evolution: not available", flush=True)
        except Exception as e:
            print(f"Evolution: init skipped ({e})", flush=True)

        # ── Launch TerminalREPL ──
        from tank_os.shell.terminal.engine import SubprocessExecutor, TerminalEngine
        from tank_os.shell.terminal.cli import TerminalREPL

        engine = TerminalEngine(
            executor_factory=SubprocessExecutor,
            default_timeout_s=15.0,
        )
        repl = TerminalREPL(engine=engine)

        # Pre-load the tool registry for a fast first command
        try:
            reg = repl._get_registry()
            if reg:
                tools = reg.list()
                cats = reg.categories()
                print(f"Tools: {len(tools)} tools in {len(cats)} categories", flush=True)
        except Exception:
            pass

        print("Ready. Type 'help' for commands, 'exit' to disconnect.", flush=True)
        print(flush=True)

        repl.cmdloop()

    except KeyboardInterrupt:
        print("\nDisconnected.", flush=True)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
