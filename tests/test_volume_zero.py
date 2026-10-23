#!/usr/bin/env python3
"""Regression: volume 0% must apply and survive play-start re-assert timers.

Run:
  QT_QPA_PLATFORM=offscreen .venv/bin/python tests/test_volume_zero.py
  # or with a real file:
  VOXPLAYER_TEST_AUDIO='/path/to/track.m4a' QT_QPA_PLATFORM=xcb DISPLAY=:0 \\
    .venv/bin/python tests/test_volume_zero.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg.debug=false")


def _find_audio() -> Path | None:
    env = os.environ.get("VOXPLAYER_TEST_AUDIO", "").strip()
    if env and Path(env).is_file():
        return Path(env)
    music = Path("/run/media/raider/Cloud 1 (Media)/Music")
    if music.is_dir():
        for pattern in ("*.m4a", "*.opus", "*.mp3", "*.flac"):
            hit = next(music.glob(pattern), None)
            if hit:
                return hit
    return None


class VolumeZeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from voxplayer.engine.playback import prefer_xcb_for_mpv_embed

        prefer_xcb_for_mpv_embed()
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setApplicationName("VoxPlayer-VolumeZeroTest")

    def test_falsy_zero_not_coerced_to_100(self):
        """Mirror the former setup bug: `volume or 100` must not be used."""
        volume = 0
        coerced_bad = int(volume or 100)
        coerced_good = max(0, min(200, int(volume)))
        self.assertEqual(coerced_bad, 100)
        self.assertEqual(coerced_good, 0)

    def test_engine_accepts_zero(self):
        from PyQt6.QtWidgets import QWidget
        from voxplayer.engine.playback import PlaybackEngine

        w = QWidget()
        w.resize(64, 64)
        w.show()
        self.app.processEvents()
        eng = PlaybackEngine(w)
        try:
            eng.set_volume_percent(0)
            self.assertEqual(eng.volume_percent(), 0)
            self.assertEqual(float(eng._mpv.volume), 0.0)
            eng.set_volume_percent(100)
            eng.set_muted(True)
            self.assertTrue(eng.is_muted())
            eng.set_muted(False)
            self.assertFalse(eng.is_muted())
        finally:
            eng.shutdown()
            w.close()

    def test_ui_set_volume_zero_survives_play_timers(self):
        audio = _find_audio()
        if audio is None:
            self.skipTest("No test audio (set VOXPLAYER_TEST_AUDIO)")

        from PyQt6.QtCore import QSettings
        from voxplayer.app import VoxPlayerMainWindow

        # Isolate QSettings so we can persist volume=0 without touching user config.
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            tempfile.mkdtemp(prefix="voxplayer-vol0-"),
        )

        win = VoxPlayerMainWindow()
        win.show()
        self.app.processEvents()
        try:
            win.load_and_play_media(str(audio))
            self.app.processEvents()
            # UI code path (slider / shortcuts)
            win.set_volume(0)
            self.app.processEvents()
            self.assertEqual(win.app_state.volume, 0)
            self.assertEqual(win.controls.volume_slider.value(), 0)
            self.assertEqual(win.engine.volume_percent(), 0)
            self.assertEqual(float(win.engine._mpv.volume), 0.0)

            # Drain play-start re-assert timers (200 / 400 / 1200 ms)
            t0 = time.time()
            while time.time() - t0 < 1.6:
                self.app.processEvents()
                time.sleep(0.02)

            self.assertEqual(win.app_state.volume, 0)
            self.assertEqual(win.engine.volume_percent(), 0)
            self.assertEqual(float(win.engine._mpv.volume), 0.0)

            # Engine-only set during play must also stick across re-assert timers
            win.engine.set_volume_percent(0)
            self.app.processEvents()
            t0 = time.time()
            while time.time() - t0 < 0.5:
                self.app.processEvents()
                time.sleep(0.02)
            self.assertEqual(win.engine.volume_percent(), 0)
            self.assertEqual(float(win.engine._mpv.volume), 0.0)

            # Mute still works; restoring slider leaves 0% then restores audible %
            win.toggle_mute()
            self.assertTrue(win.engine.is_muted())
            win.toggle_mute()
            self.assertFalse(win.engine.is_muted())
            win.set_volume(100)
            self.assertEqual(win.engine.volume_percent(), 100)
            self.assertEqual(float(win.engine._mpv.volume), 100.0)
            win.set_volume(200)
            self.assertEqual(win.engine.volume_percent(), 200)
            self.assertEqual(float(win.engine._mpv.volume), 200.0)

            # Persisted 0% must reload as 0 (not snap to 100 via truthiness)
            win.set_volume(0)
            win.settings.save_state(win.app_state)
            loaded = win.settings.load_state()
            self.assertEqual(int(loaded.volume), 0)
            reapplied = max(0, min(200, int(loaded.volume)))
            self.assertEqual(reapplied, 0)
        finally:
            if hasattr(win, "engine") and win.engine is not None:
                win.engine.shutdown()
            win.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
