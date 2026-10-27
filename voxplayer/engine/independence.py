"""
Desktop / Android independence probe — honest dependency matrix for opsec + e2e.

Does **not** invent codecs. Reports what is required today vs FOSS wrap targets
(libav / MediaCodec). See ``docs/independence_matrix.md``.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class SurfaceRow:
    surface: str
    capability: str
    today: str
    if_remove_vlc: str
    if_remove_ffmpeg_cli: str
    target: str


@dataclass
class IndependenceReport:
    libvlc_version: str = ""
    libvlc_ok: bool = False
    libvlc_error: str = ""
    python_vlc_installed: bool = False
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    bundled_native_core: bool = False
    bundled_lib_path: str = ""
    vox_scan_ok: bool = False
    vox_meta_ok: bool = False
    android_vlc_free: bool = True  # Media3 path — always true by design
    rows: List[SurfaceRow] = field(default_factory=list)
    policy_lines: List[str] = field(default_factory=list)

    def summary_lines(self) -> List[str]:
        lines: List[str] = [
            "VoxPlayer — dependency independence matrix",
            "=" * 48,
            "",
            f"libvlc (desktop decode): {'OK — ' + self.libvlc_version if self.libvlc_ok else 'MISSING'}",
        ]
        if self.libvlc_error and not self.libvlc_ok:
            lines.append(f"  error: {self.libvlc_error}")
        lines.append(
            f"python-vlc PyPI package: {'present (unused; safe to uninstall)' if self.python_vlc_installed else 'absent (expected)'}"
        )
        lines.append(f"ffmpeg CLI (meta/thumbs/viz): {self.ffmpeg_path or '(not found)'}")
        lines.append(f"ffprobe CLI: {self.ffprobe_path or '(not found)'}")
        lines.append(
            f"bundled native_core/: {'yes — ' + self.bundled_lib_path if self.bundled_native_core else 'no (dev uses system libvlc)'}"
        )
        lines.append(f"native vox_scan: {'OK' if self.vox_scan_ok else 'optional / missing'}")
        lines.append(f"native vox_meta: {'OK' if self.vox_meta_ok else 'optional / missing'}")
        lines.append(
            f"Android/Quest VLC-free: {'yes (Media3 → MediaCodec)' if self.android_vlc_free else 'no'}"
        )
        lines.append("")
        lines.append("Matrix (what breaks if you remove deps on this machine):")
        lines.append("-" * 48)
        for r in self.rows:
            lines.append(f"[{r.surface}] {r.capability}")
            lines.append(f"  today:           {r.today}")
            lines.append(f"  remove VLC:      {r.if_remove_vlc}")
            lines.append(f"  remove ffmpeg:   {r.if_remove_ffmpeg_cli}")
            lines.append(f"  FOSS target:     {r.target}")
            lines.append("")
        if self.policy_lines:
            lines.append("Opsec / codec policy:")
            for p in self.policy_lines:
                lines.append(f"  • {p}")
        return lines

    def as_text(self) -> str:
        return "\n".join(self.summary_lines())


def _probe_libvlc() -> Tuple[bool, str, str]:
    try:
        from . import libvlc_ffi

        libvlc_ffi._LIB = None  # fresh probe
        ver = libvlc_ffi.probe()
        return True, ver, ""
    except Exception as exc:
        return False, "", str(exc)


def _python_vlc_present() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("vlc") is not None
    except Exception:
        return False


def _bundled_core() -> Tuple[bool, str]:
    try:
        from ..native_core_paths import resolve_bundled_native_core

        lib, _plugins = resolve_bundled_native_core()
        if lib is not None:
            return True, str(lib)
    except Exception:
        pass
    return False, ""


def _native_libs() -> Tuple[bool, bool]:
    scan = meta = False
    try:
        from .. import native_scan

        scan = bool(native_scan.is_available())
    except Exception:
        pass
    try:
        from .. import native_workers

        meta = bool(native_workers.is_available())
    except Exception:
        pass
    return scan, meta


def build_independence_report() -> IndependenceReport:
    """Gather live probes + static matrix rows for Help / e2e / CLI."""
    ok, ver, err = _probe_libvlc()
    bundled, bundled_path = _bundled_core()
    scan_ok, meta_ok = _native_libs()

    if bundled and ok:
        remove_vlc = (
            "Survivable when staged/bundled native_core is complete "
            "(scripts/e2e_native_core_bundle.py); incomplete tree still fails decode"
        )
    elif ok:
        remove_vlc = (
            "HARD FAIL — run.py / PlaybackEngine exit; no Qt fallback "
            "(stage with: python packaging/stage_native_core.py --force)"
        )
    else:
        remove_vlc = "Already failing — install system libvlc or stage native_core/"

    rows = [
        SurfaceRow(
            surface="Desktop",
            capability="A/V decode + volume 0–200 + WID embed",
            today="libvlc via Vox libvlc_ffi (default); optional VOXPLAYER_DECODE=libav (PyAV)",
            if_remove_vlc=remove_vlc + " — or set VOXPLAYER_DECODE=libav with voxplayer[libav]",
            if_remove_ffmpeg_cli="libvlc playback OK; libav backend / thumbs / spectrum degrade without FFmpeg libs",
            target="Phase 7: strengthen libav path; retire required system VLC when FOSS core is default-capable",
        ),
        SurfaceRow(
            surface="Desktop",
            capability="Python media-suite binding (python-vlc)",
            today="Not required (removed 1.99.0)",
            if_remove_vlc="N/A (binding already gone)",
            if_remove_ffmpeg_cli="N/A",
            target="Keep absent — never reintroduce third-party media PyPI binding",
        ),
        SurfaceRow(
            surface="Desktop",
            capability="Library scan / meta workers",
            today="Rust/Zig vox_scan; vox_meta shells to ffprobe/ffmpeg",
            if_remove_vlc="Unaffected",
            if_remove_ffmpeg_cli="Meta/thumbs workers degrade until linked FOSS replace CLI",
            target="Phase 7D: linked libav in vox_meta (no external ffmpeg binary)",
        ),
        SurfaceRow(
            surface="Android / GrapheneOS",
            capability="On-device A/V decode",
            today="Media3 ExoPlayer → MediaCodec (no VLC)",
            if_remove_vlc="Unaffected (never depended on VLC)",
            if_remove_ffmpeg_cli="Unaffected (no ffmpeg CLI on device)",
            target="Stay Media3; optional Media3 FFmpeg extension only for AOSP gaps",
        ),
        SurfaceRow(
            surface="Quest",
            capability="2D panel playback",
            today="Same Media3 companion as Android",
            if_remove_vlc="Unaffected",
            if_remove_ffmpeg_cli="Unaffected",
            target="Same as Android; honest panel/PiP limits",
        ),
        SurfaceRow(
            surface="All",
            capability="H.264 / H.265 / AV1 / Opus",
            today="Desktop: VLC plugins (avcodec/dav1d/opus). Android: MediaCodec",
            if_remove_vlc="Desktop decode of those codecs fails without replacement stack",
            if_remove_ffmpeg_cli="Probe/report only; decode path unchanged",
            target="Wrap FOSS decoders (libav / dav1d / MediaCodec) — do NOT invent in-tree x264/x265",
        ),
    ]

    policy = [
        "Opsec: no GMS / proprietary cast / analytics SDKs on companion.",
        "Do not invent greenfield H.264/x264/H.265/x265 — wrap FOSS + platform MediaCodec.",
        "System libvlc is optional when FOSS libav (PyAV) is installed — auto-fallback via decode_preflight.",
        "e2e must assert python-vlc absent; require libvlc OR libav OR staged native_core.",
        "VOXPLAYER_DECODE=libvlc|libav|auto — unset/auto prefers libvlc then libav.",
    ]

    return IndependenceReport(
        libvlc_version=ver,
        libvlc_ok=ok,
        libvlc_error=err,
        python_vlc_installed=_python_vlc_present(),
        ffmpeg_path=shutil.which("ffmpeg") or "",
        ffprobe_path=shutil.which("ffprobe") or "",
        bundled_native_core=bundled,
        bundled_lib_path=bundled_path,
        vox_scan_ok=scan_ok,
        vox_meta_ok=meta_ok,
        android_vlc_free=True,
        rows=rows,
        policy_lines=policy,
    )


def assert_e2e_independence_gates() -> List[str]:
    """Return list of failure strings; empty means gates passed for current phase."""
    report = build_independence_report()
    fails: List[str] = []
    if report.python_vlc_installed:
        fails.append(
            "python-vlc is installed — uninstall it; desktop must use libvlc_ffi / libav only"
        )
    libav_ok = False
    try:
        from .libav_engine import libav_available

        libav_ok, _ = libav_available()
    except Exception:
        pass
    if not report.libvlc_ok and not report.bundled_native_core and not libav_ok:
        fails.append(
            "no decode core — need libvlc, staged native_core/, or voxplayer[libav]"
        )
    if not report.android_vlc_free:
        fails.append("Android path must remain VLC-free")
    return fails
