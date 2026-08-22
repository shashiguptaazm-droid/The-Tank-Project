from setuptools import setup
from glob import glob

package_name = "tank_learn"

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
    zip_safe=True,
    maintainer="The Tank Project",
    maintainer_email="you@example.com",
    description=(
        "The Tank Project — feedback loop, IQ scoring, and online "
        "learning (Phase 1: SQLite-WAL persistence for the OS)."
    ),
    license="TODO",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "feedback_node = tank_learn.feedback_node:main",
            "tank_learn_teach = tank_learn.scripts.teach:main",
            "tank_learn_consolidate = tank_learn.scripts.consolidate:main",
            "tank_learn_recall = tank_learn.scripts.recall:main",
        ],
    },
)
