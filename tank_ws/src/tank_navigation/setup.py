from setuptools import setup
from glob import glob

package_name = "tank_navigation"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch",
            glob("launch/*.launch.py")),
        ("share/" + package_name + "/config",
            glob("config/*.yaml")),
        ("share/" + package_name + "/rviz",
            glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "The Tank Project — navigation package (2D slam_toolbox + 3D "
        "RTAB-Map bring-up, plus a small re-publishing bridge)"
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "slam_2d_bridge_node    = tank_navigation.slam_2d_bridge:main",
            "rtabmap_bridge_node    = tank_navigation.rtabmap_bridge:main",
        ],
    },
)
