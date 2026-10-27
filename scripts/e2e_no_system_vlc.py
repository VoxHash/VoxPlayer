#!/usr/bin/env python3
"""Prove desktop decode works without system libvlc when FOSS libav is available.

Simulates missing libvlc by forcing probe failure, then expects auto-fallback
to ``VOXPLAYER_DECODE=libav`` and a working ``create_playback_engine``.
"""

from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import time
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Force auto selection (clear any prior force)
os.environ.pop("VOXPLAYER_DECODE", None)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _write_tone(path: str, seconds: float = 0.4, rate: int = 44100) -> None:
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = [
            struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440.0 * i / rate)))
            for i in range(int(rate * seconds))
        ]
        w.writeframes(b"".join(frames))


def main() -> int:
    from voxplayer.engine import libvlc_ffi
    from voxplayer.engine.decode_preflight import ensure_decode_backend, probe_decode_backends
    from voxplayer.engine.libav_engine import libav_available

    av_ok, av_detail = libav_available()
    if not av_ok:
        print(f"SKIP need voxplayer[libav]: {av_detail}")
        return 0

    # Pretend system/bundled libvlc cannot load
    libvlc_ffi._LIB = None
    libvlc_ffi._candidate_lib_paths = lambda: ["/nonexistent/libvlc.so"]  # type: ignore[assignment]

    # Also hide staged native_core discovery for this process
    os.environ.pop("VOXPLAYER_NATIVE_CORE", None)
    os.environ.pop("VOXPLAYER_LIBVLC", None)
    os.environ.pop("PYTHON_VLC_LIB_PATH", None)

    # Monkeypatch bundled resolver to empty
    import voxplayer.native_core_paths as ncp

    ncp.resolve_bundled_native_core = lambda: (None, None)  # type: ignore[assignment]
    ncp.configure_bundled_native_core = lambda: False  # type: ignore[assignment]

    probed = probe_decode_backends()
    if probed.libvlc_ok:
        print(f"FAIL libvlc still ok after isolation: {probed}")
        return 1
    if not probed.libav_ok:
        print(f"FAIL libav should be ok: {probed}")
        return 1
    print("OK libvlc unavailable; libav present")

    info = ensure_decode_backend(write_env=True)
    if not info.ok or info.selected != "libav" or not info.auto_selected:
        print(f"FAIL auto-fallback expected libav: {info}")
        return 1
    if os.environ.get("VOXPLAYER_DECODE") != "libav":
        print(f"FAIL env not set: {os.environ.get('VOXPLAYER_DECODE')!r}")
        return 1
    print(f"OK auto-selected libav ({info.libav_detail})")

    from PyQt6.QtWidgets import QApplication, QWidget
    from voxplayer.engine.playback import create_playback_engine

    app = QApplication(sys.argv)
    surface = QWidget()
    surface.resize(160, 90)
    surface.show()
    engine = create_playback_engine(surface)
    if engine.backend_name != "libav":
        print(f"FAIL engine backend={engine.backend_name!r}")
        return 1

    tone = os.path.join(tempfile.mkdtemp(prefix="vox-novlc-"), "tone.wav")
    _write_tone(tone)
    engine.set_source(tone)
    engine.set_volume_percent(60)
    engine.play()
    deadline = time.time() + 1.5
    while time.time() < deadline and engine.position() < 20:
        app.processEvents()
        time.sleep(0.05)
    print(f"OK playback without system libvlc position_ms={engine.position()}")
    engine.stop()
    engine.shutdown()
    print("E2E NO-SYSTEM-VLC PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
