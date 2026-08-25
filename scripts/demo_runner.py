#!/usr/bin/env python3
"""
TankOS Terminal Demo Runner — comprehensive showcase of all modules & tools.
Run: python3 scripts/demo_runner.py
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tank_os.shell.terminal.cli import TerminalREPL


def banner(text):
    w = 62
    print()
    print("═" * w)
    print(f"  {text}")
    print("═" * w)
    print()


def section(num, title):
    print()
    print("─" * 62)
    print(f"  [{num}] {title}")
    print("─" * 62)
    print()


def run(repl, cmd, pause=1.2):
    print(f"  tankos> {cmd}")
    print()
    repl.onecmd(cmd)
    time.sleep(pause)


def main():
    repl = TerminalREPL()

    banner("🤖 TankOS AI Terminal — Full Demo")
    print("  Jetson Orin Nano 8GB | 1,966 Tools | 5 AI Engines")
    print("  Running 15 module demonstrations...")
    time.sleep(1)

    # ─── 1. System Status ───
    section(1, "📊 System Status Dashboard")
    run(repl, "status")

    # ─── 2. System Info ───
    section(2, "💻 System Information")
    run(repl, "system")

    # ─── 3. Network ───
    section(3, "🌐 Network Status")
    run(repl, "network")

    # ─── 4. Health ───
    section(4, "🩺 Health Diagnostics")
    run(repl, "health")

    # ─── 5. Tool Registry ───
    section(5, "📦 Tool Registry — 1,966 Tools")
    run(repl, "tools --count", 2)

    # ─── 6. Search Vision Tools ───
    section(6, "🔎 Search: Vision Tools")
    run(repl, "search vision", 1.5)

    # ─── 7. Search Diagnostics Tools ───
    section(7, "🔎 Search: Diagnostics Tools")
    run(repl, "search diagnostics --category diagnostics")

    # ─── 8. Tool Details ───
    section(8, "🔍 Tool Detail: vision_smoketest.yolo")
    run(repl, "tool vision_smoketest.yolo")

    # ─── 9. Tool Details 2 ───
    section(9, "🔍 Tool Detail: diagnostics.ros")
    run(repl, "tool diagnostics.ros")

    # ─── 10. Tool Details 3 ───
    section(10, "🔍 Tool Detail: ai_vision.wildlife")
    run(repl, "tool ai_vision.wildlife")

    # ─── 11. Search AI/ML Tools ───
    section(11, "🧠 Search: AI & ML Tools")
    run(repl, "search ai --category general")

    # ─── 12. Search Mobility Tools ───
    section(12, "🚗 Search: Mobility & Navigation")
    run(repl, "search mobility")

    # ─── 13. Search Security Tools ───
    section(13, "🔐 Search: Security Tools")
    run(repl, "search security --category security-hardening")

    # ─── 14. Search Home/IoT ───
    section(14, "🏠 Search: Home Automation & IoT")
    run(repl, "search home --category iot-home")

    # ─── 15. AI Providers ───
    section(15, "🤖 AI Provider Status")
    run(repl, "providers")

    # ─── 16. AI Models ───
    section(16, "🧠 AI Models & Provider Switching")
    run(repl, "model")

    # ─── 17. AI Engine Overview ───
    section(17, "🧬 AI Engine Overview (5 Engines)")
    run(repl, "ai", 2)

    # ─── 18. Knowledge Graph ───
    section(18, "📊 Knowledge Graph Status")
    run(repl, "knowledge")

    # ─── 19. Curiosity Engine ───
    section(19, "🔍 Curiosity Engine")
    run(repl, "curiosity")

    # ─── 20. Learning Scheduler ───
    section(20, "⏰ Learning Scheduler")
    run(repl, "learning")

    # ─── 21. Invoke Tool: vision ───
    section(21, "⚡ Invoke: vision_smoketest.yolo")
    run(repl, "invoke vision_smoketest.yolo", 3)

    # ─── 22. Invoke Tool: diagnostics ───
    section(22, "⚡ Invoke: diagnostics.ros")
    run(repl, "invoke diagnostics.ros", 3)

    # ─── 23. Invoke Tool: hardware ───
    section(23, "⚡ Invoke: hardware.io.pinout")
    run(repl, "invoke hardware.io.pinout", 3)

    # ─── 24. Search Download Tools ───
    section(24, "📥 Search: Download Tools")
    run(repl, "search download --category download-music")

    # ─── 25. Search Media Tools ───
    section(25, "🎬 Search: Media & Streaming")
    run(repl, "search media --category media-streaming")

    # ─── 26. Search Voice Tools ───
    section(26, "🎤 Search: Voice & Audio")
    run(repl, "search voice --category voice")

    # ─── 27. Search Education ───
    section(27, "📚 Search: Education Tools")
    run(repl, "search education --category education-tools")

    # ─── 28. Search Cloud/DevOps ───
    section(28, "☁️ Search: Cloud & DevOps")
    run(repl, "search docker --category docker-ops")

    # ─── 29. Processes ───
    section(29, "📋 Running Processes")
    run(repl, "ps")

    # ─── 30. Environment ───
    section(30, "🔧 Environment Variables")
    run(repl, "env", 1)

    # ─── Final ───
    banner("✅ Demo Complete — All 30 Sections Run")
    print("  Modules demonstrated:")
    print("    ✓ System Status, Info, Network, Health")
    print("    ✓ Tool Registry (1,966 tools, 74 categories)")
    print("    ✓ Tool Search, Detail, Invocation")
    print("    ✓ AI Providers, Models, Engines")
    print("    ✓ Knowledge Graph, Curiosity, Learning")
    print("    ✓ Vision, Diagnostics, Hardware, Security")
    print("    ✓ Mobility, IoT, Media, Voice, Education")
    print("    ✓ Cloud, Docker, Downloads, Processes")
    print()


if __name__ == "__main__":
    main()
