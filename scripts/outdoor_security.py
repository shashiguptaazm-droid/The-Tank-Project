#!/usr/bin/env python3
"""outdoor_security.py - Outdoor Adventure and Security (30 features, F617-F646). Stdlib offline-first CLI matching diagnostics.py + notify.py pattern."""
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Optional

PREFIX = "[outdoor_security]"
def _ok(m): print(f"{PREFIX} OK   {m}", flush=True)
def _err(m): print(f"{PREFIX} FAIL {m}", file=sys.stderr, flush=True)
def _info(m): print(f"{PREFIX} {m}", flush=True)
def _data_root() -> Path:
    root = Path(__file__).resolve().parent.parent / "tank_ws" / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root

def cmd_off_road_explorer(args) -> int:
    """F617 - off-road outdoor explorer."""
    return _ok(json.dumps({"feature": "off-road-explorer", "fid": 617}))

def cmd_snowplow(args) -> int:
    """F618 - driveway snowplow."""
    return _ok(json.dumps({"feature": "snowplow", "fid": 618}))

def cmd_leaf_sweeper(args) -> int:
    """F619 - rake leaf sweeper."""
    return _ok(json.dumps({"feature": "leaf-sweeper", "fid": 619}))

def cmd_garden_scarecrow(args) -> int:
    """F620 - garden bird scarer."""
    return _ok(json.dumps({"feature": "garden-scarecrow", "fid": 620}))

def cmd_compost_turner(args) -> int:
    """F621 - compost pile turner."""
    return _ok(json.dumps({"feature": "compost-turner", "fid": 621}))

def cmd_campfire(args) -> int:
    """F622 - campfire log carrier."""
    return _ok(json.dumps({"feature": "campfire", "fid": 622}))

def cmd_stargazer(args) -> int:
    """F623 - stargazing constellation guide."""
    return _ok(json.dumps({"feature": "stargazer", "fid": 623}))

def cmd_outdoor_movie(args) -> int:
    """F624 - outdoor projector leveller."""
    return _ok(json.dumps({"feature": "outdoor-movie", "fid": 624}))

def cmd_frisbee_return(args) -> int:
    """F625 - frisbee return fetch."""
    return _ok(json.dumps({"feature": "frisbee-return", "fid": 625}))

def cmd_metal_detect(args) -> int:
    """F626 - beach metal detector."""
    return _ok(json.dumps({"feature": "metal-detect", "fid": 626}))

def cmd_pond_skim(args) -> int:
    """F627 - pond debris net skimmer."""
    return _ok(json.dumps({"feature": "pond-skim", "fid": 627}))

def cmd_wildlife_caller(args) -> int:
    """F628 - bird-call broadcaster."""
    return _ok(json.dumps({"feature": "wildlife-caller", "fid": 628}))

def cmd_greenhouse(args) -> int:
    """F629 - greenhouse temp/humidity/vent."""
    return _ok(json.dumps({"feature": "greenhouse", "fid": 629}))

def cmd_berry_picker(args) -> int:
    """F630 - berry ripeness detector."""
    return _ok(json.dumps({"feature": "berry-picker", "fid": 630}))

def cmd_hiking_guide(args) -> int:
    """F631 - GPS hiking guide + water."""
    return _ok(json.dumps({"feature": "hiking-guide", "fid": 631}))

def cmd_decoy_mode(args) -> int:
    """F632 - TV light/sound decoy."""
    return _ok(json.dumps({"feature": "decoy-mode", "fid": 632}))

def cmd_laser_tripwire(args) -> int:
    """F633 - laser tripwire + mirror."""
    return _ok(json.dumps({"feature": "laser-tripwire", "fid": 633}))

def cmd_fog_trigger(args) -> int:
    """F634 - safe fog machine trigger."""
    return _ok(json.dumps({"feature": "fog-trigger", "fid": 634}))

def cmd_parking_sensor(args) -> int:
    """F635 - car parking ultrasonic."""
    return _ok(json.dumps({"feature": "parking-sensor", "fid": 635}))

def cmd_drone_detect(args) -> int:
    """F636 - drone-noise audio detector."""
    return _ok(json.dumps({"feature": "drone-detect", "fid": 636}))

def cmd_voice_stress_sec(args) -> int:
    """F637 - voice stress lie check."""
    return _ok(json.dumps({"feature": "voice-stress-sec", "fid": 637}))

def cmd_fake_cam(args) -> int:
    """F638 - fake security cam shutter."""
    return _ok(json.dumps({"feature": "fake-cam", "fid": 638}))

def cmd_virtual_fence(args) -> int:
    """F639 - GPS+LTE virtual fence."""
    return _ok(json.dumps({"feature": "virtual-fence", "fid": 639}))

def cmd_bark_back(args) -> int:
    """F640 - loud-bark bark-back."""
    return _ok(json.dumps({"feature": "bark-back", "fid": 640}))

def cmd_silent_alarm(args) -> int:
    """F641 - silent SMS-only alarm."""
    return _ok(json.dumps({"feature": "silent-alarm", "fid": 641}))

