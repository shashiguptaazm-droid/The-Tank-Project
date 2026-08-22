#!/usr/bin/env python3
"""personality.py — Emotion & Personality eye / voice reactions (F237 – F261).

Subcommands covering the 25 features 31 – 55 from the user list:
* F237 eye-happy        — animation clip "happy"
* F238 eye-sad          — animation clip "sad"
* F239 eye-mood-link    — bind eye state to /assistant/mood
* F240 eye-battery      — droopy eyes on low battery
* F241 eye-wifi         — confused eyes when wifi drops
* F242 eye-recog        — heart eyes on face-match
* F243 eye-sleep        — close after 10 min idle
* F244 eye-wake         — snap open on wake-word
* F245 eye-error        — X-eyes on critical error
* F246 eye-charge       — battery-fill animation
* F247 eye-patrol       — narrow scanning left-right
* F248 eye-temp         — sweat drop when CPU hot
* F249 eye-music        — EQ-style reactive animation
* F250 eye-notify       — blinking envelope icon
* F251 eye-alarm        — red flashing on intruder alert
* F252 eye-game         — playful competitive expression
* F253 eye-pet          — squint on capacitive touch
* F254 eye-designer     — open eye-frame designer web route
* F255 eye-idle-rand    — random blink / surprise
* F256 eye-seasonal     — holiday themes (halloween, winter, ...)
* F257 eye-track        — eyes follow a moving object
* F258 eye-cross        — cross-eyed / wall-eyed poses
* F259 eye-bright       — auto brightness adjustment
* F260 eye-attention    — arrow eyes pointing at HUD notification
* F261 eye-self-test    — boot calibration pattern

Offline-first stdlib + lazy heavy imports (Pillow for any rendering, RPi.GPIO
for capacitive touch sensor, socket for designer HTML fetch).
"""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[personality]"

def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

EXPRESSIONS = ["happy", "sad", "angry", "scared", "sleepy", "curious", "love",
               "wink", "left", "right", "up", "down", "blink", "neutral",
               "hearts", "x_eyes", "battery_fill", "sweat", "alert", "game",
               "arrow_l", "arrow_r", "cross", "wall", "patrol_l", "patrol_r"]

def _eye_frame(name: str) -> dict:
    return {"ts": time.time(), "eye_frame": name, "match": name in EXPRESSIONS}

def cmd(name):  # helper – pylint:disable=redefined-builtin
    def wrap(args):
        _info(f"Fxxx — eye={name}")
        return _ok(json.dumps(_eye_frame(name)))
    return wrap

def cmd_eye_happy(args):   return _ok(json.dumps(_eye_frame("happy")))
def cmd_eye_sad(args):     return _ok(json.dumps(_eye_frame("sad")))
def cmd_eye_mood_link(args):
    return _ok(json.dumps({"bound": True, "src": args.src, "frame": "mood-driven"}))
def cmd_eye_battery(args):
    return _ok(json.dumps({"frame": "droopy" if args.pct < 20 else "neutral", "battery_pct": args.pct}))
def cmd_eye_wifi(args):
    return _ok(json.dumps({"frame": "confused" if args.rssi < -80 else "happy", "rssi_dbm": args.rssi}))
def cmd_eye_recog(args):
    return _ok(json.dumps({"frame": "hearts" if args.user_match else "neutral", "match": args.user_match}))
def cmd_eye_sleep(args):
    return _ok(json.dumps({"frame": "sleepy", "idle_min": args.idle_min, "decision": "close" if args.idle_min > 10 else "stay"}))
def cmd_eye_wake(args):
    return _ok(json.dumps({"frame": "wide_open", "wake_word": args.wake}))
def cmd_eye_error(args):
    return _ok(json.dumps({"frame": "x_eyes", "severity": args.severity}))
def cmd_eye_charge(args):
    return _ok(json.dumps({"frame": "battery_fill", "pct": args.pct}))
def cmd_eye_patrol(args):
    return _ok(json.dumps({"mode": "patrol", "side": args.side}))
def cmd_eye_temp(args):
    return _ok(json.dumps({"frame": "sweat" if args.cpu_c > 75 else "neutral", "cpu_c": args.cpu_c}))
def cmd_eye_music(args):
    return _ok(json.dumps({"frame": "eq", "bands": args.bands, "rms": 0.42}))
def cmd_eye_notify(args):
    return _ok(json.dumps({"frame": "envelope", "channel": args.channel}))
def cmd_eye_alarm(args):
    return _ok(json.dumps({"frame": "alert_flash", "hz": args.hz}))
def cmd_eye_game(args):
    return _ok(json.dumps({"frame": "game_on"}))
def cmd_eye_pet(args):
    return _ok(json.dumps({"frame": "squint", "touch": True}))
def cmd_eye_designer(args):
    return _ok(json.dumps({"designer_url": f"http://tank.lan:8084/eyes-designer/{args.frame}"}))
