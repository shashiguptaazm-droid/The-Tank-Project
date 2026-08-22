from setuptools import setup

package_name = "tank_command_bridge"

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
    extras_require={
        "bridge": ["fastapi>=0.100", "uvicorn[standard]", "httpx>=0.24"],
    },
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "tank_command_bridge — bidirectional bridge between The Tank Pi and "
        "external coding-assistant AIs (Freebuff / Claude Code / OpenAI-compatible). "
        "Exposes /api/cmd/* on port 8082 with bearer auth, per-token rate limits, "
        "/api/cmd/manifest for AI introspection, and an external LLM fallback client."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "command_bridge     = tank_command_bridge.app:main",
            "run_bridge         = tank_command_bridge.scripts.run_bridge:main",
            "test_commands      = tank_command_bridge.scripts.test_commands:main",
        ],
    },
)
