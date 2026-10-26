"""
Vox-owned libvlc ctypes binding — desktop decode without python-vlc.

Talks to the same system / bundled native C media core (libvlc) that
``native_core/`` stages. API surface mirrors the subset ``PlaybackEngine``
used from python-vlc so the shell stays unchanged.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from enum import IntEnum
from typing import Any, Callable, List, Optional, Sequence, Tuple, Union

c_void_p = ctypes.c_void_p
c_char_p = ctypes.c_char_p
c_int = ctypes.c_int
c_uint = ctypes.c_uint
c_int64 = ctypes.c_int64
c_float = ctypes.c_float
POINTER = ctypes.POINTER

_LIB: Optional[ctypes.CDLL] = None
_LOAD_ERROR: Optional[str] = None


class EventType(IntEnum):
    """libvlc_event_e values used by VoxPlayer (VLC 3.x)."""

    MediaPlayerMediaChanged = 0x100
    MediaPlayerNothingSpecial = 0x101
    MediaPlayerOpening = 0x102
    MediaPlayerBuffering = 0x103
    MediaPlayerPlaying = 0x104
    MediaPlayerPaused = 0x105
    MediaPlayerStopped = 0x106
    MediaPlayerForward = 0x107
    MediaPlayerBackward = 0x108
    MediaPlayerEndReached = 0x109
    MediaPlayerEncounteredError = 0x10A


class AudioOutputDevice(ctypes.Structure):
    pass


AudioOutputDevice._fields_ = [
    ("next", POINTER(AudioOutputDevice)),
    ("device", c_char_p),
    ("description", c_char_p),
]


class Event(ctypes.Structure):
    _fields_ = [
        ("type", c_int),
        ("p_obj", c_void_p),
        # Union payload unused by VoxPlayer — pad for ABI size.
        ("u", ctypes.c_byte * 64),
    ]


EventCallback = ctypes.CFUNCTYPE(None, POINTER(Event), c_void_p)


def _candidate_lib_paths() -> List[str]:
    paths: List[str] = []
    for key in ("PYTHON_VLC_LIB_PATH", "VOXPLAYER_LIBVLC", "VLC_PLUGIN_PATH"):
        # VLC_PLUGIN_PATH is plugins dir — skip as lib path
        if key == "VLC_PLUGIN_PATH":
            continue
        env = os.environ.get(key, "").strip()
        if env and os.path.isfile(env):
            paths.append(env)
    found = ctypes.util.find_library("vlc")
    if found:
        paths.append(found)
    if sys.platform.startswith("linux"):
        paths.extend(
            [
                "libvlc.so.5",
                "libvlc.so",
                "/usr/lib/libvlc.so.5",
                "/usr/lib64/libvlc.so.5",
                "/usr/local/lib/libvlc.so.5",
            ]
        )
    elif sys.platform == "darwin":
        paths.extend(
            [
                "libvlc.dylib",
                "/Applications/VLC.app/Contents/MacOS/lib/libvlc.dylib",
                "/opt/homebrew/lib/libvlc.dylib",
                "/usr/local/lib/libvlc.dylib",
            ]
        )
    elif sys.platform == "win32":
        home = os.environ.get("VLC_HOME", "").strip()
        if home:
            paths.append(os.path.join(home, "libvlc.dll"))
        paths.extend(
            [
                "libvlc.dll",
                r"C:\Program Files\VideoLAN\VLC\libvlc.dll",
                r"C:\Program Files (x86)\VideoLAN\VLC\libvlc.dll",
            ]
        )
    seen = set()
    out: List[str] = []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _bind(lib: ctypes.CDLL) -> None:
    lib.libvlc_new.argtypes = [c_int, POINTER(c_char_p)]
    lib.libvlc_new.restype = c_void_p
    lib.libvlc_release.argtypes = [c_void_p]
    lib.libvlc_release.restype = None
    lib.libvlc_retain.argtypes = [c_void_p]
    lib.libvlc_retain.restype = None

    lib.libvlc_get_version.argtypes = []
    lib.libvlc_get_version.restype = c_char_p
    lib.libvlc_errmsg.argtypes = []
    lib.libvlc_errmsg.restype = c_char_p
    try:
        lib.libvlc_clearerr.argtypes = []
        lib.libvlc_clearerr.restype = None
    except AttributeError:
        pass

    lib.libvlc_set_user_agent.argtypes = [c_void_p, c_char_p, c_char_p]
    lib.libvlc_set_user_agent.restype = None
    lib.libvlc_set_app_id.argtypes = [c_void_p, c_char_p, c_char_p, c_char_p]
    lib.libvlc_set_app_id.restype = None

    lib.libvlc_media_player_new.argtypes = [c_void_p]
    lib.libvlc_media_player_new.restype = c_void_p
    lib.libvlc_media_player_release.argtypes = [c_void_p]
    lib.libvlc_media_player_release.restype = None
    lib.libvlc_media_player_set_media.argtypes = [c_void_p, c_void_p]
    lib.libvlc_media_player_set_media.restype = None
    lib.libvlc_media_player_play.argtypes = [c_void_p]
    lib.libvlc_media_player_play.restype = c_int
    lib.libvlc_media_player_stop.argtypes = [c_void_p]
    lib.libvlc_media_player_stop.restype = None
    lib.libvlc_media_player_set_pause.argtypes = [c_void_p, c_int]
    lib.libvlc_media_player_set_pause.restype = None
    lib.libvlc_media_player_is_playing.argtypes = [c_void_p]
    lib.libvlc_media_player_is_playing.restype = c_int
    lib.libvlc_media_player_get_state.argtypes = [c_void_p]
    lib.libvlc_media_player_get_state.restype = c_int
    lib.libvlc_media_player_get_time.argtypes = [c_void_p]
    lib.libvlc_media_player_get_time.restype = c_int64
    lib.libvlc_media_player_set_time.argtypes = [c_void_p, c_int64]
    lib.libvlc_media_player_set_time.restype = None
    lib.libvlc_media_player_get_length.argtypes = [c_void_p]
    lib.libvlc_media_player_get_length.restype = c_int64
    lib.libvlc_media_player_set_position.argtypes = [c_void_p, c_float]
    lib.libvlc_media_player_set_position.restype = None
    lib.libvlc_media_player_event_manager.argtypes = [c_void_p]
    lib.libvlc_media_player_event_manager.restype = c_void_p

    lib.libvlc_audio_set_volume.argtypes = [c_void_p, c_int]
    lib.libvlc_audio_set_volume.restype = c_int
    lib.libvlc_audio_get_volume.argtypes = [c_void_p]
    lib.libvlc_audio_get_volume.restype = c_int
    lib.libvlc_audio_set_mute.argtypes = [c_void_p, c_int]
    lib.libvlc_audio_set_mute.restype = c_int
    lib.libvlc_audio_output_device_enum.argtypes = [c_void_p]
    lib.libvlc_audio_output_device_enum.restype = POINTER(AudioOutputDevice)
    lib.libvlc_audio_output_device_list_release.argtypes = [POINTER(AudioOutputDevice)]
    lib.libvlc_audio_output_device_list_release.restype = None
    lib.libvlc_audio_output_device_set.argtypes = [c_void_p, c_char_p, c_char_p]
    lib.libvlc_audio_output_device_set.restype = c_int
    lib.libvlc_audio_output_device_get.argtypes = [c_void_p]
    lib.libvlc_audio_output_device_get.restype = c_char_p

    lib.libvlc_video_set_mouse_input.argtypes = [c_void_p, c_uint]
    lib.libvlc_video_set_mouse_input.restype = None
    lib.libvlc_video_set_key_input.argtypes = [c_void_p, c_uint]
    lib.libvlc_video_set_key_input.restype = None
    lib.libvlc_video_get_size.argtypes = [c_void_p, c_uint, POINTER(c_uint), POINTER(c_uint)]
    lib.libvlc_video_get_size.restype = c_int
    lib.libvlc_video_get_track_count.argtypes = [c_void_p]
    lib.libvlc_video_get_track_count.restype = c_int
    lib.libvlc_video_get_track.argtypes = [c_void_p]
    lib.libvlc_video_get_track.restype = c_int
    lib.libvlc_video_set_track.argtypes = [c_void_p, c_int]
    lib.libvlc_video_set_track.restype = c_int
    try:
        lib.libvlc_video_set_subtitle_file.argtypes = [c_void_p, c_char_p]
        lib.libvlc_video_set_subtitle_file.restype = c_int
    except AttributeError:
        pass

    if sys.platform.startswith("linux"):
        lib.libvlc_media_player_set_xwindow.argtypes = [c_void_p, c_uint]
        lib.libvlc_media_player_set_xwindow.restype = None
    if sys.platform == "win32":
        lib.libvlc_media_player_set_hwnd.argtypes = [c_void_p, c_void_p]
        lib.libvlc_media_player_set_hwnd.restype = None
    if sys.platform == "darwin":
        lib.libvlc_media_player_set_nsobject.argtypes = [c_void_p, c_void_p]
        lib.libvlc_media_player_set_nsobject.restype = None

    lib.libvlc_media_new_path.argtypes = [c_void_p, c_char_p]
    lib.libvlc_media_new_path.restype = c_void_p
    lib.libvlc_media_release.argtypes = [c_void_p]
    lib.libvlc_media_release.restype = None
    lib.libvlc_media_add_option.argtypes = [c_void_p, c_char_p]
    lib.libvlc_media_add_option.restype = None
    lib.libvlc_media_get_duration.argtypes = [c_void_p]
    lib.libvlc_media_get_duration.restype = c_int64
    try:
        lib.libvlc_media_parse_with_options.argtypes = [c_void_p, c_int, c_int]
        lib.libvlc_media_parse_with_options.restype = c_int
    except AttributeError:
        pass
    try:
        lib.libvlc_media_parse.argtypes = [c_void_p]
        lib.libvlc_media_parse.restype = None
    except AttributeError:
        pass

    lib.libvlc_event_attach.argtypes = [c_void_p, c_int, EventCallback, c_void_p]
    lib.libvlc_event_attach.restype = c_int


def load_libvlc(force: bool = False) -> ctypes.CDLL:
    """Load libvlc from bundled path / system. Raises OSError on failure."""
    global _LIB, _LOAD_ERROR
    if _LIB is not None and not force:
        return _LIB
    try:
        from ..native_core_paths import configure_bundled_native_core

        configure_bundled_native_core()
    except Exception:
        pass
    last: Optional[BaseException] = None
    for path in _candidate_lib_paths():
        try:
            lib = ctypes.CDLL(path)
            _bind(lib)
            _LIB = lib
            _LOAD_ERROR = None
            return lib
        except (OSError, AttributeError) as exc:
            last = exc
            continue
    _LOAD_ERROR = str(last) if last else "libvlc not found"
    raise OSError(_LOAD_ERROR)


def libvlc_get_version() -> bytes:
    lib = load_libvlc()
    raw = lib.libvlc_get_version()
    return raw or b""


def libvlc_errmsg() -> Optional[bytes]:
    if _LIB is None:
        try:
            load_libvlc()
        except OSError:
            return None
    assert _LIB is not None
    return _LIB.libvlc_errmsg()


def libvlc_clearerr() -> None:
    if _LIB is None:
        return
    clear = getattr(_LIB, "libvlc_clearerr", None)
    if callable(clear):
        clear()


def libvlc_audio_output_device_list_release(head) -> None:
    if _LIB is None or head is None:
        return
    _LIB.libvlc_audio_output_device_list_release(head)


def _b(s: Optional[Union[str, bytes]]) -> Optional[bytes]:
    if s is None:
        return None
    if isinstance(s, bytes):
        return s
    return str(s).encode("utf-8", "surrogateescape")


class EventManager:
    def __init__(self, ptr: int, lib: ctypes.CDLL):
        self._ptr = ptr
        self._lib = lib
        self._kept: List[Any] = []

    def event_attach(self, event_type: int, callback: Callable[..., Any], *user_args: Any) -> int:
        et = int(event_type)

        @EventCallback
        def _c_cb(event_ptr, _data):  # type: ignore[misc]
            try:
                if user_args:
                    callback(event_ptr.contents if event_ptr else None, *user_args)
                else:
                    callback(event_ptr.contents if event_ptr else None)
            except Exception:
                pass

        self._kept.append(_c_cb)
        return int(self._lib.libvlc_event_attach(self._ptr, et, _c_cb, None))


class Media:
    def __init__(self, ptr: int, lib: ctypes.CDLL):
        self._ptr = ptr
        self._lib = lib
        self._as_parameter_ = ptr

    def add_option(self, option: str) -> None:
        self._lib.libvlc_media_add_option(self._ptr, _b(option))

    def parse_with_options(self, parse_flag: int = 0, timeout: int = 2000) -> int:
        fn = getattr(self._lib, "libvlc_media_parse_with_options", None)
        if fn is None:
            self.parse()
            return 0
        return int(fn(self._ptr, int(parse_flag), int(timeout)))

    def parse(self) -> None:
        fn = getattr(self._lib, "libvlc_media_parse", None)
        if fn is not None:
            fn(self._ptr)

    def get_duration(self) -> int:
        return int(self._lib.libvlc_media_get_duration(self._ptr))

    def release(self) -> None:
        if self._ptr:
            self._lib.libvlc_media_release(self._ptr)
            self._ptr = 0
            self._as_parameter_ = 0


class MediaPlayer:
    def __init__(self, ptr: int, lib: ctypes.CDLL):
        self._ptr = ptr
        self._lib = lib
        self._as_parameter_ = ptr
        self._event_manager: Optional[EventManager] = None

    def set_media(self, media: Optional[Media]) -> None:
        self._lib.libvlc_media_player_set_media(
            self._ptr, media._ptr if media is not None else None
        )

    def play(self) -> int:
        return int(self._lib.libvlc_media_player_play(self._ptr))

    def stop(self) -> None:
        self._lib.libvlc_media_player_stop(self._ptr)

    def set_pause(self, do_pause: bool) -> None:
        self._lib.libvlc_media_player_set_pause(self._ptr, 1 if do_pause else 0)

    def is_playing(self) -> int:
        return int(self._lib.libvlc_media_player_is_playing(self._ptr))

    def get_state(self) -> int:
        return int(self._lib.libvlc_media_player_get_state(self._ptr))

    def get_time(self) -> int:
        return int(self._lib.libvlc_media_player_get_time(self._ptr))

    def set_time(self, ms: int) -> None:
        self._lib.libvlc_media_player_set_time(self._ptr, int(ms))

    def get_length(self) -> int:
        return int(self._lib.libvlc_media_player_get_length(self._ptr))

    def set_position(self, pos: float) -> None:
        self._lib.libvlc_media_player_set_position(self._ptr, float(pos))

    def audio_set_volume(self, volume: int) -> int:
        return int(self._lib.libvlc_audio_set_volume(self._ptr, int(volume)))

    def audio_get_volume(self) -> int:
        return int(self._lib.libvlc_audio_get_volume(self._ptr))

    def audio_set_mute(self, status: bool) -> int:
        return int(self._lib.libvlc_audio_set_mute(self._ptr, 1 if status else 0))

    def audio_output_device_enum(self):
        return self._lib.libvlc_audio_output_device_enum(self._ptr)

    def audio_output_device_set(self, module: Optional[str], device_id: Optional[str]) -> int:
        return int(
            self._lib.libvlc_audio_output_device_set(
                self._ptr, _b(module) if module else None, _b(device_id) if device_id is not None else b""
            )
        )

    def audio_output_device_get(self) -> Optional[bytes]:
        return self._lib.libvlc_audio_output_device_get(self._ptr)

    def video_set_mouse_input(self, on: bool) -> None:
        self._lib.libvlc_video_set_mouse_input(self._ptr, 1 if on else 0)

    def video_set_key_input(self, on: bool) -> None:
        self._lib.libvlc_video_set_key_input(self._ptr, 1 if on else 0)

    def video_get_size(self, num: int = 0) -> Tuple[int, int]:
        px = c_uint(0)
        py = c_uint(0)
        rc = self._lib.libvlc_video_get_size(self._ptr, int(num), ctypes.byref(px), ctypes.byref(py))
        if rc != 0:
            return (0, 0)
        return (int(px.value), int(py.value))

    def video_get_track_count(self) -> int:
        return int(self._lib.libvlc_video_get_track_count(self._ptr))

    def video_get_track(self) -> int:
        return int(self._lib.libvlc_video_get_track(self._ptr))

    def video_set_track(self, track: int) -> int:
        return int(self._lib.libvlc_video_set_track(self._ptr, int(track)))

    def video_set_subtitle_file(self, path: str) -> int:
        fn = getattr(self._lib, "libvlc_video_set_subtitle_file", None)
        if fn is None:
            return -1
        return int(fn(self._ptr, _b(path)))

    def set_xwindow(self, wid: int) -> None:
        self._lib.libvlc_media_player_set_xwindow(self._ptr, c_uint(int(wid) & 0xFFFFFFFF))

    def set_hwnd(self, hwnd: int) -> None:
        self._lib.libvlc_media_player_set_hwnd(self._ptr, c_void_p(int(hwnd)))

    def set_nsobject(self, obj: int) -> None:
        self._lib.libvlc_media_player_set_nsobject(self._ptr, c_void_p(int(obj)))

    def event_manager(self) -> EventManager:
        if self._event_manager is None:
            ptr = self._lib.libvlc_media_player_event_manager(self._ptr)
            self._event_manager = EventManager(ptr, self._lib)
        return self._event_manager

    def release(self) -> None:
        if self._ptr:
            self._lib.libvlc_media_player_release(self._ptr)
            self._ptr = 0
            self._as_parameter_ = 0
            self._event_manager = None


class Instance:
    def __init__(self, *args: Union[str, Sequence[str]]):
        lib = load_libvlc()
        flat: List[str] = []
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            flat = [str(a) for a in args[0]]
        else:
            flat = [str(a) for a in args]
        argc = len(flat)
        if argc == 0:
            ptr = lib.libvlc_new(0, None)
        else:
            arr = (c_char_p * argc)(*[_b(a) for a in flat])
            ptr = lib.libvlc_new(argc, arr)
        if not ptr:
            err = libvlc_errmsg()
            detail = err.decode("utf-8", "replace") if err else "libvlc_new failed"
            raise OSError(detail)
        self._lib = lib
        self._ptr = ptr
        self._as_parameter_ = ptr
        # Keep argv alive for the lifetime of the instance (libvlc may read it).
        self._argv_keep = flat

    def media_player_new(self) -> MediaPlayer:
        ptr = self._lib.libvlc_media_player_new(self._ptr)
        if not ptr:
            raise OSError("libvlc_media_player_new failed")
        return MediaPlayer(ptr, self._lib)

    def media_new_path(self, path: str) -> Media:
        ptr = self._lib.libvlc_media_new_path(self._ptr, _b(path))
        if not ptr:
            raise OSError(f"libvlc_media_new_path failed for {path!r}")
        return Media(ptr, self._lib)

    def set_user_agent(self, name: str, http: str) -> None:
        self._lib.libvlc_set_user_agent(self._ptr, _b(name), _b(http))

    def set_app_id(self, app_id: str, version: str, icon: str) -> None:
        self._lib.libvlc_set_app_id(self._ptr, _b(app_id), _b(version), _b(icon))

    def release(self) -> None:
        if self._ptr:
            self._lib.libvlc_release(self._ptr)
            self._ptr = 0
            self._as_parameter_ = 0


def probe() -> str:
    """Return libvlc version string or raise OSError."""
    ver = libvlc_get_version()
    if not ver:
        raise OSError("libvlc version unavailable")
    return ver.decode("utf-8", "replace") if isinstance(ver, bytes) else str(ver)
