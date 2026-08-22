#!/usr/bin/env bash
# Tank — Full System Diagnostics
# One command to check every subsystem
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  TANK — System Diagnostics                      ║"
echo "║  Registration: APC-2026-RJ-75818                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

echo "── Python ──"
python3 --version 2>/dev/null && pass "Python3 available" || fail "Python3 not found"

echo "── Tank Package ──"
python3 -c "import tank; print(f'  tank v{tank.__version__}')" 2>/dev/null && pass "tank importable" || fail "tank import failed"

echo "── Hardware Registry ──"
python3 -c "from tank.core.hardware_registry import get_component_count; print(f'  {get_component_count()} components')" 2>/dev/null && pass "hardware registry OK" || fail "hardware registry failed"

echo "── Config ──"
python3 -c "from tank.core.config import get_config; c=get_config(); print(f'  sim={c.simulation}')" 2>/dev/null && pass "config loaded" || fail "config failed"

echo "── Event Bus ──"
python3 -c "
from tank.core.event_bus import get_event_bus, EventType
bus = get_event_bus()
bus.emit(EventType.SYSTEM_STARTUP, source='diag')
print(f'  {len(bus.history())} events')
" 2>/dev/null && pass "event bus OK" || fail "event bus failed"

echo "── State Machine ──"
python3 -c "
from tank.core.state_machine import StateMachine, State
sm = StateMachine()
sm.transition(State.OBSERVING)
sm.transition(State.DETECTING)
print(f'  state={sm.state.value}')
" 2>/dev/null && pass "state machine OK" || fail "state machine failed"

echo "── Mock Sensors ──"
python3 -c "
from tank.simulation.mock_sensors import create_mock_sensors
s = create_mock_sensors()
for x in s: x.connect()
print(f'  {len(s)} sensors connected')
" 2>/dev/null && pass "sensors OK" || fail "sensors failed"

echo "── Sensor Fusion ──"
python3 -c "
from tank.perception.sensor_fusion import SensorFusion
f = SensorFusion()
f.update_camera([{'object':'person','confidence':0.9,'distance_m':2.5}])
f.update_lidar(2.3)
f.update_thermal(True, 0.85)
e = f.fuse()
print(f'  {len(e)} entities, conf={e[0].confidence:.2f}')
" 2>/dev/null && pass "fusion OK" || fail "fusion failed"

echo "── Decision Engine ──"
python3 -c "
from tank.core.state_machine import StateMachine, State
from tank.core.decision_engine import DecisionEngine, AIResult
sm = StateMachine()
sm.transition(State.OBSERVING)
sm.transition(State.DETECTING)
de = DecisionEngine(sm)
ai = AIResult(object_name='person', confidence=0.95, distance_m=2.0, situation='person_detected', recommended_action='track')
d = de.process(ai)
print(f'  action={d.action.value}')
" 2>/dev/null && pass "decision engine OK" || fail "decision engine failed"

echo "── Safety ──"
python3 -c "
from tank.core.state_machine import StateMachine
from tank.control.safety import SafetyController
sm = StateMachine()
s = SafetyController(sm, timeout=1.0)
s.feed_watchdog()
print(f'  emergency={s._emergency}')
" 2>/dev/null && pass "safety OK" || fail "safety failed"

echo "── ESP32 Swarm ──"
python3 -c "
from tank.networking.esp32.swarm import create_default_swarm
sw = create_default_swarm()
sw.connect_all()
h = sw.health()
print(f'  {h[\"connected\"]}/{h[\"total_nodes\"]} nodes')
" 2>/dev/null && pass "esp32 swarm OK" || fail "esp32 swarm failed"

echo "── Storage ──"
python3 -c "
from tank.storage.event_log import EventStorage
from pathlib import Path
import tempfile
db = EventStorage(db_path=Path(tempfile.mktemp(suffix='.db')))
db.connect()
db.log_event('DIAG', 'diag')
s = db.stats()
db.disconnect()
print(f'  {s[\"events\"]} events')
" 2>/dev/null && pass "storage OK" || fail "storage failed"

echo "── Dashboard ──"
python3 -c "
from tank.ui.dashboard import render_dashboard
o = render_dashboard({'state':'IDLE','cycle':0,'sensors':[],'fusion':{},'ai_latency':0,'safety':{'emergency':False}})
print(f'  renders OK')
" 2>/dev/null && pass "dashboard OK" || fail "dashboard failed"

echo "── Full Pipeline ──"
python3 -c "
from tank.main import TankSystem
from tank.core.config import get_config
from tank.simulation.mock_sensors import create_mock_sensors
c = get_config()
t = TankSystem(c, simulation=True)
for s in create_mock_sensors(): t.add_sensor(s)
t.start()
r = [t.tick() for _ in range(5)]
t.stop()
print(f'  5 cycles complete')
" 2>/dev/null && pass "full pipeline OK" || fail "full pipeline failed"

echo "── Tests ──"
if command -v pytest &>/dev/null; then
    python3 -m pytest tank/tests/ -q --tb=no 2>&1 | tail -1
    pass "tests ran"
else
    warn "pytest not installed"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Diagnostics complete                           ║"
echo "╚══════════════════════════════════════════════════╝"
