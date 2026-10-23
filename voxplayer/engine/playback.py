"""
Playback engine: libmpv preferred (0–200% volume), Qt Multimedia fallback.

Default experience uses libmpv whenever python-mpv + system libmpv are available.
Qt remains a fallback; volume >100% on Qt still tries PipeWire/Pulse gain.
"""

from __future__ import annotations

import os
import subprocess
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import QWidget


class BackendKind(str, Enum):
    QT = "qt"
    MPV = "mpv"


def prefer_xcb_for_mpv_embed() -> None:
    """Prefer X11/XWayland so libmpv WID embedding works under Wayland sessions."""
    if os.getenv("VOXPLAYER_FORCE_WAYLAND", "").strip() in {"1", "true", "yes"}:
        return
    if os.getenv("DISPLAY") and not os.getenv("VOXPLAYER_KEEP_QPA"):
        # Only set if unset so user override wins
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


class PlaybackEngine(QObject):
    """Unified play/pause/seek/volume API over Qt or libmpv."""

    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms
    state_changed = pyqtSignal(str)  # playing|paused|stopped
    error_occurred = pyqtSignal(str)
    backend_ready = pyqtSignal(str)

    def __init__(self, video_widget: QWidget, parent=None):
        super().__init__(parent)
        self.video_widget = video_widget
        self.backend = BackendKind.QT
        self._mpv = None
        self._source_path = ""
        self._duration_ms = 0
        self._muted = False
        self._volume_pct = 100  # 0..200 logical
        self._mpv_poll = None
        self._mpv_video_bound = False

        # Hint Qt FFmpeg path toward hardware decode on Linux when available.
        os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "vaapi,cuda,vdpau,d3d11va")

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(video_widget)

        self.media_player.positionChanged.connect(self.position_changed.emit)
        self.media_player.durationChanged.connect(self._on_qt_duration)
        self.media_player.playbackStateChanged.connect(self._on_qt_state)
        self.media_player.errorOccurred.connect(self._on_qt_error)

        if self._try_init_mpv():
            self.backend = BackendKind.MPV
            self.backend_ready.emit("mpv")
        else:
            self.backend_ready.emit("qt")

    def _try_init_mpv(self) -> bool:
        """Prefer libmpv whenever available; embed into video widget when possible."""
        force_qt = os.getenv("VOXPLAYER_FORCE_QT", "").strip() in {"1", "true", "yes"}
        if force_qt:
            return False
        prefer = os.getenv("VOXPLAYER_ENGINE", "mpv").strip().lower()
        if prefer == "qt":
            return False
        # auto / mpv / empty → try mpv first
        try:
            import mpv  # noqa: WPS433
        except ImportError:
            return False

        # Attempt WID embed (works on X11 and typically XWayland).
        try:
            self.video_widget.setAttribute(
                __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.WidgetAttribute.WA_NativeWindow, True
            )
            wid = int(self.video_widget.winId())
            player = mpv.MPV(
                wid=str(wid),
                vo="gpu",
                hwdec="auto-safe",
                keep_open="yes",
                idle="yes",
                input_default_bindings=False,
                input_vo_keyboard=False,
                osc=False,
                osd_level=0,
                volume=100,
                volume_max=200,
            )
            self._mpv = player
            self._mpv_video_bound = True
            self._start_mpv_poll()
            return True
        except Exception:
            self._mpv = None
            self._mpv_video_bound = False

        # Headless / audio-first mpv — still gives reliable 0–200% volume.
        # Video frames are not embedded; shell uses posters / Qt stage as needed.
        try:
            import mpv  # noqa: WPS433

            player = mpv.MPV(
                vo="null",
                video="no",
                keep_open="yes",
                idle="yes",
                input_default_bindings=False,
                osc=False,
                osd_level=0,
                volume=100,
                volume_max=200,
            )
            self._mpv = player
            self._mpv_video_bound = False
            self._start_mpv_poll()
            return True
        except Exception:
            self._mpv = None
            return False

    def _start_mpv_poll(self) -> None:
        self._mpv_poll = QTimer(self)
        self._mpv_poll.setInterval(100)
        self._mpv_poll.timeout.connect(self._poll_mpv)
        self._mpv_poll.start()

    def rebind_video_widget(self) -> bool:
        """Re-attempt WID embed after the stage becomes visible (X11/XWayland)."""
        if self.backend != BackendKind.MPV or self._mpv is None:
            return False
        if self._mpv_video_bound:
            return True
        try:
            import mpv  # noqa: WPS433

            path = self._source_path
            pos = self.position()
            was_playing = self.is_playing()
            vol = self._volume_pct
            try:
                self._mpv.terminate()
            except Exception:
                pass
            self.video_widget.setAttribute(
                __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.WidgetAttribute.WA_NativeWindow, True
            )
            wid = int(self.video_widget.winId())
            player = mpv.MPV(
                wid=str(wid),
                vo="gpu",
                hwdec="auto-safe",
                keep_open="yes",
                idle="yes",
                input_default_bindings=False,
                input_vo_keyboard=False,
                osc=False,
                osd_level=0,
                volume=float(vol),
                volume_max=200,
            )
            self._mpv = player
            self._mpv_video_bound = True
            if path:
                player.play(path)
                if pos:
                    try:
                        player.seek(pos / 1000.0, reference="absolute")
                    except Exception:
                        pass
                player.pause = not was_playing
            return True
        except Exception:
            return False

    @property
    def backend_name(self) -> str:
        return self.backend.value

    @property
    def has_embedded_video(self) -> bool:
        return bool(self._mpv_video_bound and self.backend == BackendKind.MPV)

    def set_source(self, file_path: str) -> None:
        self._source_path = file_path
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                self._mpv.play(file_path)
                self._mpv.pause = True
                self.set_volume_percent(self._volume_pct)
                return
            except Exception as exc:
                self.error_occurred.emit(f"Native engine load failed, falling back: {exc}")
                self._fallback_to_qt()
        url = QUrl(file_path) if file_path.startswith(("http://", "https://")) else QUrl.fromLocalFile(file_path)
        self.media_player.setSource(url)

    def _fallback_to_qt(self) -> None:
        self.backend = BackendKind.QT
        if self._mpv_poll:
            self._mpv_poll.stop()
        if self._mpv is not None:
            try:
                self._mpv.terminate()
            except Exception:
                pass
        self._mpv = None
        self._mpv_video_bound = False
        if self._source_path:
            url = QUrl.fromLocalFile(self._source_path)
            self.media_player.setSource(url)
        self.backend_ready.emit("qt")

    def play(self) -> None:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            self._mpv.pause = False
            self.state_changed.emit("playing")
            return
        self.media_player.play()

    def pause(self) -> None:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            self._mpv.pause = True
            self.state_changed.emit("paused")
            return
        self.media_player.pause()

    def stop(self) -> None:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            self._mpv.command("stop")
            self.state_changed.emit("stopped")
            return
        self.media_player.stop()

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def is_playing(self) -> bool:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                return not bool(self._mpv.pause) and self._mpv.path is not None
            except Exception:
                return False
        return self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def position(self) -> int:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                t = self._mpv.time_pos
                return int((t or 0) * 1000)
            except Exception:
                return 0
        return int(self.media_player.position())

    def duration(self) -> int:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                d = self._mpv.duration
                if d:
                    self._duration_ms = int(d * 1000)
            except Exception:
                pass
            return self._duration_ms
        return int(self.media_player.duration())

    def set_position(self, ms: int) -> None:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                self._mpv.seek(ms / 1000.0, reference="absolute")
            except Exception:
                pass
            return
        self.media_player.setPosition(int(ms))

    def seek_relative(self, seconds: float) -> None:
        self.set_position(max(0, self.position() + int(seconds * 1000)))

    def volume_percent(self) -> int:
        """Logical user volume 0..200 (not Qt's clamped 0..100)."""
        return int(self._volume_pct)

    def set_volume_percent(self, volume: int) -> None:
        """0..200 logical volume with real audible gain on both engines.

        - libmpv: native ``volume`` / ``volume-max`` (0..200).
        - Qt Multimedia: ``QAudioOutput`` 0..1 for ≤100%; >100% uses Pulse/PipeWire.
        """
        volume = max(0, min(200, int(volume)))
        self._volume_pct = volume
        gain = volume / 100.0
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                self._mpv.volume_max = 200
                self._mpv.volume = float(volume)
            except Exception:
                try:
                    self._mpv.volume = float(volume)
                except Exception:
                    pass
            try:
                self.audio_output.setVolume(0.0)
            except Exception:
                pass
            self._apply_pulse_stream_volume(100)
            return

        qt_vol = min(1.0, gain)
        self.audio_output.setVolume(qt_vol)
        self._apply_pulse_stream_volume(volume if volume > 100 else 100)

    def _apply_pulse_stream_volume(self, percent: int) -> None:
        """Set this process's sink-input volume (100 = unity, 200 = +6 dB linear)."""
        percent = max(0, min(200, int(percent)))
        pa_vol = int(65536 * (percent / 100.0))
        pid = os.getpid()
        try:
            list_proc = subprocess.run(
                ["pactl", "list", "sink-inputs"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if list_proc.returncode != 0 or not list_proc.stdout:
                return
            current_id = None
            matched_ids = []
            for line in list_proc.stdout.splitlines():
                if line.startswith("Sink Input #"):
                    current_id = line.split("#", 1)[1].strip()
                elif "application.process.id" in line or "application.process.id =" in line:
                    if str(pid) in line and current_id is not None:
                        matched_ids.append(current_id)
            for sink_id in matched_ids:
                subprocess.run(
                    ["pactl", "set-sink-input-volume", sink_id, str(pa_vol)],
                    capture_output=True,
                    timeout=2,
                )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                self._mpv.mute = self._muted
            except Exception:
                pass
        self.audio_output.setMuted(self._muted)

    def is_muted(self) -> bool:
        if self.backend == BackendKind.MPV and self._mpv is not None:
            try:
                return bool(self._mpv.mute)
            except Exception:
                pass
        return bool(self.audio_output.isMuted())

    def source_path(self) -> str:
        return self._source_path

    def _on_qt_duration(self, duration: int) -> None:
        self._duration_ms = int(duration)
        self.duration_changed.emit(int(duration))

    def _on_qt_state(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.state_changed.emit("playing")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.state_changed.emit("paused")
        else:
            self.state_changed.emit("stopped")

    def _on_qt_error(self, _error, error_string: str) -> None:
        if not error_string:
            return
        if "pts == AV_NOPTS_VALUE" in error_string or "Unknown property transform" in error_string:
            return
        self.error_occurred.emit(error_string)

    def _poll_mpv(self) -> None:
        if self.backend != BackendKind.MPV or self._mpv is None:
            return
        try:
            self.position_changed.emit(self.position())
            dur = self.duration()
            if dur:
                self.duration_changed.emit(dur)
            # Detect natural end → stopped
            try:
                eof = bool(getattr(self._mpv, "eof_reached", False))
                if eof and not self.is_playing():
                    self.state_changed.emit("stopped")
            except Exception:
                pass
        except Exception:
            pass

    def shutdown(self) -> None:
        if self._mpv_poll:
            self._mpv_poll.stop()
        if self._mpv is not None:
            try:
                self._mpv.terminate()
            except Exception:
                pass
            self._mpv = None
