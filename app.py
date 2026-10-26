#!/usr/bin/env python3
"""Thin launcher — implementation lives in the voxplayer package.

Prefer the project .venv so PyQt6 and other deps resolve when users run
``python app.py`` with the system interpreter. Playback uses Vox libvlc_ffi.
"""

from __future__ import annotations

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


_reexec_with_venv_if_needed()

from voxplayer.app import VoxPlayerMainWindow, main, TorrentStreamer, UpdateChecker, Settings

__all__ = [
    "VoxPlayerMainWindow",
    "main",
    "TorrentStreamer",
    "UpdateChecker",
    "Settings",
]

if __name__ == "__main__":
    main()
