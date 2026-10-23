"""
Playback engine: native C media core (libVLC) embedded into the Qt video surface.

Phase 5 hardening:
  - Soft WID rebind on show/resize (no stop) when the window id is unchanged
  - Hard rebind only when the Qt native window is recreated
  - Coalesced, non-blocking seeks with bounded retries (scrub vs exact)
  - Platform-aware drawable (X11 / HWND / NSObject) + embed capability flag
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QEvent, pyqtSignal, QTimer
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


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def prefer_xcb_for_embed() -> None:
    """Prefer X11/XWayland so window-ID video embed works under Wayland sessions.

    Wayland sessions often export both ``WAYLAND_DISPLAY`` and ``DISPLAY`` (XWayland).
    Forcing ``QT_QPA_PLATFORM=xcb`` when DISPLAY is available is the reliable embed
    path on current system libvlc (3.x has no public Wayland surface bind API yet).
    """
    _x_init_threads()
    if _env_truthy("VOXPLAYER_FORCE_WAYLAND"):
        return
    if _env_truthy("VOXPLAYER_KEEP_QPA"):
        return
    mode = (os.getenv("VOXPLAYER_EMBED") or "auto").strip().lower()
    if mode == "wayland":
        return
    if mode == "xcb" or (mode == "auto" and os.getenv("DISPLAY")):
        # Force (not setdefault): session defaults to wayland must not win over embed.
        os.environ["QT_QPA_PLATFORM"] = "xcb"


# Backward-compatible alias used by older call sites
prefer_xcb_for_mpv_embed = prefer_xcb_for_embed


def configure_embed_surface(widget) -> None:
    """Set Qt native-window flags that libvlc needs for a reliable WID bind.

    Upstream VLC: ``WA_DontCreateNativeAncestors`` is for Wayland only. On X11 /
    XWayland it misplaces or blanks the video while audio still plays.
    """
    if widget is None:
        return
    try:
        from PyQt6.QtCore import Qt as _Qt
        from PyQt6.QtWidgets import QApplication

        widget.setAttribute(_Qt.WidgetAttribute.WA_NativeWindow, True)
        app = QApplication.instance()
        plat = (app.platformName() if app is not None else "").lower()
        pure_wayland = "wayland" in plat and "xcb" not in plat
        widget.setAttribute(
            _Qt.WidgetAttribute.WA_DontCreateNativeAncestors, bool(pure_wayland)
        )
    except Exception:
        pass


def libvlc_has_wayland_surface_api() -> bool:
    """True when libvlc exports a Wayland surface bind (VLC 4+ / experimental builds)."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        import ctypes

        for libname in ("libvlc.so.5", "libvlc.so"):
            try:
                lib = ctypes.CDLL(libname)
            except OSError:
                continue
            if hasattr(lib, "libvlc_media_player_set_wayland_surface"):
                return True
        return False
    except Exception:
        return False


def qt_platform_name() -> str:
    """Return the live Qt platform plugin name when a QGuiApplication exists."""
    try:
        from PyQt6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is not None:
            name = (app.platformName() or "").strip().lower()
            if name:
                return name
    except Exception:
        pass
    return (os.environ.get("QT_QPA_PLATFORM") or "").strip().lower()


def embed_platform_hint() -> str:
    """Short note about the current session's embed prospects."""
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    if not sys.platform.startswith("linux"):
        return "other"

    plat = qt_platform_name()
    if "wayland" in plat and "xcb" not in plat:
        if libvlc_has_wayland_surface_api():
            return "wayland-native"
        return "wayland-limited"
    if "xcb" in plat or "x11" in plat:
        return "x11"
    if os.getenv("DISPLAY"):
        return "x11"
    if os.getenv("WAYLAND_DISPLAY"):
        if libvlc_has_wayland_surface_api():
            return "wayland-native"
        return "wayland-limited"
    return "linux-unknown"


