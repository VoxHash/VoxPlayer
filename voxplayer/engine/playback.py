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


def ensure_mpv_safe_locale() -> None:
    """libmpv requires LC_NUMERIC=C; other locales can segfault on mpv_set_option."""
    import locale

    try:
        locale.setlocale(locale.LC_NUMERIC, "C")
    except locale.Error:
        pass


def prefer_xcb_for_mpv_embed() -> None:
    """Prefer X11/XWayland so libmpv WID embedding works under Wayland sessions."""
    ensure_mpv_safe_locale()
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
        self._seek_pending = None  # deferred (ms, exact) to avoid UI freezes

        # Compatibility aliases — UI historically touched these; they are unused for audio.
        self.media_player = None
        self.audio_output = None

        if not self._try_init_mpv():
            raise NativeEngineError(native_engine_install_hint())
        self.backend_ready.emit("mpv")

    @staticmethod
    def _looks_like_video(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in {
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mpg",
            ".mpeg",
            ".ts",
            ".m2ts",
            ".vob",
        }

    def _try_init_mpv(self) -> bool:
        """Initialize idle libmpv with no OS window (video loads only after WID bind)."""
        ensure_mpv_safe_locale()
        try:
            mpv = require_mpv_module()
        except NativeEngineError:
            return False

        # Idle, no window: never open an external mpv window before WID embed.
        try:
            player = mpv.MPV(
                vo="null",
                keep_open="yes",
                idle="yes",
                force_window="no",
                input_default_bindings=False,
                input_vo_keyboard=False,
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
            self._mpv_video_bound = False
            return False

    def _start_mpv_poll(self) -> None:
        self._mpv_poll = QTimer(self)
        self._mpv_poll.setInterval(100)
        self._mpv_poll.timeout.connect(self._poll_mpv)
        self._mpv_poll.start()

    def rebind_video_widget(self) -> bool:
        """Bind (or re-bind) libmpv to the in-app video widget WID.

        Always recreates the player against the current winId so video cannot
        open in an external window after the stage is shown.
        """
        if self.video_widget is None:
            return False
        try:
            mpv = require_mpv_module()
            path = self._source_path
            pos = self.position()
            was_playing = self.is_playing()
            vol = self._volume_pct
            muted = self._muted
            if self._mpv is not None:
                try:
                    self._mpv.terminate()
                except Exception:
                    pass
                self._mpv = None
            from PyQt6.QtCore import Qt as _Qt

            self.video_widget.setAttribute(_Qt.WidgetAttribute.WA_NativeWindow, True)
            self.video_widget.show()
            self.video_widget.update()
            wid = int(self.video_widget.winId())
            if wid == 0:
                # Keep a window-less player; do not open an external VO.
                player = mpv.MPV(
                    vo="null",
                    keep_open="yes",
                    idle="yes",
                    force_window="no",
                    input_default_bindings=False,
                    osc=False,
                    osd_level=0,
                    volume=float(vol),
                    volume_max=200,
                )
                self._mpv = player
                self._mpv_video_bound = False
                if path and not self._looks_like_video(path):
                    player.play(path)
                    player.pause = not was_playing
                if self._mpv_poll is None:
                    self._start_mpv_poll()
                return False

            # WID embed — video renders inside the Qt widget only.
            player = mpv.MPV(
                wid=str(wid),
                vo="x11" if sys.platform.startswith("linux") else "gpu",
                hwdec="auto-safe",
                keep_open="yes",
                idle="yes",
                force_window="no",
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
                    # Keyframe seek on rebind — never block UI with exact seek here.
                    try:
                        player.command("seek", pos / 1000.0, "absolute")
                    except Exception:
                        pass
                player.pause = not was_playing
            if self._mpv_poll is None:
                self._start_mpv_poll()
            return True
        except Exception:
            self._mpv_video_bound = False
            if self._mpv is None:
                try:
                    mpv = require_mpv_module()
                    self._mpv = mpv.MPV(
                        vo="null",
                        force_window="no",
                        keep_open="yes",
                        idle="yes",
                        volume=100,
                        volume_max=200,
                    )
                    self._start_mpv_poll()
                except Exception:
                    pass
            return False

    @property
    def backend_name(self) -> str:
        return self.backend.value

    @property
    def has_embedded_video(self) -> bool:
        return bool(self._mpv_video_bound)

    def set_source(self, file_path: str) -> None:
        """Remember path; load audio immediately, defer video until WID embed."""
        self._source_path = file_path
        if self._mpv is None:
            self.error_occurred.emit("Native engine not initialized")
            return
        # Video without embed would open an external mpv window — wait for rebind.
        if self._looks_like_video(file_path) and not self._mpv_video_bound:
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

    def set_position(self, ms: int, exact: bool = False) -> None:
        """Seek without freezing the UI.

        Scrubbing uses keyframe seeks; ``exact=True`` (slider release) uses a
        deferred absolute seek so large jumps do not block the Qt event loop.
        """
        if self._mpv is None:
            return
        ms = max(0, int(ms))
        self._seek_pending = (ms, bool(exact))
        # Coalesce rapid scrub events onto the next event-loop tick.
        QTimer.singleShot(0, self._flush_pending_seek)

    def _flush_pending_seek(self) -> None:
        if self._mpv is None or self._seek_pending is None:
            return
        ms, exact = self._seek_pending
        self._seek_pending = None
        seconds = max(0.0, float(ms) / 1000.0)
        try:
            if exact:
                # Prefer non-blocking absolute seek; fall back if needed.
                try:
                    self._mpv.command("seek", seconds, "absolute")
                except Exception:
                    self._mpv.time_pos = seconds
            else:
                self._mpv.command("seek", seconds, "absolute", "keyframes")
        except Exception:
            try:
                self._mpv.seek(seconds, reference="absolute")
            except Exception:
                pass

    def seek_relative(self, seconds: float) -> None:
        self.set_position(max(0, self.position() + int(seconds * 1000)), exact=True)

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
