"""
api_server.py - TankOS Mobile Command Center API
REST + WebSocket server for mobile app communication
"""
import json
import asyncio
import logging
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("tank.mobile_api")

app = FastAPI(title="TankOS Mobile Command Center", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import components
from tank.mobile.sms_gateway import SMSGateway
from tank.mobile.ai_commander import AICommander
from tank.mobile.telegram_bot import TelegramBot

sms = SMSGateway()
ai = AICommander()
tg = TelegramBot()

ws_clients = set()


class SMSRequest(BaseModel):
    phone: str
    message: str


class CommandRequest(BaseModel):
    command: str
    args: dict = {}


class AlertRequest(BaseModel):
    alert_type: str
    message: str
    priority: str = "normal"


# === REST API ===

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "TankOS Mobile Command Center",
        "uptime": time.time(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/system")
async def system_status():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except:
        cpu = mem_pct = disk_pct = 0
        mem = type("M", (), {"percent": 0, "used": 0, "total": 1})()
        disk = type("D", (), {"percent": 0, "used": 0, "total": 1})()

    modem_status = sms.get_status() if sms.modem else {"connected": False}

    return {
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024**3), 1),
        "ram_total_gb": round(mem.total / (1024**3), 1),
        "disk_percent": disk.percent,
        "modem": modem_status,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/robot")
async def robot_state():
    return ai.get_full_status()


@app.get("/api/alerts")
async def get_alerts():
    return {"alerts": ai.alerts[-50:]}


@app.post("/api/sms/send")
async def send_sms(req: SMSRequest):
    if not sms.modem:
        raise HTTPException(503, "Modem not connected")
    success, resp = sms.send_sms(req.phone, req.message)
    return {"success": success, "response": resp}


@app.post("/api/sms/command")
async def sms_command(req: CommandRequest):
    reply = ai.process_message("api", f"{req.command} {json.dumps(req.args)}")
    return {"reply": reply}


@app.post("/api/command")
async def execute_command(req: CommandRequest):
    reply = ai.process_message("api", f"{req.command} {json.dumps(req.args)}")
    await broadcast_ws({"type": "command", "command": req.command, "args": req.args, "reply": reply})
    return {"reply": reply, "status": "executed"}


@app.post("/api/alert")
async def create_alert(req: AlertRequest):
    alert = ai.add_alert(req.alert_type, req.message)
    await broadcast_ws({"type": "alert", "alert": alert})
    tg.send_alert(req.alert_type, req.message, req.priority)
    return {"alert": alert}


@app.post("/api/camera/capture")
async def capture_frame():
    cam_port = "/dev/ttyACM0"
    try:
        import serial
        s = serial.Serial(cam_port, 921600, timeout=5)
        time.sleep(0.3)
        s.read(s.in_waiting)
        s.write(b"SNAP\n")
        header = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            c = s.read(1)
            if c:
                header += c
                if c == b"\n":
                    break
        h = header.decode("utf-8", errors="replace").strip()
        if h.startswith("FRAME:"):
            parts = h.split(":")
            expected = int(parts[3])
            jpeg = b""
            dl = time.time() + 10
            while len(jpeg) < expected and time.time() < dl:
                chunk = s.read(min(expected - len(jpeg), 16384))
                if chunk:
                    jpeg += chunk
                    dl = time.time() + 2
            s.read(1)
            s.close()
            save_path = "/tmp/tank_frame_latest.jpg"
            with open(save_path, "wb") as f:
                f.write(jpeg)
            ai.last_camera_frame = save_path
            return {"success": True, "size": len(jpeg), "width": int(parts[1]), "height": int(parts[2])}
        s.close()
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "error": "No frame received"}


@app.get("/api/camera/frame")
async def get_frame():
    path = "/tmp/tank_frame_latest.jpg"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(404, "No frame captured yet")


@app.get("/api/camera/stream")
async def camera_stream():
    from fastapi.responses import StreamingResponse
    import serial, time

    def generate():
        try:
            s = serial.Serial("/dev/ttyACM0", 921600, timeout=10)
            time.sleep(0.3)
            s.read(s.in_waiting)
            while True:
                s.write(b"SNAP\n")
                header = b""
                deadline = time.time() + 5
                while time.time() < deadline:
                    c = s.read(1)
                    if c:
                        header += c
                        if c == b"\n":
                            break
                h = header.decode("utf-8", errors="replace").strip()
                if h.startswith("FRAME:"):
                    parts = h.split(":")
                    expected = int(parts[3])
                    jpeg = b""
                    dl = time.time() + 10
                    while len(jpeg) < expected and time.time() < dl:
                        chunk = s.read(min(expected - len(jpeg), 16384))
                        if chunk:
                            jpeg += chunk
                            dl = time.time() + 2
                    s.read(1)
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                time.sleep(0.05)
        except:
            pass

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/motors")
async def set_motors(req: CommandRequest):
    left = req.args.get("left", 0)
    right = req.args.get("right", 0)
    ai.robot_state["motors"] = {"left": left, "right": right}
    await broadcast_ws({"type": "motor", "left": left, "right": right})
    return {"left": left, "right": right}


