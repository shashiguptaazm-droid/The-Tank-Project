"""TerminalREPL — inner REPL wiring :class:`TerminalEngine` for headless use.

This is the REPL that you reach from inside TankShell's
``simulation mode`` by typing ``terminal``. It is intentionally a
nested :class:`cmd.Cmd` so ``exit`` cleanly returns to the parent
TankOS shell without killing the process.

AI engine commands (``ai``, ``curiosity``, ``knowledge``, ``learning``)
show live status from all TankOS AI engines directly in the terminal.

Safe variants (``SAFE``/``READ``) execute immediately; mutating
commands ask for an explicit ``y/N`` confirmation; ``BLOCKED``
commands print an inline ``⛔ blocked: …`` error and stop.  No real
PTY or GUI plumbing — that lives in the Qt screen.
"""

from __future__ import annotations

import cmd
import os
import platform
import re
import shutil
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from tank_os.shell.terminal.engine import SubprocessExecutor, TerminalEngine
from tank_os.shell.terminal.safety import SafetyClass

# ─── Optional psutil (used by system commands) ───────────────────────
_HAS_PSUTIL = False
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    pass


# ─── Module-level helpers shared by TerminalREPL ──────────────────────

_RISK_ICONS = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def _risk_icon(tier: str) -> str:
    return _RISK_ICONS.get(tier, "⚪")


def _close_matches(name: str, candidates: list, n: int = 5) -> list:
    """Fuzzy-match `name` against `candidates` using difflib."""
    try:
        from difflib import get_close_matches
        return get_close_matches(name, candidates, n=n, cutoff=0.4)
    except Exception:
        return []


