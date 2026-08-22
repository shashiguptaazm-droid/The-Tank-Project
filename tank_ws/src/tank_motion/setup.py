from setuptools import setup

package_name = "tank_motion"

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
    description="The Tank Project — motion package (skid-steer + pan-tilt)",
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "motor_controller_node     = tank_motion.motor_controller:main",
            "pan_tilt_controller_node  = tank_motion.pan_tilt_controller:main",
        ],
    },
)
