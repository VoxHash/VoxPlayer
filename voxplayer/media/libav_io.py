"""Linked FOSS libav I/O via PyAV (no ``ffmpeg`` / ``ffprobe`` CLI required).

Used by thumbnails, local metadata tags, and spectrum PCM when
``pip install "voxplayer[libav]"`` (or ``av``) is present. Callers may keep a
CLI fallback for hosts without PyAV.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple


def available() -> Tuple[bool, str]:
    try:
        import av  # noqa: F401
    except Exception as exc:  # ImportError or missing native libs
        return False, str(exc)
    return True, "PyAV"


def probe_duration(path: str) -> float:
    """Return media duration in seconds, or 0.0."""
    ok, _ = available()
    if not ok or not path or not os.path.isfile(path):
        return 0.0
    try:
        import av

        with av.open(path) as container:
            if container.duration is not None and container.duration > 0:
                return max(0.0, float(container.duration) / float(av.time_base))
            for stream in container.streams:
                if stream.duration is not None and stream.time_base is not None:
                    return max(0.0, float(stream.duration * stream.time_base))
    except Exception:
        return 0.0
    return 0.0


def read_tags(path: str) -> Dict[str, str]:
    """Container + stream metadata tags (lower-cased keys)."""
    ok, _ = available()
    if not ok or not path or not os.path.isfile(path):
        return {}
    tags: Dict[str, str] = {}
    try:
        import av

        with av.open(path) as container:
            for k, v in (container.metadata or {}).items():
                if v is not None and str(v).strip():
                    tags[str(k).lower()] = str(v)
            for stream in container.streams:
                for k, v in (stream.metadata or {}).items():
                    if v is not None and str(v).strip():
                        tags.setdefault(str(k).lower(), str(v))
            if container.duration is not None and container.duration > 0:
                tags.setdefault(
                    "duration",
                    str(float(container.duration) / float(av.time_base)),
                )
    except Exception:
        return {}
    return tags


def _save_rgb_frame(frame, out_path: str, max_width: int = 480) -> bool:
    """Write a video frame as JPEG via Qt (no Pillow required)."""
    try:
        w = int(frame.width)
        h = int(frame.height)
        if w < 2 or h < 2:
            return False
        if max_width > 0 and w > max_width:
            nh = max(2, int(h * (max_width / float(w))))
            # even dimensions help some encoders; QImage does not care
            nh = nh if nh % 2 == 0 else nh + 1
            frame = frame.reformat(width=max_width, height=nh, format="rgb24")
        else:
            frame = frame.reformat(format="rgb24")
        from PyQt6.QtGui import QImage

        plane = bytes(frame.planes[0])
        qimg = QImage(
            plane,
            frame.width,
            frame.height,
            frame.width * 3,
            QImage.Format.Format_RGB888,
        )
        if qimg.isNull():
            return False
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        return bool(qimg.save(out_path, "JPG", 85)) and os.path.isfile(out_path) and os.path.getsize(out_path) > 0
    except Exception:
        return False


def extract_frame(path: str, out_path: str, seek_seconds: float = 3.0) -> bool:
    """Seek near ``seek_seconds`` and write one scaled JPEG poster frame."""
    ok, _ = available()
    if not ok or not path or not os.path.isfile(path):
        return False
    try:
        import av

        with av.open(path) as container:
            stream = next((s for s in container.streams if s.type == "video"), None)
            if stream is None:
                return False
            stream.thread_type = "AUTO"
            target = max(0.0, float(seek_seconds))
            if target > 0 and stream.time_base is not None:
                offset = int(target / float(stream.time_base))
                try:
                    container.seek(offset, stream=stream, backward=True, any_frame=False)
                except Exception:
                    try:
                        container.seek(int(target / float(av.time_base)))
                    except Exception:
                        pass
            for frame in container.decode(stream):
                if frame is None:
                    continue
                return _save_rgb_frame(frame, out_path)
    except Exception:
        return False
    return False


def extract_cover(path: str, out_path: str) -> bool:
    """Pull embedded cover / attached pic (or first video frame) to JPEG."""
    ok, _ = available()
    if not ok or not path or not os.path.isfile(path):
        return False
    try:
        import av

        with av.open(path) as container:
            # Prefer attached_pic disposition streams
            pic_streams = []
            for s in container.streams:
                if s.type != "video":
                    continue
                disp = getattr(s, "disposition", None)
                attached = False
                if disp is not None:
                    attached = bool(getattr(disp, "attached_pic", False))
                if attached:
                    pic_streams.append(s)
            streams = pic_streams or [
                s for s in container.streams if s.type == "video"
            ]
            for stream in streams:
                try:
                    for packet in container.demux(stream):
                        for frame in packet.decode():
                            if _save_rgb_frame(frame, out_path):
                                return True
                except Exception:
                    continue
                # rewind for next candidate
                try:
                    container.seek(0)
                except Exception:
                    pass
    except Exception:
        return False
    return False


def decode_pcm_mono_f32(
    path: str,
    sample_rate: int = 8000,
    max_seconds: float = 900.0,
) -> bytes:
    """Decode mono float32 little-endian PCM (same layout as former ffmpeg CLI)."""
    ok, _ = available()
    if not ok or not path or not os.path.isfile(path):
        return b""
    try:
        import av
        import array

        chunks = array.array("f")
        max_samples = int(max(1.0, max_seconds) * sample_rate)
        with av.open(path) as container:
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is None:
                return b""
            resampler = av.AudioResampler(
                format="flt",
                layout="mono",
                rate=sample_rate,
            )
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    # to_ndarray needs numpy; plane bytes are interleaved float32
                    plane = bytes(out.planes[0])
                    # packed flt mono: 4 bytes per sample
                    n = len(plane) // 4
                    if n <= 0:
                        continue
                    part = array.array("f")
                    part.frombytes(plane[: n * 4])
                    remain = max_samples - len(chunks)
                    if remain <= 0:
                        break
                    if len(part) > remain:
                        chunks.extend(part[:remain])
                        break
                    chunks.extend(part)
                if len(chunks) >= max_samples:
                    break
            # flush resampler
            try:
                for out in resampler.resample(None):
                    plane = bytes(out.planes[0])
                    n = len(plane) // 4
                    if n <= 0:
                        continue
                    part = array.array("f")
                    part.frombytes(plane[: n * 4])
                    remain = max_samples - len(chunks)
                    if remain <= 0:
                        break
                    chunks.extend(part[:remain])
            except Exception:
                pass
        return chunks.tobytes() if chunks else b""
    except Exception:
        return b""
