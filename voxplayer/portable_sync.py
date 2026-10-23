"""Detect mounted portable/USB volumes and sync playlists or podcasts.

Linux-first: ``/proc/mounts`` + ``/sys/block/*/removable``, plus common
``/run/media/$USER`` and ``/media/$USER`` mount roots. macOS/Windows get
best-effort volume roots without a second media stack — sync is file copy only.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple


@dataclass
class PortableVolume:
    label: str
    path: str
    device: str = ""
    removable: bool = True


def _user() -> str:
    return os.environ.get("USER") or os.environ.get("USERNAME") or "user"


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _block_device_from_source(source: str) -> str:
    """``/dev/sdb1`` → ``sdb``; ``/dev/nvme0n1p1`` → ``nvme0n1``."""
    base = os.path.basename(source)
    if base.startswith("nvme") and "p" in base:
        return base.rsplit("p", 1)[0]
    i = len(base)
    while i > 0 and base[i - 1].isdigit():
        i -= 1
    return base[:i] or base


def _is_removable_device(source: str) -> bool:
    if not source.startswith("/dev/"):
        return False
    block = _block_device_from_source(source)
    if _read_text(f"/sys/block/{block}/removable") == "1":
        return True
    by_id = "/dev/disk/by-id"
    try:
        real_source = os.path.realpath(source)
        for name in os.listdir(by_id):
            if not name.startswith("usb-"):
                continue
            target = os.path.realpath(os.path.join(by_id, name))
            if real_source == target or real_source.startswith(target):
                return True
            if target == real_source or os.path.basename(real_source).startswith(
                os.path.basename(target)
            ):
                return True
    except OSError:
        pass
    return False


def _unescape_mount(path: str) -> str:
    try:
        return path.encode("utf-8").decode("unicode_escape")
    except Exception:
        return path.replace("\\040", " ")


def _linux_mounts() -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 3:
                    continue
                out.append((parts[0], _unescape_mount(parts[1]), parts[2]))
    except OSError:
        pass
    return out


def list_portable_volumes() -> List[PortableVolume]:
    """Enumerate likely portable / removable mounted volumes."""
    seen: Set[str] = set()
    volumes: List[PortableVolume] = []

    def _add(path: str, device: str = "", label: str = "") -> None:
        path = os.path.abspath(path)
        if not path or path in seen or not os.path.isdir(path):
            return
        if path in {"/", "/home", "/boot", "/boot/efi", "/usr", "/var", "/tmp"}:
            return
        # Skip if path is the user's home itself
        home = os.path.expanduser("~")
        if path == home:
            return
        seen.add(path)
        name = label or os.path.basename(path.rstrip(os.sep)) or path
        volumes.append(PortableVolume(label=name, path=path, device=device, removable=True))

    if sys.platform.startswith("linux"):
        user = _user()
        media_roots = [
            os.path.abspath(f"/run/media/{user}"),
            os.path.abspath(f"/media/{user}"),
            os.path.abspath("/media"),
        ]
        for source, target, fstype in _linux_mounts():
            if fstype in {
                "proc",
                "sysfs",
                "devtmpfs",
                "devpts",
                "tmpfs",
                "cgroup",
                "cgroup2",
                "squashfs",
                "overlay",
            }:
                continue
            abs_target = os.path.abspath(target)
            under_media = any(
                abs_target == root or abs_target.startswith(root + os.sep)
                for root in media_roots
            )
            if not (_is_removable_device(source) or under_media):
                continue
            _add(abs_target, device=source)

        for root in (f"/run/media/{user}", f"/media/{user}"):
            if not os.path.isdir(root):
                continue
            try:
                for name in os.listdir(root):
                    path = os.path.join(root, name)
                    if os.path.isdir(path):
                        _add(path, label=name)
            except OSError:
                pass

    elif sys.platform == "darwin":
        root = "/Volumes"
        if os.path.isdir(root):
            try:
                for name in os.listdir(root):
                    if name in {"Macintosh HD", "Macintosh HD - Data"}:
                        continue
                    path = os.path.join(root, name)
                    if os.path.isdir(path):
                        _add(path, label=name)
            except OSError:
                pass

    elif sys.platform.startswith("win"):
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            path = f"{letter}:\\"
            if os.path.isdir(path):
                _add(path, label=f"{letter}:")

    volumes.sort(key=lambda v: v.label.lower())
    return volumes


def write_m3u(playlist_path: str, media_paths: Sequence[str], *, relative: bool = True) -> None:
    lines = ["#EXTM3U"]
    base = os.path.dirname(playlist_path)
    for path in media_paths:
        if not path:
            continue
        entry = os.path.relpath(path, base) if relative else path
        lines.append(entry.replace("\\", "/"))
    with open(playlist_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _unique_dest(folder: str, filename: str) -> str:
    dest = os.path.join(folder, filename)
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(filename)
    n = 2
    while True:
        cand = os.path.join(folder, f"{stem}_{n}{ext}")
        if not os.path.exists(cand):
            return cand
        n += 1


_MEDIA_EXTS = {
    ".mp3",
    ".flac",
    ".wav",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".m4v",
}


def on_device_library_root(volume_path: str, subdir: str = "VoxPlayer") -> str:
    return os.path.join(volume_path, subdir)


def list_on_device_library(
    volume_path: str, *, subdir: str = "VoxPlayer"
) -> Tuple[str, List[str], List[str]]:
    """
    List media files and M3U playlists under ``volume/VoxPlayer``.

    Returns ``(root, media_paths, m3u_paths)``. Missing root → empty lists.
    """
    root = on_device_library_root(volume_path, subdir)
    media: List[str] = []
    playlists: List[str] = []
    if not os.path.isdir(root):
        return root, media, playlists
    try:
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                ext = os.path.splitext(name)[1].lower()
                if ext in {".m3u", ".m3u8"}:
                    playlists.append(path)
                elif ext in _MEDIA_EXTS:
                    media.append(path)
    except OSError:
        pass
    media.sort(key=lambda p: os.path.basename(p).lower())
    playlists.sort(key=lambda p: os.path.basename(p).lower())
    return root, media, playlists


def sync_files_to_volume(
    volume_path: str,
    files: Iterable[str],
    *,
    subdir: str = "VoxPlayer",
    playlist_name: str = "",
) -> Tuple[int, int, str]:
    """
    Copy media files onto ``volume_path/subdir``.

    Returns ``(copied, skipped_or_failed, destination_dir)``.
    Optionally writes an M3U named ``playlist_name``.
    """
    files = [os.path.abspath(p) for p in files if p and os.path.isfile(p)]
    dest_root = os.path.join(volume_path, subdir)
    os.makedirs(dest_root, exist_ok=True)
    copied = 0
    skipped = 0
    placed: List[str] = []
    for src in files:
        name = os.path.basename(src)
        dest = os.path.join(dest_root, name)
        try:
            if os.path.isfile(dest) and os.path.getsize(dest) == os.path.getsize(src):
                skipped += 1
                placed.append(dest)
                continue
            dest = _unique_dest(dest_root, name) if os.path.exists(dest) else dest
            shutil.copy2(src, dest)
            copied += 1
            placed.append(dest)
        except OSError:
            skipped += 1
    if playlist_name and placed:
        safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in playlist_name).strip() or "Playlist"
        m3u = os.path.join(dest_root, f"{safe}.m3u")
        write_m3u(m3u, placed, relative=True)
    return copied, skipped, dest_root
