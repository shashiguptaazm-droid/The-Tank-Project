from setuptools import find_packages, setup

package_name = "tank_patrol"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{package_name}"]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/patrol.launch.py"]),
        ("share/" + package_name + "/config", [
            "config/patrol.yaml",
            "config/waypoints_demo.json",
        ]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Tank Maintainer",
    maintainer_email="tank@example.invalid",
    description=(
        "Autonomous AI patrolling + AI-driven surveillance. Pure-Python "
        "Waypoint/Random modes, ROS 2 patrol state machine, motion-event "
        "fusion with severity rules, and a CLI review tool."
    ),
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "patrol_node = tank_patrol.patrol_node:main",
            "surveillance_node = tank_patrol.surveillance_node:main",
            "run_patrol = tank_patrol.scripts.run_patrol:main",
            "surveillance_review = tank_patrol.scripts.surveillance_review:main",
        ],
    },
)
