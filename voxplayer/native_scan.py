"""
Load a native folder scanner for parallel library walks.

Preference order (Phase 3):
  1. Zig ``libvox_scan_zig`` (smaller artifact) under ``native/target/zig-release/``
  2. Rust ``libvox_scan`` under ``native/target/release/``
  3. ``None`` → caller uses the pure-Python walker

Build::

    cargo build --release --manifest-path native/Cargo.toml
    # optional lighter scanner:
    zig build -Doptimize=ReleaseFast --build-file native/vox_scan_zig/build.zig
    # or: native/vox_scan_zig/build.sh
"""

from __future__ import annotations

import ctypes
import os
import sys
from typing import List, Optional, Sequence, Tuple

_LIB: Optional[ctypes.CDLL] = None
_BACKEND: Optional[str] = None  # "zig" | "rust"
_LOAD_ERROR: Optional[str] = None


def _search_roots() -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    roots: List[str] = []
    env = os.environ.get("VOXPLAYER_NATIVE_DIR", "").strip()
    if env:
        roots.extend(
            [
                env,
                os.path.join(env, "target"),
                os.path.join(env, "release"),
                os.path.join(env, "zig-release"),
            ]
        )
    roots.append(os.path.abspath(os.path.join(here, "..", "native", "target")))
    roots.append(
        os.path.abspath(os.path.join(here, "..", "..", "..", "..", "..", "native", "target"))
    )
    seen = set()
    out: List[str] = []
    for r in roots:
        if r and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _candidate_paths() -> List[Tuple[str, str]]:
    """Return (path, backend) pairs — Zig first (smaller), then Rust."""
    zig_names = {
        "linux": ["libvox_scan_zig.so"],
        "darwin": ["libvox_scan_zig.dylib"],
        "win32": ["vox_scan_zig.dll", "libvox_scan_zig.dll"],
    }
    rust_names = {
        "linux": ["libvox_scan.so"],
        "darwin": ["libvox_scan.dylib"],
        "win32": ["vox_scan.dll", "libvox_scan.dll"],
    }
    plat = (
        "win32"
        if sys.platform.startswith("win")
        else ("darwin" if sys.platform == "darwin" else "linux")
    )
    out: List[Tuple[str, str]] = []
    for root in _search_roots():
        for build in ("zig-release", "release", "debug", ""):
            base = os.path.join(root, build) if build else root
            for name in zig_names[plat]:
                out.append((os.path.join(base, name), "zig"))
        for build in ("release", "debug", ""):
            base = os.path.join(root, build) if build else root
            for name in rust_names[plat]:
                out.append((os.path.join(base, name), "rust"))
    return out


def load_library() -> Optional[ctypes.CDLL]:
    global _LIB, _LOAD_ERROR, _BACKEND
    if _LIB is not None:
        return _LIB
    for path, backend in _candidate_paths():
        if not os.path.isfile(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.vox_scan_dir.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            lib.vox_scan_dir.restype = ctypes.c_void_p
            lib.vox_scan_free.argtypes = [ctypes.c_void_p]
            lib.vox_scan_free.restype = None
            _LIB = lib
            _BACKEND = backend
            _LOAD_ERROR = None
            return _LIB
        except OSError as exc:
            _LOAD_ERROR = str(exc)
    _LOAD_ERROR = _LOAD_ERROR or (
        "vox_scan shared library not found (build native/vox_scan or native/vox_scan_zig)"
    )
    return None


def is_available() -> bool:
    return load_library() is not None


def backend_name() -> Optional[str]:
    """``zig``, ``rust``, or ``None`` if no native scanner loaded."""
    load_library()
    return _BACKEND


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
