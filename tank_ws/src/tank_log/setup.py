from setuptools import find_packages, setup

package_name = "tank_log"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{package_name}"]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/log.launch.py"]),
        ("share/" + package_name + "/config", ["config/log.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Tank Maintainer",
    maintainer_email="tank@example.invalid",
    description=(
        "Append-only event logger + periodic learner. Captures system-"
        "level ROS topics into a portable sqlite file with /log/stats and "
        "/log/tail feeds for the dashboard."
    ),
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "log_node = tank_log.log_node:main",
            "query_log = tank_log.scripts.query_log:main",
            "learn_summary = tank_log.scripts.learn_summary:main",
        ],
    },
)
