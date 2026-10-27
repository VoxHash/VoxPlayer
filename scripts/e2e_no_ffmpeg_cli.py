#!/usr/bin/env python3
"""Prove meta/thumbs/viz work without ffmpeg/ffprobe CLI when FOSS libav is present."""

from __future__ import annotations

import math
import os
import shutil
import struct
import sys
import tempfile
import wave
from fractions import Fraction

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _hide_ffmpeg_cli() -> str:
    """Put a decoy bin dir first on PATH so ffmpeg/ffprobe resolve to missing stubs."""
    decoy = tempfile.mkdtemp(prefix="vox-no-ffmpeg-")
    for name in ("ffmpeg", "ffprobe"):
        stub = os.path.join(decoy, name)
        with open(stub, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho blocked >&2\nexit 127\n")
        os.chmod(stub, 0o755)
    os.environ["PATH"] = decoy + os.pathsep + os.environ.get("PATH", "")
    return decoy


def _write_tone(path: str, seconds: float = 0.5, rate: int = 44100) -> None:
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = [
            struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440.0 * i / rate)))
            for i in range(int(rate * seconds))
        ]
        w.writeframes(b"".join(frames))


def _write_clip(path: str) -> None:
    import av

    out = av.open(path, "w")
    stream = out.add_stream("libx264", rate=10)
    stream.width = 64
    stream.height = 48
    stream.pix_fmt = "yuv420p"
    stream.time_base = Fraction(1, 10)
    for i in range(12):
        frame = av.VideoFrame(64, 48, "rgb24")
        frame.planes[0].update(bytes([180, 60, 40]) * (64 * 48))
        frame.pts = i
        for packet in stream.encode(frame):
            out.mux(packet)
    for packet in stream.encode(None):
        out.mux(packet)
    out.close()


def main() -> int:
    from voxplayer.media import libav_io
    from voxplayer.media.metadata import load_local_metadata
    from voxplayer.media.thumbnails import ThumbnailCache
    from voxplayer.audio_viz import analyze_track

    ok, detail = libav_io.available()
    if not ok:
        print(f"SKIP need voxplayer[libav]: {detail}")
        return 0

    decoy = _hide_ffmpeg_cli()
    try:
        if shutil.which("ffmpeg") and os.path.dirname(shutil.which("ffmpeg") or "") != decoy:
            # which may still find real binary if decoy failed — force check
            pass
        which_ff = shutil.which("ffmpeg") or ""
        if which_ff and os.path.dirname(which_ff) != decoy:
            print(f"FAIL decoy PATH not first: {which_ff}")
            return 1
        # Real CLI must not succeed
        import subprocess

        bad = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if bad.returncode == 0:
            print("FAIL ffmpeg still runnable")
            return 1
        print("OK ffmpeg/ffprobe CLI blocked")

        with tempfile.TemporaryDirectory(prefix="vox-e2e-meta-") as td:
            wav = os.path.join(td, "tone.wav")
            mp4 = os.path.join(td, "clip.mp4")
            _write_tone(wav)
            _write_clip(mp4)

            meta = load_local_metadata(wav)
            if not meta.path:
                print("FAIL metadata empty path")
                return 1
            print(f"OK local metadata without ffprobe (title={meta.display_title()!r})")

            cache = ThumbnailCache()
            # use isolated cache via monkeypatch of root — path_for still uses home cache;
            # ensure generates under ~/.cache; assert file exists
            thumb = cache.ensure(mp4, seek_seconds=0.2)
            if not thumb or not os.path.isfile(thumb) or os.path.getsize(thumb) < 100:
                print(f"FAIL thumb without ffmpeg: {thumb!r}")
                return 1
            print(f"OK poster frame without ffmpeg ({os.path.getsize(thumb)} bytes)")

            viz = analyze_track(wav, buckets=32, sample_rate=8000)
            if not viz.ok or len(viz.peaks) < 8:
                print(f"FAIL viz without ffmpeg: ok={viz.ok} peaks={len(viz.peaks)}")
                return 1
            print(f"OK spectrum PCM without ffmpeg (peaks={len(viz.peaks)})")

        print("E2E NO-FFMPEG-CLI PASS")
        return 0
    finally:
        shutil.rmtree(decoy, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