class TerminalREPL(cmd.Cmd):
    prompt = "tankos[ai]> "
    intro = (
        "\n"
        "  ╔══════════════════════════════════════════════════════╗\n"
        "  ║          🤖  TankOS AI Terminal v2.1              ║\n"
        "  ║    1,166 Tools · 12 AI Providers · 5 AI Engines   ║\n"
        "  ║         🦙 Local LLM · 🔄 Rotation · 🛡 Safety      ║\n"
        "  ╚══════════════════════════════════════════════════════╝\n"
        "\n"
        "  💬 AI & Shell:\n"
        "     <sentence>     Natural language → AI translates to command\n"
        "     !<cmd>         Run a shell command directly\n"
        "     ask <prompt>    Chat with the AI (uses default provider)\n"
        "     ask -p <prov> <prompt>  Chat with a specific provider\n"
        "     explain         AI explains the last failed command\n"
        "\n"
        "  🧠 AI Engines:\n"
        "     ai              Overview of all AI engines\n"
        "     providers       Show AI provider status & health\n"
        "     model           List available models & switch providers\n"
        "     curiosity       Curiosity engine stats & explore\n"
        "     knowledge       Knowledge graph status\n"
        "     learning        Learning scheduler status\n"
        "\n"
        "  📦 Agent Framework (1,166 tools):\n"
        "     tools           List all tools (--count/--category/--all/--json)\n"
        "     tool <name>     Show details for a specific tool\n"
        "     invoke <name>   Invoke a tool by dotted name\n"
        "     search <q>      Search tools by keyword\n"
        "\n"
        "  🌊 Torrents:\n"
        "     torrent <q>     Search torrents → pick → add to aria2\n"
        "\n"
        "  🖥 System:\n"
        "     status          System overview (CPU, RAM, disk, battery)\n"
        "     system          OS, kernel, hostname, uptime info\n"
        "     network         Network interfaces & connectivity\n"
        "     health          Health diagnostics (temps, ROS, services)\n"
        "     ps              List running processes\n"
        "     env             Show environment variables\n"
        "\n"
        "  📋 History:\n"
        "     history         List recent commands\n"
        "     recall <q>      Search command history\n"
        "     clear           Clear the screen\n"
        "\n"
        "  Type `help` for all commands, `exit` to return to TankOS shell.\n"
    )

    _SCRIPTS_DIR = None  # overridable for tests; None = auto-detect

    # ------------------------------------------------------------------
    def __init__(self, engine: Optional[TerminalEngine] = None) -> None:
        super().__init__()
        self._engine = engine or TerminalEngine(
            executor_factory=SubprocessExecutor,
            default_timeout_s=15.0,
        )
        self._registry: Optional[object] = None  # lazy ToolRegistry

    # ------------------------------------------------------------------
    # Agent Framework Tool Registry (lazy, cached)
    # ------------------------------------------------------------------

    def _get_registry(self):
        """Return a cached ToolRegistry, discovering scripts on first call."""
        if self._registry is not None:
            return self._registry
        try:
            from tank_os.agent_framework.registry import ToolRegistry
            from pathlib import Path
            scripts_dir = self._SCRIPTS_DIR or (
                Path(__file__).resolve().parent.parent.parent.parent / "scripts"
            )
            reg = ToolRegistry(scripts_dir=scripts_dir)
            reg.discover()
            self._registry = reg
        except Exception as exc:
            print(f"  ⚠ ToolRegistry init failed: {exc}")
            self._registry = None
        return self._registry

    def _all_tool_names(self):
        """Sorted list of all discovered tool names."""
        reg = self._get_registry()
        if reg is None:
            return []
        try:
            return sorted(t.name for t in reg.list())
        except Exception:
            return []

    # Tab-completion for Agent Framework tool commands
    # ------------------------------------------------------------------

    def complete_tools(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'tools --category <cat>' or 'tools --<flag>'."""
        _TOOLS_FLAGS = ["--category", "--risk", "--count", "--all", "--json"]
        # If the user is typing a flag (starts with --), suggest flags
        if text.startswith("--"):
            return [f for f in _TOOLS_FLAGS if f.startswith(text.lower())]
        # Otherwise suggest category names for the --category value
        reg = self._get_registry()
        if reg is None:
            return []
        try:
            cats = sorted(reg.categories().keys())
        except Exception:
            cats = []
        if not text:
            return cats
        return [c for c in cats if c.startswith(text.lower())]

    def complete_tool(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'tool <name>'."""
        names = self._all_tool_names()
        if not text:
            return names[:50]
        return [n for n in names if n.startswith(text.lower())][:50]

    complete_invoke = complete_tool
    complete_search = complete_tool

    # ------------------------------------------------------------------
    # Tab-completion for AI commands
    # ------------------------------------------------------------------

    def complete_curiosity(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'curiosity <subcommand>'."""
        subcommands = ["explore", "gaps", "stats"]
        if not text:
            return subcommands
        return [c for c in subcommands if c.startswith(text.lower())]

    def complete_knowledge(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'knowledge <entity-name>' from the live knowledge graph."""
        try:
            from tank_os.ai.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            entities = list(kg._entities.values()) if hasattr(kg, '_entities') else []
            names = sorted(e.name for e in entities if hasattr(e, 'name'))
            if not text:
                return names[:50]
            return [n for n in names if n.lower().startswith(text.lower())][:50]
        except Exception:
            return []

    def complete_learning(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'learning <subcommand>'."""
        subcommands = ["tasks", "budget", "status"]
        if not text:
            return subcommands
        return [c for c in subcommands if c.startswith(text.lower())]

    def complete_ask(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'ask -p <provider>' with provider names; free-form otherwise."""
        parts = line[:begidx].split()
        # If we're after '-p', complete provider names
        if len(parts) >= 2 and parts[-1] == "-p":
            try:
                from tank_os.core.ai_manager import AIManager
                providers = AIManager().list_providers()
                names = [p["name"] for p in providers]
            except Exception:
                names = ["local-stub", "local-llama", "rotation"]
            if not text:
                return names
            return [n for n in names if n.startswith(text.lower())]
        return []

    def complete_providers(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for providers."""
        return []

    def complete_status(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for status."""
        return []

    def complete_system(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for system."""
        return []

    def complete_network(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for network."""
        return []

    def complete_health(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for health."""
        return []

    def complete_ps(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for ps."""
        return []

    def complete_env(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete environment variable names."""
        names = sorted(os.environ.keys())
        if not text:
            return names[:50]
        return [n for n in names if n.lower().startswith(text.lower())][:50]

    def complete_clear(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for clear."""
        return []

    def complete_df(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for df."""
        return []

    def complete_free(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for free."""
        return []

    def complete_uptime(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for uptime."""
        return []

    def complete_ai(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for ai."""
        return []

    def complete_ai_engines(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for ai_engines."""
        return []

    def complete_history(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for history."""
        return []

    def complete_explain(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """No subcommands for explain."""
        return []

    # ------------------------------------------------------------------
    # TankOS AI Engine Commands
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # do_model — list models and switch default AI provider
    # ------------------------------------------------------------------

    def do_model(self, arg: str) -> None:
        """List available models and switch the default AI provider.

        Usage: model               — list all providers and models
               model <provider>    — switch default provider
               model local-llama   — switch to offline GGUF model
               model rotation      — switch to auto-rotation mode
        """
        from tank_os.core.ai_manager import AIManager
        ai = AIManager()
        switch_to = arg.strip().lower()

        # ── Switch mode ──
        if switch_to:
            providers = ai.list_providers()
            names = [p["name"] for p in providers]

            if switch_to not in names:
                close = [n for n in names if switch_to in n.lower()]
                print(f"\n  ❌ Unknown provider: {switch_to!r}")
                if close:
                    print(f"  Did you mean: {', '.join(close)}?")
                print(f"  Available: {', '.join(names[:10])}")
                print()
                return

            ok = ai.set_default(switch_to)
            if ok:
                p = next((p for p in providers if p["name"] == switch_to), {})
                model = p.get("model", "")
                model_str = f" ({model})" if model else ""
                print(f"\n  ✅ Switched to: {switch_to}{model_str}")
                print(f"  Try: ask -p {switch_to} hello\n")
            else:
                print(f"  ❌ Could not switch to {switch_to}\n")
            return

        # ── List mode ──
        print()
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │              🤖  AI Models & Providers                  │")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

        providers = ai.list_providers()
        default = ai.default_provider

        # Try to get local model info
        local_models = []
        try:
            from tank_os.core.local_llm_provider import discover_gguf_models
            local_models = discover_gguf_models()
        except Exception:
            pass

        print(f"  Default provider: {default} ★\n")
        print(f"  {'Provider':<18} {'Model':<35} {'Status':<10}")
        print(f"  {'─'*18} {'─'*35} {'─'*10}")

        for p in providers:
            name = p["name"]
            model = p.get("model", "") or "—"
            available = p.get("available", False)
            mark = " ★" if name == default else ""
            icon = "🟢" if available else "🔴"
            status = "available" if available else "offline"

            if name == "rotation":
                icon = "🔄"
                status = f"{p.get('providers_total', '?')} prov"
                model = "auto-fallback"
            elif name == "local-llama":
                icon = "🦙"
                loaded = p.get("loaded", False)
                status = "loaded" if loaded else "ready"
                model = p.get("model", "tinyllama") or "—"
            elif name == "local-stub":
                icon = "📋"
                status = "fallback"

            model_display = str(model)[:32] + "..." if len(str(model)) > 32 else str(model)
            print(f"  {icon} {name:<15}{mark} {model_display:<35} {status:<10}")

        # Show local GGUF models
        if local_models:
            print()
            print("  🦙 Local GGUF models on disk:")
            for m in local_models:
                print(f"     📦 {m.name} ({m.size_mb:.0f} MB){' [VLM]' if m.is_multimodal else ''}")

        print()
        print(f"  Switch: model <name>   (e.g. 'model rotation', 'model local-llama')")
        print(f"  Chat:   ask -p <name> <prompt>\n")

    def complete_model(self, text: str, line: str, begidx: int, endidx: int) -> list:
        """Tab-complete 'model <provider>' with provider names."""
        try:
            from tank_os.core.ai_manager import AIManager
            providers = AIManager().list_providers()
            names = [p["name"] for p in providers]
        except Exception:
            names = ["local-stub", "local-llama", "rotation"]
        if not text:
            return names
        return [n for n in names if n.startswith(text.lower())]

    # ------------------------------------------------------------------
    # do_ai — overview of all AI engines
    # ------------------------------------------------------------------

    def do_ai(self, arg: str) -> None:
        """Show overview of all TankOS AI engines."""
        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │             🧠  AI Engine Overview              │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        # ── AIManager status ──
        try:
            from tank_os.core.ai_manager import AIManager
            ai = AIManager()
            providers = ai.list_providers()
            online = sum(1 for p in providers if p.get("available", False))
            print(f"  🤖 AI Providers")
            print(f"     Total:     {len(providers)}")
            print(f"     Online:    {online}")
            print(f"     Default:   {ai.default_provider}")

            # Local LLM status
            try:
                from tank_os.core.local_llm_provider import discover_gguf_models
                models = discover_gguf_models()
                if models:
                    loaded = ai.provider_status("local-llama")
                    is_loaded = loaded.get("loaded", False)
                    print(f"     Local LLM: {'🟢 loaded' if is_loaded else '🟡 ' + str(len(models)) + ' models on disk'}")
                    if is_loaded:
                        model_name = loaded.get("model", "")
                        if model_name:
                            print(f"     Model:     {model_name}")
            except Exception:
                pass
            print()
        except Exception as e:
            print(f"  🤖 AI Providers: unavailable ({e})\n")

        # Knowledge Graph
        try:
            from tank_os.ai.knowledge_graph import KnowledgeGraph
            s = KnowledgeGraph().get_summary()
            print(f"  📊 Knowledge Graph")
            print(f"     Entities:  {s['total_entities']}")
            print(f"     Relations: {s['total_relationships']}")
            types = s.get('entity_types', [])
            print(f"     Types:     {', '.join(types) if types else 'none'}")
            print()
        except Exception as e:
            print(f"  📊 Knowledge Graph: unavailable ({e})\n")

        # Curiosity Engine
        try:
            from tank_os.ai.curiosity_engine import CuriosityEngine
            s = CuriosityEngine().get_summary()
            status = '🔍 exploring' if s['exploring_now'] else '💤 idle'
            print(f"  🔍 Curiosity Engine  {status}")
            print(f"     Explorations: {s['explorations']}")
            print(f"     Gaps:         {s['open_gaps']} open")
            print(f"     Discoveries:  {s['discoveries']} total")
            print()
        except Exception as e:
            print(f"  🔍 Curiosity Engine: unavailable ({e})\n")

        # Continuous Learning
        try:
            from tank_os.ai.continuous_learning import ContinuousLearningEngine
            s = ContinuousLearningEngine().get_summary()
            print(f"  📈 Learning Engine")
            print(f"     Patterns:    {s['patterns']}")
            print(f"     Preferences: {s['preferences']}")
            print(f"     Insights:    {s['insights']}")
            print(f"     Cycles:      {s['cycles']}")
            print()
        except Exception as e:
            print(f"  📈 Learning Engine: unavailable ({e})\n")

        # Learning Scheduler
        try:
            from tank_os.ai.learning_scheduler import LearningScheduler
            s = LearningScheduler().get_summary()
            sched_status = '🟢 running' if s['running'] else '🔴 stopped'
            print(f"  ⏰ Scheduler  {sched_status}")
            print(f"     Tasks:     {s['tasks']}")
            print(f"     Active:    {'✅ yes' if s['active'] else '—'}")
            print(f"     Budget:    {s['budget_used']:.1f}h used")
            print()
        except Exception as e:
            print(f"  ⏰ Scheduler: unavailable ({e})\n")

        # Experience Engine
        try:
            from tank_os.ai.experience_engine import ExperienceEngine
            s = ExperienceEngine().get_summary()
            print(f"  📝 Experience Engine")
            print(f"     Total:     {s['total_experiences']}")
            print(f"     Today:     {s['today_count']}")
            print(f"     Success:   {s['success_rate']:.0%}")
            print()
        except Exception as e:
            print(f"  📝 Experience Engine: unavailable ({e})\n")

    # ------------------------------------------------------------------
    # do_curiosity — curiosity engine stats and controls
    # ------------------------------------------------------------------

    def do_curiosity(self, arg: str) -> None:
        """Show curiosity engine status.  Sub-commands:
           curiosity          — display stats
           curiosity explore  — trigger an exploration now
           curiosity gaps     — list knowledge gaps
        """
        from datetime import datetime as _dt
        sub = arg.strip().lower()

        try:
            from tank_os.ai.curiosity_engine import CuriosityEngine
            ce = CuriosityEngine()

            if sub == "explore":
                print("  🔍 Triggering exploration...")
                exp = ce.auto_explore()
                if exp:
                    print(f"  ✅ Exploration complete: {exp.description}")
                    for finding in exp.findings:
                        print(f"     · {finding}")
                else:
                    print("  (cooldown active or nothing to explore)\n")
                return

            elif sub == "gaps":
                gaps = ce.get_knowledge_gaps()
                if gaps:
                    print(f"\n  📋 Knowledge Gaps ({len(gaps)}):\n")
                    for gap in gaps:
                        print(f"     {gap.topic}")
                        print(f"     Priority: {'⭐' * gap.priority} | Source: {gap.source}")
                        print()
                else:
                    print("  (no knowledge gaps)\n")
                return

            # Default: show stats
            stats = ce.get_stats()
            print()
            print("  ┌──────────────────────────────────────────────────┐")
            print("  │             🔍  Curiosity Engine               │")
            print("  └──────────────────────────────────────────────────┘")
            print()
            print(f"  Explorations:     {stats['total_explorations']}")
            print(f"  Successful:       {stats['successful']}")
            print(f"  Interrupted:      {stats['interrupted']}")
            print(f"  Auto-mode:        {'✅ on' if stats['auto_mode'] else '❌ off'}")
            print()

            if stats.get('by_type'):
                print("  By type:")
                for etype, count in sorted(stats['by_type'].items(), key=lambda x: -x[1]):
                    print(f"    {etype.replace('_', ' ').title()}: {count}")
            print()

            gaps_s = stats.get('knowledge_gaps', {})
            print(f"  Open gaps:        {gaps_s.get('open', 0)}")
            print(f"  Filled gaps:      {gaps_s.get('filled', 0)}")
            print(f"  Discoveries:      {stats['discoveries']['total']} total, "
                  f"{stats['discoveries']['working']} working")
            print()

            recent = ce.get_recent_explorations(3)
            if recent:
                print("  Recent explorations:")
                for exp in recent:
                    ts = _dt.fromtimestamp(exp.start_time).strftime("%H:%M:%S")
                    emoji = '✅' if exp.result == 'success' else '❌'
                    print(f"    {emoji} [{ts}] {exp.exploration_type.value}: "
                          f"{len(exp.findings)} findings — {exp.description[:50]}")
                print()
            print("  (try 'curiosity explore' or 'curiosity gaps')\n")

        except Exception as e:
            print(f"  (error) {e}\n")

    # ------------------------------------------------------------------
    # do_knowledge — knowledge graph status
    # ------------------------------------------------------------------

    def do_knowledge(self, arg: str) -> None:
        """Show knowledge graph status.  Sub-commands:
           knowledge            — display stats
           knowledge <keyword>  — search entities by name
        """
        sub = arg.strip()

        try:
            from tank_os.ai.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()

            if sub:
                # Search mode
                results = kg.search_entities(sub)
                if results:
                    print(f"\n  Entity search for '{sub}':")
                    for entity in results:
                        print(f"    🔹 {entity.name}  ({entity.entity_type})")
                        if entity.description:
                            print(f"       {entity.description[:80]}")
                        rels = kg.get_relationships(entity.id)
                        if rels:
                            print(f"       ({len(rels)} relationships)")
                        print()
                else:
                    print(f"  (no entities matching '{sub}')\n")
                return

            # Default: show stats
            stats = kg.get_stats()
            print()
            print("  ┌──────────────────────────────────────────────────┐")
            print("  │             📊  Knowledge Graph                │")
            print("  └──────────────────────────────────────────────────┘")
            print()
            print(f"  Total entities:    {stats['total_entities']}")
            print(f"  Relationships:     {stats['total_relationships']}")
            print(f"  Avg strength:      {stats['average_strength']}")
            print(f"  Communities:       {stats['communities']}")
            print()

            if stats.get('by_type'):
                print("  Entity types:")
                for etype, count in sorted(stats['by_type'].items(),
                                            key=lambda x: -x[1]):
                    bar = "█" * min(count, 20)
                    print(f"    {etype:<12} {bar} {count}")
                print()

            if stats.get('most_connected'):
                print("  Most connected:")
                for item in stats['most_connected'][:5]:
                    print(f"    🔗 {item['name']} ({item['type']}) "
                          f"— {item['connections']} connections")
                print()

            print("  (try 'knowledge <keyword>' to search entities)\n")

        except Exception as e:
            print(f"  (error) {e}\n")

    # ------------------------------------------------------------------
    # do_learning — learning scheduler status
    # ------------------------------------------------------------------

    def do_learning(self, arg: str) -> None:
        """Show learning scheduler status. Sub-commands:
           learning          — full status overview
           learning tasks    — list all scheduled tasks
           learning budget   — show daily budget usage
           learning status   — scheduler status (default)
        """
        from datetime import timedelta as _td
        from time import time
        sub = arg.strip().lower()

        try:
            from tank_os.ai.learning_scheduler import LearningScheduler
            ls = LearningScheduler()
            status = ls.get_status()

            # ── Sub-command: budget only ──
            if sub == "budget":
                b = status.get('budget', {})
                used = b.get('used_today_h', 0)
                max_h = b.get('max_daily_h', 4)
                bar_len = 20
                filled = int((used / max(max_h, 1)) * bar_len)
                bar_str = "█" * filled + "░" * (bar_len - filled)
                print()
                print("  Daily budget:     [{bar_str}]")
                print(f"  Used:             {used:.1f}h / {max_h}h")
                print(f"  Completed:        {b.get('tasks_completed', 0)}")
                print(f"  Failed:           {b.get('tasks_failed', 0)}")
                print()
                return

            # ── Sub-command: tasks only ──
            if sub == "tasks":
                tasks = ls.get_tasks()
                if not tasks:
                    print("  (no scheduled tasks)\n")
                    return
                print()
                print("  Scheduled tasks:")
                for task in tasks:
                    remaining = max(0, int(task.next_run - time()))
                    label = task.task_type.value.replace('_', ' ').title()
                    due_str = str(_td(seconds=remaining)) if remaining > 0 else 'now'
                    runs = f"({task.run_count}x)" if task.run_count else ""
                    icon = '🟢' if task.enabled else '⚪'
                    print(f"    {icon} {label:<30} in {due_str:<12} {runs}")
                print()
                return

            # ── Full status (default) ──
            print()
            print("  ┌──────────────────────────────────────────────────┐")
            print("  │             ⏰  Learning Scheduler              │")
            print("  └──────────────────────────────────────────────────┘")
            print()

            sched_status = '🟢 running' if status['running'] else '🔴 stopped'
            system_state = 'busy' if status['system_busy'] else 'idle'
            print(f"  Status:           {sched_status} ({system_state})")
            print(f"  Scheduled tasks:  {status['scheduled_tasks']} "
                  f"({status['enabled_tasks']} enabled)")
            print(f"  Active now:       {status['active_task'] or '—'}")
            print()

            b = status.get('budget', {})
            used = b.get('used_today_h', 0)
            max_h = b.get('max_daily_h', 4)
            bar_len = 20
            filled = int((used / max(max_h, 1)) * bar_len)
            bar_str = "█" * filled + "░" * (bar_len - filled)
            print(f"  Daily budget:     [{bar_str}] {used:.1f}h / {max_h}h")
            print(f"  Tasks today:      {b.get('tasks_completed', 0)} done, "
                  f"{b.get('tasks_failed', 0)} failed")
            print()

            nt = status.get('next_task', {})
            if nt.get('type'):
                remaining = nt['in_seconds']
                print(f"  Next task:        {nt['type']} "
                      f"(in {_td(seconds=remaining)})")
            print()

            lw = status.get('learning_window', {})
            window_icon = '🟢' if lw.get('active') else '🔴'
            print(f"  Learning window:  {window_icon} "
                  f"{lw.get('start', '?')} – {lw.get('end', '?')}")
            print()

            tasks = ls.get_tasks()
            if tasks:
                print("  All scheduled tasks:")
                for task in tasks:
                    remaining = max(0, int(task.next_run - time()))
                    label = task.task_type.value.replace('_', ' ').title()
                    due_str = str(_td(seconds=remaining)) if remaining > 0 else 'now'
                    runs = f"({task.run_count}x)" if task.run_count else ""
                    icon = '🟢' if task.enabled else '⚪'
                    print(f"    {icon} {label:<30} in {due_str:<12} {runs}")
                print()

        except Exception as e:
            print(f"  (error) {e}\n")

    # ------------------------------------------------------------------
    # Agent Framework Tool Commands
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # do_tools — list all tools from the Agent Framework
    # ------------------------------------------------------------------

    def do_tools(self, arg: str) -> None:
        """List all tools discovered by the Agent Framework.

        Sub-options:
           tools                    — show all tools (paginated)
           tools --category <cat>   — filter by category
           tools --risk <tier>      — filter by risk (low|medium|high)
           tools --count            — only show category counts
           tools --all              — show all tools (no pagination)
           tools --json             — raw JSON dump
        """
        reg = self._get_registry()
        if reg is None:
            print("  ⚠ Agent Framework not available (ToolRegistry failed)\n")
            return

        args = (arg or "").strip().lower().split()
        show_count = "--count" in args
        show_json = "--json" in args
        show_all = "--all" in args
        category_filter = None
        risk_filter = None

        for i, a in enumerate(args):
            if a == "--category" and i + 1 < len(args):
                category_filter = args[i + 1]
            if a == "--risk" and i + 1 < len(args):
                risk_filter = args[i + 1]

        try:
            cats = reg.categories()
            tools = reg.list()
        except Exception as e:
            print(f"  ⚠ Failed to read registry: {e}\n")
            return

        if show_json:
            import json as _json
            print(_json.dumps(reg.as_dict(), indent=2))
            print()
            return

        if show_count:
            print()
            print(f"  📦  Tool Registry — {len(tools)} total tools in {len(cats)} categories")
            print()
            for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
                bar_len = min(count, 30)
                bar = "█" * bar_len if bar_len > 0 else ""
                print(f"    {cat:<25} {bar} {count}")
            print()
            return

        # Filter
        filtered = list(tools)
        if category_filter:
            filtered = [t for t in filtered if t.category == category_filter]
        if risk_filter:
            filtered = [t for t in filtered if t.risk_tier == risk_filter]
        filtered.sort(key=lambda t: t.name)

        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │           📦  Agent Framework Tools             │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        if category_filter:
            print(f"  Category: {category_filter}")
        if risk_filter:
            print(f"  Risk:     {risk_filter}")
        if not category_filter and not risk_filter:
            print(f"  {len(filtered)} tools in {len(cats)} categories")
        print()

        if not filtered:
            print("  (no matching tools)\n")
            return

        max_show = len(filtered) if show_all else 40
        shown = filtered[:max_show]

        for t in shown:
            risk_icon = _risk_icon(t.risk_tier)
            print(f"  {risk_icon} {t.name}")
            desc = (t.description or "").strip()[:100]
            if desc:
                print(f"     {desc}")
            print()

        if len(filtered) > max_show:
            print(f"  ... and {len(filtered) - max_show} more (use --all to show all)\n")

        print(f"  (try 'tool <name>' for details, 'invoke <name>' to run)\n")

    # ------------------------------------------------------------------
    # do_tool — show details for a single tool
    # ------------------------------------------------------------------

    def do_tool(self, arg: str) -> None:
        """Show detailed information about a specific tool.

        Usage: tool <dotted.name>
        """
        name = arg.strip()
        if not name:
            print("  Usage: tool <name>  (e.g. 'tool diagnostics.run')\n")
            names = self._all_tool_names()
            if names:
                print("  Available tools (first 20):")
                for n in names[:20]:
                    print(f"    · {n}")
                if len(names) > 20:
                    print(f"    ... and {len(names) - 20} more")
                print()
            return

        reg = self._get_registry()
        if reg is None:
            print("  ⚠ Agent Framework not available\n")
            return

        try:
            t = reg.get(name)
        except Exception as e:
            print(f"  ⚠ {e}\n")
            return

        if t is None:
            print(f"  ❌ Unknown tool: {name!r}")
            # Suggest close matches
            names = self._all_tool_names()
            close = _close_matches(name, names)
            if close:
                print(f"  Did you mean: {', '.join(close)}?")
            print()
            return

        risk_icon = _risk_icon(t.risk_tier)
        print()
        print(f"  ┌─ {t.name}")
        print(f"  │")
        print(f"  │  {t.description}")
        print(f"  │")
        print(f"  │  Category:    {t.category}")
        print(f"  │  Risk tier:   {risk_icon} {t.risk_tier}")
        print(f"  │  Script:      {t.script_path}")
        print(f"  │  Subcommand:  {t.subcommand}")
        if t.fids:
            print(f"  │  F-IDs:       {', '.join(f'F{fid}' for fid in t.fids)}")
        print(f"  │")
        if t.args_schema and t.args_schema.get('properties'):
            props = t.args_schema['properties']
            print(f"  │  Arguments (JSON Schema):")
            for pname, pschema in props.items():
                ptype = pschema.get('type', 'any')
                pdesc = pschema.get('description', '')
                default = pschema.get('default', None)
                default_str = f" (default: {default})" if default is not None else ""
                print(f"  │    --{pname}  <{ptype}>  {pdesc}{default_str}")
            print(f"  │")
        if t.examples:
            print(f"  │  Examples:")
            for ex in t.examples:
                cli_ex = ex.get('cli', '')
                if cli_ex:
                    print(f"  │    $ {cli_ex}")
            print(f"  │")
        print(f"  └─  (try 'invoke {t.name} ...' to run)\n")

    # ------------------------------------------------------------------
    # do_invoke — invoke a tool through the Agent Framework
    # ------------------------------------------------------------------

    def do_invoke(self, arg: str) -> None:
        """Invoke a tool by its dotted name.

        Usage: invoke <name> [--dry-run] [--key value ...]

        Examples:
          invoke diagnostics.run
          invoke diagnostics.run --dry-run
          invoke download_music.album --out /tmp/music
        """
        parts = (arg or "").strip().split()
        if not parts:
            print("  Usage: invoke <name> [--dry-run] [--key value ...]\n")
            return

        tool_name = parts[0]
        raw_args = parts[1:]

        # Parse optional --key value pairs
        parsed_kwargs = {}
        i = 0
        while i < len(raw_args):
            k = raw_args[i]
            if k.startswith("--"):
                key = k[2:].replace("-", "_")
                if i + 1 < len(raw_args) and not raw_args[i + 1].startswith("--"):
                    val = raw_args[i + 1]
                    if val.lower() in ("true", "false"):
                        val = val.lower() == "true"
                    else:
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    parsed_kwargs[key] = val
                    i += 2
                else:
                    parsed_kwargs[key] = True
                    i += 1
            else:
                i += 1

        reg = self._get_registry()
        if reg is None:
            print("  ⚠ Agent Framework not available\n")
            return

        try:
            from tank_os.agent_framework.invoker import ToolInvoker
            from tank_os.agent_framework.schemas import ToolCallRequest
        except Exception as e:
            print(f"  ⚠ ToolInvoker import failed: {e}\n")
            return

        tool_def = reg.get(tool_name)
        if tool_def is None:
            print(f"  ❌ Unknown tool: {tool_name!r}")
            names = self._all_tool_names()
            close = _close_matches(tool_name, names)
            if close:
                print(f"  Did you mean: {', '.join(close)}?")
            print()
            return

        # Confirmation gate for high-risk tools
        if tool_def.risk_tier == "high":
            try:
                answer = input(
                    f"  🔴 High-risk tool ({tool_name}) — confirm invoke? [y/N] "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer not in ("y", "yes"):
                print("  (cancelled)\n")
                return
            print()

        risk_icon = _risk_icon(tool_def.risk_tier)
        print(f"  {risk_icon} Invoking: {tool_name}")
        print(f"  Script:   {tool_def.script_path} {tool_def.subcommand}")
        if parsed_kwargs:
            print(f"  Args:     {parsed_kwargs}")
        print()

        try:
            invoker = ToolInvoker(reg)
            req = ToolCallRequest(
                tool_name=tool_name,
                args=parsed_kwargs,
                timeout_s=30,
            )
            resp = invoker.invoke(req)
        except Exception as e:
            print(f"  ❌ Invocation failed: {e}\n")
            return

        # Show result
        status_icon = {
            'ok': '✅', 'err': '❌', 'timeout': '⏰',
            'unknown': '❓', 'denied': '🚫'
        }.get(resp.status, '❓')
        print(f"  {status_icon} Status:    {resp.status} (exit {resp.exit_code})")
        print(f"  ⏱  Duration:  {resp.duration_ms} ms")
        print()

        if resp.stdout:
            print("  stdout:")
            for line in resp.stdout.rstrip().split("\n"):
                print(f"    {line}")
            print()
        if resp.stderr:
            print(f"  stderr: {resp.stderr[:500]}")
            print()

    # ------------------------------------------------------------------
    # do_search — search tools by keyword
    # ------------------------------------------------------------------

    def do_search(self, arg: str) -> None:
        """Search tools by keyword across name + description.

        Usage: search <keyword> [--category <cat>] [--risk <tier>] [--all]
        """
        query = arg.strip()
        if not query:
            print("  Usage: search <keyword>  (e.g. 'search vision')\n")
            return

        reg = self._get_registry()
        if reg is None:
            print("  ⚠ Agent Framework not available\n")
            return

        # Strip options from query for the search, but pass them to filter
        options = ["--category", "--risk", "--all"]
        search_query = query
        category_filter = None
        risk_filter = None
        show_all = "--all" in query.split()

        tokens = query.split()
        for i, tok in enumerate(tokens):
            if tok == "--category" and i + 1 < len(tokens):
                category_filter = tokens[i + 1]
                search_query = search_query.replace(f"--category {tokens[i+1]}", "")
            if tok == "--risk" and i + 1 < len(tokens):
                risk_filter = tokens[i + 1]
                search_query = search_query.replace(f"--risk {tokens[i+1]}", "")
            if tok in options:
                search_query = search_query.replace(tok, "")

        search_query = search_query.strip()

        try:
            results = reg.search(search_query, top_k=200)
        except Exception as e:
            print(f"  ⚠ Search failed: {e}\n")
            return

        # Apply post-filter
        if category_filter:
            results = [t for t in results if t.category == category_filter]
        if risk_filter:
            results = [t for t in results if t.risk_tier == risk_filter]

        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print(f"  │       🔎  Search Results: '{search_query}'        │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        if category_filter:
            print(f"  Category: {category_filter}")
        if risk_filter:
            print(f"  Risk:     {risk_filter}")
        print(f"  {len(results)} matching tools\n")

        if not results:
            print("  (no matches — try a broader keyword)\n")
            return

        max_show = len(results) if show_all else 25
        shown = results[:max_show]

        for t in shown:
            risk_icon = _risk_icon(t.risk_tier)
            print(f"  {risk_icon} {t.name}")
            desc = (t.description or "").strip()[:100]
            if desc:
                print(f"     [{t.category}] {desc}")
            print()

        if len(results) > max_show:
            print(f"  ... and {len(results) - max_show} more (use --all to show all)\n")

        print(f"  (try 'tool <name>' for details, 'invoke <name>' to run)\n")

    # ------------------------------------------------------------------
    # do_torrent — search torrents + interactive picker + add to aria2
    # ------------------------------------------------------------------

    def do_torrent(self, arg: str) -> None:
        """Search torrent sites and download via interactive picker.

        Usage: torrent <search query>
        Example: torrent game of thrones s01
        Example: torrent --category TV stranger things
        Example: torrent --provider ThePirateBay ubuntu iso
        """
        args = (arg or "").strip()
        if not args:
            print("  Usage: torrent <search query>")
            print("  Example: torrent game of thrones")
            print("  Example: torrent --category TV stranger things")
            print()
            return

        # Build the command for torrent_search.py
        scripts_dir = self._SCRIPTS_DIR or (
            Path(__file__).resolve().parent.parent.parent.parent / "scripts"
        )
        script_path = Path(scripts_dir) / "torrent_search.py"

        if not script_path.exists():
            print(f"  ❌ Torrent search script not found: {script_path}")
            print("  Install: scripts/torrent_search.py must exist")
            print()
            return

        cmd = ["python3", str(script_path), "--interactive"]
        # Forward optional flags
        tokens = args.split()
        query_parts = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok in ("--category", "-c") and i + 1 < len(tokens):
                cmd.extend(["--category", tokens[i + 1]])
                i += 2
            elif tok in ("--provider", "-p") and i + 1 < len(tokens):
                cmd.extend(["--provider", tokens[i + 1]])
                i += 2
            elif tok in ("--limit", "-l") and i + 1 < len(tokens):
                cmd.extend(["--limit", tokens[i + 1]])
                i += 2
            else:
                query_parts.append(tok)
                i += 1

        query = " ".join(query_parts).strip()
        if not query:
            print("  Usage: torrent <search query>")
            print()
            return

        cmd.append(query)

        print()
        print(f"  🔍 Searching torrents for: '{query}'...")
        print()

        try:
            result = subprocess.run(
                cmd,
                capture_output=False,  # let interactive picker use stdin/stdout
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"  ❌ Search failed (exit {result.returncode})")
                print()
        except subprocess.TimeoutExpired:
            print("  ❌ Search timed out")
            print()
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()

    complete_torrent = complete_search  # free-form query, no tab-completion

    # ------------------------------------------------------------------
    # do_ask — chat with the AI directly
    # ------------------------------------------------------------------

    def do_ask(self, arg: str) -> None:
        """Send a prompt to the AI and stream the response.

        Usage: ask [-p <provider>] <your prompt>
        Example: ask what is the capital of France?
        Example: ask -p local-llama tell me a joke
        Example: ask -p rotation summarize this
        """
        args = (arg or "").strip()
        provider = None

        # Parse -p <provider> flag
        if args.startswith("-p "):
            parts = args[3:].split(None, 1)
            if len(parts) >= 1:
                provider = parts[0]
                prompt = parts[1] if len(parts) > 1 else ""
            else:
                prompt = ""
        else:
            prompt = args

        if not prompt:
            print("  Usage: ask [-p <provider>] <your prompt>\n")
            print("  Available providers (use 'providers' to see all):")
            try:
                from tank_os.core.ai_manager import AIManager
                ai = AIManager()
                providers = ai.list_providers()
                for p in providers[:8]:
                    name = p.get("name", "?")
                    avail = "🟢" if p.get("available") else "🔴"
                    model = p.get("model", "")
                    model_str = f" ({model})" if model else ""
                    default = " ★" if name == ai.default_provider else ""
                    print(f"    {avail} {name}{default}{model_str}")
                if len(providers) > 8:
                    print(f"    ... and {len(providers) - 8} more")
            except Exception:
                pass
            print()
            return

        print(f"\n  🤔 Thinking{f' ({provider})' if provider else ''}...")
        try:
            from tank_os.core.ai_manager import AIManager
            ai = AIManager()
            resp = ai.chat(prompt, provider=provider)
            print(f"\n  💬 {resp.text}\n")
            print(f"  ({resp.provider}, {resp.duration_ms:.0f}ms)\n")
        except Exception as e:
            print(f"  ❌ AI error: {e}\n")

    # ------------------------------------------------------------------
    # do_providers — show AI provider status with model names + health
    # ------------------------------------------------------------------

    def do_providers(self, arg: str) -> None:
        """Show all registered AI providers with model names and health."""
        print()
        print("  ┌──────────────────────────────────────────────────────────┐")
        print("  │              🤖  AI Provider Status                     │")
        print("  └──────────────────────────────────────────────────────────┘")
        print()

        try:
            from tank_os.core.ai_manager import AIManager
            ai = AIManager()
            providers = ai.list_providers()
            default = ai.default_provider

            if not providers:
                print("  (no providers registered)\n")
                return

            # Try to get evolution health details
            evolution_health = {}
            try:
                from tank_assistant.evolution.health import health_monitor
                for p in providers:
                    name = p.get("name", "")
                    if name:
                        evolution_health[name] = health_monitor.get_provider_state(name)
            except Exception:
                pass

            # Try to get local-llama details
            local_llama_info = None
            try:
                from tank_os.core.local_llm_provider import LocalLlamaProvider, discover_gguf_models
                models = discover_gguf_models()
                if models:
                    local_llama_info = models
            except Exception:
                pass

            online_count = sum(1 for p in providers if p.get("available") and p.get("name") != "local-stub")
            print(f"  Default: {default}")
            print(f"  Online:  {online_count} providers")
            if local_llama_info:
                print(f"  Local:   {len(local_llama_info)} GGUF model(s) on disk")
            print()

            # Print provider table
            print(f"  {'Provider':<18} {'Model':<35} {'Health':<10}")
            print(f"  {'─'*18} {'─'*35} {'─'*10}")

            for p in providers:
                name = p.get("name", "unknown")
                model = p.get("model", "") or "—"
                available = p.get("available", False)
                default_mark = " ★" if name == default else ""

                # Health icon from evolution circuit breaker
                health_icon = "🟢" if available else "🔴"
                health_text = "healthy" if available else "offline"
                if name in evolution_health:
                    state = evolution_health[name]
                    if hasattr(state, 'current'):
                        cb = state.current
                        if cb == "DEAD":
                            health_icon = "💀"
                            health_text = "dead"
                        elif cb == "DEGRADED":
                            health_icon = "🟡"
                            health_text = "degraded"
                        elif cb == "HEALTHY":
                            health_icon = "🟢"
                            health_text = "healthy"

                if name == "local-stub":
                    health_icon = "📋"
                    health_text = "stub"
                elif name == "local-llama":
                    health_icon = "🦙"
                    health_text = "gguf"
                elif name == "rotation":
                    health_icon = "🔄"
                    health_text = "auto"

                # Truncate model name for display
                model_display = model[:32] + "..." if len(str(model)) > 32 else model
                print(f"  {health_icon} {name:<15}{default_mark} {model_display:<35} {health_text:<10}")

            print()

            # Show local-llama models on disk
            if local_llama_info:
                print("  🦙 Local GGUF models:")
                for m in local_llama_info[:5]:
                    loaded = "✅" if getattr(m, 'is_multimodal', False) else "📦"
                    print(f"     {loaded} {m.name} ({m.size_mb:.0f} MB)")
                print()

            print(f"  (try 'ask <prompt>' to chat with {default}, 'model' to switch)\n")

        except Exception as e:
            print(f"  (error) {e}\n")

    # ------------------------------------------------------------------
    # do_status — system overview dashboard
    # ------------------------------------------------------------------

    def do_status(self, arg: str) -> None:
        """Show system status overview — CPU, RAM, disk, battery, ROS, network."""
        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │           🖥  System Status Dashboard            │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        # Hostname + time
        host = socket.gethostname()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  🏠 Host:     {host}")
        print(f"  🕐 Time:     {now}")
        print()

        # CPU
        if _HAS_PSUTIL:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_bar = _bar(cpu_pct / 100, 20)
            load = psutil.getloadavg()
            print(f"  🧠 CPU:      {cpu_bar} {cpu_pct:.0f}% ({cpu_count} cores)")
            print(f"     Load:     {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}")
        else:
            print(f"  🧠 CPU:      (psutil not installed)")

        # RAM
        if _HAS_PSUTIL:
            mem = psutil.virtual_memory()
            mem_bar = _bar(mem.percent / 100, 20)
            print(f"  💾 RAM:      {mem_bar} {mem.percent:.0f}% "
                  f"({_fmt_bytes(mem.used)} / {_fmt_bytes(mem.total)})")

        # Disk
        try:
            usage = shutil.disk_usage("/")
            disk_pct = usage.used / usage.total
            disk_bar = _bar(disk_pct, 20)
            print(f"  💿 Disk:     {disk_bar} {disk_pct*100:.0f}% "
                  f"({_fmt_bytes(usage.used)} / {_fmt_bytes(usage.total)})")
        except Exception:
            pass

        # Temperature (Linux only)
        try:
            temps = _read_temps()
            if temps:
                print(f"  🌡 Temp:     {', '.join(temps)}")
        except Exception:
            pass

        # Battery
        if _HAS_PSUTIL:
            bat = psutil.sensors_battery()
            if bat:
                bat_bar = _bar(bat.percent / 100, 20)
                charging = "⚡" if bat.power_plugged else "🔋"
                print(f"  {charging} Battery:  {bat_bar} {bat.percent:.0f}%")

        # Uptime
        if _HAS_PSUTIL:
            uptime_s = time.time() - psutil.boot_time()
            if uptime_s > 0:
                days, rem = divmod(uptime_s, 86400)
                hrs, rem = divmod(rem, 3600)
                mins, _ = divmod(rem, 60)
                print(f"  ⏱ Uptime:    {int(days)}d {int(hrs)}h {int(mins)}m")

        print()

        # Network
        try:
            hn = socket.gethostname()
            ip = socket.gethostbyname(hn)
            print(f"  🌐 Network:  {hn} → {ip}")
        except Exception:
            pass

        # Tool registry stats
        reg = self._get_registry()
        if reg:
            try:
                cats = reg.categories()
                tools = reg.list()
                print(f"  📦 Tools:    {len(tools)} tools in {len(cats)} categories")
            except Exception:
                pass

        print()

    # ------------------------------------------------------------------
    # do_system — detailed system info
    # ------------------------------------------------------------------

    def do_system(self, arg: str) -> None:
        """Show detailed system information."""
        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │           💻  System Information                │")
        print("  └──────────────────────────────────────────────────┘")
        print()
        print(f"  OS:        {platform.system()} {platform.release()}")
        print(f"  Version:   {platform.version()}")
        print(f"  Machine:   {platform.machine()}")
        print(f"  Processor: {platform.processor()}")
        print(f"  Hostname:  {socket.gethostname()}")
        print(f"  Python:    {platform.python_version()}")
        print(f"  CWD:       {os.getcwd()}")
        print(f"  Home:      {Path.home()}")
        print(f"  Shell:     {os.environ.get('SHELL', '?')}")
        print()

        # Python path
        pp = os.environ.get("PYTHONPATH", "")
        if pp:
            print(f"  PYTHONPATH:")
            for p in pp.split(":")[:3]:
                print(f"    {p}")
            print()

    # ------------------------------------------------------------------
    # do_network — network interfaces and connectivity
    # ------------------------------------------------------------------

    def do_network(self, arg: str) -> None:
        """Show network interfaces and connectivity status."""
        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │           🌐  Network Status                    │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        # Hostname + IP
        try:
            hn = socket.gethostname()
            print(f"  Hostname:    {hn}")
        except Exception:
            hn = "unknown"

        # Get all IP addresses
        try:
            addrs = socket.getaddrinfo(hn, None)
            seen = set()
            for addr in addrs:
                ip = addr[4][0]
                if ip not in seen and not ip.startswith("127."):
                    seen.add(ip)
                    print(f"  IP:          {ip}")
            if not seen:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    print(f"  IP:          {s.getsockname()[0]}")
                    s.close()
                except Exception:
                    print(f"  IP:          (unknown)")
        except Exception as e:
            print(f"  IP:          (error: {e})")

        # Internet connectivity
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
            s.close()
            print(f"  Internet:    ✅ Connected")
        except Exception:
            print(f"  Internet:    ❌ Offline")

        print()

        # Network interfaces (if psutil available)
        if _HAS_PSUTIL:
            print("  Interfaces:")
            for name, stats in psutil.net_if_stats().items():
                if name == "lo":
                    continue
                status = "🟢 up" if stats.isup else "🔴 down"
                speed = f"{stats.speed}Mbps" if stats.speed > 0 else ""
                print(f"    {name}: {status} {speed}")
        else:
            # Fallback: try /sys/class/net
            try:
                nets = os.listdir("/sys/class/net")
                for n in sorted(nets):
                    if n == "lo":
                        continue
                    operstate = "unknown"
                    try:
                        operstate = (Path("/sys/class/net") / n / "operstate").read_text().strip()
                    except Exception:
                        pass
                    icon = "🟢" if operstate == "up" else "🔴"
                    print(f"    {n}: {icon} {operstate}")
            except Exception:
                pass

        print()

        # Port checks for TankOS services
        print("  TankOS services:")
        for port, name in [(8080, "Dashboard"), (8082, "Cmd Bridge"),
                            (8083, "Meta API"), (8084, "Personalize"),
                            (8900, "Simple Internet"), (2223, "TCP Terminal")]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                s.close()
                print(f"    :{port}  🟢 {name}")
            except Exception:
                print(f"    :{port}  🔴 {name}")
        print()

    # ------------------------------------------------------------------
    # do_health — health diagnostics
    # ------------------------------------------------------------------

    def do_health(self, arg: str) -> None:
        """Show health diagnostics — temps, services, memory, ROS status."""
        print()
        print("  ┌──────────────────────────────────────────────────┐")
        print("  │           🏥  Health Diagnostics                │")
        print("  └──────────────────────────────────────────────────┘")
        print()

        # Temperature
        temps = _read_temps()
        if temps:
            print(f"  🌡 Temps:     {', '.join(temps)}")
        else:
            print(f"  🌡 Temps:     (unavailable)")

        # Memory
        if _HAS_PSUTIL:
            mem = psutil.virtual_memory()
            print(f"  💾 Memory:    {mem.percent:.0f}% used "
                  f"({_fmt_bytes(mem.available)} free)")

        # Disk usage warning
        try:
            usage = shutil.disk_usage("/")
            pct = usage.used / usage.total * 100
            if pct > 90:
                print(f"  ⚠ Disk:       {pct:.0f}% used — CRITICAL")
            elif pct > 75:
                print(f"  ⚡ Disk:       {pct:.0f}% used — warning")
            else:
                print(f"  💿 Disk:       {pct:.0f}% used — OK")
        except Exception:
            pass

        # Python process count
        try:
            result = subprocess.run(
                ["pgrep", "-c", "python"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                count = result.stdout.strip()
                print(f"  🐍 Python:    {count} processes")
        except Exception:
            pass

        # ROS 2 check
        try:
            result = subprocess.run(
                ["ros2", "topic", "list"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                topics = [t for t in result.stdout.strip().split("\n") if t]
                print(f"  🔄 ROS2:      {len(topics)} topics active")
            else:
                print(f"  🔄 ROS2:      not running")
        except FileNotFoundError:
            print(f"  🔄 ROS2:      not installed")
        except Exception:
            print(f"  🔄 ROS2:      (unavailable)")

        # AI provider health
        try:
            from tank_os.core.ai_manager import AIManager
            ai = AIManager()
            providers = ai.list_providers()
            healthy = sum(1 for p in providers if p.get("available"))
            print(f"  🤖 AI:        {healthy}/{len(providers)} providers healthy")
        except Exception:
            pass

        print()

    # ------------------------------------------------------------------
    # do_clear — clear screen
    # ------------------------------------------------------------------

    def do_clear(self, arg: str) -> None:
        """Clear the terminal screen."""
        print("\033[2J\033[H", end="")

    # ------------------------------------------------------------------
    # do_ps — list running processes
    # ------------------------------------------------------------------

    def do_ps(self, arg: str) -> None:
        """List running Python and TankOS processes."""
        print()
        print("  Running processes (Python + TankOS):")
        print()

        if _HAS_PSUTIL:
            procs = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    info = proc.info
                    cmdline = " ".join(info['cmdline'] or [])
                    if 'python' in (info['name'] or '').lower() or 'tank' in cmdline.lower():
                        pid = info['pid']
                        name = info['name'] or '?'
                        cpu = info['cpu_percent'] or 0
                        mem = info['memory_percent'] or 0
                        short_cmd = cmdline[:80]
                        procs.append((pid, name, cpu, mem, short_cmd))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            procs.sort(key=lambda x: -x[2])
            if procs:
                print(f"  {'PID':<8} {'NAME':<12} {'CPU%':<8} {'MEM%':<8} CMD")
                print(f"  {'─'*70}")
                for pid, name, cpu, mem, cmd in procs[:20]:
                    print(f"  {pid:<8} {name:<12} {cpu:<8.1f} {mem:<8.1f} {cmd}")
            else:
                print("  (no Python/TankOS processes found)")

        else:
            # Fallback to ps/pgrep
            try:
                result = subprocess.run(
                    ["ps", "aux", "--sort=-%cpu"],
                    capture_output=True, text=True, timeout=5
                )
                lines = result.stdout.strip().split("\n")
                if lines:
                    print(f"  {lines[0]}")
                    tank_lines = [l for l in lines[1:] if 'python' in l.lower() or 'tank' in l.lower()]
                    for line in tank_lines[:15]:
                        print(f"  {line[:120]}")
            except Exception:
                print("  (ps not available)")

        print()

    # ------------------------------------------------------------------
    # do_env — show environment
    # ------------------------------------------------------------------

    def do_env(self, arg: str) -> None:
        """Show environment variables (filtered)."""
        filt = arg.strip().lower()
        print()
        print("  Environment variables:")
        print()

        keys = sorted(os.environ.keys())
        shown = 0
        for k in keys:
            v = os.environ[k]
            if filt and filt not in k.lower():
                continue
            # Mask sensitive values
            if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD")):
                v = v[:4] + "***" if len(v) > 4 else "***"
            elif len(v) > 60:
                v = v[:57] + "..."
            print(f"  {k}={v}")
            shown += 1
            if shown > 50:
                print(f"  ... and {len(keys) - shown} more")
                break

        if shown == 0:
            print(f"  (no vars matching '{filt}')" if filt else "  (no environment variables)")
        print()

    # ------------------------------------------------------------------
    # Backwards-compatible aliases
    # ------------------------------------------------------------------
    def do_ai_engines(self, arg: str) -> None:
        self.do_ai(arg)

    def do_knowledge_graph(self, arg: str) -> None:
        self.do_knowledge(arg)

    def do_scheduler(self, arg: str) -> None:
        self.do_learning(arg)

    def do_df(self, arg: str) -> None:
        """Alias for disk usage."""
        result = self._engine.run("df -h")
        self._print_result(result)

    def do_free(self, arg: str) -> None:
        """Alias for memory usage."""
        result = self._engine.run("free -h")
        self._print_result(result)

    def do_uptime(self, arg: str) -> None:
        """Show system uptime."""
        result = self._engine.run("uptime")
        self._print_result(result)

    # ------------------------------------------------------------------
    # Original recognised sub-commands
    # ------------------------------------------------------------------
    def do_explain(self, _arg: str) -> None:
        explanation = self._engine.explain_last_error()
        if explanation:
            print("\n" + explanation + "\n")
        else:
            print("(no recent failed command to explain)\n")

    def do_history(self, _arg: str) -> None:
        entries = self._engine.get_history(limit=30)
        if not entries:
            print("(no history yet)\n")
            return
        for i, cmd_text in enumerate(reversed(entries), start=1):
            print(f"  {len(entries) - i + 1:4d}  {cmd_text}")
        print()

    def do_recall(self, arg: str) -> None:
        query = arg.strip()
        if not query:
            print("(usage) recall <keyword>\n")
            return
        hits = self._engine.recall_history(query, limit=10)
        if not hits:
            print(f"(no history matches {query!r})\n")
            return
        for line in hits:
            print(f"  · {line}")
        print()

    def do_exit(self, _arg: str) -> bool:
        print("Exiting TankOS AI Terminal.\n")
        return True

    def do_quit(self, _arg: str) -> bool:
        return self.do_exit(_arg)

    # ------------------------------------------------------------------
    # Default line — anything else is treated as user input.
    # ------------------------------------------------------------------
    def default(self, line: str) -> None:
        self._execute_user_line(line)

    def emptyline(self) -> None:
        # Don't repeat the previous command on accidental Enter.
        pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _execute_user_line(self, raw: str) -> None:
        line = (raw or "").strip()
        if not line:
            return

        # ── Torrent intent: auto-detect natural language torrent queries ──
        if not line.startswith("!") and not line.startswith("torrent "):
            lowered = line.lower()
            # Try to match a torrent-intent prefix; extract the search query
            query = None
            for prefix in [
                r"get me (a |the )?torrent (of |for )?",
                r"search (for )?(a |the )?torrent (of |for )?",
                r"find (a |the )?torrent (of |for )?",
                r"download (a |the )?torrent (of |for )?",
                r"show (me )?(a |the )?torrent (of |for )?",
                r"torrent (of |for )?",
            ]:
                m = re.match(prefix, lowered, re.IGNORECASE)
                if m:
                    query = line[m.end():].strip()
                    break
            if query:
                print(f"\n  🌊 Detected torrent request → searching for: '{query}'\n")
                self.do_torrent(query)
                return

        # Wire the ToolRegistry into the engine so it can search tools
        if self._engine._tool_registry is None:
            reg = self._get_registry()
            if reg is not None:
                self._engine.set_tool_registry(reg)

        result = self._engine.interpret(line)

        # ── Tool suggestions / unrecognized NL: show and exit ──
        if result.tool_suggestion_shown or result.unrecognized:
            msg = result.error or ""
            # Strip sentinel prefix for clean display
            sentinel = "__TOOL_SUGGEST__ "
            if msg.startswith(sentinel):
                msg = msg[len(sentinel):]
            print(f"\n{msg}\n")
            return

        if not result.command:
            if result.error:
                print(f"(error) {result.error}\n")
            return

        # ── Confirmation gate ──
        if result.pending_confirmation:
            print(f"\n→ {result.command}")
            if result.pending_explanation:
                print(f"  {result.pending_explanation}")
            try:
                answer = input("[y/N] confirm? ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            confirmed = answer in ("y", "yes")
            final = self._engine.confirm_and_run(confirmed)
        else:
            # SAFE / READ — run immediately.
            final = self._engine.run(result.command)
        self._print_result(final)

    @staticmethod
    def _print_result(result) -> None:
        if result.error and not result.stdout and result.exit_code is None:
            print(f"(error) {result.error}")
            print()
            return
        if result.stdout:
            print(result.stdout.rstrip("\n"))
        if result.stderr:
            print(f"[stderr] {result.stderr.rstrip(chr(10))}")
        if result.exit_code is None:
            print(f"(failed: {result.error or 'unknown'})\n")
        else:
            print(f"(exit {result.exit_code}, "
                  f"{result.duration_ms:.0f} ms)\n")


# ─── Module-level helpers ─────────────────────────────────────────────

def _bar(ratio: float, width: int = 20) -> str:
    """Draw a unicode bar for 0.0–1.0 ratios."""
    r = max(0.0, min(1.0, ratio))
    filled = int(r * width)
    if filled == 0 and r > 0:
        filled = 1
    return "█" * filled + "░" * (width - filled)


def _fmt_bytes(n: int) -> str:
    """Format bytes into human-readable form."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _read_temps() -> list:
    """Read CPU/GPU temperature from sysfs (Linux)."""
    results = []
    # CPU temp via /sys/class/thermal
    try:
        tz_dir = Path("/sys/class/thermal")
        if tz_dir.exists():
            for zone in sorted(tz_dir.glob("thermal_zone*")):
                try:
                    temp_raw = (zone / "temp").read_text().strip()
                    temp_c = int(temp_raw) / 1000.0
                    ttype = "cpu"
                    try:
                        ttype = (zone / "type").read_text().strip()
                    except Exception:
                        pass
                    if temp_c > 0:
                        results.append(f"{ttype}: {temp_c:.1f}°C")
                except Exception:
                    pass
    except Exception:
        pass
    # GPU temp (Raspberry Pi)
    try:
        gpu_path = Path("/sys/class/thermal/thermal_zone0/temp")
        if gpu_path.exists():
            raw = gpu_path.read_text().strip()
            t = int(raw) / 1000.0
            results.append(f"gpu: {t:.1f}°C")
    except Exception:
        pass
    # vcgencmd (Pi-specific)
    try:
        r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            results.append(r.stdout.strip().replace("temp=", "pi: "))
    except Exception:
        pass
    return results[-4:] if results else []
