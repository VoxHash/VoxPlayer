"""Locate and activate a bundled or system native C media core (libvlc).

Used at runtime (frozen desktop bundles) and by ``voxplayer.spec`` when
packaging. Prefer a core shipped next to the executable; fall back to the
system install. Docs/commits refer to this as the native C media core.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BUNDLE_DIRNAME = "native_core"


def _frozen_base() -> Optional[Path]:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return None


def _project_native_core() -> Optional[Path]:
    """``<repo>/native_core`` when running from a source checkout."""
    here = Path(__file__).resolve().parent  # voxplayer/
    repo = here.parent
    candidate = repo / BUNDLE_DIRNAME
    if candidate.is_dir() and (
        _find_lib_in_dir(candidate) is not None or _find_plugins(candidate) is not None
    ):
        return candidate
    return None


def candidate_bundle_roots() -> List[Path]:
    roots: List[Path] = []
    # Explicit override always wins
    env = os.environ.get("VOXPLAYER_NATIVE_CORE", "").strip()
    if env:
        roots.append(Path(env).expanduser())
    base = _frozen_base()
    if base is not None:
        roots.append(base / BUNDLE_DIRNAME)
        roots.append(base)
        # PyInstaller 6 onedir: exe dir + _internal
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir / BUNDLE_DIRNAME)
        roots.append(exe_dir / "_internal" / BUNDLE_DIRNAME)
    # Dev / CI staged tree next to the package
    proj = _project_native_core()
    if proj is not None:
        roots.append(proj)
    # De-dupe while preserving order
    seen = set()
    out: List[Path] = []
    for r in roots:
        key = str(r.resolve()) if r.exists() else str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _find_lib_in_dir(directory: Path) -> Optional[Path]:
    if not directory.is_dir():
        return None
    names = (
        "libvlc.dll",
        "libvlc.dylib",
        "libvlc.so.5",
        "libvlc.so",
        "libvlc.5.dylib",
    )
    for name in names:
        p = directory / name
        if p.is_file():
            return p
    # Versioned / alternate layouts
    for p in sorted(directory.glob("libvlc.so*")):
        if p.is_file():
            return p
    for p in sorted(directory.glob("libvlc*.dylib")):
        if p.is_file():
            return p
    return None


def _find_plugins(directory: Path) -> Optional[Path]:
    for candidate in (
        directory / "plugins",
        directory / "vlc" / "plugins",
    ):
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def resolve_bundled_native_core() -> Tuple[Optional[Path], Optional[Path]]:
    """Return ``(libvlc_path, plugins_dir)`` for a bundled core, or ``(None, None)``."""
    for root in candidate_bundle_roots():
        lib = _find_lib_in_dir(root)
        plugins = _find_plugins(root)
        if lib is None and plugins is None:
            continue
        if lib is None:
            lib = _find_lib_in_dir(root.parent)
        return lib, plugins
    return None, None


def configure_bundled_native_core() -> bool:
    """Point the Vox libvlc FFI / loader at a bundled core. Safe to call repeatedly.

    Returns True when a bundled lib and/or plugins directory was activated.
    """
    lib, plugins = resolve_bundled_native_core()
    activated = False
    if plugins is not None:
        path = str(plugins)
        os.environ.setdefault("PYTHON_VLC_MODULE_PATH", path)  # legacy env some plugins honor
        os.environ.setdefault("VLC_PLUGIN_PATH", path)
        activated = True
    if lib is not None:
        os.environ.setdefault("PYTHON_VLC_LIB_PATH", str(lib))  # also read by libvlc_ffi
        os.environ.setdefault("VOXPLAYER_LIBVLC", str(lib))
        lib_dir = str(lib.parent)
        if sys.platform == "win32":
            try:
                os.add_dll_directory(lib_dir)  # type: ignore[attr-defined]
            except (AttributeError, OSError):
                os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")
        else:
            key = "DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH"
            cur = os.environ.get(key, "")
            if lib_dir not in cur.split(os.pathsep):
                os.environ[key] = lib_dir + (os.pathsep + cur if cur else "")
        try:
            import ctypes

            ctypes.CDLL(str(lib))
        except OSError:
            pass
        activated = True
    return activated


def plugin_path_args() -> List[str]:
    """Ensure ``VLC_PLUGIN_PATH`` points at bundled plugins; return Instance argv.

    VLC 3.x no longer accepts ``--plugin-path`` (use the environment instead).
    """
    _, plugins = resolve_bundled_native_core()
    if plugins is None:
        env = os.environ.get("VLC_PLUGIN_PATH") or os.environ.get("PYTHON_VLC_MODULE_PATH")
        if env and Path(env).is_dir():
            os.environ.setdefault("VLC_PLUGIN_PATH", env)
        return []
    path = str(plugins)
    os.environ["VLC_PLUGIN_PATH"] = path
    os.environ.setdefault("PYTHON_VLC_MODULE_PATH", path)
    return []


# --- packaging discovery (system install → copy into bundle) ---


def _linux_lib_candidates() -> List[Path]:
    out: List[Path] = []
    for root in (
        Path("/usr/lib"),
        Path("/usr/lib64"),
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/lib/aarch64-linux-gnu"),
        Path("/lib"),
        Path("/lib64"),
    ):
        if not root.is_dir():
            continue
        for name in ("libvlc.so.5", "libvlc.so", "libvlccore.so.9", "libvlccore.so"):
            p = root / name
            if p.exists():
                out.append(p)
        for p in root.glob("libvlc.so.*"):
            out.append(p)
        for p in root.glob("libvlccore.so.*"):
            out.append(p)
    return out


def _linux_plugins() -> Optional[Path]:
    for p in (
        Path("/usr/lib/vlc/plugins"),
        Path("/usr/lib64/vlc/plugins"),
        Path("/usr/lib/x86_64-linux-gnu/vlc/plugins"),
        Path("/usr/lib/aarch64-linux-gnu/vlc/plugins"),
    ):
        if p.is_dir():
            return p
    return None


def _linux_helper_libs() -> List[Path]:
    helpers: List[Path] = []
    for root in (Path("/usr/lib/vlc"), Path("/usr/lib64/vlc"), Path("/usr/lib/x86_64-linux-gnu/vlc")):
        if not root.is_dir():
            continue
        for p in root.glob("libvlc_*.so*"):
            if p.is_file() or p.is_symlink():
                helpers.append(p)
    return helpers


def _windows_vlc_root() -> Optional[Path]:
    env = os.environ.get("VLC_HOME") or os.environ.get("VOXPLAYER_VLC_HOME")
    if env:
        p = Path(env)
        if (p / "libvlc.dll").is_file():
            return p
    for base in (
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    ):
        if not base:
            continue
        p = Path(base) / "VideoLAN" / "VLC"
        if (p / "libvlc.dll").is_file():
            return p
    return None


def _macos_vlc_roots() -> List[Path]:
    roots: List[Path] = []
    for p in (
        Path("/Applications/VLC.app/Contents/MacOS/lib"),
        Path("/Applications/VLC.app/Contents/MacOS"),
        Path.home() / "Applications" / "VLC.app" / "Contents" / "MacOS" / "lib",
    ):
        if p.is_dir():
            roots.append(p)
    # Homebrew cellar (best-effort)
    cellar = Path("/opt/homebrew/Cellar/vlc")
    if not cellar.is_dir():
        cellar = Path("/usr/local/Cellar/vlc")
    if cellar.is_dir():
        for ver in sorted(cellar.iterdir(), reverse=True):
            lib = ver / "lib"
            if lib.is_dir():
                roots.append(lib)
            plugins = ver / "lib" / "vlc" / "plugins"
            if plugins.is_dir():
                roots.append(ver / "lib" / "vlc")
    return roots


def discover_system_native_core() -> Dict[str, object]:
    """Return paths to copy into a desktop bundle.

    Keys::

        found: bool
        binaries: list[(src, dest_rel)]   # dest under native_core/
        datas: list[(src, dest_rel)]
        message: str
    """
    binaries: List[Tuple[str, str]] = []
    datas: List[Tuple[str, str]] = []
    platform = sys.platform

    if platform.startswith("linux"):
        seen = set()
        for lib in _linux_lib_candidates():
            real = str(lib.resolve()) if lib.exists() else str(lib)
            if real in seen:
                continue
            seen.add(real)
            # Keep the basename users expect (libvlc.so.5)
            binaries.append((str(lib), BUNDLE_DIRNAME))
        for helper in _linux_helper_libs():
            real = str(helper.resolve()) if helper.exists() else str(helper)
            if real in seen:
                continue
            seen.add(real)
            binaries.append((str(helper), BUNDLE_DIRNAME))
        plugins = _linux_plugins()
        if plugins is not None:
            datas.append((str(plugins), f"{BUNDLE_DIRNAME}/plugins"))
        found = bool(binaries) and plugins is not None
        msg = (
            f"Linux native core: {len(binaries)} libs, plugins={plugins}"
            if found
            else "Linux native core not found (install system libvlc / vlc package)"
        )
        return {"found": found, "binaries": binaries, "datas": datas, "message": msg}

    if platform == "win32":
        root = _windows_vlc_root()
        if root is None:
            return {
                "found": False,
                "binaries": [],
                "datas": [],
                "message": "Windows native core not found (install desktop media suite or set VLC_HOME)",
            }
        for name in ("libvlc.dll", "libvlccore.dll"):
            p = root / name
            if p.is_file():
                binaries.append((str(p), BUNDLE_DIRNAME))
        plugins = root / "plugins"
        if plugins.is_dir():
            datas.append((str(plugins), f"{BUNDLE_DIRNAME}/plugins"))
        found = bool(binaries) and plugins.is_dir()
        return {
            "found": found,
            "binaries": binaries,
            "datas": datas,
            "message": f"Windows native core from {root}" if found else "Incomplete Windows native core",
        }

    if platform == "darwin":
        for root in _macos_vlc_roots():
            lib = _find_lib_in_dir(root)
            plugins = _find_plugins(root) or _find_plugins(root / "vlc")
            if lib is None:
                continue
            binaries.append((str(lib), BUNDLE_DIRNAME))
            core = root / "libvlccore.dylib"
            if not core.is_file():
                for p in root.glob("libvlccore*.dylib"):
                    core = p
                    break
            if core.is_file():
                binaries.append((str(core), BUNDLE_DIRNAME))
            if plugins is not None:
                datas.append((str(plugins), f"{BUNDLE_DIRNAME}/plugins"))
            found = bool(binaries) and plugins is not None
            return {
                "found": found,
                "binaries": binaries,
                "datas": datas,
                "message": f"macOS native core from {root}" if found else "Incomplete macOS native core",
            }
        return {
            "found": False,
            "binaries": [],
            "datas": [],
            "message": "macOS native core not found (brew install vlc or install VLC.app)",
        }

    return {
        "found": False,
        "binaries": [],
        "datas": [],
        "message": f"Unsupported packaging platform: {platform}",
    }


def pyinstaller_binaries_and_datas() -> Tuple[list, list, str]:
    """Convenience for ``voxplayer.spec``."""
    info = discover_system_native_core()
    binaries = list(info["binaries"])  # type: ignore[arg-type]
    datas = list(info["datas"])  # type: ignore[arg-type]
    return binaries, datas, str(info["message"])


# Minimum plugin categories for a usable desktop decode core
_REQUIRED_PLUGIN_DIRS = ("codec", "demux", "audio_output")


def validate_native_core(root: Path) -> Dict[str, object]:
    """Return ``{ok, errors, lib, plugins, plugin_files}`` for a staged tree."""
    errors: List[str] = []
    root = Path(root)
    if not root.is_dir():
        return {
            "ok": False,
            "errors": [f"not a directory: {root}"],
            "lib": None,
            "plugins": None,
            "plugin_files": 0,
        }
    lib = _find_lib_in_dir(root)
    if lib is None:
        errors.append("libvlc shared library missing (expected libvlc.so.5 / libvlc.dll / …)")
    # libvlccore is required on Linux/macOS for a working CDLL load chain
    if sys.platform.startswith("linux"):
        core = None
        for name in ("libvlccore.so.9", "libvlccore.so"):
            p = root / name
            if p.is_file() or p.is_symlink():
                core = p
                break
        if core is None:
            for p in root.glob("libvlccore.so*"):
                if p.is_file() or p.is_symlink():
                    core = p
                    break
        if core is None:
            errors.append("libvlccore shared library missing beside libvlc")
    plugins = _find_plugins(root)
    plugin_files = 0
    if plugins is None:
        errors.append("plugins/ directory missing or empty")
    else:
        for dirpath, _dirnames, filenames in os.walk(plugins):
            plugin_files += sum(1 for f in filenames if f.endswith((".so", ".dll", ".dylib")))
        if plugin_files < 20:
            errors.append(f"plugins look incomplete ({plugin_files} module files; expect dozens)")
        for need in _REQUIRED_PLUGIN_DIRS:
            if not (plugins / need).is_dir():
                errors.append(f"missing plugin category directory: plugins/{need}")
    return {
        "ok": not errors,
        "errors": errors,
        "lib": str(lib) if lib else None,
        "plugins": str(plugins) if plugins else None,
        "plugin_files": plugin_files,
    }
