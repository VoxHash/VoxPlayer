"""Cross-platform codec fixture matrix (H.264 / HEVC / AV1 / Opus).

Generates tiny decode samples via linked FOSS encoders (PyAV → libav) and
probes whether Desktop FOSS decode can open them. Policy: wrap maintained
FOSS — never invent in-tree x264/x265.

Android / Quest coverage lives in ``CodecFixtureMatrix.kt`` (MediaCodec probe);
this module is the desktop + CI half.
"""

from __future__ import annotations

import array
import math
import os
import tempfile
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

from .codecs import FOCUS_CODECS

# Encoder candidates (first available wins). Decode uses whatever FOSS decoder PyAV links.
_ENCODERS: Dict[str, Tuple[str, ...]] = {
    "h264": ("libx264", "h264"),
    "hevc": ("libx265", "hevc"),
    "av1": ("libsvtav1", "libaom-av1", "av1"),
    "opus": ("libopus", "opus"),
}

_FIXTURE_NAMES = {
    "h264": "fixture_h264.mp4",
    "hevc": "fixture_hevc.mp4",
    "av1": "fixture_av1.mp4",
    "opus": "fixture_opus.ogg",
}


@dataclass
class FixtureResult:
    codec: str
    path: str = ""
    encoded: bool = False
    decoded: bool = False
    encoder: str = ""
    decoder: str = ""
    size_bytes: int = 0
    frames: int = 0
    error: str = ""
    skipped: bool = False

    def status(self) -> str:
        if self.skipped:
            return "SKIP"
        if self.encoded and self.decoded:
            return "PASS"
        if self.encoded and not self.decoded:
            return "FAIL"
        return "SKIP"


@dataclass
class FixtureMatrixReport:
    results: Dict[str, FixtureResult] = field(default_factory=dict)
    root: str = ""
    backend: str = "libav"

    def summary_lines(self) -> List[str]:
        lines = [
            "Codec fixture matrix (Desktop FOSS decode)",
            f"Backend: {self.backend}",
            f"Fixtures: {self.root or '(temp)'}",
            "",
            "Policy: wrap FOSS (libav/dav1d/MediaCodec) — do not invent in-tree x264/x265.",
            "",
        ]
        for key in FOCUS_CODECS:
            r = self.results.get(key) or FixtureResult(codec=key, skipped=True, error="missing")
            detail = ""
            if r.skipped and r.error:
                detail = f" — {r.error}"
            elif r.encoded:
                detail = f" — enc={r.encoder or '?'} dec={r.decoder or '?'} frames={r.frames} ({r.size_bytes} B)"
                if r.error:
                    detail += f" err={r.error}"
            lines.append(f"  [{r.status()}] {key.upper()}{detail}")
        lines.append("")
        lines.append(
            "Android/Quest: device MediaCodec probe (see CodecFixtureMatrix / "
            "docs/codec_fixture_matrix.md) — GrapheneOS-honest, per-device."
        )
        return lines

    def required_ok(self) -> bool:
        """H.264 + Opus must encode+decode when PyAV is present; HEVC/AV1 soft."""
        h = self.results.get("h264")
        o = self.results.get("opus")
        return bool(h and h.decoded and o and o.decoded)


def _av_available() -> Tuple[bool, str]:
    try:
        import av  # noqa: F401
    except Exception as exc:
        return False, str(exc)
    return True, "PyAV"


def _pick_encoder(codec_key: str) -> Optional[str]:
    import av

    for name in _ENCODERS.get(codec_key, ()):
        try:
            av.Codec(name, "w")
            return name
        except Exception:
            continue
    return None


def default_fixture_root() -> str:
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    root = os.path.join(here, "fixtures", "codecs")
    os.makedirs(root, exist_ok=True)
    return root


def _rgb_frame(w: int, h: int, r: int, g: int, b: int, pts: int):
    import av

    frame = av.VideoFrame(w, h, "rgb24")
    frame.planes[0].update(bytes([r & 255, g & 255, b & 255]) * (w * h))
    frame.pts = pts
    return frame


def _encode_video(path: str, encoder: str, *, frames: int = 6, w: int = 64, h: int = 48) -> None:
    import av

    # AV1 SVT prefers slightly larger than 32x32
    if "svt" in encoder or encoder in {"av1", "libaom-av1"}:
        w, h = max(w, 64), max(h, 64)

    out = av.open(path, "w")
    stream = out.add_stream(encoder, rate=10)
    stream.width = w
    stream.height = h
    stream.pix_fmt = "yuv420p"
    stream.time_base = Fraction(1, 10)
    if encoder in {"libx264", "h264"}:
        stream.options = {"preset": "ultrafast", "tune": "zerolatency"}
    elif encoder in {"libx265", "hevc"}:
        stream.options = {"preset": "ultrafast", "x265-params": "log-level=error"}
    elif "svt" in encoder:
        stream.options = {"preset": "10"}

    for i in range(frames):
        frame = _rgb_frame(w, h, 40 + i * 20, 90, 160 - i * 10, i)
        for packet in stream.encode(frame):
            out.mux(packet)
    for packet in stream.encode(None):
        out.mux(packet)
    out.close()


