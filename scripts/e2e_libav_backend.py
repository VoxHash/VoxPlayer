#!/usr/bin/env python3
"""E2E: FOSS libav backend (VOXPLAYER_DECODE=libav) play/pause/seek/volume on a tone."""

from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import time
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["VOXPLAYER_DECODE"] = "libav"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _write_tone(path: str, seconds: float = 0.8, rate: int = 44100) -> None:
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = []
        for i in range(int(rate * seconds)):
            sample = int(12000 * math.sin(2 * math.pi * 440.0 * i / rate))
            frames.append(struct.pack("<h", sample))
        w.writeframes(b"".join(frames))


def main() -> int:
    from PyQt6.QtWidgets import QApplication, QWidget

    from voxplayer.engine.libav_engine import libav_available
    from voxplayer.engine.playback import create_playback_engine, resolve_decode_backend

    ok, detail = libav_available()
    if not ok:
        print(f"SKIP libav backend (install voxplayer[libav]): {detail}")
        return 0

    if resolve_decode_backend() != "libav":
        print("FAIL VOXPLAYER_DECODE did not resolve to libav")
        return 1

    app = QApplication(sys.argv)
    surface = QWidget()
    surface.resize(320, 180)
    surface.show()

    engine = create_playback_engine(surface)
    if engine.backend_name != "libav":
        print(f"FAIL backend_name={engine.backend_name!r}")
        return 1
    print(f"OK backend={engine.backend_name}")

    tone = os.path.join(tempfile.mkdtemp(prefix="vox-libav-"), "tone.wav")
    _write_tone(tone)

    states = []
    engine.state_changed.connect(lambda s: states.append(s))
    engine.set_volume_percent(80)
    engine.set_source(tone)
    app.processEvents()
    time.sleep(0.15)
    engine.play()
    deadline = time.time() + 2.0
    while time.time() < deadline and engine.position() < 50:
        app.processEvents()
        time.sleep(0.05)
    pos1 = engine.position()
    print(f"OK playing position_ms={pos1} duration_ms={engine.duration()}")
    if engine.duration() <= 0:
        print("FAIL duration not reported")
        return 1

    engine.set_position(200, exact=True)
    time.sleep(0.1)
    app.processEvents()
    engine.pause()
    app.processEvents()
    if not engine.is_muted():
        engine.set_muted(True)
        engine.set_muted(False)
    engine.set_volume_percent(150)
    if engine.volume_percent() != 150:
        print(f"FAIL volume={engine.volume_percent()}")
        return 1
    print("OK seek/pause/volume 0–200")

    engine.stop()
    engine.shutdown()
    print("E2E LIBAV BACKEND PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
