"""Media helpers: thumbnails, metadata enrichment, torrent gating."""

from .thumbnails import ThumbnailCache, get_thumbnail_path
from .metadata import (
    MediaMetadata,
    enrich_metadata,
    file_identity,
    is_online,
    load_local_metadata,
    load_cached_metadata,
)
from .torrent_gate import (
    MEDIA_EXTENSIONS,
    PLAYLIST_EXTENSIONS,
    is_media_library_torrent,
    validate_torrent_file,
    validate_torrent_file_list,
)

__all__ = [
    "ThumbnailCache",
    "get_thumbnail_path",
    "MediaMetadata",
    "enrich_metadata",
    "file_identity",
    "is_online",
    "load_local_metadata",
    "load_cached_metadata",
    "MEDIA_EXTENSIONS",
    "PLAYLIST_EXTENSIONS",
    "is_media_library_torrent",
    "validate_torrent_file",
    "validate_torrent_file_list",
]
