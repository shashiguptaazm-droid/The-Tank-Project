from setuptools import setup
package_name = "tank_health"
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
    description="tank_health — battery + temperature diagnostics + Prometheus output",
    license="TODO",
    entry_points={
        "console_scripts": [
            "health_node = tank_health.health_node:main",
        ],
    },
)
