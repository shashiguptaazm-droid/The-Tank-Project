"""2D SLAM bring-up via slam_toolbox (online_async).

This launch file:
  * spawns the slam_toolbox solver (async, with /scan + /odom + /tf)
  * spawns our slam_2d_bridge node that re-publishes /map_metadata and
    saves snapshots of the occupancy grid to /tmp as `.pgm` files

Subscribed by both nodes:
  * /scan  sensor_msgs/LaserScan     (from lidar_publisher)
  * /odom  nav_msgs/Odometry         (from motor_controller)
  * /tf    tf2_msgs/TFMessage

Published:
  * /map             nav_msgs/OccupancyGrid
  * /map_metadata    nav_msgs/MapMetaData
  * /map/saved       std_msgs/String
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg    = FindPackageShare("tank_navigation")
    config = PathJoinSubstitution([pkg, "config", "slam_toolbox.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        Node(
            package="slam_toolbox", executable="async_slam_toolbox_node",
            name="slam_toolbox", output="screen",
            parameters=[config,
                        {"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
        Node(
            package="tank_navigation", executable="slam_2d_bridge_node",
            name="slam_2d_bridge", output="screen",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
        ),
    ])
