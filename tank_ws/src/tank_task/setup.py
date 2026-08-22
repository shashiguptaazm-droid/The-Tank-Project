from setuptools import setup

package_name = "tank_task"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name, "tank_task.tasks"],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "tank_task — voice-commandable task framework for The Tank "
        "(Raspberry Jetson ROS 2 Humble robot). Each task is a small "
        "Python module that supports regex + LLM-fallback intent "
        "matching and runs in a separate process/thread so /cmd_vel "
        "and other ROS topics keep flowing."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "task_router        = tank_task.router_node:main",
            "run_task_registry  = tank_task.scripts.run_router:main",
        ],
    },
)
