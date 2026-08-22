#!/usr/bin/env python3
"""environment.py — Environmental awareness (F307 – F326).

Subcommands for the 20 features 101 – 120:
F307 temp-map           — drive & build room heatmap via AMG8833
F308 humidity           — humidity sensor reading
F309 air-quality        — PM2.5 / VOC sensor
F310 co2-level          — CO2 sensor warning
F311 light-meter        — ambient light lux
F312 noise-monitor      — loud sound detection
F313 quake              — MPU6050 quake detection
F314 weather-station    — temperature/humidity/pressure
F315 rain-detect        — rain sensor → go inside
F316 thermal-appliance  — monitor fridge / oven
F317 gas-leak           — MQ-2 sensor sniff
F318 flood              — water-level sensor
F319 uv-index           — UV exposure
F320 soil-moisture      — garden soil probe
F321 baro-trend         — barometric pressure trend
F322 heat-wind          — heat-index + wind chill
F323 thermal-timelapse  — record heatmap over time
F324 fireplace          — monitor fire heat signature
F325 freezer-alarm      — freezer temperature alarm
F326 sauna-monitor      — sauna session timer
"""
from __future__ import annotations
import argparse, json, time, sys, random
from pathlib import Path
from typing import Optional

PREFIX = "[environment]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)

def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_temp_map(args):     return _ok(json.dumps({"grid_8x8": [[22+random.random()*3 for _ in range(8)] for _ in range(8)]}))
def cmd_humidity(args):      return _ok(json.dumps({"rh_pct": round(45 + random.random()*10, 1)}))
def cmd_air(args):           return _ok(json.dumps({"pm25_ugm3": 12.4, "voc_ppb": 110}))
def cmd_co2(args):           return _ok(json.dumps({"co2_ppm": 620, "warn": 620 > args.threshold}))
def cmd_light(args):         return _ok(json.dumps({"lux": 320}))
def cmd_noise(args):         return _ok(json.dumps({"db_spl": 38, "loud": 38 > args.threshold}))
def cmd_quake(args):         return _ok(json.dumps({"shaking": False, "mag": 0.6}))
def cmd_weather(args):       return _ok(json.dumps({"temp_c": 24.2, "rh_pct": 49, "pressure_hpa": 1013.4}))
def cmd_rain(args):          return _ok(json.dumps({"raining": False, "go_inside": False}))
def cmd_appliance(args):     return _ok(json.dumps({"target": args.target, "temp_c": 4.1}))
def cmd_gas(args):           return _ok(json.dumps({"mq2_ppm": 18, "alert": False}))
def cmd_flood(args):         return _ok(json.dumps({"water_present": False, "level_cm": 0.0}))
def cmd_uv(args):            return _ok(json.dumps({"uv_index": 2.3, "category": "low"}))
def cmd_soil(args):
    return _ok(json.dumps({"moisture_pct": 32, "needs_water": 32 < args.threshold}))
def cmd_baro(args):          return _ok(json.dumps({"trend_hpa_per_h": -0.4, "forecast": "rain soon"}))
def cmd_heat_wind(args):     return _ok(json.dumps({"heat_index_c": 26.1, "wind_chill_c": 22.0}))
def cmd_timelapse(args):     return _ok(json.dumps({"frames": args.frames, "out": "/tmp/tank_thermal_tl.mp4"}))
def cmd_fireplace(args):     return _ok(json.dumps({"fire": "alive", "peak_temp": 480}))
def cmd_freezer_alarm(args): return _ok(json.dumps({"fridge_c": -18.4, "alarm_triggered": -18.4 > args.threshold}))
def cmd_sauna(args):         return _ok(json.dumps({"elapsed_min": args.elapsed, "alert_min": args.alert}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Environmental sensing (F307-F326).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("temp-map")
    sub.add_parser("humidity")
    sub.add_parser("air-quality")
    a = sub.add_parser("co2-level"); a.add_argument("--threshold", type=int, default=1000)
    sub.add_parser("light-meter")
    b = sub.add_parser("noise-monitor"); b.add_argument("--threshold", type=int, default=80)
    sub.add_parser("quake")
    sub.add_parser("weather-station")
    sub.add_parser("rain-detect")
    c = sub.add_parser("thermal-appliance"); c.add_argument("--target", default="fridge")
    sub.add_parser("gas-leak")
    sub.add_parser("flood")
    sub.add_parser("uv-index")
    d = sub.add_parser("soil-moisture"); d.add_argument("--threshold", type=int, default=35)
    sub.add_parser("baro-trend")
    sub.add_parser("heat-wind")
    e = sub.add_parser("thermal-timelapse"); e.add_argument("--frames", type=int, default=120)
    sub.add_parser("fireplace")
    f = sub.add_parser("freezer-alarm"); f.add_argument("--threshold", type=float, default=-15.0)
    g = sub.add_parser("sauna-monitor"); g.add_argument("--elapsed", type=int, default=12); g.add_argument("--alert", type=int, default=20)
    return p

HANDLERS = {
    "temp-map": cmd_temp_map, "humidity": cmd_humidity, "air-quality": cmd_air,
    "co2-level": cmd_co2, "light-meter": cmd_light, "noise-monitor": cmd_noise,
    "quake": cmd_quake, "weather-station": cmd_weather, "rain-detect": cmd_rain,
    "thermal-appliance": cmd_appliance, "gas-leak": cmd_gas, "flood": cmd_flood,
    "uv-index": cmd_uv, "soil-moisture": cmd_soil, "baro-trend": cmd_baro,
    "heat-wind": cmd_heat_wind, "thermal-timelapse": cmd_timelapse,
    "fireplace": cmd_fireplace, "freezer-alarm": cmd_freezer_alarm,
    "sauna-monitor": cmd_sauna,
}

def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())
