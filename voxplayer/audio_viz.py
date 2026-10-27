"""Real PCM-based waveform / spectrum helpers for transport chrome.

Decodes a short mono float stream via linked FOSS libav (PyAV), with ``ffmpeg``
CLI as fallback — same toolchain preference as thumbnails. No second playback
engine; viz is offline analysis of the current file around the playhead.
"""

from __future__ import annotations

import math
import os
import struct
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from voxplayer.media import libav_io


@dataclass
class TrackVizData:
    path: str
    peaks: List[float] = field(default_factory=list)  # 0..1 envelope for waveform
    samples: List[float] = field(default_factory=list)  # downsampled mono PCM for spectrum
    sample_rate: int = 8000
    ok: bool = False


_cache: Dict[str, TrackVizData] = {}
_lock = threading.Lock()
_inflight: Dict[str, threading.Thread] = {}


def _ffmpeg_pcm(path: str, sample_rate: int = 8000, max_seconds: float = 900.0) -> bytes:
    linked = libav_io.decode_pcm_mono_f32(path, sample_rate=sample_rate, max_seconds=max_seconds)
    if linked:
        return linked
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        path,
        "-t",
        str(max_seconds),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        return b""
    return proc.stdout or b""


def _bytes_to_floats(raw: bytes) -> List[float]:
    if len(raw) < 4:
        return []
    n = len(raw) // 4
    return list(struct.unpack("<" + "f" * n, raw[: n * 4]))


def _peaks_from_samples(samples: List[float], buckets: int = 256) -> List[float]:
    if not samples or buckets <= 0:
        return []
    n = len(samples)
    out: List[float] = []
    for i in range(buckets):
        a = int(i * n / buckets)
        b = int((i + 1) * n / buckets)
        if b <= a:
            b = min(n, a + 1)
        chunk = samples[a:b]
        peak = max(abs(x) for x in chunk) if chunk else 0.0
        out.append(peak)
    mx = max(out) if out else 0.0
    if mx > 1e-9:
        out = [min(1.0, p / mx) for p in out]
    return out


def analyze_track(path: str, *, buckets: int = 256, sample_rate: int = 8000) -> TrackVizData:
    """Synchronously decode and build viz data for ``path``."""
    path = os.path.abspath(path) if path else ""
    data = TrackVizData(path=path)
    if not path or not os.path.isfile(path):
        return data
    try:
        raw = _ffmpeg_pcm(path, sample_rate=sample_rate)
    except (OSError, subprocess.TimeoutExpired):
        return data
    samples = _bytes_to_floats(raw)
    if not samples:
        return data
    # Cap stored PCM for spectrum windows (~45s at 8kHz keeps memory reasonable)
    max_keep = sample_rate * 45
    if len(samples) > max_keep:
        step = len(samples) / max_keep
        samples = [samples[int(i * step)] for i in range(max_keep)]
    data.samples = samples
    data.sample_rate = sample_rate
    data.peaks = _peaks_from_samples(samples, buckets=buckets)
    data.ok = bool(data.peaks)
    return data


def get_cached(path: str) -> Optional[TrackVizData]:
    if not path:
        return None
    key = os.path.abspath(path)
    with _lock:
        return _cache.get(key)


def analyze_track_async(
    path: str,
    on_done: Optional[Callable[[TrackVizData], None]] = None,
    *,
    buckets: int = 256,
) -> None:
    """Background analyze; ``on_done`` invoked from the worker thread."""
    if not path or not os.path.isfile(path):
        return
    key = os.path.abspath(path)
    with _lock:
        if key in _cache and _cache[key].ok:
            cached = _cache[key]
            if on_done:
                on_done(cached)
            return
        if key in _inflight and _inflight[key].is_alive():
            return

        def _run() -> None:
            data = analyze_track(key, buckets=buckets)
            with _lock:
                _cache[key] = data
                _inflight.pop(key, None)
            if on_done:
                on_done(data)

        t = threading.Thread(target=_run, name="vox-audio-viz", daemon=True)
        _inflight[key] = t
        t.start()


def spectrum_bands(
    data: TrackVizData,
    position_ms: int,
    duration_ms: int,
    *,
    n_bands: int = 32,
    window_ms: int = 80,
) -> List[float]:
    """
    Real spectrum-ish bands from PCM around the playhead.

    Uses banded RMS of a short window (no numpy). Returns ``n_bands`` values in 0..1.
    """
    if not data.ok or not data.samples or n_bands <= 0:
        return [0.0] * max(1, n_bands)
    n = len(data.samples)
    if duration_ms <= 0:
        center = 0
    else:
        ratio = max(0.0, min(1.0, float(position_ms) / float(duration_ms)))
        center = int(ratio * (n - 1))
    win = max(32, int(data.sample_rate * (window_ms / 1000.0)))
    a = max(0, center - win // 2)
    b = min(n, a + win)
    a = max(0, b - win)
    window = data.samples[a:b]
    if not window:
        return [0.0] * n_bands
    bands: List[float] = []
    for i in range(n_bands):
        s = int(i * len(window) / n_bands)
        e = int((i + 1) * len(window) / n_bands)
        chunk = window[s:e] or [0.0]
        acc = sum(x * x for x in chunk) / len(chunk)
        bands.append(math.sqrt(acc))
    mx = max(bands) if bands else 0.0
    if mx > 1e-9:
        # Mild boost so quiet passages still move
        bands = [min(1.0, (v / mx) ** 0.7) for v in bands]
    return bands


def waveform_slice(data: TrackVizData, width: int) -> List[float]:
    """Resample cached peaks to ``width`` columns for painting."""
    if not data.ok or not data.peaks or width <= 0:
        return []
    peaks = data.peaks
    if width == len(peaks):
        return list(peaks)
    out: List[float] = []
    for i in range(width):
        a = int(i * len(peaks) / width)
        b = int((i + 1) * len(peaks) / width)
        chunk = peaks[a:max(a + 1, b)]
        out.append(max(chunk) if chunk else 0.0)
    return out
