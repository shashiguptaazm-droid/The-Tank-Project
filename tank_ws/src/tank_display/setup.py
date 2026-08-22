from setuptools import setup

package_name = "tank_display"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch",
            ["launch/display.launch.py"]),
        ("share/" + package_name + "/config",
            ["config/tank_display.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "tank_display — face-emotion display on the 1.3\" SH1106 OLED "
        "(I²C 0x70). Pure-Python with luma.oled and a NullHal fallback "
        "for benches without the panel."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "display_node = tank_display.display_node:main",
            "run_oled     = tank_display.scripts.run_oled:main",
        ],
    },
)
