#!/usr/bin/env python3
"""
VoxPlayer Launcher
Prefer the project .venv interpreter so deps (python-vlc, qbittorrent-api) resolve.
Requires system libvlc — there is no Qt Multimedia playback fallback.
"""

import os
import sys


def _reexec_with_venv_if_needed() -> None:
    """If .venv exists and we are not already using it, re-exec under that Python.

    Compare ``sys.prefix`` to the project venv — do not use ``realpath`` on the
    interpreter binary (venv ``python`` often resolves to the system binary).
    """
    root = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(root, ".venv")
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
    if not os.path.isfile(venv_python):
        return
    try:
        if os.path.samefile(sys.prefix, venv_dir):
            return
    except OSError:
        if os.path.abspath(sys.prefix) == os.path.abspath(venv_dir):
            return
    os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])


def _preflight_native_engine() -> None:
    """Fail fast with install guidance if python-vlc / libvlc are missing."""
    try:
        from voxplayer.native_core_paths import configure_bundled_native_core

        configure_bundled_native_core()
    except Exception:
        pass
    try:
        import vlc
    except ImportError:
        print(
            "VoxPlayer requires python-vlc and system libvlc (no Qt playback fallback).\n"
            "  .venv/bin/pip install -r requirements.txt\n"
            "  Arch:   sudo pacman -S vlc\n"
            "  Debian: sudo apt install vlc libvlc-dev\n"
            "  macOS:  brew install vlc\n"
            "  Windows: install the desktop media suite so libvlc is on PATH\n"
            "Then: python run.py",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        ver = vlc.libvlc_get_version()
        if not ver:
            raise RuntimeError("libvlc version unavailable")
    except Exception as exc:
        print(f"libvlc load failed: {exc}", file=sys.stderr)
        print(
            "Install system libvlc (e.g. pacman -S vlc / apt install vlc / brew install vlc).",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    """Launch VoxPlayer"""
    _reexec_with_venv_if_needed()
    print("Starting VoxPlayer (native C media core)...")

    os.environ["QT_LOGGING_RULES"] = (
        "qt.multimedia.ffmpeg.debug=false;qt.core.qfuture.continuations=false"
    )
    os.environ["VOXPLAYER_ENGINE"] = "native"

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
