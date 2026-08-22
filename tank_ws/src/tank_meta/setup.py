from setuptools import find_packages, setup

package_name = "tank_meta"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{package_name}"]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/meta.launch.py"]),
        ("share/" + package_name + "/config", ["config/meta.yaml"]),
        ("share/" + package_name + "/content", [
            "content/hardware.json",
            "content/decisions.json",
            "content/project.json",
        ]),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=True,
    maintainer="Tank Maintainer",
    maintainer_email="tank@example.invalid",
    description=(
        "Structured coding-agent memory layer for The Tank Project. "
        "Indexes Python files, hardware components, past decisions, and "
        "knowledge notes into a portable SQLite file."
    ),
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "meta_node = tank_meta.meta_node:main",
            "search_meta = tank_meta.scripts.search_meta:main",
            "index_workspace = tank_meta.scripts.index_workspace:main",
            "serve_meta_api = tank_meta.scripts.serve_meta_api:main",
        ],
    },
)
