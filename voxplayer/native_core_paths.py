"""Locate and activate a bundled or system native C media core (libvlc).

Used at runtime (frozen desktop bundles) and by ``voxplayer.spec`` when
packaging. Prefer a core shipped next to the executable; fall back to the
system install. Docs/commits refer to this as the native C media core.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BUNDLE_DIRNAME = "native_core"

# Minimum plugin categories for a usable desktop decode core (Linux layout).
# macOS VLC.app ships a flat plugins/ directory instead — see validate_native_core.
_REQUIRED_PLUGIN_DIRS = ("codec", "demux", "audio_output")


def _host_macho_arch() -> Optional[str]:
    """Return ``arm64`` / ``x86_64`` for this Python process on macOS, else None."""
    if sys.platform != "darwin":
        return None
    machine = os.uname().machine
    if machine in {"arm64", "x86_64"}:
        return machine
    return "arm64" if sys.maxsize > 2**32 and machine == "arm" else machine


def _macho_file_arch(path: Path) -> Optional[str]:
    """Best-effort Mach-O CPU type for a dylib/executable (single-arch or first slice)."""
    try:
        data = path.read_bytes()[:4096]
    except OSError:
        return None
    if len(data) < 8:
        return None
    magic = struct.unpack(">I", data[:4])[0]
    # Fat / universal
    if magic in (0xCAFEBABE, 0xBEBAFECA):
        # Prefer host arch when present
        host = _host_macho_arch()
        try:
            _, nfat = struct.unpack(">II", data[:8])
            off = 8
            arches = []
            for _ in range(min(nfat, 8)):
                cputype, _cpusub, _offset, _size, _align = struct.unpack(">IIIII", data[off : off + 20])
                off += 20
                if cputype & 0xFF == 0x0C:  # ARM64 / ARM
                    arches.append("arm64" if cputype & 0x01000000 else "arm")
                elif cputype & 0xFF == 0x07:  # x86 / x86_64
                    arches.append("x86_64" if cputype & 0x01000000 else "i386")
            if host and host in arches:
                return host
            return arches[0] if arches else None
        except Exception:
            return None
    # Thin Mach-O (little-endian modern)
    if magic in (0xFEEDFACF, 0xCFFAEDFE, 0xFEEDFACE, 0xCEFAEDFE):
        le = magic in (0xCFFAEDFE, 0xCEFAEDFE)
        fmt = "<II" if le else ">II"
        try:
            _m, cputype = struct.unpack(fmt, data[:8])
        except struct.error:
            return None
        if cputype & 0xFF == 0x0C:
            return "arm64" if cputype & 0x01000000 else "arm"
        if cputype & 0xFF == 0x07:
            return "x86_64" if cputype & 0x01000000 else "i386"
    return None


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
    """Locate a VLC plugins tree (Linux category layout or macOS flat dylibs)."""
    candidates = [
        directory / "plugins",
        directory / "vlc" / "plugins",
    ]
    # VLC.app: libs live in Contents/MacOS/lib, plugins in Contents/MacOS/plugins
    if directory.name == "lib":
        candidates.append(directory.parent / "plugins")
    candidates.append(directory.parent / "plugins")
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def _plugins_look_complete(plugins: Path) -> bool:
    """True when plugins dir has category subdirs (Linux) or enough flat dylibs (macOS)."""
    if not plugins.is_dir():
        return False
    if all((plugins / need).is_dir() for need in _REQUIRED_PLUGIN_DIRS):
        return True
    dylibs = sum(
        1
        for dirpath, _dns, filenames in os.walk(plugins)
        for f in filenames
        if f.endswith((".dylib", ".so", ".dll"))
    )
    return dylibs >= 20


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
        # Prefer bundled plugins over a stale process env from a previous run.
        os.environ["PYTHON_VLC_MODULE_PATH"] = path
        os.environ["VLC_PLUGIN_PATH"] = path
        activated = True
    if lib is not None:
        os.environ["PYTHON_VLC_LIB_PATH"] = str(lib)
        os.environ["VOXPLAYER_LIBVLC"] = str(lib)
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

            # Preload libvlccore first so plugin @rpath deps can resolve on macOS.
            if sys.platform == "darwin":
                for name in ("libvlccore.dylib", "libvlccore.9.dylib"):
                    core = lib.parent / name
                    if core.is_file():
                        try:
                            ctypes.CDLL(str(core))
                        except OSError:
                            pass
                        break
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


def _macos_vlc_app_candidates() -> List[Path]:
    """VLC.app MacOS roots (lib + sibling plugins), user apps before system when arch matches."""
    apps: List[Path] = []
    for app in (
        Path.home() / "Applications" / "VLC.app",
        Path("/Applications/VLC.app"),
        Path("/opt/homebrew/Caskroom/vlc"),  # rare; cask usually links to /Applications
    ):
        if app.name == "vlc" and app.is_dir():
            # Newest cask version → VLC.app
            for ver in sorted(app.iterdir(), reverse=True):
                cand = ver / "VLC.app"
                if cand.is_dir():
                    apps.append(cand)
            continue
        if app.is_dir():
            apps.append(app)
    return apps


def _macos_vlc_roots() -> List[Path]:
    """Lib directories to probe; paired with sibling ``plugins/`` via ``_find_plugins``."""
    roots: List[Path] = []
    for app in _macos_vlc_app_candidates():
        macos = app / "Contents" / "MacOS"
        lib = macos / "lib"
        if lib.is_dir():
            roots.append(lib)
        elif macos.is_dir():
            roots.append(macos)
    # Homebrew formula cellar (best-effort)
    for cellar in (Path("/opt/homebrew/Cellar/vlc"), Path("/usr/local/Cellar/vlc")):
        if not cellar.is_dir():
            continue
        for ver in sorted(cellar.iterdir(), reverse=True):
            lib = ver / "lib"
            if lib.is_dir():
                roots.append(lib)
            vlc_lib = ver / "lib" / "vlc"
            if vlc_lib.is_dir():
                roots.append(vlc_lib)
    return roots


def _macos_core_from_root(root: Path) -> Optional[Dict[str, object]]:
    """Build a discover payload for one macOS lib root, or None if unusable."""
    lib = _find_lib_in_dir(root)
    if lib is None:
        return None
    plugins = _find_plugins(root) or _find_plugins(root / "vlc")
    if plugins is None or not _plugins_look_complete(plugins):
        return None
    host = _host_macho_arch()
    arch = _macho_file_arch(lib)
    if host and arch and arch != host:
        # Wrong CPU slice (e.g. Intel VLC.app on Apple Silicon) — skip.
        return None
    binaries: List[Tuple[str, str]] = [(str(lib), BUNDLE_DIRNAME)]
    # Copy every VLC dylib beside libvlc (helpers / versioned aliases).
    for p in sorted(root.glob("libvlc*.dylib")):
        if p.is_file() and str(p) != str(lib):
            binaries.append((str(p), BUNDLE_DIRNAME))
    for p in sorted(root.glob("libvlccore*.dylib")):
        if p.is_file():
            binaries.append((str(p), BUNDLE_DIRNAME))
    # Deduplicate by resolved path
    seen = set()
    uniq: List[Tuple[str, str]] = []
    for src, dest in binaries:
        key = str(Path(src).resolve()) if Path(src).exists() else src
        if key in seen:
            continue
        seen.add(key)
        uniq.append((src, dest))
    return {
        "found": True,
        "binaries": uniq,
        "datas": [(str(plugins), f"{BUNDLE_DIRNAME}/plugins")],
        "message": f"macOS native core from {root} ({arch or 'unknown arch'})",
        "arch": arch,
    }


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
        # Prefer arch-matching complete installs; do not return incomplete /Applications first.
        host = _host_macho_arch()
        ranked: List[Dict[str, object]] = []
        for root in _macos_vlc_roots():
            payload = _macos_core_from_root(root)
            if payload is not None:
                ranked.append(payload)
        if ranked:
            # Prefer host arch (already filtered) then user ~/Applications (earlier in roots).
            best = ranked[0]
            return {
                "found": True,
                "binaries": best["binaries"],
                "datas": best["datas"],
                "message": best["message"],
            }
        # Fallback message: mention wrong-arch /Applications when that is the only hit
        wrong_arch_hint = ""
        for app_lib in (
            Path("/Applications/VLC.app/Contents/MacOS/lib/libvlc.dylib"),
            Path.home() / "Applications" / "VLC.app" / "Contents" / "MacOS" / "lib" / "libvlc.dylib",
        ):
            if app_lib.is_file():
                arch = _macho_file_arch(app_lib)
                if host and arch and arch != host:
                    wrong_arch_hint = (
                        f" Found {app_lib} ({arch}) but this Python is {host}; "
                        "install a matching VLC.app (brew install --cask vlc) or use ~/Applications."
                    )
                    break
        return {
            "found": False,
            "binaries": [],
            "datas": [],
            "message": (
                "macOS native core not found (brew install --cask vlc or install matching VLC.app)"
                + wrong_arch_hint
            ),
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
    elif sys.platform == "darwin":
        core = None
        for name in ("libvlccore.dylib", "libvlccore.9.dylib"):
            p = root / name
            if p.is_file() or p.is_symlink():
                core = p
                break
        if core is None:
            for p in root.glob("libvlccore*.dylib"):
                if p.is_file() or p.is_symlink():
                    core = p
                    break
        if core is None:
            errors.append("libvlccore.dylib missing beside libvlc")
        host = _host_macho_arch()
        if lib is not None and host:
            arch = _macho_file_arch(Path(lib))
            if arch and arch != host:
                errors.append(f"libvlc arch {arch} does not match host Python ({host})")
    plugins = _find_plugins(root)
    plugin_files = 0
    if plugins is None:
        errors.append("plugins/ directory missing or empty")
    else:
        for dirpath, _dirnames, filenames in os.walk(plugins):
            plugin_files += sum(1 for f in filenames if f.endswith((".so", ".dll", ".dylib")))
        if plugin_files < 20:
            errors.append(f"plugins look incomplete ({plugin_files} module files; expect dozens)")
        # Linux ships category subdirs; macOS VLC.app uses a flat plugins/ tree.
        has_categories = any((plugins / need).is_dir() for need in _REQUIRED_PLUGIN_DIRS)
        if has_categories:
            for need in _REQUIRED_PLUGIN_DIRS:
                if not (plugins / need).is_dir():
                    errors.append(f"missing plugin category directory: plugins/{need}")
        elif not _plugins_look_complete(plugins):
            errors.append("macOS/flat plugins tree looks incomplete")
    return {
        "ok": not errors,
        "errors": errors,
        "lib": str(lib) if lib else None,
        "plugins": str(plugins) if plugins else None,
        "plugin_files": plugin_files,
    }
