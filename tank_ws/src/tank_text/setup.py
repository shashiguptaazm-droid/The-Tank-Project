from setuptools import setup
package_name = "tank_text"
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
    description="tank_text — Whisper STT + Piper TTS",
    license="TODO",
    entry_points={
        "console_scripts": [
            "stt_node = tank_text.stt_node:main",
            "tts_node = tank_text.tts_node:main",
        ],
    },
)