def embed_status_message(hint: Optional[str] = None) -> str:
    """User-facing one-liner for the engine / status bar."""
    h = hint or embed_platform_hint()
    if h == "x11":
        return "Video embed: X11/XWayland (window-ID)"
    if h == "wayland-native":
        return "Video embed: Wayland surface (native libvlc)"
    if h == "wayland-limited":
        return (
            "Video embed limited on pure Wayland — relaunch with X11/XWayland "
            "(unset VOXPLAYER_FORCE_WAYLAND; ensure DISPLAY is set) for in-app video"
        )
    if h == "win32":
        return "Video embed: HWND"
    if h == "darwin":
        return "Video embed: NSObject"
    return f"Video embed: {h}"


def native_engine_install_hint() -> str:
    """Cross-platform install guidance for the native C media core."""
    lines = [
        "VoxPlayer requires the native C media core (python-vlc + system libvlc).",
        "Qt Multimedia is not used for playback.",
        "",
        "Desktop bundles: prefer a release that ships the native core under native_core/,",
        "  or run the clear per-OS installer: packaging/install_native_core_*.{sh,ps1}",
        "",
        "Install steps (dev / pip):",
        "  • Python binding:  pip install python-vlc",
        "  • Or project venv: .venv/bin/pip install -r requirements.txt",
        "  • Then launch:     python run.py   (or: .venv/bin/python run.py)",
        "",
        "System libvlc:",
        "  • Arch / Manjaro:     sudo pacman -S vlc",
        "  • Debian / Ubuntu:    sudo apt install vlc libvlc-dev",
        "  • Fedora:             sudo dnf install vlc",
        "  • macOS (Homebrew):   brew install vlc",
        "  • Windows:            install the desktop media suite; ensure libvlc.dll is on PATH",
        "                        or set VLC_HOME to that install folder",
        "",
        "Wayland / embed:",
        "  • Default: force X11/XWayland when DISPLAY is set (reliable in-app video).",
        "  • Pure Wayland without libvlc Wayland surface API: audio works; video embed is limited.",
        "  • VOXPLAYER_EMBED=xcb|wayland|auto   VOXPLAYER_FORCE_WAYLAND=1   VOXPLAYER_KEEP_QPA=1",
    ]
    return "\n".join(lines)


def require_vlc_module():
    """Import python-vlc or raise NativeEngineError with install text."""
    try:
        from ..native_core_paths import configure_bundled_native_core

        configure_bundled_native_core()
    except Exception:
        pass
    try:
        import vlc  # noqa: WPS433

        return vlc
    except ImportError as exc:
        raise NativeEngineError(native_engine_install_hint()) from exc


class _VideoSurfaceFilter(QObject):
    """Watch the Qt video surface for show/resize so we can soft-rebind WID."""

    def __init__(self, engine: "PlaybackEngine"):
        super().__init__(engine)
        self._engine = engine

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is not self._engine.video_widget:
            return False
        et = event.type()
        if et in (QEvent.Type.Show, QEvent.Type.Resize, QEvent.Type.WinIdChange):
            self._engine.schedule_soft_rebind()
        return False


