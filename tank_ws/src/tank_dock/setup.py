from setuptools import setup
package_name = "tank_dock"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description="tank_dock — auto-docking via AprilTag + IR homing + charge contactor",
    license="TODO",
    entry_points={
        "console_scripts": [
            "dock_node = tank_dock.dock_node:main",
        ],
    },
)
