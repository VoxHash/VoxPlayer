"""
Load the optional Rust ``vox_scan`` cdylib for parallel library folder walks.

Build once from the repo root:

    cargo build --release --manifest-path native/Cargo.toml

The shared library is looked up under ``native/target/release/`` (and
``debug/``). If it is missing, callers fall back to the pure-Python walker.
"""

from __future__ import annotations

import ctypes
import os
import sys
from typing import List, Optional, Sequence

_LIB: Optional[ctypes.CDLL] = None
_LOAD_ERROR: Optional[str] = None


def _candidate_paths() -> List[str]:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "native", "target"))
    names = {
        "linux": ["libvox_scan.so"],
        "darwin": ["libvox_scan.dylib"],
        "win32": ["vox_scan.dll", "libvox_scan.dll"],
    }
    plat = "win32" if sys.platform.startswith("win") else ("darwin" if sys.platform == "darwin" else "linux")
    out: List[str] = []
    for build in ("release", "debug"):
        for name in names[plat]:
            out.append(os.path.join(root, build, name))
    return out


def load_library() -> Optional[ctypes.CDLL]:
    global _LIB, _LOAD_ERROR
    if _LIB is not None:
        return _LIB
    if _LOAD_ERROR is not None and _LIB is None:
        # Already failed once this process
        pass
    for path in _candidate_paths():
        if not os.path.isfile(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.vox_scan_dir.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            lib.vox_scan_dir.restype = ctypes.c_void_p
            lib.vox_scan_free.argtypes = [ctypes.c_void_p]
            lib.vox_scan_free.restype = None
            _LIB = lib
            _LOAD_ERROR = None
            return _LIB
        except OSError as exc:
            _LOAD_ERROR = str(exc)
    _LOAD_ERROR = _LOAD_ERROR or "vox_scan shared library not found (build native/vox_scan)"
    return None


def is_available() -> bool:
    return load_library() is not None


def scan_media_dir(root: str, extensions: Sequence[str]) -> Optional[List[str]]:
    """
    Return matching media paths under ``root``, or ``None`` if the native
    library is unavailable (caller should use the Python walker).
    """
    lib = load_library()
    if lib is None:
        return None
    if not root or not os.path.isdir(root):
        return []
    exts = ",".join(
        (e if e.startswith(".") else f".{e}").lower() for e in extensions if e
    )
    ptr = lib.vox_scan_dir(root.encode("utf-8"), exts.encode("utf-8"))
    if not ptr:
        return []
    try:
        raw = ctypes.cast(ptr, ctypes.c_char_p).value or b""
        text = raw.decode("utf-8", errors="replace")
    finally:
        lib.vox_scan_free(ptr)
    if not text.strip():
        return []
    return [line for line in text.splitlines() if line]
