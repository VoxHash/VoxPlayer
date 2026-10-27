"""Native C media-core playback for VoxPlayer (no Qt Multimedia playback path)."""

from .playback import (
    PlaybackEngine,
    BackendKind,
    NativeEngineError,
    prefer_xcb_for_embed,
    prefer_xcb_for_mpv_embed,
    configure_embed_surface,
    native_engine_install_hint,
    show_native_engine_failure,
    require_vlc_module,
    embed_platform_hint,
    embed_status_message,
    libvlc_has_wayland_surface_api,
    resolve_decode_backend,
    create_playback_engine,
)
from .independence import (
    IndependenceReport,
    assert_e2e_independence_gates,
    build_independence_report,
)
from .decode_preflight import (
    DecodeAvailability,
    decode_install_hint,
    ensure_decode_backend,
    probe_decode_backends,
)

__all__ = [
    "PlaybackEngine",
    "BackendKind",
    "NativeEngineError",
    "prefer_xcb_for_embed",
    "prefer_xcb_for_mpv_embed",
    "configure_embed_surface",
    "native_engine_install_hint",
    "show_native_engine_failure",
    "require_vlc_module",
    "embed_platform_hint",
    "embed_status_message",
    "libvlc_has_wayland_surface_api",
    "resolve_decode_backend",
    "create_playback_engine",
    "IndependenceReport",
    "assert_e2e_independence_gates",
    "build_independence_report",
    "DecodeAvailability",
    "decode_install_hint",
    "ensure_decode_backend",
    "probe_decode_backends",
]
