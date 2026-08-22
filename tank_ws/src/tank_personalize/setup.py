from setuptools import setup

package_name = "tank_personalize"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name, package_name + ".scripts"],
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/static",
            [item for item in __import__("glob").glob("static/*")]),
    ],
    install_requires=["setuptools"],
    extras_require={
        "server": ["fastapi>=0.100", "uvicorn[standard]"],
    },
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "tank_personalize — makes The Tank's onboard AI feel human: "
        "Persona dataclass, SQLite-backed preferences and memory, "
        "dialogue patterns that inject persona + memory into the LLM "
        "system prompt, plus a complete FastAPI-backed preferences "
        "dashboard on port 8084 (bearer-token auth)."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "personalize = tank_personalize.app:main",
            "run_personalize = tank_personalize.scripts.run_personalize:main",
        ],
    },
)