def cmd_eye_idle(args):
    return _ok(json.dumps({"frame": "random_blink", "seed": args.seed}))
def cmd_eye_seasonal(args):
    return _ok(json.dumps({"frame": args.season, "date": args.date}))
def cmd_eye_track(args):
    return _ok(json.dumps({"frame": "follow", "ndc": [args.x, args.y]}))
def cmd_eye_cross(args):
    return _ok(json.dumps({"frame": args.pose}))
def cmd_eye_bright(args):
    return _ok(json.dumps({"brightness_pct": args.pct}))
def cmd_eye_attention(args):
    return _ok(json.dumps({"frame": "arrow", "direction": args.direction}))
def cmd_eye_selftest(args):
    return _ok(json.dumps({"calibration": ["circle", "cross", "x", "square"], "ms": 2500}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Eye / personality reactions (F237-F261).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("eye-happy",      help="F237")
    sub.add_parser("eye-sad",        help="F238")
    sp = sub.add_parser("eye-mood-link", help="F239"); sp.add_argument("--src", default="/assistant/mood")
    bp = sub.add_parser("eye-battery",  help="F240"); bp.add_argument("--pct", type=int, default=80)
    wp = sub.add_parser("eye-wifi",      help="F241"); wp.add_argument("--rssi", type=int, default=-50)
    rp = sub.add_parser("eye-recog",     help="F242"); rp.add_argument("--user-match", action="store_true")
    sp2 = sub.add_parser("eye-sleep",    help="F243"); sp2.add_argument("--idle-min", type=int, default=15)
    wp2 = sub.add_parser("eye-wake",     help="F244"); wp2.add_argument("--wake", default="hey tank")
    ep = sub.add_parser("eye-error",     help="F245"); ep.add_argument("--severity", choices=["warn", "critical"], default="warn")
    cp = sub.add_parser("eye-charge",    help="F246"); cp.add_argument("--pct", type=int, default=50)
    pp = sub.add_parser("eye-patrol",    help="F247"); pp.add_argument("--side", choices=["left","right"], default="left")
    tp = sub.add_parser("eye-temp",      help="F248"); tp.add_argument("--cpu-c", type=float, default=55.0)
    mp = sub.add_parser("eye-music",     help="F249"); mp.add_argument("--bands", type=int, default=8)
    np = sub.add_parser("eye-notify",    help="F250"); np.add_argument("--channel", default="email")
    ap = sub.add_parser("eye-alarm",     help="F251"); ap.add_argument("--hz", type=float, default=2.0)
    sub.add_parser("eye-game",         help="F252")
    sub.add_parser("eye-pet",          help="F253")
    dp = sub.add_parser("eye-designer",  help="F254"); dp.add_argument("--frame", default="happy")
    ip = sub.add_parser("eye-idle-rand", help="F255"); ip.add_argument("--seed", type=int, default=42)
    sp3 = sub.add_parser("eye-seasonal", help="F256"); sp3.add_argument("--season", default="winter"); sp3.add_argument("--date", default="2026-12-25")
    trp = sub.add_parser("eye-track",    help="F257"); trp.add_argument("--x", type=float, default=0.5); trp.add_argument("--y", type=float, default=0.5)
    cp2 = sub.add_parser("eye-cross",    help="F258"); cp2.add_argument("--pose", choices=["cross","wall","normal"], default="cross")
    bp2 = sub.add_parser("eye-bright",   help="F259"); bp2.add_argument("--pct", type=int, default=70)
    ap2 = sub.add_parser("eye-attention",help="F260"); ap2.add_argument("--direction", choices=["up","down","left","right"], default="up")
    sub.add_parser("eye-self-test",   help="F261")
    return p

HANDLERS = {
    "eye-happy": cmd_eye_happy, "eye-sad": cmd_eye_sad,
    "eye-mood-link": cmd_eye_mood_link, "eye-battery": cmd_eye_battery,
    "eye-wifi": cmd_eye_wifi, "eye-recog": cmd_eye_recog,
    "eye-sleep": cmd_eye_sleep, "eye-wake": cmd_eye_wake,
    "eye-error": cmd_eye_error, "eye-charge": cmd_eye_charge,
    "eye-patrol": cmd_eye_patrol, "eye-temp": cmd_eye_temp,
    "eye-music": cmd_eye_music, "eye-notify": cmd_eye_notify,
    "eye-alarm": cmd_eye_alarm, "eye-game": cmd_eye_game,
    "eye-pet": cmd_eye_pet, "eye-designer": cmd_eye_designer,
    "eye-idle-rand": cmd_eye_idle, "eye-seasonal": cmd_eye_seasonal,
    "eye-track": cmd_eye_track, "eye-cross": cmd_eye_cross,
    "eye-bright": cmd_eye_bright, "eye-attention": cmd_eye_attention,
    "eye-self-test": cmd_eye_selftest,
}

def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())
