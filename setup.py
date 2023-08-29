from setuptools import find_packages, setup

setup(
    name="talking_keyboard",
    version="0.1.0",
    description="A Raspberry Pi based talking keyboard",
    author="Vincent Le Bourlot",
    author_email="vlebourl@gmail.com",
    url="https://github.com/vlebourl/keyboard",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "talking_keyboard = main:main",
        ],
    },
    install_requires=[
        "pyalsaaudio",
        "evdev",
        "pygame",
        "gtts",
        "requests",
        "rpi_ws281x",
        "RPLCD",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: System :: Hardware",
    ],
    python_requires=">=3.10",
)
