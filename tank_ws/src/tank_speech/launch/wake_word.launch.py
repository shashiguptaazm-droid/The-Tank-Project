"""Wake-word listener bring-up.

Brings up `wake_word_listener` (openWakeWord) on its own.  Drift toward
``robot.launch.py`` once the audio capture node is also wired.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg = FindPackageShare("tank_speech")
    config = PathJoinSubstitution([pkg, "config", "wake_word.yaml"])
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("audio_topic",  default_value="/audio"),
        DeclareLaunchArgument("threshold",    default_value="0.55"),
        DeclareLaunchArgument("cooldown_sec", default_value="2.0"),
        DeclareLaunchArgument("window_sec",   default_value="5.0"),
        DeclareLaunchArgument("model_name",   default_value="hey_jarvis"),
        Node(
            package="tank_speech", executable="wake_word_listener_node",
            name="wake_word_listener", output="screen",
            parameters=[config, {
                "use_sim_time":  LaunchConfiguration("use_sim_time"),
                "audio_topic":   LaunchConfiguration("audio_topic"),
                "threshold":     LaunchConfiguration("threshold"),
                "cooldown_sec":  LaunchConfiguration("cooldown_sec"),
                "window_sec":    LaunchConfiguration("window_sec"),
                "model_name":    LaunchConfiguration("model_name"),
            }],
        ),
    ])
