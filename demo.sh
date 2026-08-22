#!/usr/bin/env bash
# Tank — Competition Demo Script
# Deterministic demonstration of SENSE→PERCEIVE→FUSE→AI→DECIDE→ACTION→VERIFY
set -euo pipefail

echo "╔══════════════════════════════════════════════════╗"
echo "║  TANK — Physical AI Competition Demo            ║"
echo "║  APC-2026-RJ-75818                              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Diagnostics
echo "▶ [1/10] Running diagnostics..."
python3 -c "from tank.core import get_config; c = get_config(); print(f'  Config loaded: sim={c.simulation}')"

# 2. Connect sensors
echo "▶ [2/10] Connecting sensors (simulation mode)..."
python3 -c "
from tank.perception.sensor import SensorInterface
from tank.simulation.mock_sensors import create_mock_sensors
sensors = create_mock_sensors()
for s in sensors:
    s.connect()
    print(f'  ✓ {s.name} connected')
"

# 3. Begin perception
echo "▶ [3/10] Beginning perception pipeline..."
python3 -c "
from tank.simulation.mock_sensors import create_mock_sensors
from tank.perception.sensor_fusion import SensorFusion
sensors = create_mock_sensors()
for s in sensors: s.connect()
fusion = SensorFusion()
print('  ✓ Perception pipeline ready')
"

# 4. Full cycle demo
echo "▶ [4/10] Running full SENSE→PERCEIVE→FUSE→AI→DECIDE→ACT→VERIFY cycle..."
python3 -m tank.main --demo --cycles 15

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Demo complete — all systems operational         ║"
echo "║  Registration: APC-2026-RJ-75818                ║"
echo "╚══════════════════════════════════════════════════╝"
