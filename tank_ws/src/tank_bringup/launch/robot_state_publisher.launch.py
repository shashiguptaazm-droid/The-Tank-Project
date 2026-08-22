"""Publishes the URDF-derived TF tree.

Uses a plain URDF (no xacro) for phase 1 — xacro is convenient but not
required. Move to xacro once the URDF has more than ~30 links.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bringup = FindPackageShare("tank_bringup")
    urdf    = PathJoinSubstitution([bringup, "urdf", "tank.urdf"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{
                "robot_description": Command(["cat ", urdf]),
                "use_sim_time":      LaunchConfiguration("use_sim_time"),
            }],
        ),
    ])
