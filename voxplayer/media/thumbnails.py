"""Generate and cache media thumbnails (FOSS libav / ffmpeg frame extract / embedded art)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from typing import List, Optional

from . import libav_io

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
    """Return cached JPEG path if present and non-empty."""
    if not media_path or not os.path.exists(media_path):
        return None
    out = os.path.join(_cache_root(), f"{_key_for(media_path)}.jpg")
    return out if os.path.isfile(out) and os.path.getsize(out) > 0 else None


def _is_mostly_black_file(path: str, sample: int = 20, threshold: int = 16) -> bool:
    """Detect failed / black poster frames without requiring Qt."""
    try:
        from PyQt6.QtGui import QImage

        img = QImage(path)
        if img.isNull():
            return True
        w, h = img.width(), img.height()
        if w < 2 or h < 2:
            return True
        total = 0
        count = 0
        step_x = max(1, w // sample)
        step_y = max(1, h // sample)
        for y in range(0, h, step_y):
            for x in range(0, w, step_x):
                c = img.pixelColor(x, y)
                total += (c.red() + c.green() + c.blue()) // 3
                count += 1
        return count == 0 or (total / count) < threshold
    except Exception:
        # Fallback: tiny file is suspicious
        try:
            return os.path.getsize(path) < 1200
        except OSError:
            return True


def _probe_duration(media_path: str) -> float:
    dur = libav_io.probe_duration(media_path)
    if dur > 0:
        return dur
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                media_path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return max(0.0, float(proc.stdout.strip()))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0.0


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
        if cached and not _is_mostly_black_file(cached):
            return cached
        if cached and _is_mostly_black_file(cached):
            try:
                os.remove(cached)
            except OSError:
                pass
        out = self.path_for(media_path)
        ext = os.path.splitext(media_path)[1].lower()
        try:
            if ext in VIDEO_EXT:
                if self._frame_smart(media_path, out, seek_seconds):
                    return out
            elif ext in AUDIO_EXT:
                if self._embedded_or_cover(media_path, out):
                    return out
            else:
                if self._frame_smart(media_path, out, seek_seconds):
                    return out
        except Exception:
            return None
        return out if os.path.isfile(out) and os.path.getsize(out) > 0 and not _is_mostly_black_file(out) else None

    def _seek_candidates(self, media_path: str, preferred: float) -> List[float]:
        duration = _probe_duration(media_path)
        candidates = [preferred, 1.0, 0.5, 0.0]
        if duration > 5:
            candidates.extend(
                [
                    duration * 0.10,
                    duration * 0.25,
                    duration * 0.40,
                    duration * 0.55,
                ]
            )
        # unique, non-negative, under duration when known
        seen = set()
        ordered: List[float] = []
        for s in candidates:
            s = max(0.0, float(s))
            if duration > 0:
                s = min(s, max(0.0, duration - 0.25))
            key = round(s, 2)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(s)
        return ordered

    def _frame_smart(self, media_path: str, out_path: str, seek: float) -> bool:
        for s in self._seek_candidates(media_path, seek):
            if self._extract_frame(media_path, out_path, s):
                if not _is_mostly_black_file(out_path):
                    return True
                try:
                    os.remove(out_path)
                except OSError:
                    pass
        return False

    def _extract_frame(self, media_path: str, out_path: str, seek: float) -> bool:
        if libav_io.extract_frame(media_path, out_path, seek):
            return True
        return self._ffmpeg_frame(media_path, out_path, seek)

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
            "3",
            "-vf",
            "scale=480:-2",
            "-y",
            out_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=45)
            return (
                proc.returncode == 0
                and os.path.isfile(out_path)
                and os.path.getsize(out_path) > 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _embedded_or_cover(self, media_path: str, out_path: str) -> bool:
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

        if libav_io.extract_cover(media_path, out_path):
            return True

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
