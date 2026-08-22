from setuptools import setup
package_name = "tank_assistant"
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
    description="tank_assistant — LLM, RAG bridge, emotion engine",
    license="TODO",
    entry_points={
        "console_scripts": [
            "llm_node     = tank_assistant.llm_node:main",
            "rag_node     = tank_assistant.rag_node:main",
            "emotion_node = tank_assistant.emotion_node:main",
        ],
    },
)
