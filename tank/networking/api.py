"""Tank — FastAPI REST API + WebSocket Server.

Endpoints for remote control, status, sensor data, events, decisions.
WebSocket for real-time event streaming.

Usage:
    python3 -m tank.networking.api          # starts on port 8080
    python3 -m tank.networking.api --port 9000
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("tank.api")

# ── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Tank — Physical AI Robot API",
    description="REST API + WebSocket for The Tank robot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared State ────────────────────────────────────────────────

_tank_system = None
_event_storage = None
_websocket_clients: List[WebSocket] = []


def set_tank_system(system) -> None:
    global _tank_system
    _tank_system = system


def set_event_storage(storage) -> None:
    global _event_storage
    _event_storage = storage


# ── Models ──────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    action: str
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class DemoRequest(BaseModel):
    cycles: int = 10
    slow: bool = False


# ── REST Endpoints ──────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """System status: state, cycle, sensors, safety."""
    if _tank_system:
        return _tank_system.status()
    return {"state": "OFFLINE", "cycle": 0, "sensors": [], "safety": {"emergency": True}, "running": False}


@app.get("/api/sensors")
async def get_sensors():
    """All sensor data."""
    if not _tank_system:
        return {"error": "system offline"}
    status = _tank_system.status()
    return {
        "fusion": status.get("fusion", {}),
        "sensors": status.get("sensors", []),
    }


@app.get("/api/decisions")
async def get_decisions(limit: int = Query(50, le=500)):
    """Decision history."""
    if _tank_system:
        history = _tank_system.decision_engine.history(limit)
        return [{"action": d.action.value, "reason": d.reason,
                 "confidence": d.confidence, "source": d.source,
                 "timestamp": d.timestamp} for d in history]
    return []


@app.get("/api/events")
async def get_events(
    event_type: Optional[str] = None,
    limit: int = Query(50, le=500)
):
    """Event log from storage."""
    if _event_storage:
        events = _event_storage.query_events(event_type, limit)
        return events
    if _tank_system:
        from tank.core.event_bus import EventType
        etype = None
        if event_type:
            try:
                etype = EventType(event_type)
            except ValueError:
                pass
        history = _tank_system.bus.history(etype, limit)
        return [{"timestamp": e.timestamp, "event_type": e.event_type.value,
                 "source": e.source, "confidence": e.confidence,
                 "data": e.data, "system_state": e.system_state} for e in history]
    return []


@app.get("/api/health")
async def get_health():
    """Health check with uptime and resource usage."""
    import os
    import psutil if hasattr(__builtins__, '__import__') else None
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
    except ImportError:
        cpu = 0.0
        ram = 0.0

    health = {
        "status": "ok",
        "uptime_s": round(time.time() - _start_time, 1),
        "cpu_percent": cpu,
        "ram_percent": ram,
        "pid": os.getpid(),
    }
    if _tank_system:
        health["system"] = _tank_system.status()
        health["safety"] = _tank_system.safety.health()
    if _event_storage:
        health["storage"] = _event_storage.stats()
    return health


@app.get("/api/config")
async def get_config():
    """Current configuration (sanitized — no secrets)."""
    if _tank_system:
        cfg = _tank_system.config
        return {
            "simulation": cfg.simulation,
            "demo_mode": cfg.demo_mode,
            "log_level": cfg.log_level,
            "dashboard_port": cfg.dashboard_port,
            "api_port": cfg.api_port,
            "ai_model": cfg.ai.model,
            "vps_url": cfg.vps.url if cfg.vps.api_key else "(not configured)",
            "sensors": {
                "camera_device": cfg.sensors.camera_device,
                "lidar_port": cfg.sensors.lidar_port,
            },
        }
    return {"simulation": True}


@app.post("/api/command")
async def send_command(req: CommandRequest):
    """Send a command to the robot."""
    if not _tank_system:
        return {"ok": False, "error": "system offline"}
    # Validate command through decision engine
    from tank.core.decision_engine import AIResult, ActionType
    action_map = {
        "track": ActionType.TRACK,
        "approach": ActionType.APPROACH,
        "retreat": ActionType.RETREAT,
        "stop": ActionType.STOP,
        "idle": ActionType.IDLE,
        "safe_stop": ActionType.SAFE_STOP,
    }
    action = action_map.get(req.action)
    if action is None:
        return {"ok": False, "error": f"unknown action: {req.action}"}

    ai = AIResult(
        object_name=req.target or "unknown",
        confidence=0.9,
        distance_m=1.0,
        situation=f"manual_{req.action}",
        recommended_action=req.action,
    )
    decision = _tank_system.decision_engine.process(ai)
    return {"ok": True, "action": decision.action.value if decision else "none"}


@app.post("/api/demo")
async def run_demo(req: DemoRequest):
    """Run a demo cycle and return results."""
    if not _tank_system:
        return {"ok": False, "error": "system offline"}
    results = []
    for i in range(req.cycles):
        result = _tank_system.tick()
        results.append(result)
        if req.slow:
            await asyncio.sleep(0.5)
    return {"ok": True, "cycles": results}


@app.post("/api/safety/emergency_stop")
async def emergency_stop():
    """Emergency stop — kills all motors."""
    if _tank_system:
        _tank_system.safety.emergency_stop()
        return {"ok": True, "state": _tank_system.sm.state.value}
    return {"ok": False, "error": "system offline"}


@app.post("/api/safety/reset")
async def safety_reset():
    """Reset emergency stop."""
    if _tank_system:
        _tank_system.safety.reset_emergency()
        return {"ok": True, "state": _tank_system.sm.state.value}
    return {"ok": False, "error": "system offline"}


@app.get("/api/telemetry")
async def get_telemetry(metric: Optional[str] = None, limit: int = Query(50, le=500)):
    """Telemetry data from storage."""
    if _event_storage:
        return _event_storage.query_telemetry(metric, limit)
    return []


@app.get("/api/hardware")
async def get_hardware():
    """Full hardware registry."""
    from tank.core.hardware_registry import get_all_components, BodySection
    components = get_all_components()
    by_section = {}
    for c in components:
        section = c.section.value
        if section not in by_section:
            by_section[section] = []
        by_section[section].append({
            "id": c.id, "name": c.name, "bus": c.bus,
            "address": c.address, "status": c.status.value,
            "specs": c.specs, "notes": c.notes,
        })
    return {"total": len(components), "sections": by_section}


# ── WebSocket ───────────────────────────────────────────────────

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Real-time event streaming via WebSocket."""
    await websocket.accept()
    _websocket_clients.append(websocket)
    logger.info(f"WebSocket client connected ({len(_websocket_clients)} total)")
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _websocket_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected ({len(_websocket_clients)} total)")


