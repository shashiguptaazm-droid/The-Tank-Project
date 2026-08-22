from setuptools import setup
from glob import glob
import os

package_name = "tank_bringup"

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
        ("share/" + package_name + "/urdf",
            glob("urdf/*.xacro") + glob("urdf/*.urdf")),
        ("share/" + package_name + "/systemd",
            glob("systemd/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description="The Tank Project — bring-up launch files, global config, safety watchdog",
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "safety_watchdog_node = tank_bringup.safety_watchdog:main",
        ],
    },
)
