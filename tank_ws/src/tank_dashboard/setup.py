from setuptools import setup
package_name = "tank_dashboard"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/dashboard",
         [item for item in __import__("glob").glob("dashboard/*")]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description="tank_dashboard — FastAPI backend exposing ROS2 topics over HTTP/WS",
    license="TODO",
    entry_points={
        "console_scripts": [],   # run via `uvicorn tank_dashboard.app:app`
    },
)
