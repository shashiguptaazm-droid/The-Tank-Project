"""Launch file for autonomous patrolling + AI surveillance (tank_patrol).

Bring-up::

    ros2 launch tank_patrol patrol.launch.py
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    repo_root = "/root/the tank project"
    return LaunchDescription([
        DeclareLaunchArgument(
            "waypoints_file",
            default_value=f"{repo_root}/tank_ws/src/tank_patrol/config/waypoints_demo.json",
            description="JSON file of patrol waypoints"),
        DeclareLaunchArgument(
            "battery_return_threshold", default_value="0.20"),
        DeclareLaunchArgument(
            "battery_critical_threshold", default_value="0.10"),
        DeclareLaunchArgument(
            "collision_min_range_m", default_value="0.45"),

        Node(
            package="tank_patrol",
            executable="patrol_node",
            name="patrol_node",
            output="screen",
            parameters=[{
                "waypoints_file":            LaunchConfiguration("waypoints_file"),
                "battery_return_threshold": LaunchConfiguration("battery_return_threshold"),
                "battery_critical_threshold": LaunchConfiguration("battery_critical_threshold"),
                "collision_min_range_m":     LaunchConfiguration("collision_min_range_m"),
            }],
        ),

        Node(
            package="tank_patrol",
            executable="surveillance_node",
            name="surveillance_node",
            output="screen",
        ),
    ])
