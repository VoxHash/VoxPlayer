#!/usr/bin/env python3
"""
VoxPlayer Launcher
Prefer the project .venv interpreter so deps (python-mpv, qbittorrent-api) resolve.
Requires system libmpv — there is no Qt Multimedia playback fallback.
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


def _preflight_native_engine() -> None:
    """Fail fast with install guidance if python-mpv / libmpv are missing."""
    try:
        import mpv
    except ImportError:
        print(
            "VoxPlayer requires python-mpv and system libmpv (no Qt playback fallback).\n"
            "  .venv/bin/pip install -r requirements.txt\n"
            "  Arch:   sudo pacman -S mpv\n"
            "  Debian: sudo apt install libmpv2   # or libmpv1\n"
            "  macOS:  brew install mpv\n"
            "  Windows: install libmpv and put mpv-2.dll on PATH\n"
            "Then: python run.py",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        # Instantiate briefly so a missing libmpv .so fails before the Qt window opens.
        probe = mpv.MPV(vo="null", video="no", idle="yes", quiet=True)
        try:
            probe.terminate()
        except Exception:
            pass
    except Exception as exc:
        print(f"libmpv load failed: {exc}", file=sys.stderr)
        print(
            "Install system libmpv (e.g. pacman -S mpv / apt install libmpv2 / brew install mpv).",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    """Launch VoxPlayer"""
    _reexec_with_venv_if_needed()
    print("Starting VoxPlayer (libmpv engine)...")

    os.environ["QT_LOGGING_RULES"] = (
        "qt.multimedia.ffmpeg.debug=false;qt.core.qfuture.continuations=false"
    )
    os.environ["VOXPLAYER_ENGINE"] = "mpv"

    _preflight_native_engine()

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