@app.post("/api/move")
async def move_robot(req: CommandRequest):
    direction = req.args.get("direction", "forward")
    speed = req.args.get("speed", 100)
    reply = ai.process_message("api", f"MOVE {direction.upper()}")
    await broadcast_ws({"type": "move", "direction": direction, "speed": speed})
    return {"reply": reply, "direction": direction, "speed": speed}


@app.post("/api/stop")
async def emergency_stop():
    reply = ai.process_message("api", "STOP")
    await broadcast_ws({"type": "estop"})
    return {"reply": reply}


@app.post("/api/sms/broadcast")
async def broadcast_sms(req: SMSRequest):
    contacts = os.environ.get("TANK_SMS_CONTACTS", "").split(",")
    results = []
    for contact in contacts:
        contact = contact.strip()
        if contact:
            ok, resp = sms.send_sms(contact, req.message)
            results.append({"phone": contact, "success": ok})
    return {"results": results}


@app.get("/api/logs")
async def get_logs():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "tank-vps", "--no-pager", "-n", "50"],
            capture_output=True, text=True, timeout=5,
        )
        return {"logs": result.stdout.split("\n")}
    except:
        return {"logs": ["Log service unavailable"]}


# === WEBSOCKET ===

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        await ws.send_json({"type": "connected", "message": "TankOS Mobile connected"})
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": datetime.now().isoformat()})
            elif msg_type == "command":
                reply = ai.process_message("ws", msg.get("text", ""))
                await ws.send_json({"type": "reply", "text": reply})
            elif msg_type == "subscribe":
                await ws.send_json({"type": "subscribed", "topics": msg.get("topics", [])})
    except WebSocketDisconnect:
        ws_clients.discard(ws)


async def broadcast_ws(data):
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(data)
        except:
            dead.add(ws)
    ws_clients -= dead


# === TELEGRAM COMMAND HANDLERS ===

def _tg_status(chat_id, user, args):
    s = ai.robot_state
    return (f"🤖 Tank Status\nMode: {s['mode']}\n"
            f"Motors: L={s['motors']['left']} R={s['motors']['right']}\n"
            f"Alerts: {s['alerts_count']}")

def _tg_help(chat_id, user, args):
    return ai.cmd_help(chat_id, args, None)

def _tg_camera(chat_id, user, args):
    result = asyncio.run(capture_frame())
    if result.get("success"):
        tg.send_photo("/tmp/tank_frame_latest.jpg", f"📷 {result['width']}x{result['height']} {result['size']} bytes", chat_id)
        return "Photo sent above"
    return "Camera capture failed"

def _tg_move(chat_id, user, args):
    return ai.process_message(chat_id, f"MOVE {args}")

def _tg_stop(chat_id, user, args):
    return ai.process_message(chat_id, "STOP")

def _tg_where(chat_id, user, args):
    return ai.cmd_location(chat_id, args, None)

def _tg_battery(chat_id, user, args):
    return ai.cmd_battery(chat_id, args, None)

def _tg_ai(chat_id, user, args):
    return ai._ai_respond(args, None)


def setup_telegram():
    tg.register_command("start", lambda c, u, a: "🤖 TankOS Mobile Command Center\nType HELP for commands")
    tg.register_command("help", _tg_help)
    tg.register_command("status", _tg_status)
    tg.register_command("camera", _tg_camera)
    tg.register_command("photo", _tg_camera)
    tg.register_command("move", _tg_move)
    tg.register_command("stop", _tg_stop)
    tg.register_command("estop", _tg_stop)
    tg.register_command("where", _tg_where)
    tg.register_command("battery", _tg_battery)
    tg.register_command("ai", _tg_ai)
    tg.on_message(lambda c, u, t: ai.process_message(c, t, None))


# === STARTUP ===

@app.on_event("startup")
async def startup():
    logger.info("TankOS Mobile API starting...")
    sms_connected = sms.connect()
    if sms_connected:
        sms.start_listening()
        logger.info("SMS gateway active")

    ai.load_local_model("phi3")

    if tg.token:
        setup_telegram()
        tg.start_polling()
        logger.info("Telegram bot active")

    logger.info("TankOS Mobile API ready!")


@app.on_event("shutdown")
async def shutdown():
    sms.stop()
    tg.stop()


# Mount PWA static files
pwa_dir = Path(__file__).parent / "web_pwa"
if pwa_dir.exists():
    app.mount("/app", StaticFiles(directory=str(pwa_dir), html=True), name="pwa")
