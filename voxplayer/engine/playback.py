"""
Playback engine: native C media core (libVLC) embedded into the Qt video surface.

The desktop shell stays PyQt6. Video/audio decode and presentation use the
system C library (libvlc), matching the architecture of major open desktop
media players (C core + UI toolkit embed via window ID).

Volume: 0–100 via libvlc; 101–200 via media gain so boost still works.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QMessageBox


class BackendKind(str, Enum):
    NATIVE = "native"  # C libvlc media core


class NativeEngineError(RuntimeError):
    """Raised when the native C media core cannot be initialized."""


def _x_init_threads() -> None:
    """Required before libvlc on X11 (Xlib is not thread-safe by default)."""
    if not sys.platform.startswith("linux"):
        return
    try:
        import ctypes

        x11 = ctypes.CDLL("libX11.so.6")
        x11.XInitThreads()
    except Exception:
        pass


def prefer_xcb_for_embed() -> None:
    """Prefer X11/XWayland so window-ID video embed works under Wayland sessions."""
    _x_init_threads()
    if os.getenv("VOXPLAYER_FORCE_WAYLAND", "").strip() in {"1", "true", "yes"}:
        return
    if os.getenv("DISPLAY") and not os.getenv("VOXPLAYER_KEEP_QPA"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


# Backward-compatible alias used by older call sites
prefer_xcb_for_mpv_embed = prefer_xcb_for_embed


def native_engine_install_hint() -> str:
    """Cross-platform install guidance for the native C media core."""
    lines = [
        "VoxPlayer requires the native C media core (python-vlc + system libvlc).",
        "Qt Multimedia is not used for playback.",
        "",
        "Install steps:",
        "  • Python binding:  pip install python-vlc",
        "  • Or project venv: .venv/bin/pip install -r requirements.txt",
        "  • Then launch:     python run.py   (or: .venv/bin/python run.py)",
        "",
        "System libvlc:",
        "  • Arch / Manjaro:     sudo pacman -S vlc",
        "  • Debian / Ubuntu:    sudo apt install vlc libvlc-dev",
        "  • Fedora:             sudo dnf install vlc",
        "  • macOS (Homebrew):   brew install vlc",
        "  • Windows:            install VLC and ensure libvlc.dll is on PATH",
        "",
        "Wayland note: prefer X11/XWayland for embedded video (DISPLAY set).",
    ]
    return "\n".join(lines)


def require_vlc_module():
    """Import python-vlc or raise NativeEngineError with install text."""
    try:
        import vlc  # noqa: WPS433

        return vlc
    except ImportError as exc:
        raise NativeEngineError(native_engine_install_hint()) from exc


class PlaybackEngine(QObject):
    """Play/pause/seek/volume API backed by the native C media core (libvlc)."""

    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms
    state_changed = pyqtSignal(str)  # playing|paused|stopped
    error_occurred = pyqtSignal(str)
    backend_ready = pyqtSignal(str)

    def __init__(self, video_widget: QWidget, parent=None):
        super().__init__(parent)
        self.video_widget = video_widget
        self.backend = BackendKind.NATIVE
        self._vlc = None
        self._instance = None
        self._player = None
        self._media = None
        self._source_path = ""
        self._duration_ms = 0
        self._muted = False
        self._volume_pct = 100  # 0..200 logical
        self._poll = None
        self._video_bound = False
        self._seek_pending = None
        self._last_state = "stopped"
        # When True, a deferred pause from set_source/load must not cancel a later play().
        self._pause_after_load = False

        self.media_player = None
        self.audio_output = None

        if not self._try_init_native():
            raise NativeEngineError(native_engine_install_hint())
        self.backend_ready.emit("native")

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

    def _try_init_native(self) -> bool:
        prefer_xcb_for_embed()
        try:
            vlc = require_vlc_module()
        except NativeEngineError:
            return False
        self._vlc = vlc
        try:
            # Headless C core only — never open the desktop UI. Embed via window ID.
            # Use --key=value form; a bare "--intf"/"dummy" pair can fall through to Qt UI.
            self._instance = vlc.Instance(
                "--intf=dummy",
                "--no-video-title-show",
                "--no-stats",
                "--no-osd",
                "--quiet",
                "--no-keyboard-events",
                "--no-mouse-events",
                "--no-xlib",
            )
            self._player = self._instance.media_player_new()
            try:
                self._player.video_set_mouse_input(False)
                self._player.video_set_key_input(False)
            except Exception:
                pass
            self._bind_video_drawable()
            self._start_poll()
            self._apply_volume_to_player()
            return True
        except Exception:
            self._player = None
            self._instance = None
            return False

    def _bind_video_drawable(self) -> bool:
        """Attach the C media core to the Qt video surface window id."""
        if self._player is None or self.video_widget is None:
            self._video_bound = False
            return False
        from PyQt6.QtCore import Qt as _Qt

        self.video_widget.setAttribute(_Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_widget.setAttribute(_Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True)
        self.video_widget.show()
        wid = int(self.video_widget.winId())
        if wid == 0:
            self._video_bound = False
            return False
        try:
            if sys.platform.startswith("linux"):
                self._player.set_xwindow(wid)
            elif sys.platform == "win32":
                self._player.set_hwnd(wid)
            elif sys.platform == "darwin":
                self._player.set_nsobject(wid)
            else:
                self._player.set_xwindow(wid)
            self._video_bound = True
            return True
        except Exception:
            self._video_bound = False
            return False

    def _start_poll(self) -> None:
        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._poll_state)
        self._poll.start()

    def rebind_video_widget(self) -> bool:
        """Re-attach drawable after the stage becomes visible."""
        if self._player is None:
            return False
        was_playing = self.is_playing()
        path = self._source_path
        pos = self.position()
        # Stop briefly so set_xwindow takes effect on next play (libvlc contract).
        try:
            self._player.stop()
        except Exception:
            pass
        ok = self._bind_video_drawable()
        if path:
            self._load_media_path(path, start_paused=not was_playing)
            if pos > 0:
                self.set_position(pos, exact=False)
            if was_playing:
                self.play()
        return ok

    @property
    def backend_name(self) -> str:
        return self.backend.value

    @property
    def has_embedded_video(self) -> bool:
        return bool(self._video_bound)

    def _load_media_path(self, file_path: str, start_paused: bool = True) -> None:
        if self._instance is None or self._player is None:
            return
        media = self._instance.media_new_path(file_path)
        # Software volume boost above 100% via linear gain (libvlc volume caps at 100).
        if self._volume_pct > 100:
            gain = self._volume_pct / 100.0
            try:
                media.add_option(f":gain={gain:.3f}")
            except Exception:
                pass
        self._media = media
        self._player.set_media(media)
        try:
            media.parse_with_options(0x1, 2000)  # parse local
        except Exception:
            try:
                media.parse()
            except Exception:
                pass
        try:
            length = media.get_duration()
            if length is not None and length > 0:
                self._duration_ms = int(length)
                self.duration_changed.emit(self._duration_ms)
        except Exception:
            pass
        self._bind_video_drawable()
        self._apply_volume_to_player()
        self.set_muted(self._muted)
        self._pause_after_load = bool(start_paused)
        self._player.play()
        if start_paused:
            # Pause after open so layout can finish; cancelled if play() runs first.
            QTimer.singleShot(80, self._apply_pause_after_load)
        else:
            self._last_state = "playing"
            self.state_changed.emit("playing")

    def _apply_pause_after_load(self) -> None:
        if not self._pause_after_load or self._player is None:
            return
        self._pause_after_load = False
        try:
            self._player.set_pause(True)
        except Exception:
            pass
        self._last_state = "paused"
        self.state_changed.emit("paused")

    def set_source(self, file_path: str) -> None:
        self._source_path = file_path
        if self._player is None:
            self.error_occurred.emit("Native engine not initialized")
            return
        # Ensure drawable before starting video so output stays in-app.
        if self._looks_like_video(file_path):
            self._bind_video_drawable()
        try:
            self._load_media_path(file_path, start_paused=True)
        except Exception as exc:
            self.error_occurred.emit(f"Native engine load failed: {exc}")

    def play(self) -> None:
        if self._player is None:
            return
        # Cancel any deferred pause from set_source / rebind load.
        self._pause_after_load = False
        if self._looks_like_video(self._source_path):
            self._bind_video_drawable()
        try:
            # Resume if already paused; otherwise start.
            if self._state_int(self._player.get_state()) == 4:  # Paused
                self._player.set_pause(False)
            else:
                self._player.play()
        except Exception:
            self._player.play()
        self._last_state = "playing"
        self.state_changed.emit("playing")
        if self._seek_pending is not None:
            QTimer.singleShot(50, self._flush_pending_seek)

    def pause(self) -> None:
        if self._player is None:
            return
        self._pause_after_load = False
        self._player.set_pause(True)
        self._last_state = "paused"
        self.state_changed.emit("paused")

    def stop(self) -> None:
        if self._player is None:
            return
        self._player.stop()
        self._last_state = "stopped"
        self.state_changed.emit("stopped")

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    @staticmethod
    def _state_int(st) -> int:
        """Normalize libvlc State (enum / int / bytes) to an int."""
        if st is None:
            return -1
        try:
            return int(st)
        except Exception:
            pass
        if isinstance(st, (bytes, bytearray)):
            try:
                return int.from_bytes(st[:4], "little", signed=False)
            except Exception:
                return -1
        try:
            return int(getattr(st, "value", -1))
        except Exception:
            return -1

    def is_playing(self) -> bool:
        if self._player is None:
            return False
        try:
            if bool(self._player.is_playing()):
                return True
        except Exception:
            pass
        try:
            return self._state_int(self._player.get_state()) == 3  # Playing
        except Exception:
            return False

    def position(self) -> int:
        if self._player is None:
            return 0
        try:
            # get_time is milliseconds
            t = self._player.get_time()
            return max(0, int(t)) if t is not None and t >= 0 else 0
        except Exception:
            return 0

    def duration(self) -> int:
        if self._player is None:
            return self._duration_ms
        try:
            d = self._player.get_length()
            if d is not None and d > 0:
                self._duration_ms = int(d)
        except Exception:
            pass
        return self._duration_ms

    def set_position(self, ms: int, exact: bool = False) -> None:
        if self._player is None:
            return
        ms = max(0, int(ms))
        self._seek_pending = (ms, bool(exact))
        QTimer.singleShot(0, self._flush_pending_seek)

    def _flush_pending_seek(self) -> None:
        if self._player is None or self._seek_pending is None:
            return
        ms, _exact = self._seek_pending
        # libvlc ignores seeks until Opening/Buffering finishes — retry briefly.
        st_i = self._state_int(self._player.get_state())
        if st_i in (1, 2):  # Opening, Buffering
            QTimer.singleShot(40, self._flush_pending_seek)
            return
        self._seek_pending = None
        dur = self.duration()
        try:
            self._player.set_time(ms)
            if dur > 0:
                # Also set fractional position (some builds honor one or the other).
                self._player.set_position(min(1.0, max(0.0, ms / float(dur))))
        except Exception:
            try:
                self._player.set_time(ms)
            except Exception:
                pass

    def seek_relative(self, seconds: float) -> None:
        self.set_position(max(0, self.position() + int(seconds * 1000)), exact=True)

    def volume_percent(self) -> int:
        return int(self._volume_pct)

    def engine_volume(self) -> float:
        """Raw C-core volume readback (0–100). Logical UI volume may be 0–200."""
        if self._player is None:
            return 0.0
        try:
            v = self._player.audio_get_volume()
            return float(v) if v is not None and v >= 0 else 0.0
        except Exception:
            return float(max(0, min(100, self._volume_pct)))

    def _apply_volume_to_player(self) -> None:
        if self._player is None:
            return
        # libvlc software volume is 0–100; boost uses :gain= on the media.
        # Some libvlc builds accept >100; clamp logical boost into audio_set_volume when possible.
        if self._muted:
            core_vol = 0
        elif self._volume_pct <= 100:
            core_vol = int(self._volume_pct)
        else:
            # Prefer native >100 when the library accepts it; else cap + :gain=.
            core_vol = min(200, int(self._volume_pct))
        try:
            self._player.audio_set_volume(core_vol)
        except Exception:
            try:
                self._player.audio_set_volume(min(100, core_vol))
            except Exception:
                pass

    def set_volume_percent(self, volume: int) -> None:
        volume = max(0, min(200, int(volume)))
        prev = self._volume_pct
        self._volume_pct = volume
        self._apply_volume_to_player()
        # Reload media options when crossing the 100% boost boundary while loaded.
        if self._source_path and (
            (prev <= 100 < volume) or (volume <= 100 < prev)
        ):
            was = self.is_playing()
            pos = self.position()
            self._load_media_path(self._source_path, start_paused=not was)
            if pos:
                self.set_position(pos, exact=False)

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        if self._player is None:
            return
        # Prefer audio_set_mute; always fall through to volume=0 because some
        # libvlc builds leave audio_get_mute() stuck at 0 regardless.
        try:
            self._player.audio_set_mute(self._muted)
        except Exception:
            pass
        self._apply_volume_to_player()

    def is_muted(self) -> bool:
        # Trust local flag — audio_get_mute() is unreliable across libvlc builds.
        return bool(self._muted)

    def source_path(self) -> str:
        return self._source_path

    def _poll_state(self) -> None:
        if self._player is None:
            return
        try:
            self.position_changed.emit(self.position())
            dur = self.duration()
            if dur:
                self.duration_changed.emit(dur)
            playing = self.is_playing()
            if playing and self._last_state != "playing":
                self._last_state = "playing"
                self.state_changed.emit("playing")
            elif not playing and self._last_state == "playing":
                # Ended or paused externally
                try:
                    # 5 = Stopped, 6 = Ended (libvlc State enum)
                    ended = self._state_int(self._player.get_state()) in (5, 6)
                except Exception:
                    ended = False
                if ended:
                    self._last_state = "stopped"
                    self.state_changed.emit("stopped")
        except Exception:
            pass

    def shutdown(self) -> None:
        if self._poll:
            self._poll.stop()
        if self._player is not None:
            try:
                self._player.stop()
            except Exception:
                pass
            try:
                self._player.release()
            except Exception:
                pass
            self._player = None
        if self._instance is not None:
            try:
                self._instance.release()
            except Exception:
                pass
            self._instance = None


def show_native_engine_failure(message: Optional[str] = None) -> None:
    """Print and optionally dialog the install hint."""
    text = message or native_engine_install_hint()
    print(text, file=sys.stderr)
    try:
        from PyQt6.QtWidgets import QApplication

        if QApplication.instance() is not None:
            QMessageBox.critical(None, "VoxPlayer — native engine required", text)
    except Exception:
        pass
