"""Track-width calibration helper for The Tank Project.

This script does NOT measure anything automatically — the geometry depends
on your floor surface, motor temperature, and how taut your tracks are.
Instead, it prints a printable procedure you can follow with a stopwatch
and a measuring tape.

Run::

    python3 scripts/measure_track_width.py

Outputs plain text describing how to back-derive ``track_width`` and
``wheel_radius`` from a spin-in-place / straight-line test so you can dial
in ``tank_bringup/config/tank_motion.yaml`` values empirically.
"""
from __future__ import annotations

from pathlib import Path


def banner(text: str) -> str:
    line = "=" * (len(text) + 4)
    return f"\n{line}\n  {text}\n{line}\n"


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    config = repo / "tank_ws" / "src" / "tank_bringup" / "config" / "tank_motion.yaml"

    ros_run_start = "ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "
    ros_run_rate  = "ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist "
    twist_spin    = '{"linear": {"x": 0.0}, "angular": {"z": 0.5}}'
    twist_straight = '{"linear": {"x": 0.5}, "angular": {"z": 0.0}}'

    print(banner("Track-width calibration"))
    print("Step 1 — spin in place at a known rate")
    print("  Mark the robot's heading on the floor. Then run:")
    print("  ", ros_run_start, twist_spin)
    print()
    print("  Time how long the robot takes to complete a full 360° turn (T).")
    print()
    print("Step 2 — derive track_width")
    print("    commanded_omega = 0.5                                              (rad/s)")
    print("    measured_period = T                                                (sec)")
    print("    measured_omega  = 2*pi / T                                         (rad/s)")
    print("    actual_error    = (commanded - measured)/commanded                 (unitless)")
    print()
    print("  If actual_error > 5%, your track_width is wrong. The relationship is:")
    print("    omega = (v_right - v_left) / track_width   -- pure rotation,")
    print("             v_left = -v_right")
    print("    => track_width = 2 * v_right / omega")
    print("  Solve for the wheel_radius the same way using a straight-line test:")
    print("  ", ros_run_rate, twist_straight)
    print()
    print("Step 3 — write the calibrated values")
    print(f"  Open: {config}")
    print("  Adjust motor_controller.track_width  and  motor_controller.wheel_radius")
    print("  Then reload by relaunching:  ros2 launch tank_bringup motion.launch.py")
    print()
    print(banner("Tip"))
    print("  Run the test 3 times and average the measurements — the first run is")
    print("  usually off because the tracks need to settle on the surface.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