class PlaybackEngine(QObject):
    """Play/pause/seek/volume API backed by the native C media core (libvlc)."""

    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms
    state_changed = pyqtSignal(str)  # playing|paused|stopped
    error_occurred = pyqtSignal(str)
    backend_ready = pyqtSignal(str)
    embed_changed = pyqtSignal(bool)  # True when WID bind succeeded

    _SEEK_MAX_RETRIES = 30  # ~1.2s at 40ms
    _SOFT_REBIND_MS = 30

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
        self._bound_wid = 0
        self._seek_pending: Optional[Tuple[int, bool]] = None
        self._seek_retries = 0
        self._seek_token = 0
        self._last_state = "stopped"
        self._pause_after_load = False
        self._soft_rebind_scheduled = False
        self._embed_hint = embed_platform_hint()
        self._surface_filter = None
        self._last_error_msg = ""
        self._error_emitted_for_source = ""
        self._event_manager = None
        # Gapless queue: secondary player from the same Instance (same native stack).
        self._next_player = None
        self._next_media = None
        self._next_path = ""
        self._user_stop = False
        self._suppress_error_reports = False
        self._load_generation = 0

        self.media_player = None
        self.audio_output = None

        if not self._try_init_native():
            raise NativeEngineError(native_engine_install_hint())
        self._install_surface_filter()
        self.backend_ready.emit("native")

    def _install_surface_filter(self) -> None:
        if self.video_widget is None:
            return
        self._surface_filter = _VideoSurfaceFilter(self)
        self.video_widget.installEventFilter(self._surface_filter)

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
            ".hevc",
            ".h265",
            ".av1",
            ".ivf",
        }

    def _try_init_native(self) -> bool:
        prefer_xcb_for_embed()
        self._embed_hint = embed_platform_hint()
        try:
            vlc = require_vlc_module()
        except NativeEngineError:
            return False
        self._vlc = vlc
        try:
            # Headless C core — never open the desktop UI. Embed via window ID.
            args = [
                "--intf=dummy",
                "--no-video-title-show",
                "--no-stats",
                "--no-osd",
                "--quiet",
                "--no-keyboard-events",
                "--no-mouse-events",
                # Prefer dav1d for AV1 and the dedicated Opus module for audio.
                # Do NOT use dav1d,avcodec alone — that forces Opus through avcodec and
                # yields "cannot start codec (opus)" / "No active audio output".
                "--codec=dav1d,opus,avcodec,all",
            ]
            # Pulse/PipeWire: device enum + mixer identity (not the stock VLC aout brand)
            if sys.platform.startswith("linux"):
                args.append("--aout=pulse")
            # --no-xlib only on pure Wayland; X11/XWayland embed needs Xlib/xcb vout.
            if sys.platform.startswith("linux") and embed_platform_hint() == "wayland-limited":
                args.append("--no-xlib")
            try:
                from ..codecs import avcodec_hw_arg

                hw = avcodec_hw_arg()
                if hw:
                    args.append(hw)
            except Exception:
                pass
            try:
                from ..native_core_paths import plugin_path_args

                args.extend(plugin_path_args())
            except Exception:
                pass
            self._instance = vlc.Instance(*args)
            self._apply_native_app_identity()
            self._player = self._instance.media_player_new()
            try:
                self._player.video_set_mouse_input(False)
                self._player.video_set_key_input(False)
            except Exception:
                pass
            self._attach_error_events()
            self._bind_video_drawable(force=True)
            self._start_poll()
            self._apply_volume_to_player()
            return True
        except Exception:
            self._player = None
            self._instance = None
            return False

    def _apply_native_app_identity(self) -> None:
        """Tell Pulse/PipeWire we are VoxPlayer — not stock VLC mixer branding."""
        if self._instance is None:
            return
        try:
            from .. import __version__ as ver
        except Exception:
            ver = "1.0"
        try:
            # application.name in the system mixer
            self._instance.set_user_agent(f"VoxPlayer {ver}", f"VoxPlayer/{ver}")
        except Exception:
            try:
                self._instance.set_user_agent("VoxPlayer", "VoxPlayer")
            except Exception:
                pass
        try:
            # application.id / application.icon_name (needs XDG icon theme name ``voxplayer``)
            self._instance.set_app_id("dev.voxhash.voxplayer", str(ver), "voxplayer")
        except Exception:
            pass

    def list_audio_output_devices(self) -> List[Tuple[str, str]]:
        """Return ``(device_id, description)`` for every Pulse/system sink libvlc sees."""
        if self._player is None:
            return []
        out: List[Tuple[str, str]] = []
        head = None
        try:
            head = self._player.audio_output_device_enum()
            cur = head
            while cur:
                d = cur.contents
                device = d.device
                desc = d.description
                if isinstance(device, bytes):
                    device = device.decode("utf-8", "replace")
                if isinstance(desc, bytes):
                    desc = desc.decode("utf-8", "replace")
                device = (device or "").strip()
                desc = (desc or device or "Audio device").strip()
                if device:
                    out.append((device, desc))
                cur = d.next
        except Exception:
            out = []
        finally:
            if head is not None and self._vlc is not None:
                try:
                    self._vlc.libvlc_audio_output_device_list_release(head)
                except Exception:
                    pass
        return out

    def set_audio_output_device(self, device_id: Optional[str]) -> bool:
        """Route playback to ``device_id`` (Pulse sink name) or system default if empty."""
        if self._player is None:
            return False
        try:
            if not device_id or device_id in {"default", "auto", ""}:
                # Empty id = follow the session default sink
                self._player.audio_output_device_set(None, "")
            else:
                self._player.audio_output_device_set(None, str(device_id))
            return True
        except Exception:
            return False

    def current_audio_output_device(self) -> str:
        if self._player is None:
            return ""
        try:
            raw = self._player.audio_output_device_get()
            if raw is None:
                return ""
            if isinstance(raw, bytes):
                return raw.decode("utf-8", "replace")
            return str(raw)
        except Exception:
            return ""

    def _attach_error_events(self) -> None:
        """Subscribe to native EncounteredError — never silently switch engines."""
        if self._player is None or self._vlc is None:
            return
        try:
            self._event_manager = self._player.event_manager()
            self._event_manager.event_attach(
                self._vlc.EventType.MediaPlayerEncounteredError,
                self._on_native_encountered_error,
            )
        except Exception:
            self._event_manager = None

    def _on_native_encountered_error(self, event) -> None:
        # libvlc callbacks are not on the Qt thread — queue to the main loop.
        gen = self._load_generation
        QTimer.singleShot(0, lambda g=gen: self._report_playback_error("encountered_error", g))

    def _clear_libvlc_errmsg(self) -> None:
        if self._vlc is None:
            return
        try:
            clear = getattr(self._vlc, "libvlc_clearerr", None)
            if callable(clear):
                clear()
        except Exception:
            pass

    def _libvlc_errmsg(self) -> str:
        if self._vlc is None:
            return ""
        try:
            raw = self._vlc.libvlc_errmsg()
            if raw is None:
                return ""
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace").strip()
            return str(raw).strip()
        except Exception:
            return ""

    def _begin_load_transition(self) -> None:
        """Suppress false EncounteredError alerts while stopping / swapping tracks."""
        self._load_generation += 1
        self._suppress_error_reports = True
        self._user_stop = False
        self._clear_libvlc_errmsg()
        self.clear_last_error()
        gen = self._load_generation

        def _lift(g=gen):
            if g == self._load_generation:
                self._suppress_error_reports = False

        QTimer.singleShot(700, _lift)

    def _format_playback_error(self, reason: str) -> str:
        path = self._source_path or ""
        name = os.path.basename(path) if path else "(no file)"
        ext = os.path.splitext(path)[1].lower() if path else ""
        core = self._libvlc_errmsg()
        bits = [
            f"Native media core could not play “{name}”.",
            f"Reason: {reason.replace('_', ' ')}.",
        ]
        if ext:
            bits.append(f"Extension: {ext}.")
        if core:
            bits.append(f"Engine detail: {core}")
        bits.append(
            "VoxPlayer does not switch to another playback stack — "
            "install or enable the matching libvlc plugin/codec, or use a supported format."
        )
        return "\n".join(bits)

    def _near_natural_end(self) -> bool:
        dur = self.duration()
        pos = self.position()
        if dur <= 0:
            return False
        return pos >= max(0, dur - 1500)

    def _report_playback_error(self, reason: str, generation: Optional[int] = None) -> None:
        """Surface a codec/demux failure once per source (no silent fallback)."""
        if generation is not None and generation != self._load_generation:
            return
        if self._suppress_error_reports or self._user_stop:
            return
        # Interrupted decode at EOS / queue advance often reports Error — treat as end.
        if self._near_natural_end():
            self._last_state = "ended"
            self.state_changed.emit("ended")
            return
        key = f"{self._source_path}|{reason}|{self._libvlc_errmsg()}"
        if key == self._error_emitted_for_source and self._last_error_msg:
            return
        msg = self._format_playback_error(reason)
        self._error_emitted_for_source = key
        self._last_error_msg = msg
        self._last_state = "error"
        self.state_changed.emit("error")
        self.error_occurred.emit(msg)

    def clear_last_error(self) -> None:
        self._last_error_msg = ""
        self._error_emitted_for_source = ""

    def _current_wid(self) -> int:
        if self.video_widget is None:
            return 0
        try:
            configure_embed_surface(self.video_widget)
            return int(self.video_widget.winId())
        except Exception:
            return 0

    def _try_bind_wayland_surface(self) -> bool:
        """Bind via libvlc Wayland surface API when the compositor build exports it."""
        if self._player is None or not sys.platform.startswith("linux"):
            return False
        if not libvlc_has_wayland_surface_api():
            return False
        try:
            import ctypes
            from PyQt6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            if app is None or self.video_widget is None:
                return False
            wh = self.video_widget.window().windowHandle()
            if wh is None:
                self.video_widget.winId()
                wh = self.video_widget.window().windowHandle()
            if wh is None:
                return False
            # Best-effort: future PyQt builds may expose display/surface pointers.
            display = surface = None
            try:
                ni = app.nativeInterface(type(wh))
                display = getattr(ni, "display", None) or getattr(ni, "wlDisplay", None)
                surface = getattr(ni, "surface", None) or getattr(ni, "wlSurface", None)
            except Exception:
                pass
            if not display or not surface:
                return False
            lib = None
            for libname in ("libvlc.so.5", "libvlc.so"):
                try:
                    lib = ctypes.CDLL(libname)
                    break
                except OSError:
                    continue
            if lib is None or not hasattr(lib, "libvlc_media_player_set_wayland_surface"):
                return False
            fn = lib.libvlc_media_player_set_wayland_surface
            fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
            fn.restype = None
            # python-vlc MediaPlayer wraps a C pointer at ._as_parameter_ / .value
            player_ptr = getattr(self._player, "_as_parameter_", None) or int(self._player)
            fn(ctypes.c_void_p(int(player_ptr)), ctypes.c_void_p(int(display)), ctypes.c_void_p(int(surface)))
            self._embed_hint = "wayland-native"
            return True
        except Exception:
            return False

    def _apply_wid(self, wid: int) -> bool:
        if self._player is None:
            return False
        # Prefer native Wayland surface bind when available (no second media stack).
        if self._try_bind_wayland_surface():
            return True
        hint = embed_platform_hint()
        # Pure Wayland without the surface API: skip XID bind (avoids a detached toplevel).
        if hint == "wayland-limited" and sys.platform.startswith("linux"):
            self._embed_hint = "wayland-limited"
            return False
        if wid == 0:
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
            return True
        except Exception:
            return False

    def _bind_video_drawable(self, force: bool = False) -> bool:
        """Attach the C media core to the Qt video surface window id."""
        if self._player is None or self.video_widget is None:
            self._set_bound(False, 0)
            return False
        self.video_widget.show()
        wid = self._current_wid()
        if wid == 0:
            self._set_bound(False, 0)
            return False
        if not force and wid == self._bound_wid and self._video_bound:
            return True
        ok = self._apply_wid(wid)
        self._set_bound(ok, wid if ok else 0)
        return ok

    def _set_bound(self, ok: bool, wid: int) -> None:
        changed = ok != self._video_bound
        self._video_bound = bool(ok)
        self._bound_wid = int(wid) if ok else 0
        if changed:
            self.embed_changed.emit(self._video_bound)

    def schedule_soft_rebind(self) -> None:
        """Debounced soft rebind after show/resize/WinIdChange (never blocks)."""
        if self._soft_rebind_scheduled:
            return
        self._soft_rebind_scheduled = True
        QTimer.singleShot(self._SOFT_REBIND_MS, self._do_soft_rebind)

    def _do_soft_rebind(self) -> None:
        self._soft_rebind_scheduled = False
        if self._player is None:
            return
        wid = self._current_wid()
        if wid == 0:
            return
        if wid != self._bound_wid:
            # Native window recreated — soft apply without stop when possible.
            if self._apply_wid(wid):
                self._set_bound(True, wid)
            else:
                self._set_bound(False, 0)

    def _start_poll(self) -> None:
        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._poll_state)
        self._poll.start()

    def rebind_video_widget(self, hard: bool = False) -> bool:
        """
        Re-attach drawable after the stage becomes visible.

        Soft (default): re-apply WID if needed; no stop/reload.
        Hard: stop → bind → reload media (when the surface was destroyed).
        """
        if self._player is None:
            return False
        if not hard:
            ok = self._bind_video_drawable(force=False)
            if ok or self._current_wid() == self._bound_wid:
                return ok
            # WID changed and soft apply failed — fall through to hard.
            hard = True
        was_playing = self.is_playing()
        path = self._source_path
        pos = self.position()
        try:
            self._player.stop()
        except Exception:
            pass
        self._bound_wid = 0
        ok = self._bind_video_drawable(force=True)
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

    @property
    def embed_limited(self) -> bool:
        """True when the session is unlikely to host reliable WID video."""
        hint = embed_platform_hint()
        self._embed_hint = hint
        return hint == "wayland-limited" and not self._video_bound

    @property
    def embed_platform(self) -> str:
        self._embed_hint = embed_platform_hint()
        return self._embed_hint

    def refresh_embed_hint(self) -> str:
        """Re-evaluate platform after QApplication exists; return current hint."""
        self._embed_hint = embed_platform_hint()
        return self._embed_hint

    def _load_media_path(self, file_path: str, start_paused: bool = True) -> None:
        if self._instance is None or self._player is None:
            return
        media = self._instance.media_new_path(file_path)
        if self._volume_pct > 100:
            gain = self._volume_pct / 100.0
            try:
                media.add_option(f":gain={gain:.3f}")
            except Exception:
                pass
        # Hint demux/codec for HEVC / AV1 elementary streams and modern containers.
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in {".hevc", ".h265"}:
                media.add_option(":demux=hevc")
            elif ext in {".av1", ".ivf"}:
                media.add_option(":demux=avformat,none")
            elif ext == ".opus":
                media.add_option(":demux=ogg,avformat,none")
        except Exception:
            pass
        self._media = media
        self._player.set_media(media)
        try:
            media.parse_with_options(0x1, 2000)
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
        self._bind_video_drawable(force=True)
        self._apply_volume_to_player()
        self.set_muted(self._muted)
        self._pause_after_load = bool(start_paused)
        self._player.play()
        # Re-apply WID after the surface is mapped — first bind often races show().
        QTimer.singleShot(50, lambda: self._bind_video_drawable(force=True))
        QTimer.singleShot(250, self._ensure_video_output)
        if start_paused:
            QTimer.singleShot(80, self._apply_pause_after_load)
        else:
            self._last_state = "playing"
            self.state_changed.emit("playing")

    def _ensure_video_output(self) -> None:
        """If a video track exists but size is still 0, force another WID bind."""
        if self._player is None or not self._looks_like_video(self._source_path):
            return
        try:
            size = self._player.video_get_size(0)
            w = int(size[0]) if size else 0
            h = int(size[1]) if size else 0
        except Exception:
            w = h = 0
        if w > 0 and h > 0 and self._video_bound:
            return
        configure_embed_surface(self.video_widget)
        self._bind_video_drawable(force=True)
        try:
            # Ensure the first enabled video track is selected.
            tracks = self._player.video_get_track_count()
            if tracks and int(tracks) > 0:
                cur = self._player.video_get_track()
                if cur is None or int(cur) < 0:
                    self._player.video_set_track(0)
        except Exception:
            pass

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
        self._begin_load_transition()
        self.clear_prepared_next()
        self._source_path = file_path
        if self._player is None:
            self._report_playback_error("engine_not_initialized")
            return
        if self._looks_like_video(file_path):
            self._bind_video_drawable(force=False)
        try:
            self._load_media_path(file_path, start_paused=True)
        except Exception as exc:
            self.error_occurred.emit(
                self._format_playback_error(f"load_failed: {exc}")
            )

    def play(self) -> None:
        if self._player is None:
            return
        self._pause_after_load = False
        if self._looks_like_video(self._source_path):
            self._bind_video_drawable(force=False)
        try:
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
        self._begin_load_transition()
        self._user_stop = True
        self.clear_prepared_next()
        self._player.stop()
        self._last_state = "stopped"
        self.state_changed.emit("stopped")

    def clear_prepared_next(self) -> None:
        """Drop a buffered next track (same Instance — no second media stack)."""
        if self._next_player is not None:
            try:
                self._next_player.stop()
            except Exception:
                pass
            try:
                self._next_player.release()
            except Exception:
                pass
        self._next_player = None
        self._next_media = None
        self._next_path = ""

    def prepared_next_path(self) -> str:
        return self._next_path or ""

    def prepare_next(self, file_path: str) -> bool:
        """
        Buffer the next audio file on a second MediaPlayer from this Instance.

        Best-effort gapless queue (libVLC 3 has no true DSP gapless). Call
        ``promote_prepared_next`` when the current track ends.
        """
        if not file_path or not os.path.isfile(file_path):
            return False
        if self._instance is None or self._vlc is None:
            return False
        if self._looks_like_video(file_path):
            return False
        if self._next_path == file_path and self._next_player is not None:
            return True
        self.clear_prepared_next()
        try:
            player = self._instance.media_player_new()
            media = self._instance.media_new_path(file_path)
            if self._volume_pct > 100:
                try:
                    media.add_option(f":gain={self._volume_pct / 100.0:.3f}")
                except Exception:
                    pass
            player.set_media(media)
            player.audio_set_volume(
                0 if self._muted else min(200, int(self._volume_pct))
            )
            player.play()
            # Pause once opened so the track is buffered without audible overlap.
            QTimer.singleShot(120, lambda p=player: self._pause_prepared(p))
            self._next_player = player
            self._next_media = media
            self._next_path = file_path
            return True
        except Exception:
            self.clear_prepared_next()
            return False

    def _pause_prepared(self, player) -> None:
        if player is None or player is not self._next_player:
            return
        try:
            player.set_pause(True)
            player.set_time(0)
        except Exception:
            pass

    def promote_prepared_next(self) -> Optional[str]:
        """Swap to the prepared player. Returns the new source path or None."""
        if self._next_player is None or not self._next_path:
            return None
        self._begin_load_transition()
        old = self._player
        path = self._next_path
        self._player = self._next_player
        self._media = self._next_media
        self._source_path = path
        self._next_player = None
        self._next_media = None
        self._next_path = ""
        self._duration_ms = 0
        self._attach_error_events()
        try:
            self._player.set_pause(False)
            self._player.play()
        except Exception:
            pass
        self._apply_volume_to_player()
        self.set_muted(self._muted)
        if old is not None:
            try:
                old.stop()
            except Exception:
                pass
            try:
                old.release()
            except Exception:
                pass
        self._last_state = "playing"
        self.state_changed.emit("playing")
        try:
            d = self._player.get_length()
            if d and d > 0:
                self._duration_ms = int(d)
                self.duration_changed.emit(self._duration_ms)
        except Exception:
            pass
        return path

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
            return self._state_int(self._player.get_state()) == 3
        except Exception:
            return False

    def position(self) -> int:
        if self._player is None:
            return 0
        try:
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
        """Queue a non-blocking seek. Scrub (exact=False) coalesces; release uses exact."""
        if self._player is None:
            return
        ms = max(0, int(ms))
        self._seek_pending = (ms, bool(exact))
        self._seek_token += 1
        token = self._seek_token
        self._seek_retries = 0
        # Debounce scrub moves so the UI thread never floods libvlc.
        delay = 0 if exact else 16
        QTimer.singleShot(delay, lambda t=token: self._flush_pending_seek(t))

    def _flush_pending_seek(self, token: Optional[int] = None) -> None:
        if self._player is None or self._seek_pending is None:
            return
        if token is not None and token != self._seek_token:
            return  # superseded by a newer scrub/seek
        ms, exact = self._seek_pending
        st_i = self._state_int(self._player.get_state())
        if st_i in (1, 2):  # Opening, Buffering
            self._seek_retries += 1
            if self._seek_retries > self._SEEK_MAX_RETRIES:
                self._seek_pending = None
                return
            QTimer.singleShot(40, lambda t=self._seek_token: self._flush_pending_seek(t))
            return
        # NothingSpecial / Stopped — try once after a short play nudge if we have media.
        if st_i in (0, 5) and self._source_path:
            self._seek_retries += 1
            if self._seek_retries > self._SEEK_MAX_RETRIES:
                self._seek_pending = None
                return
            try:
                self._player.play()
            except Exception:
                pass
            QTimer.singleShot(40, lambda t=self._seek_token: self._flush_pending_seek(t))
            return

        self._seek_pending = None
        dur = self.duration()
        try:
            if exact or dur <= 0:
                self._player.set_time(ms)
            else:
                # Scrub: fractional position is cheaper and non-keyframe-friendly.
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
        if self._muted:
            core_vol = 0
        elif self._volume_pct <= 100:
            core_vol = int(self._volume_pct)
        else:
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
        try:
            self._player.audio_set_mute(self._muted)
        except Exception:
            pass
        self._apply_volume_to_player()

    def is_muted(self) -> bool:
        return bool(self._muted)

    def source_path(self) -> str:
        return self._source_path

    def _poll_state(self) -> None:
        if self._player is None:
            return
        try:
            st_i = self._state_int(self._player.get_state())
            # libvlc State.Error == 6 — surface clearly; do not treat as a quiet stop.
            if st_i == 6 and self._last_state != "error":
                if self._suppress_error_reports or self._user_stop:
                    return
                if self._near_natural_end():
                    self._last_state = "ended"
                    self.state_changed.emit("ended")
                    return
                self._report_playback_error("decoder_or_demux_error")
                return
            self.position_changed.emit(self.position())
            dur = self.duration()
            if dur:
                self.duration_changed.emit(dur)
            playing = self.is_playing()
            if playing and self._last_state != "playing":
                self._last_state = "playing"
                self.state_changed.emit("playing")
            elif not playing and self._last_state == "playing":
                # 5 = Ended, 6 handled above
                if st_i == 5:
                    if self._user_stop:
                        self._user_stop = False
                        self._last_state = "stopped"
                        self.state_changed.emit("stopped")
                    else:
                        self._last_state = "ended"
                        self.state_changed.emit("ended")
                elif st_i not in (1, 2, 4):  # Opening/Buffering/Paused
                    self._last_state = "stopped"
                    self.state_changed.emit("stopped")
        except Exception:
            pass

    def shutdown(self) -> None:
        if self._poll:
            self._poll.stop()
        self.clear_prepared_next()
        if self.video_widget is not None and self._surface_filter is not None:
            try:
                self.video_widget.removeEventFilter(self._surface_filter)
            except Exception:
                pass
            self._surface_filter = None
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
