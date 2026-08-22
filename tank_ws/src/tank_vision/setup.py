from setuptools import setup

package_name = "tank_vision"

setup(
    name=package_name,
    version="0.2.0",
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
    description=(
        "The Tank Project — vision package (camera publisher, eye-LCD "
        "UART bridge, YOLOv8 object tracker with pan-tilt feedback)"
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "camera_publisher_node = tank_vision.camera_publisher:main",
            "eye_lcd_bridge_node   = tank_vision.eye_lcd_bridge:main",
            "object_tracker_node   = tank_vision.object_tracker:main",
        ],
    },
)
