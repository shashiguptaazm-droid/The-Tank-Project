"""Persistent memory bring-up.

Spawns ``memory_node`` (sqlite-vec + sentence-transformers).  Embedding
work runs in a ``MutuallyExclusiveCallbackGroup`` so it never starves the
wake-word listener, ASR node, or pan-tilt controller.

Usage::

    ros2 launch tank_memory memory.launch.py
    ros2 launch tank_memory memory.launch.py auto_compact_events:=0
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg    = FindPackageShare("tank_memory")
    config = PathJoinSubstitution([pkg, "config", "memory.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time",        default_value="false"),
        DeclareLaunchArgument("db_path",             default_value="tank_ws/data/memory.db"),
        DeclareLaunchArgument("embedding_model",     default_value="all-MiniLM-L6-v2"),
        DeclareLaunchArgument("snapshot_period_sec", default_value="30.0"),
        DeclareLaunchArgument("auto_compact_events", default_value="10000"),
        Node(
            package="tank_memory", executable="memory_node",
            name="memory_node", output="screen",
            parameters=[config, {
                "use_sim_time":        LaunchConfiguration("use_sim_time"),
                "db_path":             LaunchConfiguration("db_path"),
                "embedding_model":     LaunchConfiguration("embedding_model"),
                "snapshot_period_sec": LaunchConfiguration("snapshot_period_sec"),
                "auto_compact_events": LaunchConfiguration("auto_compact_events"),
            }],
        ),
    ])
