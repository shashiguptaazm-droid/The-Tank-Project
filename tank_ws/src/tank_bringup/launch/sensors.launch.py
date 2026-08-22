"""Spawns the IMU and LiDAR publishers."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bringup = FindPackageShare("tank_bringup")
    config  = PathJoinSubstitution([bringup, "config", "tank_sensors.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="tank_sensors", executable="imu_publisher_node",
            name="imu_publisher", output="screen",
            parameters=[config,
                        {"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
        Node(
            package="tank_sensors", executable="lidar_publisher_node",
            name="lidar_publisher", output="screen",
            parameters=[config,
                        {"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
    ])
