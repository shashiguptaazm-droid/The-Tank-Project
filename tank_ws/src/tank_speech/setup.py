from setuptools import setup
from glob import glob

package_name = "tank_speech"

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
        "The Tank Project — speech/vision package (wake-word listener "
        "via openWakeWord, plus (later) Whisper STT and Piper TTS)"
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "wake_word_listener_node = tank_speech.wake_word_listener:main",
            "intent_router_node     = tank_speech.intent_router:main",
        ],
    },
)
