"""Native C media-core playback for VoxPlayer (no Qt Multimedia playback path)."""

from .playback import (
    PlaybackEngine,
    BackendKind,
    NativeEngineError,
    prefer_xcb_for_embed,
    prefer_xcb_for_mpv_embed,
    native_engine_install_hint,
    show_native_engine_failure,
    require_vlc_module,
)

__all__ = [
    "PlaybackEngine",
    "BackendKind",
    "NativeEngineError",
    "prefer_xcb_for_embed",
    "prefer_xcb_for_mpv_embed",
    "native_engine_install_hint",
    "show_native_engine_failure",
    "require_vlc_module",
]
