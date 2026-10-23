"""
Playback engine: libmpv only (0–200% volume, native mute).

PyQt6 remains the UI shell. There is no Qt Multimedia playback path —
if python-mpv or system libmpv is missing, startup fails with an install hint.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QMessageBox


class BackendKind(str, Enum):
    MPV = "mpv"


class NativeEngineError(RuntimeError):
    """Raised when libmpv / python-mpv cannot be initialized."""


def prefer_xcb_for_mpv_embed() -> None:
    """Prefer X11/XWayland so libmpv WID embedding works under Wayland sessions."""
    if os.getenv("VOXPLAYER_FORCE_WAYLAND", "").strip() in {"1", "true", "yes"}:
        return
    if os.getenv("DISPLAY") and not os.getenv("VOXPLAYER_KEEP_QPA"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


def native_engine_install_hint() -> str:
    """Cross-platform install guidance for libmpv + python-mpv."""
    lines = [
        "VoxPlayer requires the native libmpv engine (python-mpv + system libmpv).",
        "Qt Multimedia is not used for playback.",
        "",
        "Install steps:",
        "  • Python binding:  pip install python-mpv",
        "  • Or project venv: .venv/bin/pip install -r requirements.txt",
        "  • Then launch:     python run.py   (or: .venv/bin/python run.py)",
        "",
        "System libmpv:",
        "  • Arch / Manjaro:     sudo pacman -S mpv",
        "  • Debian / Ubuntu:    sudo apt install libmpv2  # or libmpv1 on older releases",
        "  • Fedora:             sudo dnf install mpv-libs",
        "  • macOS (Homebrew):   brew install mpv",
        "  • Windows:            install mpv / libmpv and ensure mpv-2.dll is on PATH",
        "                        ",
        "",
        "Wayland note: prefer X11/XWayland for embedded video (DISPLAY set).",
        "On pure Wayland, audio volume still works; video embed may be limited.",
    ]
    return "\n".join(lines)


def require_mpv_module():
    """Import python-mpv or raise NativeEngineError with install text."""
    try:
        import mpv  # noqa: WPS433

        return mpv
    except ImportError as exc:
        raise NativeEngineError(native_engine_install_hint()) from exc


class PlaybackEngine(QObject):
    """Play/pause/seek/volume API backed exclusively by libmpv."""

    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms
    state_changed = pyqtSignal(str)  # playing|paused|stopped
    error_occurred = pyqtSignal(str)
    backend_ready = pyqtSignal(str)

    def __init__(self, video_widget: QWidget, parent=None):
        super().__init__(parent)
        self.video_widget = video_widget
        self.backend = BackendKind.MPV
        self._mpv = None
        self._source_path = ""
        self._duration_ms = 0
        self._muted = False
        self._volume_pct = 100  # 0..200 logical
        self._mpv_poll = None
        self._mpv_video_bound = False

        # Compatibility aliases — UI historically touched these; they are unused for audio.
        self.media_player = None
        self.audio_output = None

        if not self._try_init_mpv():
            raise NativeEngineError(native_engine_install_hint())
        self.backend_ready.emit("mpv")

    def _try_init_mpv(self) -> bool:
        """Initialize libmpv with WID embed when possible; audio-only otherwise."""
        try:
            mpv = require_mpv_module()
        except NativeEngineError:
            return False

        # Attempt WID embed (works on X11 and typically XWayland).
        try:
            from PyQt6.QtCore import Qt as _Qt

            self.video_widget.setAttribute(_Qt.WidgetAttribute.WA_NativeWindow, True)
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

        # Audio-first mpv — reliable 0–200% volume when embed is unavailable
        # (pure Wayland, headless, or WID failure). Video frames are not embedded.
        try:
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
        if self._mpv is None:
            return False
        if self._mpv_video_bound:
            return True
        try:
            mpv = require_mpv_module()
            path = self._source_path
            pos = self.position()
            was_playing = self.is_playing()
            vol = self._volume_pct
            muted = self._muted
            try:
                self._mpv.terminate()
            except Exception:
                pass
            from PyQt6.QtCore import Qt as _Qt

            self.video_widget.setAttribute(_Qt.WidgetAttribute.WA_NativeWindow, True)
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
            try:
                player.mute = bool(muted)
            except Exception:
                pass
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
        return bool(self._mpv_video_bound)

    def set_source(self, file_path: str) -> None:
        self._source_path = file_path
        if self._mpv is None:
            self.error_occurred.emit("Native engine not initialized")
            return
        try:
            self._mpv.play(file_path)
            self._mpv.pause = True
            self.set_volume_percent(self._volume_pct)
            self.set_muted(self._muted)
        except Exception as exc:
            self.error_occurred.emit(f"Native engine load failed: {exc}")

    def play(self) -> None:
        if self._mpv is None:
            return
        self._mpv.pause = False
        self.state_changed.emit("playing")

    def pause(self) -> None:
        if self._mpv is None:
            return
        self._mpv.pause = True
        self.state_changed.emit("paused")

    def stop(self) -> None:
        if self._mpv is None:
            return
        self._mpv.command("stop")
        self.state_changed.emit("stopped")

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def is_playing(self) -> bool:
        if self._mpv is None:
            return False
        try:
            return not bool(self._mpv.pause) and self._mpv.path is not None
        except Exception:
            return False

    def position(self) -> int:
        if self._mpv is None:
            return 0
        try:
            t = self._mpv.time_pos
            return int((t or 0) * 1000)
        except Exception:
            return 0

    def duration(self) -> int:
        if self._mpv is None:
            return self._duration_ms
        try:
            d = self._mpv.duration
            if d:
                self._duration_ms = int(d * 1000)
        except Exception:
            pass
        return self._duration_ms

    def set_position(self, ms: int) -> None:
        if self._mpv is None:
            return
        try:
            self._mpv.seek(ms / 1000.0, reference="absolute")
        except Exception:
            pass

    def seek_relative(self, seconds: float) -> None:
        self.set_position(max(0, self.position() + int(seconds * 1000)))

    def volume_percent(self) -> int:
        """Logical user volume 0..200."""
        return int(self._volume_pct)

    def set_volume_percent(self, volume: int) -> None:
        """0..200 logical volume via libmpv ``volume`` / ``volume-max`` only."""
        volume = max(0, min(200, int(volume)))
        self._volume_pct = volume
        if self._mpv is None:
            return
        try:
            self._mpv.volume_max = 200
            self._mpv.volume = float(volume)
        except Exception:
            try:
                self._mpv.volume = float(volume)
            except Exception as exc:
                self.error_occurred.emit(f"Volume set failed: {exc}")

    def set_muted(self, muted: bool) -> None:
        """Toggle mute without changing the stored volume percent."""
        self._muted = bool(muted)
        if self._mpv is None:
            return
        try:
            self._mpv.mute = self._muted
        except Exception as exc:
            self.error_occurred.emit(f"Mute set failed: {exc}")

    def is_muted(self) -> bool:
        if self._mpv is not None:
            try:
                self._muted = bool(self._mpv.mute)
            except Exception:
                pass
        return bool(self._muted)

    def source_path(self) -> str:
        return self._source_path

    def _poll_mpv(self) -> None:
        if self._mpv is None:
            return
        try:
            self.position_changed.emit(self.position())
            dur = self.duration()
            if dur:
                self.duration_changed.emit(dur)
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


def show_native_engine_failure(message: Optional[str] = None) -> None:
    """Print and optionally dialog the install hint, then exit."""
    text = message or native_engine_install_hint()
    print(text, file=sys.stderr)
    try:
        # Only if a QApplication already exists
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            QMessageBox.critical(None, "VoxPlayer — native engine required", text)
    except Exception:
        pass
