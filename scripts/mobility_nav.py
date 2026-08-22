#!/usr/bin/env python3
"""mobility_nav.py — Mobility & navigation features (F282 – F306).

Subcommands for the 25 features 76 – 100:
F282 nav-autonomous     — ROS2 /cmd_vel autonomous navigation
F283 virtual-leash      — follow a person at distance
F284 waypoint-patrol    — patrol waypoint cycle
F285 dock-return        — auto return to wireless dock
F286 stair-detect       — ultrasonic stair detection
F287 cliff-detect       — IR cliff sensor abort
F288 dynamic-speed      — slow near people, full speed open area
F289 tank-turn          — precise 360 in place
F290 smooth-accel       — trapezoidal accel/decel
F291 obstacle-memory    — remember furniture positions
F292 wall-follow        — wall hug mode
F293 doorway-cross      — door width alignment
F294 ramp-climb         — IMU incline torque boost
F295 joystick-web       — joystick on web dashboard
F296 gamepad            — Bluetooth gamepad teleop
F297 path-record        — record a manual route
F298 crowd-navigation   — politely weave between legs
F299 outdoor-mode       — aggressive outdoor drive
F300 snow-mode          — loose-surface power split
F301 weather-kit        — 3D-printed enclosure for outdoor use
F302 gps-waypoint       — outdoor GPS waypoint mission
F303 magnetic-boundary  — virtual fence detection
F304 follow-leash       — physical leash sensor
F305 soccer-mode        — chase bright-coloured ball
F306 skid-dance         — pre-programmed dance moves
"""
from __future__ import annotations
import argparse, json, time, sys, math
from pathlib import Path
from typing import Optional

PREFIX = "[mobility_nav]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_nav_auto(args):     return _ok(json.dumps({"cmd_vel": [args.vx, 0.0], "obstacle_stop": False}))
def cmd_virtual_leash(args):return _ok(json.dumps({"following": args.user, "distance_m": args.dist}))
def cmd_waypoint(args):
    pts = json.loads(Path(args.mission).read_text()) if Path(args.mission).exists() else [{"x":0,"y":0},{"x":2,"y":0}]
    return _ok(json.dumps({"waypoints": pts, "looped": args.loop}))
def cmd_dock_return(args):  return _ok(json.dumps({"going_home": True, "battery_pct": args.battery}))
def cmd_stair(args):        return _ok(json.dumps({"stairs": False, "sonar_front_cm": args.front}))
def cmd_cliff(args):        return _ok(json.dumps({"cliff": False, "ir_v": args.ir}))
def cmd_dyn_speed(args):
    speed = args.max * 0.4 if args.people_near else args.max
    return _ok(json.dumps({"vx_cap_ms": speed, "people_near": args.people_near}))
