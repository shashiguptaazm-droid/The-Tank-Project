"""Spawns the safety watchdog, motor controller, and pan-tilt controller."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bringup = FindPackageShare("tank_bringup")
    config  = PathJoinSubstitution([bringup, "config", "tank_motion.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="tank_bringup", executable="safety_watchdog_node",
            name="safety_watchdog", output="screen",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
        Node(
            package="tank_motion", executable="motor_controller_node",
            name="motor_controller", output="screen",
            parameters=[config,
                        {"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
        Node(
            package="tank_motion", executable="pan_tilt_controller_node",
            name="pan_tilt_controller", output="screen",
            parameters=[config,
                        {"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
    ])
