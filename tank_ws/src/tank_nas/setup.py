from setuptools import setup
package_name = "tank_nas"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config",
         [item for item in __import__("glob").glob("config/*")]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description="tank_nas — Samba + WebDAV + SFTP + rclone (config-only package)",
    license="TODO",
    entry_points={
        "console_scripts": [],
    },
)