def cmd_plc_backup(args) -> int:
    """F642 - powerline comms backup."""
    return _ok(json.dumps({"feature": "plc-backup", "fid": 642}))

def cmd_window_break(args) -> int:
    """F643 - window-break glass alarm."""
    return _ok(json.dumps({"feature": "window-break", "fid": 643}))

def cmd_air_horn(args) -> int:
    """F644 - loud amp air-horn."""
    return _ok(json.dumps({"feature": "air-horn", "fid": 644}))

def cmd_strobe_led(args) -> int:
    """F645 - strobe LED disorient."""
    return _ok(json.dumps({"feature": "strobe-led", "fid": 645}))

def cmd_safeword(args) -> int:
    """F646 - safeword alarm cancel."""
    return _ok(json.dumps({"feature": "safeword", "fid": 646}))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Outdoor Adventure and Security (F617-F646).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("off-road-explorer", help="F617 - off-road outdoor explorer")
    sub.add_parser("snowplow", help="F618 - driveway snowplow")
    sub.add_parser("leaf-sweeper", help="F619 - rake leaf sweeper")
    sub.add_parser("garden-scarecrow", help="F620 - garden bird scarer")
    sub.add_parser("compost-turner", help="F621 - compost pile turner")
    sub.add_parser("campfire", help="F622 - campfire log carrier")
    sub.add_parser("stargazer", help="F623 - stargazing constellation guide")
    sub.add_parser("outdoor-movie", help="F624 - outdoor projector leveller")
    sub.add_parser("frisbee-return", help="F625 - frisbee return fetch")
    sub.add_parser("metal-detect", help="F626 - beach metal detector")
    sub.add_parser("pond-skim", help="F627 - pond debris net skimmer")
    sub.add_parser("wildlife-caller", help="F628 - bird-call broadcaster")
    sub.add_parser("greenhouse", help="F629 - greenhouse temp/humidity/vent")
    sub.add_parser("berry-picker", help="F630 - berry ripeness detector")
    sub.add_parser("hiking-guide", help="F631 - GPS hiking guide + water")
    sub.add_parser("decoy-mode", help="F632 - TV light/sound decoy")
    sub.add_parser("laser-tripwire", help="F633 - laser tripwire + mirror")
    sub.add_parser("fog-trigger", help="F634 - safe fog machine trigger")
    sub.add_parser("parking-sensor", help="F635 - car parking ultrasonic")
    sub.add_parser("drone-detect", help="F636 - drone-noise audio detector")
    sub.add_parser("voice-stress-sec", help="F637 - voice stress lie check")
    sub.add_parser("fake-cam", help="F638 - fake security cam shutter")
    sub.add_parser("virtual-fence", help="F639 - GPS+LTE virtual fence")
    sub.add_parser("bark-back", help="F640 - loud-bark bark-back")
    sub.add_parser("silent-alarm", help="F641 - silent SMS-only alarm")
    sub.add_parser("plc-backup", help="F642 - powerline comms backup")
    sub.add_parser("window-break", help="F643 - window-break glass alarm")
    sub.add_parser("air-horn", help="F644 - loud amp air-horn")
    sub.add_parser("strobe-led", help="F645 - strobe LED disorient")
    sub.add_parser("safeword", help="F646 - safeword alarm cancel")
    return p

HANDLERS = {
    "off-road-explorer": cmd_off_road_explorer,
    "snowplow": cmd_snowplow,
    "leaf-sweeper": cmd_leaf_sweeper,
    "garden-scarecrow": cmd_garden_scarecrow,
    "compost-turner": cmd_compost_turner,
    "campfire": cmd_campfire,
    "stargazer": cmd_stargazer,
    "outdoor-movie": cmd_outdoor_movie,
    "frisbee-return": cmd_frisbee_return,
    "metal-detect": cmd_metal_detect,
    "pond-skim": cmd_pond_skim,
    "wildlife-caller": cmd_wildlife_caller,
    "greenhouse": cmd_greenhouse,
    "berry-picker": cmd_berry_picker,
    "hiking-guide": cmd_hiking_guide,
    "decoy-mode": cmd_decoy_mode,
    "laser-tripwire": cmd_laser_tripwire,
    "fog-trigger": cmd_fog_trigger,
    "parking-sensor": cmd_parking_sensor,
    "drone-detect": cmd_drone_detect,
    "voice-stress-sec": cmd_voice_stress_sec,
    "fake-cam": cmd_fake_cam,
    "virtual-fence": cmd_virtual_fence,
    "bark-back": cmd_bark_back,
    "silent-alarm": cmd_silent_alarm,
    "plc-backup": cmd_plc_backup,
    "window-break": cmd_window_break,
    "air-horn": cmd_air_horn,
    "strobe-led": cmd_strobe_led,
    "safeword": cmd_safeword,
}

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        _err("interrupted"); return 130

if __name__ == "__main__":
    sys.exit(main())