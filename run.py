#!/usr/bin/env python3
"""
VoxPlayer Launcher
Prefer the project .venv interpreter so deps (PyQt6, qbittorrent-api) resolve.

Decode core: system/bundled libvlc (default when present) OR FOSS libav via PyAV.
System VLC packages are not required when ``voxplayer[libav]`` works.
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


def _preflight_decode_core() -> None:
    """Fail fast only when neither libvlc nor FOSS libav can run."""
    try:
        from voxplayer.native_core_paths import configure_bundled_native_core

        configure_bundled_native_core()
    except Exception:
        pass
    try:
        from voxplayer.engine.decode_preflight import (
            decode_install_hint,
            ensure_decode_backend,
        )

        info = ensure_decode_backend(write_env=True)
    except Exception as exc:
        print(f"decode preflight failed: {exc}", file=sys.stderr)
        sys.exit(1)
    if not info.ok:
        print(decode_install_hint(info), file=sys.stderr)
        sys.exit(1)
    if info.selected == "libav":
        how = "auto-fallback" if info.auto_selected else "VOXPLAYER_DECODE"
        print(f"Decode core: FOSS libav ({info.libav_detail}; {how})")
    else:
        print(
            f"Decode core: libvlc {info.libvlc_version} ({info.libvlc_via})"
        )


def main():
    """Launch VoxPlayer"""
    _reexec_with_venv_if_needed()
    print("Starting VoxPlayer...")

    os.environ["QT_LOGGING_RULES"] = (
        "qt.multimedia.ffmpeg.debug=false;qt.core.qfuture.continuations=false"
    )
    os.environ["VOXPLAYER_ENGINE"] = "native"

    _preflight_decode_core()

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
