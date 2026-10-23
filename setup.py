#!/usr/bin/env python3
"""
VoxPlayer - A modern multimedia player built with PyQt6
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def read_version():
    init_path = os.path.join(os.path.dirname(__file__), "voxplayer", "__init__.py")
    with open(init_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise RuntimeError("version not found in voxplayer/__init__.py")


setup(
    name="voxplayer",
    version=read_version(),
    author="VoxHash Technologies",
    author_email="contact@voxhash.dev",
    description="A modern multimedia player built with PyQt6",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/VoxHash/VoxPlayer",
    project_urls={
        "Bug Reports": "https://github.com/VoxHash/VoxPlayer/issues",
        "Source": "https://github.com/VoxHash/VoxPlayer",
        "Documentation": "https://github.com/VoxHash/VoxPlayer#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video :: Display",
        "Topic :: Multimedia :: Sound/Audio :: Players",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
        "torrent": [
            "qbittorrent-api>=2024.1.0",
        ],
        "native": [
            "python-vlc>=3.0.0",
        ],
        "metadata": [
            "mutagen>=1.45.0",
            "pyacoustid>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "voxplayer=voxplayer.app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "voxplayer": [
            "*.ico",
            "*.png",
            "*.txt",
            "logo.png",
        ],
    },
    keywords="media player, video player, audio player, PyQt6, multimedia, playlist, torrent streaming",
    zip_safe=False,
)
