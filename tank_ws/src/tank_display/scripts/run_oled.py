"""CLI first-pass for tank_display (per STATUS.md design rule 8).

Renders the face for each supported mood onto the OLED (or NullHal)
so you can validate the panel without spinning up ROS.

Usage::

    # bench mode, no panel:
    python3 -m tank_display.scripts.run_oled --no-luma

    # on the Pi, with the panel wired at I²C 0x70:
    sudo python3 -m tank_display.scripts.run_oled --luma

    # hold each face for a custom duration:
    python3 -m tank_display.scripts.run_oled --hold 1.5
"""
from __future__ import annotations

import argparse
import sys
import time

from tank_display.faces import DRAWERS, render_face
from tank_display.oled_hal import NullOledHal, open_hal


MOODS = ["happy", "sad", "angry", "scared", "neutral"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--luma", action="store_true",
                   help="drive the real SH1106 panel via luma.oled")
    p.add_argument("--no-luma", action="store_true",
                   help="(default) use NullHal — no I²C traffic")
    p.add_argument("--i2c-port", type=int, default=1)
    p.add_argument("--i2c-address", type=lambda s: int(s, 0), default=0x70)
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--hold", type=float, default=1.0,
                   help="seconds to hold each face")
    p.add_argument("--loop", action="store_true",
                   help="loop forever (Ctrl-C to stop)")
    args = p.parse_args(argv)

    use_luma = args.luma and not args.no_luma
    hal = open_hal(use_luma=use_luma, port=args.i2c_port,
                   address=args.i2c_address,
                   width=args.width, height=args.height)
    mode = "Luma SH1106" if use_luma else "NullHal"
    print(f"tank_display CLI — {mode} {args.width}x{args.height}", flush=True)

    try:
        while True:
            for mood in MOODS:
                img = render_face(mood, size=(hal.width, hal.height))
                hal.display(img, mood=mood)
                if isinstance(hal, NullOledHal):
                    frames = len(hal.frames)
                    last = hal.frames[-1]
                    pixel_count = sum(last["image"].getdata())
                    print(f"  mood={mood:7s} frame#{frames} "
                          f"lit_pixels={pixel_count}", flush=True)
                time.sleep(args.hold)
            if not args.loop:
                return 0
    except KeyboardInterrupt:
        return 0
    finally:
        hal.close()


if __name__ == "__main__":
    sys.exit(main())
