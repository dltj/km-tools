from setuptools import find_packages, setup

setup(
    name="kmtools",
    version="0.1.0",
    packages=find_packages(include=["kmtools", "kmtools.*"]),
    include_package_data=True,
    install_requires=[
        "Click",
    ],
    entry_points={
        "console_scripts": [
            "kmtools = kmtools:kmtools.cli",
        ],
    },
)
