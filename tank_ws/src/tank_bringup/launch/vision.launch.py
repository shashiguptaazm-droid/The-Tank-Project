"""Spawns the AI vision camera publisher."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bringup = FindPackageShare("tank_bringup")
    config  = PathJoinSubstitution([bringup, "config", "tank_vision.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("device", default_value="0"),
        Node(
            package="tank_vision", executable="camera_publisher_node",
            name="camera_publisher", output="screen",
            parameters=[
                config,
                {
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "device":       LaunchConfiguration("device"),
                },
            ],
        ),
    ])
