"""Launch file for ``log_node`` — the append-only event logger + learner.

Bring-up::

    ros2 launch tank_log log.launch.py
    ros2 launch tank_log log.launch.py learner_period_sec:=30.0
"""
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    repo_root = "/root/the tank project"
    return LaunchDescription([
        DeclareLaunchArgument(
            "db_path", default_value=f"{repo_root}/tank_ws/data/log.db",
            description="Path to the append-only log sqlite file"),
        DeclareLaunchArgument(
            "topics_to_listen", default_value="",
            description="JSON list of topic names (empty = use built-in defaults)"),
        DeclareLaunchArgument(
            "source_label", default_value="log_node"),
        DeclareLaunchArgument(
            "learner_period_sec", default_value="30.0",
            description="If >0, runs a Learner pass every N seconds"),

        Node(
            package="tank_log",
            executable="log_node",
            name="log_node",
            output="screen",
            parameters=[{
                "db_path":          LaunchConfiguration("db_path"),
                "topics_to_listen": LaunchConfiguration("topics_to_listen"),
                "source_label":     LaunchConfiguration("source_label"),
            }],
        ),

        # Optional periodic learner scheduler.
        ExecuteProcess(
            cmd=[
                "python3", "-m", "tank_log.scripts.learn_summary",
                "--db", LaunchConfiguration("db_path"),
                "--loop", LaunchConfiguration("learner_period_sec"),
            ],
            output="screen",
            condition=None,    # always on; set "0.0" in launch to disable manually
            name="learner_scheduler",
        ),
    ])