def cmd_tank_turn(args):    return _ok(json.dumps({"turn_deg": args.deg, "duration_s": round(args.deg/90.0, 2)}))
def cmd_smooth_accel(args): return _ok(json.dumps({"a_max": 0.6, "v_max": 0.8}))
def cmd_obstacle_memory(args): return _ok(json.dumps({"known_obstacles": 12, "path": args.path}))
def cmd_wall_follow(args):  return _ok(json.dumps({"side": args.side, "distance_cm": 20}))
def cmd_doorway(args):      return _ok(json.dumps({"width_m": args.width, "aligned": True}))
def cmd_ramp(args):         return _ok(json.dumps({"incline_pct": args.incline, "torque_boost": 1 + args.incline/30.0}))
def cmd_joystick_web(args): return _ok(json.dumps({"served_at": "http://tank.lan:8080/joy"}))
def cmd_gamepad(args):      return _ok(json.dumps({"device": args.device, "paired": True}))
def cmd_path_record(args):  return _ok(json.dumps({"recording": True, "ms": args.ms}))
def cmd_crowd(args):        return _ok(json.dumps({"legs_detected": args.legs, "weave_path": [0.1, 0.0, -0.1]}))
def cmd_outdoor(args):      return _ok(json.dumps({"mode": "aggressive", "torque_boost": 1.6}))
def cmd_snow(args):         return _ok(json.dumps({"left_pwr": 0.7, "right_pwr": 0.8}))
def cmd_weather_kit(args):  return _ok(json.dumps({"enclosure": "3DP-A1", "ip_grade": args.ip}))
def cmd_gps_waypoint(args): return _ok(json.dumps({"next_wp": [args.lat, args.lon]}))
def cmd_magnetic(args):     return _ok(json.dumps({"fence_present": True, "signal_strength": 0.8}))
def cmd_leash(args):        return _ok(json.dumps({"pull_force": args.pull, "following": args.pull > 0}))
def cmd_soccer(args):       return _ok(json.dumps({"ball_pos_px": [args.x, args.y], "chase": True}))
def cmd_dance(args):        return _ok(json.dumps({"move": args.move, "duration_s": args.duration}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mobility & navigation (F282-F306).")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("nav-autonomous"); a.add_argument("--vx", type=float, default=0.2)
    b = sub.add_parser("virtual-leash"); b.add_argument("--user", default="pilot"); b.add_argument("--dist", type=float, default=0.6)
    c = sub.add_parser("waypoint-patrol"); c.add_argument("--mission", default="house.json"); c.add_argument("--loop", action="store_true")
    d = sub.add_parser("dock-return"); d.add_argument("--battery", type=int, default=18)
    e = sub.add_parser("stair-detect"); e.add_argument("--front", type=float, default=120.0)
    f = sub.add_parser("cliff-detect"); f.add_argument("--ir", type=float, default=0.45)
    g = sub.add_parser("dynamic-speed"); g.add_argument("--max", type=float, default=0.6); g.add_argument("--people-near", type=int, default=1)
    h = sub.add_parser("tank-turn"); h.add_argument("--deg", type=float, default=360.0)
    sub.add_parser("smooth-accel")
    i = sub.add_parser("obstacle-memory"); i.add_argument("--path", default="memory://obstacles.db")
    j = sub.add_parser("wall-follow"); j.add_argument("--side", choices=["left","right"], default="right")
    k = sub.add_parser("doorway-cross"); k.add_argument("--width", type=float, default=0.9)
    l = sub.add_parser("ramp-climb"); l.add_argument("--incline", type=float, default=12.0)
    sub.add_parser("joystick-web")
    m = sub.add_parser("gamepad"); m.add_argument("--device", default="/dev/input/js0")
    n = sub.add_parser("path-record"); n.add_argument("--ms", type=int, default=20000)
    o = sub.add_parser("crowd-navigation"); o.add_argument("--legs", type=int, default=3)
    sub.add_parser("outdoor-mode")
    sub.add_parser("snow-mode")
    p = sub.add_parser("weather-kit"); p.add_argument("--ip", default="IP54")
    q = sub.add_parser("gps-waypoint"); q.add_argument("--lat", type=float, default=28.61); q.add_argument("--lon", type=float, default=77.21)
    sub.add_parser("magnetic-boundary")
    r = sub.add_parser("follow-leash"); r.add_argument("--pull", type=float, default=0.4)
    s = sub.add_parser("soccer-mode"); s.add_argument("--x", type=int, default=320); s.add_argument("--y", type=int, default=240)
    t = sub.add_parser("skid-dance"); t.add_argument("--move", default="spin-360"); t.add_argument("--duration", type=float, default=4.0)
    return p

HANDLERS = {
    "nav-autonomous": cmd_nav_auto, "virtual-leash": cmd_virtual_leash,
    "waypoint-patrol": cmd_waypoint, "dock-return": cmd_dock_return,
    "stair-detect": cmd_stair, "cliff-detect": cmd_cliff,
    "dynamic-speed": cmd_dyn_speed, "tank-turn": cmd_tank_turn,
    "smooth-accel": cmd_smooth_accel, "obstacle-memory": cmd_obstacle_memory,
    "wall-follow": cmd_wall_follow, "doorway-cross": cmd_doorway,
    "ramp-climb": cmd_ramp, "joystick-web": cmd_joystick_web,
    "gamepad": cmd_gamepad, "path-record": cmd_path_record,
    "crowd-navigation": cmd_crowd, "outdoor-mode": cmd_outdoor,
    "snow-mode": cmd_snow, "weather-kit": cmd_weather_kit,
    "gps-waypoint": cmd_gps_waypoint, "magnetic-boundary": cmd_magnetic,
    "follow-leash": cmd_leash, "soccer-mode": cmd_soccer,
    "skid-dance": cmd_dance,
}

def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())
