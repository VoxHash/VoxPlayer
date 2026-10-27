"""
Decode-core preflight — system libvlc is no longer mandatory when FOSS libav is enough.

Selection order when ``VOXPLAYER_DECODE`` is unset / ``auto``:
  1. libvlc (system or staged/bundled ``native_core/``)
  2. FOSS libav via PyAV (``voxplayer[libav]``)

Explicit ``VOXPLAYER_DECODE=libvlc`` or ``libav`` forces that path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class DecodeAvailability:
    libvlc_ok: bool = False
    libvlc_version: str = ""
    libvlc_via: str = "none"  # system | bundled | none
    libav_ok: bool = False
    libav_detail: str = ""
    selected: str = ""  # libvlc | libav
    auto_selected: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.selected in {"libvlc", "libav"} and not self.error


def _probe_libvlc() -> Tuple[bool, str, str]:
    try:
        from ..native_core_paths import configure_bundled_native_core, resolve_bundled_native_core

        configure_bundled_native_core()
        bundled_lib, _plugins = resolve_bundled_native_core()
        via = "bundled" if bundled_lib is not None else "system"
    except Exception:
        via = "system"
        bundled_lib = None
    try:
        from . import libvlc_ffi

        libvlc_ffi._LIB = None
        ver = libvlc_ffi.probe()
        if not ver:
            return False, "", "none"
        # If only bundled path was configured, prefer saying bundled
        if bundled_lib is not None:
            via = "bundled"
        return True, ver if isinstance(ver, str) else str(ver), via
    except Exception as exc:
        return False, str(exc), "none"


def _probe_libav() -> Tuple[bool, str]:
    try:
        from .libav_engine import libav_available

        return libav_available()
    except Exception as exc:
        return False, str(exc)


def probe_decode_backends() -> DecodeAvailability:
    """Probe libvlc + libav without mutating ``VOXPLAYER_DECODE``."""
    lib_ok, lib_ver_or_err, via = _probe_libvlc()
    av_ok, av_detail = _probe_libav()
    info = DecodeAvailability(
        libvlc_ok=lib_ok,
        libvlc_version=lib_ver_or_err if lib_ok else "",
        libvlc_via=via if lib_ok else "none",
        libav_ok=av_ok,
        libav_detail=av_detail,
    )
    if not lib_ok:
        info.libvlc_version = ""
        if lib_ver_or_err:
            info.error = ""  # keep aggregate error only when nothing works
    return info


def _forced_mode() -> Optional[str]:
    raw = (os.getenv("VOXPLAYER_DECODE") or "").strip().lower()
    if raw in {"libav", "ffmpeg", "foss", "av"}:
        return "libav"
    if raw in {"libvlc", "vlc", "native"}:
        return "libvlc"
    if raw in {"", "auto"}:
        return None
    # Unknown value → treat as auto with warning stored nowhere; prefer libvlc name
    return None


def ensure_decode_backend(*, write_env: bool = True) -> DecodeAvailability:
    """
    Choose a working decode backend; auto-fall back to libav when libvlc is absent.

    When auto-selecting libav, sets ``VOXPLAYER_DECODE=libav`` so ``create_playback_engine``
    agrees. Returns availability; ``.ok`` is False only if neither core works.
    """
    info = probe_decode_backends()
    forced = _forced_mode()

    if forced == "libav":
        if info.libav_ok:
            info.selected = "libav"
            info.auto_selected = False
            info.error = ""
            return info
        info.error = "VOXPLAYER_DECODE=libav but PyAV/FFmpeg libs are unavailable"
        info.selected = ""
        return info

    if forced == "libvlc":
        if info.libvlc_ok:
            info.selected = "libvlc"
            info.auto_selected = False
            info.error = ""
            return info
        info.error = "VOXPLAYER_DECODE=libvlc but libvlc is unavailable"
        info.selected = ""
        return info

    # auto
    if info.libvlc_ok:
        info.selected = "libvlc"
        info.auto_selected = False
        info.error = ""
        if write_env and not (os.getenv("VOXPLAYER_DECODE") or "").strip():
            # Leave unset so default remains libvlc; resolve_decode_backend treats unset as libvlc
            pass
        return info

    if info.libav_ok:
        info.selected = "libav"
        info.auto_selected = True
        info.error = ""
        if write_env:
            os.environ["VOXPLAYER_DECODE"] = "libav"
        return info

    info.selected = ""
    info.error = "No decode core available (libvlc and FOSS libav both missing)"
    return info


def decode_install_hint(info: Optional[DecodeAvailability] = None) -> str:
    """User-facing install text when no decode core is available."""
    lines = [
        "VoxPlayer needs a desktop decode core — system libvlc is NOT required when FOSS libav works.",
        "",
        "Option A — FOSS libav (no distro VLC package):",
        "  .venv/bin/pip install \"voxplayer[libav]\"",
        "  # needs system FFmpeg shared libraries (Arch: pacman -S ffmpeg)",
        "  VOXPLAYER_DECODE=libav python run.py",
        "  # or leave VOXPLAYER_DECODE unset — auto-falls back to libav if libvlc is missing",
        "",
        "Option B — libvlc (default when present):",
        "  Stage:  python packaging/stage_native_core.py --force",
        "  Or OS:  packaging/install_native_core_*.{sh,ps1}",
        "  Arch:   sudo pacman -S vlc",
        "  Debian: sudo apt install vlc libvlc-dev",
        "  macOS:  brew install vlc",
        "",
        "There is no Qt Multimedia player fallback. python-vlc is not used.",
    ]
    if info is not None:
        lines.extend(
            [
                "",
                f"Probe: libvlc_ok={info.libvlc_ok} via={info.libvlc_via} "
                f"libav_ok={info.libav_ok} selected={info.selected or '(none)'}",
            ]
        )
        if info.libvlc_version:
            lines.append(f"  libvlc: {info.libvlc_version}")
        if info.libav_detail:
            lines.append(f"  libav:  {info.libav_detail}")
        if info.error:
            lines.append(f"  error:  {info.error}")
    return "\n".join(lines)
