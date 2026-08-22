"""Launch file for ``meta_node`` — the structured coding-agent memory layer.

Default args match a Jetson install under ``/root/the tank project/``.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    repo_root = "/root/the tank project"
    return LaunchDescription([
        DeclareLaunchArgument(
            "db_path",
            default_value=f"{repo_root}/tank_ws/data/meta.db",
            description="Path to the meta SQLite file"),
        DeclareLaunchArgument(
            "workspace_root",
            default_value=f"{repo_root}/tank_ws",
            description="Workspace root Python indexer walks"),
        DeclareLaunchArgument(
            "content_root",
            default_value=f"{repo_root}/tank_ws/src/tank_meta/content",
            description="Static JSON content directory"),
        DeclareLaunchArgument(
            "docs_root",
            default_value=f"{repo_root}/docs",
            description="Markdown knowledge root"),
        DeclareLaunchArgument(
            "auto_reindex_sec",
            default_value="0.0",
            description="If >0, run a periodic reindex at this period"),

        Node(
            package="tank_meta",
            executable="meta_node",
            name="meta_node",
            output="screen",
            parameters=[{
                "db_path":          LaunchConfiguration("db_path"),
                "workspace_root":   LaunchConfiguration("workspace_root"),
                "content_root":     LaunchConfiguration("content_root"),
                "docs_root":        LaunchConfiguration("docs_root"),
                "auto_reindex_sec": LaunchConfiguration("auto_reindex_sec"),
            }],
        ),
    ])
