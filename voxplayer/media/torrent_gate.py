"""Gate torrents: only accept contents that look like a media library."""

from __future__ import annotations

import os
from typing import Iterable, List, Optional, Sequence, Tuple

from .bencode import decode as bdecode

VIDEO_EXTENSIONS = {
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
AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
    ".ape",
    ".aiff",
}
PLAYLIST_EXTENSIONS = {".m3u", ".m3u8", ".pls", ".xspf", ".cue"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Common non-media payloads we explicitly reject when they dominate.
JUNK_EXTENSIONS = {
    ".iso",
    ".img",
    ".dmg",
    ".exe",
    ".msi",
    ".apk",
    ".deb",
    ".rpm",
    ".zip",
    ".rar",
    ".7z",
    ".gz",
    ".xz",
    ".torrent",
}


def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def _paths_from_info(info: dict) -> List[str]:
    """Extract relative file paths from torrent info dict."""
    files = info.get(b"files")
    if files is None:
        name = info.get(b"name", b"")
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        return [name] if name else []
    paths = []
    for entry in files:
        parts = entry.get(b"path") or []
        segs = []
        for p in parts:
            if isinstance(p, bytes):
                segs.append(p.decode("utf-8", errors="replace"))
            else:
                segs.append(str(p))
        if segs:
            paths.append("/".join(segs))
    return paths


def classify_paths(paths: Sequence[str]) -> dict:
    media = []
    playlists = []
    junk = []
    other = []
    for path in paths:
        ext = _ext(path)
        if ext in MEDIA_EXTENSIONS:
            media.append(path)
        elif ext in PLAYLIST_EXTENSIONS:
            playlists.append(path)
        elif ext in JUNK_EXTENSIONS:
            junk.append(path)
        else:
            other.append(path)
    return {
        "media": media,
        "playlists": playlists,
        "junk": junk,
        "other": other,
        "paths": list(paths),
    }


def is_media_library_torrent(paths: Sequence[str]) -> Tuple[bool, str]:
    """
    Accept when the torrent looks like video/music/playlist media.
    Reject ISO/distro/archives and torrents with no playable media.
    """
    if not paths:
        return False, "Torrent has no files to inspect."

    stats = classify_paths(paths)
    media_count = len(stats["media"])
    playlist_count = len(stats["playlists"])
    junk_count = len(stats["junk"])
    total = len(paths)

    # Require at least one audio or video file (playlists alone are not enough).
    if media_count == 0:
        if junk_count:
            return (
                False,
                "Torrent rejected: contents look like installers/ISOs/archives, not audio/video media.",
            )
        if playlist_count:
            return (
                False,
                "Torrent rejected: playlist-only torrents are not accepted; include audio or video files.",
            )
        return (
            False,
            "Torrent rejected: no audio or video files found in the torrent contents.",
        )

    if junk_count >= media_count and media_count > 0 and junk_count / max(total, 1) >= 0.5:
        # Mixed: allow if there is substantial media, else reject.
        media_ratio = media_count / max(total, 1)
        if media_ratio < 0.2:
            return (
                False,
                "Torrent rejected: majority of files are non-media (ISO/archive); not a media library.",
            )

    kinds = []
    if any(_ext(p) in VIDEO_EXTENSIONS for p in stats["media"]):
        kinds.append("video")
    if any(_ext(p) in AUDIO_EXTENSIONS for p in stats["media"]):
        kinds.append("audio")
    if playlist_count:
        kinds.append("playlist")
    kind_txt = "/".join(kinds) if kinds else "media"
    return True, f"Accepted as {kind_txt} library ({media_count} media, {playlist_count} playlist)."


def validate_torrent_file(torrent_path: str) -> Tuple[bool, str, List[str]]:
    """Parse .torrent metainfo and gate before add. Returns (ok, message, paths)."""
    if not torrent_path or not os.path.isfile(torrent_path):
        return False, "Torrent file not found.", []
    try:
        with open(torrent_path, "rb") as fh:
            raw = fh.read()
        meta = bdecode(raw)
        if not isinstance(meta, dict) or b"info" not in meta:
            return False, "Invalid torrent metainfo (missing info dictionary).", []
        paths = _paths_from_info(meta[b"info"])
        ok, msg = is_media_library_torrent(paths)
        return ok, msg, paths
    except Exception as exc:
        return False, f"Could not parse torrent metainfo: {exc}", []


def validate_torrent_file_list(names: Iterable[str]) -> Tuple[bool, str]:
    """Gate using client-provided file names after metadata download (magnets)."""
    paths = [str(n) for n in names if n]
    return is_media_library_torrent(paths)