async def broadcast_event(event_data: Dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    dead = []
    for ws in _websocket_clients:
        try:
            await ws.send_json(event_data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _websocket_clients.remove(ws)


# ── Dashboard HTML ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the real-time dashboard."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tank — Physical AI Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono',Monaco,'Cascadia Code',monospace;background:#0a0e17;color:#e2e8f0;min-height:100vh}
.header{background:linear-gradient(135deg,#0f172a,#1e293b);border-bottom:2px solid #0ea5e9;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:20px;color:#38bdf8}
.header .reg{background:#dc2626;color:#fff;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;padding:16px 24px}
.card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;min-height:200px}
.card h2{font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;border-bottom:1px solid #334155;padding-bottom:8px}
.metric{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e293b}
.metric .label{color:#94a3b8;font-size:12px}
.metric .value{color:#f1f5f9;font-weight:600;font-size:13px}
.state-badge{display:inline-block;padding:4px 12px;border-radius:12px;font-size:14px;font-weight:700;margin:8px 0}
.state-IDLE{background:#1e40af;color:#93c5fd}
.state-OBSERVING{background:#065f46;color:#6ee7b7}
.state-DETECTING{background:#92400e;color:#fcd34d}
.state-ANALYZING{background:#581c87;color:#c4b5fd}
.state-TRACKING{background:#0e7490;color:#67e8f9}
.state-ACTING{background:#b45309;color:#fde68a}
.state-VERIFYING{background:#047857;color:#a7f3d0}
.state-SAFE_STOP{background:#dc2626;color:#fca5a5}
.state-ERROR{background:#991b1b;color:#fecaca}
.state-OFFLINE{background:#374151;color:#9ca3af}
.sensor-row{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px}
.dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.dot.green{background:#22c55e}
.dot.red{background:#ef4444}
.dot.yellow{background:#eab308}
.events{max-height:300px;overflow-y:auto;font-size:11px}
.event-row{padding:4px 8px;border-bottom:1px solid #0f172a;display:flex;gap:8px}
.event-row:nth-child(even){background:#0f172a}
.event-ts{color:#64748b;flex-shrink:0}
.event-type{color:#38bdf8;flex-shrink:0;width:160px}
.event-src{color:#94a3b8}
.log{background:#0f172a;border-radius:4px;padding:8px;font-size:11px;max-height:200px;overflow-y:auto;color:#6ee7b7}
#ws-status{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}
.connected{background:#22c55e}
.disconnected{background:#ef4444}
</style>
</head>
<body>
<div class="header">
  <h1>🪖 TANK — Physical AI Robot</h1>
  <div style="display:flex;align-items:center;gap:12px">
    <span><span id="ws-status" class="disconnected"></span><span id="ws-label" style="font-size:11px;color:#94a3b8">Connecting...</span></span>
    <span class="reg">APC-2026-RJ-75818</span>
  </div>
</div>
<div class="grid">
  <div class="card">
    <h2>⚡ System State</h2>
    <div id="state-display"><span class="state-badge state-IDLE">IDLE</span></div>
    <div class="metric"><span class="label">Cycle</span><span class="value" id="cycle">0</span></div>
    <div class="metric"><span class="label">Uptime</span><span class="value" id="uptime">0s</span></div>
    <div class="metric"><span class="label">CPU</span><span class="value" id="cpu">0%</span></div>
    <div class="metric"><span class="label">RAM</span><span class="value" id="ram">0%</span></div>
  </div>
  <div class="card">
    <h2>👁 Sensors</h2>
    <div id="sensors-list"><div style="color:#64748b;font-size:12px">Loading...</div></div>
  </div>
  <div class="card">
    <h2>🧠 Sensor Fusion</h2>
    <div class="metric"><span class="label">Camera detections</span><span class="value" id="fusion-cam">0</span></div>
    <div class="metric"><span class="label">LiDAR distance</span><span class="value" id="fusion-lidar">N/A</span></div>
    <div class="metric"><span class="label">Thermal human</span><span class="value" id="fusion-thermal">clear</span></div>
    <div class="metric"><span class="label">AI Latency</span><span class="value" id="ai-latency">0ms</span></div>
    <div class="metric"><span class="label">Safety</span><span class="value" id="safety-status">OK</span></div>
  </div>
  <div class="card">
    <h2>🎯 Decision Engine</h2>
    <div id="decisions-list"><div style="color:#64748b;font-size:12px">No decisions yet</div></div>
  </div>
  <div class="card" style="grid-column:span 2">
    <h2>📋 Event Log</h2>
    <div class="events" id="events-list"><div style="color:#64748b;font-size:12px">Waiting for events...</div></div>
  </div>
  <div class="card">
    <h2>🎮 Controls</h2>
    <div style="display:flex;flex-direction:column;gap:8px">
      <button onclick="sendCmd('safe_stop')" style="background:#dc2626;color:#fff;border:none;padding:10px;border-radius:4px;cursor:pointer;font-weight:700">🛑 EMERGENCY STOP</button>
      <button onclick="sendCmd('reset')" style="background:#059669;color:#fff;border:none;padding:8px;border-radius:4px;cursor:pointer">✅ Reset Safety</button>
      <button onclick="runDemo(5)" style="background:#0ea5e9;color:#fff;border:none;padding:8px;border-radius:4px;cursor:pointer">▶ Run 5-Cycle Demo</button>
    </div>
    <div class="log" id="cmd-log" style="margin-top:8px"></div>
  </div>
  <div class="card">
    <h2>📡 Connectivity</h2>
    <div class="metric"><span class="label">VPS</span><span class="value" id="vps-status">checking...</span></div>
    <div class="metric"><span class="label">ESP32 nodes</span><span class="value" id="esp32-status">0/5</span></div>
    <div class="metric"><span class="label">WebSocket clients</span><span class="value" id="ws-clients">0</span></div>
  </div>
</div>
<script>
const ws = new WebSocket(`ws://${location.host}/ws/events`);
const wsStatus = document.getElementById('ws-status');
const wsLabel = document.getElementById('ws-label');
ws.onopen = () => { wsStatus.className = 'connected'; wsLabel.textContent = 'Live'; };
ws.onclose = () => { wsStatus.className = 'disconnected'; wsLabel.textContent = 'Disconnected'; };
ws.onmessage = (e) => {
  const d = JSON.parse(e.data);
  if (d.type === 'pong') return;
  addEvent(d);
};
function addEvent(e) {
  const el = document.getElementById('events-list');
  if (el.querySelector('div[style]')) el.innerHTML = '';
  const ts = new Date(e.timestamp * 1000).toLocaleTimeString();
  const row = document.createElement('div');
  row.className = 'event-row';
  row.innerHTML = `<span class="event-ts">${ts}</span><span class="event-type">${e.event_type||'?'}</span><span class="event-src">${e.source||''}</span>`;
  el.prepend(row);
  if (el.children.length > 100) el.removeChild(el.lastChild);
}
async function refresh() {
  try {
    const r = await fetch('/api/status');
    const s = await r.json();
    document.getElementById('cycle').textContent = s.cycle || 0;
    const st = s.state || 'OFFLINE';
    document.getElementById('state-display').innerHTML = `<span class="state-badge state-${st}">${st}</span>`;
    const sl = document.getElementById('sensors-list');
    sl.innerHTML = (s.sensors||[]).map(sh => {
      const ok = sh.status === 'CONNECTED';
      return `<div class="sensor-row"><span class="dot ${ok?'green':'red'}"></span><span>${sh.name||sh.type||'?'}</span><span style="color:#64748b;margin-left:auto">${sh.status||'?'}</span></div>`;
    }).join('');
    const f = s.fusion || {};
    document.getElementById('fusion-cam').textContent = f.camera_detections || 0;
    document.getElementById('fusion-lidar').textContent = f.lidar_distance != null ? f.lidar_distance + 'm' : 'N/A';
    document.getElementById('fusion-thermal').textContent = f.thermal_human ? 'CONFIRMED' : 'clear';
    document.getElementById('ai-latency').textContent = (s.ai_latency*1000||0).toFixed(0) + 'ms';
    document.getElementById('safety-status').textContent = s.safety?.emergency ? 'ACTIVE' : 'OK';
    const hr = await fetch('/api/health');
    const h = await hr.json();
    document.getElementById('uptime').textContent = (h.uptime_s||0).toFixed(0) + 's';
    document.getElementById('cpu').textContent = (h.cpu_percent||0).toFixed(1) + '%';
    document.getElementById('ram').textContent = (h.ram_percent||0).toFixed(1) + '%';
  } catch(e) {}
  try {
    const r = await fetch('/api/decisions?limit=10');
    const d = await r.json();
    const el = document.getElementById('decisions-list');
    el.innerHTML = d.length ? d.map(x => `<div class="metric"><span class="label">${x.action}</span><span class="value">${x.reason} (${(x.confidence*100).toFixed(0)}%)</span></div>`).join('') : '<div style="color:#64748b;font-size:12px">No decisions yet</div>';
  } catch(e) {}
}
async function sendCmd(action) {
  const log = document.getElementById('cmd-log');
  try {
    const url = action === 'reset' ? '/api/safety/reset' : '/api/safety/emergency_stop';
    const r = await fetch(url, {method:'POST'});
    const d = await r.json();
    log.textContent = `[${new Date().toLocaleTimeString()}] ${action}: ${JSON.stringify(d)}\\n` + log.textContent;
  } catch(e) { log.textContent = `ERROR: ${e}\\n` + log.textContent; }
}
async function runDemo(cycles) {
  const log = document.getElementById('cmd-log');
  log.textContent = `[${new Date().toLocaleTimeString()}] Running ${cycles}-cycle demo...\\n` + log.textContent;
  try {
    const r = await fetch('/api/demo', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cycles})});
    const d = await r.json();
    log.textContent = `[${new Date().toLocaleTimeString()}] Demo: ${d.cycles?.length||0} cycles complete\\n` + log.textContent;
  } catch(e) { log.textContent = `ERROR: ${e}\\n` + log.textContent; }
}
refresh();
setInterval(refresh, 2000);
setInterval(() => { if (ws.readyState === 1) ws.send('ping'); }, 25000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── Server Startup ──────────────────────────────────────────────

_start_time = time.time()


def create_app(tank_system=None, storage=None) -> FastAPI:
    """Factory to create app with injected dependencies."""
    global _tank_system, _event_storage, _start_time
    _start_time = time.time()
    if tank_system:
        _tank_system = tank_system
    if storage:
        _event_storage = storage
    return app


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tank API Server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    # Initialize system in simulation mode
    from tank.core.config import get_config
    from tank.main import TankSystem
    from tank.simulation.mock_sensors import create_mock_sensors
    from tank.storage.event_log import EventStorage

    config = get_config()
    tank = TankSystem(config, simulation=True)
    for s in create_mock_sensors():
        tank.add_sensor(s)
    tank.start()

    storage = EventStorage()
    storage.connect()

    set_tank_system(tank)
    set_event_storage(storage)

    logger.info(f"Tank API starting on {args.host}:{args.port}")
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
