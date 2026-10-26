#!/usr/bin/env python3
"""
VoxPlayer Launcher
Prefer the project .venv interpreter so deps (PyQt6, qbittorrent-api) resolve.
Requires system / bundled libvlc via Vox ctypes binding — no Qt Multimedia playback fallback.
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
    """Fail fast with install guidance if libvlc cannot be loaded via Vox FFI."""
    try:
        from voxplayer.native_core_paths import configure_bundled_native_core

        configure_bundled_native_core()
    except Exception:
        pass
    try:
        from voxplayer.engine import libvlc_ffi

        ver = libvlc_ffi.probe()
        if not ver:
            raise RuntimeError("libvlc version unavailable")
    except Exception as exc:
        print(f"libvlc load failed: {exc}", file=sys.stderr)
        print(
            "VoxPlayer needs system or bundled libvlc (Vox ctypes binding; no python-vlc).\n"
            "  Arch:   sudo pacman -S vlc\n"
            "  Debian: sudo apt install vlc libvlc-dev\n"
            "  macOS:  brew install vlc\n"
            "  Windows: install the desktop media suite so libvlc is on PATH\n"
            "  Or: packaging/install_native_core_*.{sh,ps1}\n"
            "Then: python run.py",
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
