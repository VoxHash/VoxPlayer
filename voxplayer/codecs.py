"""Supported formats and system codec capability probe (HEVC / AV1 / Opus).

Playback remains the native C media core (libvlc). This module only:
  • centralizes extension lists (including HEVC/AV1/Opus containers)
  • probes what ffmpeg/ffprobe on the machine can decode (honest capability report)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# Containers / extensions VoxPlayer will open (engine still needs matching demux/decoder).
VIDEO_EXTENSIONS: Set[str] = {
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".3gp",
    ".3g2",
    ".mj2",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".vob",
    ".hevc",
    ".h265",
    ".av1",
    ".ivf",
}

AUDIO_EXTENSIONS: Set[str] = {
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".oga",
    ".wma",
    ".m4a",
    ".opus",
    ".ape",
    ".aiff",
    ".aif",
}

ALL_EXTENSIONS: Set[str] = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Priority codecs called out on the roadmap
FOCUS_CODECS = ("hevc", "av1", "opus")


def is_supported_extension(path: str) -> bool:
    ext = os.path.splitext(path or "")[1].lower()
    return ext in ALL_EXTENSIONS


def video_extensions_list() -> List[str]:
    return sorted(VIDEO_EXTENSIONS)


def audio_extensions_list() -> List[str]:
    return sorted(AUDIO_EXTENSIONS)


def formats_hint() -> str:
    return (
        "Video: MP4, MKV, WebM, AVI, MOV, TS/M2TS, HEVC (.hevc/.h265), AV1 (.av1/.ivf), and similar.\n"
        "Audio: MP3, FLAC, M4A, Opus, OGG/OGA, WAV, AAC, and similar.\n"
        "HEVC / AV1 / Opus need matching decoders in system libvlc + ffmpeg (Help → Codec support)."
    )


def file_dialog_filter() -> str:
    v = " ".join(f"*{e}" for e in sorted(VIDEO_EXTENSIONS))
    a = " ".join(f"*{e}" for e in sorted(AUDIO_EXTENSIONS))
    return (
        f"Media Files ({v} {a});;"
        f"Video Files ({v});;"
        f"Audio Files ({a});;"
        "All Files (*)"
    )


@dataclass
class CodecCapability:
    name: str
    ffmpeg_decoder: bool = False
    ffmpeg_encoder: bool = False
    notes: str = ""


@dataclass
class CodecProbeReport:
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    capabilities: Dict[str, CodecCapability] = field(default_factory=dict)
    hwaccels: List[str] = field(default_factory=list)
    error: str = ""

    def summary_lines(self) -> List[str]:
        lines: List[str] = []
        if self.error:
            lines.append(self.error)
            return lines
        lines.append(f"ffmpeg:  {self.ffmpeg_path or '(not found)'}")
        lines.append(f"ffprobe: {self.ffprobe_path or '(not found)'}")
        if self.hwaccels:
            lines.append("HW accel: " + ", ".join(self.hwaccels))
        else:
            lines.append("HW accel: (none reported)")
        lines.append("")
        lines.append("Focus codecs (roadmap):")
        for key in FOCUS_CODECS:
            cap = self.capabilities.get(key)
            if not cap:
                lines.append(f"  • {key}: unknown")
                continue
            status = "decoder OK" if cap.ffmpeg_decoder else "decoder missing"
            lines.append(f"  • {key.upper()}: {status}" + (f" — {cap.notes}" if cap.notes else ""))
        lines.append("")
        lines.append(
            "Playback uses system libvlc. If a file fails, install/update VLC "
            "(or distro libvlc plugins) so HEVC/AV1/Opus demuxers are present."
        )
        return lines


_DECODER_ALIASES = {
    "hevc": ("hevc", "libde265", "h265"),
    "av1": ("av1", "libdav1d", "libaom-av1"),
    "opus": ("opus", "libopus"),
}


def _run(cmd: List[str], timeout: float = 8.0) -> str:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def probe_system_codecs() -> CodecProbeReport:
    """Probe local ffmpeg/ffprobe for HEVC, AV1, Opus (and list hwaccels)."""
    report = CodecProbeReport()
    report.ffmpeg_path = shutil.which("ffmpeg") or ""
    report.ffprobe_path = shutil.which("ffprobe") or ""
    if not report.ffmpeg_path:
        report.error = (
            "ffmpeg not found on PATH. Install ffmpeg to enrich metadata/thumbnails "
            "and to verify HEVC/AV1/Opus decoder availability."
        )
        for name in FOCUS_CODECS:
            report.capabilities[name] = CodecCapability(name=name)
        return report

    decoders_out = _run([report.ffmpeg_path, "-hide_banner", "-decoders"])
    encoders_out = _run([report.ffmpeg_path, "-hide_banner", "-encoders"])
    hw_out = _run([report.ffmpeg_path, "-hide_banner", "-hwaccels"])

    for line in hw_out.splitlines():
        name = line.strip().lower()
        if not name or name.startswith("hardware") or name == "Hardware acceleration methods:":
            continue
        if re.match(r"^[a-z0-9_\-]+$", name):
            report.hwaccels.append(name)

    dec_lower = decoders_out.lower()
    enc_lower = encoders_out.lower()
    for key, aliases in _DECODER_ALIASES.items():
        has_dec = any(a in dec_lower for a in aliases)
        has_enc = any(a in enc_lower for a in aliases)
        note = ""
        if key == "av1" and has_dec and "dav1d" in dec_lower:
            note = "dav1d present"
        elif key == "hevc" and has_dec:
            note = "hevc/h265 decoder listed"
        elif key == "opus" and has_dec:
            note = "opus decoder listed"
        report.capabilities[key] = CodecCapability(
            name=key, ffmpeg_decoder=has_dec, ffmpeg_encoder=has_enc, notes=note
        )
    return report


def probe_file_codecs(path: str) -> Dict[str, str]:
    """Return stream codec names via ffprobe (video_codec, audio_codec, …)."""
    out: Dict[str, str] = {}
    if not path or not os.path.isfile(path):
        return out
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return out
    raw = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-of",
            "csv=p=0",
            path,
        ]
    )
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            ctype, cname = parts[0], parts[1]
            if ctype == "video" and "video_codec" not in out:
                out["video_codec"] = cname
            elif ctype == "audio" and "audio_codec" not in out:
                out["audio_codec"] = cname
    return out


def avcodec_hw_arg() -> Optional[str]:
    """
    LibVLC Instance arg for hardware decode when allowed.

    Override with ``VOXPLAYER_AVCODEC_HW`` (e.g. ``vaapi``, ``none``, ``any``).
    Default ``any`` on Linux/macOS/Windows so HEVC/AV1 can use GPU when present.
    """
    raw = os.environ.get("VOXPLAYER_AVCODEC_HW", "any").strip()
    if not raw or raw.lower() in {"0", "off", "false", "no"}:
        return None
    if raw.lower() == "none":
        return "--avcodec-hw=none"
    return f"--avcodec-hw={raw}"
