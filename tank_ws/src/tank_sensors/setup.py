from setuptools import setup

package_name = "tank_sensors"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description="The Tank Project — sensors package (IMU + LiDAR)",
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "imu_publisher_node    = tank_sensors.imu_publisher:main",
            "lidar_publisher_node  = tank_sensors.lidar_publisher:main",
        ],
    },
)
