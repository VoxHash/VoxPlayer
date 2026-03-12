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

setup(
    name="voxplayer",
    version="1.0.1",
    author="VoxHash",
    author_email="voxhash@example.com",
    description="A modern multimedia player built with PyQt6",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/voxhash/voxplayer",
    project_urls={
        "Bug Reports": "https://github.com/voxhash/voxplayer/issues",
        "Source": "https://github.com/voxhash/voxplayer",
        "Documentation": "https://github.com/voxhash/voxplayer#readme",
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
            "qbittorrent-api>=0.4.0",
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
