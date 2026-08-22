"""RTAB-Map 3D mapping bring-up.

RTAB-Map is used here in RGB-only mode: camera + LiDAR + odometry + TF.
If you have a depth camera, flip the launch arg ``depth:=true`` and the
config will switch to RGB-D mode automatically.

Inputs:
  * /camera/image_raw      (vision_msgs/Image)
  * /camera/camera_info    (sensor_msgs/CameraInfo)
  * /scan                  (sensor_msgs/LaserScan)
  * /odom                  (nav_msgs/Odometry)
  * /tf                    (tf2_msgs/TFMessage)

Outputs:
  * /rtabmap/cloud_map     (sensor_msgs/PointCloud2)
  * /rtabmap/info          (rtabmap_msgs/Info)
  * /mapping/loop_count    (std_msgs/Int32)
  * /mapping/stats         (std_msgs/String    JSON)
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg    = FindPackageShare("tank_navigation")
    config = PathJoinSubstitution([pkg, "config", "rtabmap.yaml"])

    use_sim_time = LaunchConfiguration("use_sim_time")
    depth        = LaunchConfiguration("depth")
    frame_id     = LaunchConfiguration("frame_id")

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time",   default_value="false"),
        DeclareLaunchArgument("depth",          default_value="false"),
        DeclareLaunchArgument("frame_id",       default_value="base_link"),
        DeclareLaunchArgument("odom_frame_id",  default_value="odom"),
        DeclareLaunchArgument("map_frame_id",   default_value="map"),
        Node(
            package="rtabmap_ros", executable="rtabmap",
            name="rtabmap", output="screen",
            parameters=[config, {
                "use_sim_time":         use_sim_time,
                "subscribe_depth":      depth,
                "subscribe_stereo":     False,
                "subscribe_scan":       True,
                "approx_sync":          True,
                "visual_odometry":      False,   # we have wheel odometry
                "publish_tf":           True,
                "frame_id":             frame_id,
                "odom_frame_id":        LaunchConfiguration("odom_frame_id"),
                "map_frame_id":         LaunchConfiguration("map_frame_id"),
            }],
            remappings=[
                ("scan",              "/scan"),
                ("odom",              "/odom"),
                ("rgb/image",         "/camera/image_raw"),
                ("rgb/camera_info",   "/camera/camera_info"),
            ],
        ),
        Node(
            package="tank_navigation", executable="rtabmap_bridge_node",
            name="rtabmap_bridge", output="screen",
            parameters=[{"use_sim_time": use_sim_time}],
        ),
    ])
