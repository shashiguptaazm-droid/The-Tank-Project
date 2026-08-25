#!/usr/bin/env bash
# TankOS Terminal Demo Script — records terminal actions for video
# Run: bash scripts/demo_terminal.sh

set -e
cd "$(dirname "$0")/.."

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🎬 TankOS Terminal Demo — Agent Chat & Tools"
echo "═══════════════════════════════════════════════════════════"
echo ""

python3 -c "
import sys, time
sys.path.insert(0, '.')
from tank_os.shell.terminal.cli import TerminalREPL

repl = TerminalREPL()

def run(cmd, delay=1.5):
    print(f'\n{'─'*60}')
    print(f'  💻 tankos> {cmd}')
    print(f'{'─'*60}\n')
    time.sleep(0.3)
    repl.onecmd(cmd)
    time.sleep(delay)

# ── 1. System Status ──
print('\n' + '═'*60)
print('  📊 SECTION 1: System Status')
print('═'*60)
run('status', 2)

# ── 2. Tool Categories ──
print('\n' + '═'*60)
print('  📦 SECTION 2: Tool Registry Overview')
print('═'*60)
run('tools --count', 2)

# ── 3. Search Tools ──
print('\n' + '═'*60)
print('  🔎 SECTION 3: Searching for Vision Tools')
print('═'*60)
run('search vision', 2)

# ── 4. Tool Details ──
print('\n' + '═'*60)
print('  🔍 SECTION 4: Tool Details')
print('═'*60)
run('tool diagnostics.run', 2)

# ── 5. AI Providers ──
print('\n' + '═'*60)
print('  🤖 SECTION 5: AI Provider Status')
print('═'*60)
run('providers', 2)

# ── 6. AI Models ──
print('\n' + '═'*60)
print('  🧠 SECTION 6: AI Models & Providers')
print('═'*60)
run('model', 2)

# ── 7. AI Engine Overview ──
print('\n' + '═'*60)
print('  🧬 SECTION 7: AI Engine Overview')
print('═'*60)
run('ai', 2)

# ── 8. Knowledge Graph ──
print('\n' + '═'*60)
print('  📊 SECTION 8: Knowledge Graph Status')
print('═'*60)
run('knowledge', 2)

# ── 9. Curiosity Engine ──
print('\n' + '═'*60)
print('  🔍 SECTION 9: Curiosity Engine')
print('═'*60)
run('curiosity', 2)

# ── 10. Learning Scheduler ──
print('\n' + '═'*60)
print('  ⏰ SECTION 10: Learning Scheduler')
print('═'*60)
run('learning', 2)

# ── 11. System Info ──
print('\n' + '═'*60)
print('  🖥 SECTION 11: System Information')
print('═'*60)
run('system', 2)

# ── 12. Network Info ──
print('\n' + '═'*60)
print('  🌐 SECTION 12: Network Information')
print('═'*60)
run('network', 2)

# ── 13. Health Check ──
print('\n' + '═'*60)
print('  🩺 SECTION 13: Health Diagnostics')
print('═'*60)
run('health', 2)

# ── 14. Invoke a Tool ──
print('\n' + '═'*60)
print('  ⚡ SECTION 14: Invoking a Tool')
print('═'*60)
run('invoke diagnostics.run', 3)

# ── 15. Search for AI Tools ──
print('\n' + '═'*60)
print('  🧠 SECTION 15: Searching AI Tools')
print('═'*60)
run('search ai --category ai-ml-tools', 2)

print('\n' + '═'*60)
print('  ✅ Demo Complete!')
print('═'*60)
print()
" 2>&1
