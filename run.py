#!/usr/bin/env python3
"""
VoxPlayer Launcher
Prefer the project .venv interpreter so deps (e.g. qbittorrent-api) resolve correctly.
"""

import os
import sys


def _reexec_with_venv_if_needed() -> None:
    """If .venv exists and we are not already using it, re-exec under that Python."""
    root = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(root, ".venv", "bin", "python")
    if not os.path.isfile(venv_python):
        return
    try:
        current = os.path.realpath(sys.executable)
        target = os.path.realpath(venv_python)
    except OSError:
        return
    if current == target:
        return
    os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])


def main():
    """Launch VoxPlayer"""
    _reexec_with_venv_if_needed()
    print("Starting VoxPlayer...")

    os.environ["QT_LOGGING_RULES"] = (
        "qt.multimedia.ffmpeg.debug=false;qt.core.qfuture.continuations=false"
    )

    try:
        from app import main as app_main

        app_main()
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install dependencies with: .venv/bin/pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting VoxPlayer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
