from setuptools import setup
from glob import glob

package_name = "tank_memory"

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
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "The Tank Project — persistent memory (sqlite-vec + "
        "sentence-transformers all-MiniLM-L6-v2, numpy fallback)"
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "memory_node = tank_memory.memory_node:main",
        ],
    },
)
