from glob import glob
import os

from setuptools import find_packages, setup

PACKAGE_NAME = "tank_emotions"

setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{PACKAGE_NAME}"]),
        (os.path.join("share", PACKAGE_NAME), ["package.xml"]),
    ],
    install_requires=[
        # pure-Python; no runtime deps.  Tests optionally pull in pytest.
    ],
    zip_safe=True,
    maintainer="Tank Pilot",
    maintainer_email="pilot@medigyaan.xyz",
    description=(
        "Emotion catalog + companions for The Tank Project."
    ),
    license="TBD",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "tank-emotion-lookup = tank_emotions.scripts.emotion_lookup:main",
            "tank-emotion-audit = tank_emotions.scripts.emotion_audit:main",
            "tank-emotion-transition = tank_emotions.scripts.emotion_transition:main",
            "tank-emotion-companion = tank_emotions.scripts.emotion_companion:main",
        ],
    },
)
