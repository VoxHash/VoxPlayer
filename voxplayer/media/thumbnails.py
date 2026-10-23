"""Generate and cache media thumbnails (ffmpeg frame extract / embedded art)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from typing import Optional

VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}
AUDIO_EXT = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus"}


def _cache_root() -> str:
    root = os.path.join(os.path.expanduser("~"), ".cache", "voxplayer", "thumbnails")
    os.makedirs(root, exist_ok=True)
    return root


def _key_for(path: str) -> str:
    try:
        st = os.stat(path)
        raw = f"{path}|{st.st_mtime_ns}|{st.st_size}".encode("utf-8", errors="replace")
    except OSError:
        raw = path.encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:40]


def get_thumbnail_path(media_path: str) -> Optional[str]:
    """Return cached JPEG path if present."""
    if not media_path or not os.path.exists(media_path):
        return None
    out = os.path.join(_cache_root(), f"{_key_for(media_path)}.jpg")
    return out if os.path.isfile(out) and os.path.getsize(out) > 0 else None


class ThumbnailCache:
    """Create poster frames / cover art for library cards and transport."""

    def __init__(self):
        self.root = _cache_root()

    def path_for(self, media_path: str) -> str:
        return os.path.join(self.root, f"{_key_for(media_path)}.jpg")

    def ensure(self, media_path: str, seek_seconds: float = 3.0) -> Optional[str]:
        """Return path to a thumbnail JPEG, generating if needed."""
        if not media_path or not os.path.isfile(media_path):
            return None
        cached = get_thumbnail_path(media_path)
        if cached:
            return cached
        out = self.path_for(media_path)
        ext = os.path.splitext(media_path)[1].lower()
        try:
            if ext in VIDEO_EXT:
                if self._ffmpeg_frame(media_path, out, seek_seconds):
                    return out
            elif ext in AUDIO_EXT:
                if self._embedded_or_ffmpeg_cover(media_path, out):
                    return out
            else:
                if self._ffmpeg_frame(media_path, out, seek_seconds):
                    return out
        except Exception:
            return None
        return out if os.path.isfile(out) and os.path.getsize(out) > 0 else None

    def _ffmpeg_frame(self, media_path: str, out_path: str, seek: float) -> bool:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(max(0.0, seek)),
            "-i",
            media_path,
            "-frames:v",
            "1",
            "-q:v",
            "4",
            "-y",
            out_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=45)
            if proc.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                return True
            # Retry from start for short clips
            cmd[5] = "0"
            proc = subprocess.run(cmd, capture_output=True, timeout=45)
            return (
                proc.returncode == 0
                and os.path.isfile(out_path)
                and os.path.getsize(out_path) > 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _embedded_or_ffmpeg_cover(self, media_path: str, out_path: str) -> bool:
        # Prefer mutagen embedded art when available.
        try:
            from mutagen import File as MutagenFile  # type: ignore

            audio = MutagenFile(media_path)
            if audio is not None:
                pictures = getattr(audio, "pictures", None)
                if pictures:
                    with open(out_path, "wb") as fh:
                        fh.write(pictures[0].data)
                    return True
                tags = getattr(audio, "tags", None)
                if tags is not None:
                    for key in list(tags.keys()):
                        if str(key).lower().startswith("apic"):
                            apic = tags[key]
                            data = getattr(apic, "data", None)
                            if data:
                                with open(out_path, "wb") as fh:
                                    fh.write(data)
                                return True
        except Exception:
            pass

        # ffmpeg attached_pic / video stream from audio container
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            media_path,
            "-an",
            "-vcodec",
            "mjpeg",
            "-frames:v",
            "1",
            "-y",
            out_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=30)
            return (
                proc.returncode == 0
                and os.path.isfile(out_path)
                and os.path.getsize(out_path) > 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def save_pixmap_bytes(self, media_path: str, jpeg_bytes: bytes) -> Optional[str]:
        if not jpeg_bytes or not media_path:
            return None
        out = self.path_for(media_path)
        try:
            with open(out, "wb") as fh:
                fh.write(jpeg_bytes)
            return out
        except OSError:
            return None
