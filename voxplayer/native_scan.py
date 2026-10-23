"""
Load a native folder scanner for parallel library walks.

Preference order (Phase 3+):
  1. Zig ``libvox_scan_zig`` (smaller artifact) under ``native/target/zig-release/``
  2. Rust ``libvox_scan`` under ``native/target/release/``
  3. ``None`` → caller uses the pure-Python walker

Phase 6 ABI (when present)::

    vox_scan_dir_meta(root, exts) -> \"path\\tsize\\tmtime_ns\" lines
    vox_scan_quick_ids(paths_nl)  -> \"path\\thex\" lines (Rust)
    vox_scan_version()

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
from typing import Dict, List, Optional, Sequence, Tuple

_LIB: Optional[ctypes.CDLL] = None
_BACKEND: Optional[str] = None  # "zig" | "rust"
_LOAD_ERROR: Optional[str] = None
_HAS_META = False
_HAS_QUICK_IDS = False


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


def _bind_optional(lib: ctypes.CDLL) -> None:
    global _HAS_META, _HAS_QUICK_IDS
    _HAS_META = False
    _HAS_QUICK_IDS = False
    if hasattr(lib, "vox_scan_dir_meta"):
        lib.vox_scan_dir_meta.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        lib.vox_scan_dir_meta.restype = ctypes.c_void_p
        _HAS_META = True
    if hasattr(lib, "vox_scan_quick_ids"):
        lib.vox_scan_quick_ids.argtypes = [ctypes.c_char_p]
        lib.vox_scan_quick_ids.restype = ctypes.c_void_p
        _HAS_QUICK_IDS = True
    if hasattr(lib, "vox_scan_version"):
        lib.vox_scan_version.argtypes = []
        lib.vox_scan_version.restype = ctypes.c_char_p


def load_library() -> Optional[ctypes.CDLL]:
    global _LIB, _LOAD_ERROR, _BACKEND
    if _LIB is not None:
        return _LIB
    # Prefer a build that exposes Phase 6 meta ABI; otherwise first loadable lib.
    candidates: List[Tuple[ctypes.CDLL, str, str, bool]] = []
    for path, backend in _candidate_paths():
        if not os.path.isfile(path):
            continue
        try:
            lib = ctypes.CDLL(path)
            lib.vox_scan_dir.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            lib.vox_scan_dir.restype = ctypes.c_void_p
            lib.vox_scan_free.argtypes = [ctypes.c_void_p]
            lib.vox_scan_free.restype = None
            has_meta = hasattr(lib, "vox_scan_dir_meta")
            candidates.append((lib, backend, path, has_meta))
        except OSError as exc:
            _LOAD_ERROR = str(exc)
    if not candidates:
        _LOAD_ERROR = _LOAD_ERROR or (
            "vox_scan shared library not found (build native/vox_scan or native/vox_scan_zig)"
        )
        return None
    # Prefer meta ABI, then quick_ids (Rust), then smaller Zig artifact.
    candidates.sort(
        key=lambda row: (
            0 if row[3] else 1,
            0 if hasattr(row[0], "vox_scan_quick_ids") else 1,
            0 if row[1] == "zig" else 1,
        )
    )
    lib, backend, _path, _has = candidates[0]
    _bind_optional(lib)
    _LIB = lib
    _BACKEND = backend
    _LOAD_ERROR = None
    return _LIB


def is_available() -> bool:
    return load_library() is not None


def backend_name() -> Optional[str]:
    """``zig``, ``rust``, or ``None`` if no native scanner loaded."""
    load_library()
    return _BACKEND


def has_meta_scan() -> bool:
    load_library()
    return _HAS_META


def has_quick_ids() -> bool:
    load_library()
    return _HAS_QUICK_IDS


def native_version() -> Optional[str]:
    lib = load_library()
    if lib is None or not hasattr(lib, "vox_scan_version"):
        return None
    try:
        raw = lib.vox_scan_version()
        if not raw:
            return None
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _decode_ptr(lib: ctypes.CDLL, ptr) -> str:
    if not ptr:
        return ""
    try:
        raw = ctypes.cast(ptr, ctypes.c_char_p).value or b""
        return raw.decode("utf-8", errors="replace")
    finally:
        lib.vox_scan_free(ptr)


def _exts_csv(extensions: Sequence[str]) -> bytes:
    return ",".join(
        (e if e.startswith(".") else f".{e}").lower() for e in extensions if e
    ).encode("utf-8")


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
    ptr = lib.vox_scan_dir(root.encode("utf-8"), _exts_csv(extensions))
    text = _decode_ptr(lib, ptr)
    if not text.strip():
        return []
    return [line for line in text.splitlines() if line]


def scan_media_dir_meta(
    root: str, extensions: Sequence[str]
) -> Optional[Dict[str, Dict[str, int]]]:
    """
    Native parallel walk + stat. Returns ``{abspath: {\"size\": int, \"mtime\": int}}``
    where ``mtime`` is seconds (from mtime_ns) for compatibility with library_index.

    ``None`` if the meta ABI is unavailable.
    """
    lib = load_library()
    if lib is None or not _HAS_META:
        return None
    if not root or not os.path.isdir(root):
        return {}
    ptr = lib.vox_scan_dir_meta(root.encode("utf-8"), _exts_csv(extensions))
    text = _decode_ptr(lib, ptr)
    out: Dict[str, Dict[str, int]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        path, size_s, mtime_ns_s = parts[0], parts[1], parts[2]
        try:
            size = int(size_s)
            mtime_ns = int(mtime_ns_s)
        except ValueError:
            continue
        abs_path = os.path.abspath(path)
        out[abs_path] = {"size": size, "mtime": int(mtime_ns // 1_000_000_000)}
    return out


def quick_ids_for_paths(paths: Sequence[str]) -> Optional[Dict[str, str]]:
    """Parallel blake3 quick ids (Rust). ``None`` if ABI unavailable."""
    lib = load_library()
    if lib is None or not _HAS_QUICK_IDS:
        return None
    payload = "\n".join(p for p in paths if p).encode("utf-8")
    if not payload:
        return {}
    ptr = lib.vox_scan_quick_ids(payload)
    text = _decode_ptr(lib, ptr)
    out: Dict[str, str] = {}
    for line in text.splitlines():
        if "\t" not in line:
            continue
        path, hex_id = line.split("\t", 1)
        out[os.path.abspath(path)] = hex_id.strip()
    return out
