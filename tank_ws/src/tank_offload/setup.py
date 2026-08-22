from setuptools import setup

package_name = "tank_offload"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name, package_name + ".scripts"],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/systemd",
            [item for item in __import__("glob").glob("systemd/*")]),
    ],
    install_requires=["setuptools"],
    extras_require={
        "server": ["fastapi>=0.100", "uvicorn[standard]"],
        "runtime": ["httpx>=0.24"],   # for the tank-offload CLI / sweep timer
    },
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "tank_offload — automatic overflow-storage node: when /var/tank "
        "fills past a configurable threshold the Pi pushes cold files to "
        "a Nextcloud-backed VPS over rclone + WebDAV. SQLite-backed "
        "manifest with retries, dead-lettering, bandwidth caps, and "
        "optional client-side encryption at rest. Exposes a FastAPI on "
        "port 8085 for status / threshold / trigger / manifest. systemd "
        "service + hourly timer for unattended operation."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "offload             = tank_offload.app:main",
            "run_offload         = tank_offload.scripts.run_offload:main",
            "tank-offload        = tank_offload.scripts.tank_offload_cli:main",
        ],
    },
)