def _encode_opus(path: str, encoder: str, *, seconds: float = 0.4) -> None:
    import av

    rate = 48000
    frame_samples = 960  # 20 ms
    out = av.open(path, "w")
    stream = out.add_stream(encoder, rate=rate)
    stream.layout = "mono"
    total = int(rate * seconds)
    pts = 0
    for start in range(0, total, frame_samples):
        n = min(frame_samples, total - start)
        if n < frame_samples:
            # pad last frame to opus frame size
            n = frame_samples
        frame = av.AudioFrame(format="s16", layout="mono", samples=n)
        frame.sample_rate = rate
        frame.pts = pts
        buf = array.array(
            "h",
            [
                int(9000 * math.sin(2 * math.pi * 440.0 * (start + i) / rate))
                for i in range(n)
            ],
        )
        frame.planes[0].update(buf.tobytes())
        for packet in stream.encode(frame):
            out.mux(packet)
        pts += n
    for packet in stream.encode(None):
        out.mux(packet)
    out.close()


def generate_fixture(codec: str, dest_dir: str) -> FixtureResult:
    """Encode one focus-codec fixture into ``dest_dir``."""
    result = FixtureResult(codec=codec)
    ok, detail = _av_available()
    if not ok:
        result.skipped = True
        result.error = f"PyAV unavailable: {detail}"
        return result

    encoder = _pick_encoder(codec)
    if not encoder:
        result.skipped = True
        result.error = f"no FOSS encoder on host for {codec}"
        return result

    name = _FIXTURE_NAMES.get(codec, f"fixture_{codec}.bin")
    path = os.path.join(dest_dir, name)
    try:
        if codec == "opus":
            _encode_opus(path, encoder)
        else:
            _encode_video(path, encoder)
        result.path = path
        result.encoded = True
        result.encoder = encoder
        result.size_bytes = os.path.getsize(path) if os.path.isfile(path) else 0
    except Exception as exc:
        result.error = f"encode failed: {exc}"
        result.skipped = True
    return result


def decode_fixture(path: str, expect: str) -> Tuple[bool, str, int]:
    """Decode at least one frame/packet; return (ok, decoder_name, frame_count)."""
    ok, detail = _av_available()
    if not ok:
        return False, "", 0
    try:
        import av

        with av.open(path) as container:
            if expect == "opus":
                stream = next((s for s in container.streams if s.type == "audio"), None)
            else:
                stream = next((s for s in container.streams if s.type == "video"), None)
            if stream is None:
                return False, "", 0
            decoder = getattr(getattr(stream, "codec_context", None), "name", None) or getattr(
                stream.codec, "name", "?"
            )
            # Prefer reported codec name matching focus key
            codec_name = getattr(stream.codec, "name", decoder) or decoder
            count = 0
            for _frame in container.decode(stream):
                count += 1
                if count >= 1:
                    break
            return count > 0, str(codec_name), count
    except Exception:
        return False, "", 0


def run_fixture_matrix(
    root: Optional[str] = None,
    codecs: Optional[Sequence[str]] = None,
) -> FixtureMatrixReport:
    """Generate + FOSS-decode fixtures for each focus codec."""
    dest = root or tempfile.mkdtemp(prefix="vox-codec-fixtures-")
    os.makedirs(dest, exist_ok=True)
    report = FixtureMatrixReport(root=dest, backend="libav (PyAV)")
    ok, detail = _av_available()
    if not ok:
        for key in FOCUS_CODECS:
            report.results[key] = FixtureResult(
                codec=key, skipped=True, error=f"PyAV unavailable: {detail}"
            )
        return report

    for key in codecs or FOCUS_CODECS:
        result = generate_fixture(key, dest)
        if result.encoded and result.path:
            decoded, dec_name, frames = decode_fixture(result.path, key)
            result.decoded = decoded
            result.decoder = dec_name
            result.frames = frames
            if not decoded and not result.error:
                result.error = "decode produced no frames"
        report.results[key] = result
    return report


def ensure_repo_fixtures(root: Optional[str] = None) -> FixtureMatrixReport:
    """Write fixtures under ``fixtures/codecs/`` (repo tree) and verify decode."""
    return run_fixture_matrix(root=root or default_fixture_root())
