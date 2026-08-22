"""Launch tank_display — emotion-driven face on the 1.3\" OLED (or NullHal in CI).

Default is NullHal; flip ``use_luma`` True on the Pi 5 with the panel
wired at I²C 0x70 (per WIRING.md)."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    use_luma = LaunchConfiguration("use_luma")
    port     = LaunchConfiguration("i2c_port")
    addr     = LaunchConfiguration("i2c_address")

    return LaunchDescription([
        DeclareLaunchArgument("use_luma", default_value="false"),
        DeclareLaunchArgument("i2c_port", default_value="1"),
        DeclareLaunchArgument("i2c_address", default_value="0x70"),
        Node(
            package="tank_display",
            executable="display_node",
            name="display_node",
            parameters=[{
                "use_luma": use_luma,
                "i2c_port": port,
                "i2c_address": addr,
            }],
            output="screen",
        ),
    ])
