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
    embed_platform_hint,
    embed_status_message,
    libvlc_has_wayland_surface_api,
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
    "embed_platform_hint",
    "embed_status_message",
    "libvlc_has_wayland_surface_api",
]
