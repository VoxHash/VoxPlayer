"""Persistent library fingerprints + play stats; incremental re-scan helpers.

Uses the native ``vox_scan`` / Zig scanner when available (same path as
``find_media_files_in_folder``) so watch-folder refreshes stay off the slow
pure-Python walk when the cdylib is built.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .native_scan import scan_media_dir

from .codecs import ALL_EXTENSIONS

DEFAULT_EXTS: Tuple[str, ...] = tuple(sorted(ALL_EXTENSIONS))


def _cache_path() -> str:
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = xdg if xdg else os.path.join(os.path.expanduser("~"), ".cache")
    root = os.path.join(base, "voxplayer")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "library_index.json")


def _file_fingerprint(path: str) -> Optional[Dict[str, int]]:
    try:
        st = os.stat(path)
        return {"mtime": int(st.st_mtime), "size": int(st.st_size)}
    except OSError:
        return None


@dataclass
class LibraryIndex:
    """Root → file fingerprints, plus per-path play stats."""

    roots: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "LibraryIndex":
        path = _cache_path()
        if not os.path.isfile(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError, TypeError):
            return cls()
        roots = data.get("roots") if isinstance(data, dict) else {}
        stats = data.get("stats") if isinstance(data, dict) else {}
        if not isinstance(roots, dict):
            roots = {}
        if not isinstance(stats, dict):
            stats = {}
        return cls(roots=roots, stats=stats)

    def save(self) -> None:
        payload = {"roots": self.roots, "stats": self.stats, "saved_at": time.time()}
        path = _cache_path()
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
        except OSError:
            try:
                if os.path.isfile(tmp):
                    os.unlink(tmp)
            except OSError:
                pass

    def record_play(self, path: str) -> None:
        if not path:
            return
        key = os.path.abspath(path)
        entry = self.stats.get(key) or {}
        entry["play_count"] = float(entry.get("play_count") or 0) + 1.0
        entry["last_played"] = float(time.time())
        self.stats[key] = entry

    def play_count(self, path: str) -> int:
        entry = self.stats.get(os.path.abspath(path)) or {}
        try:
            return int(entry.get("play_count") or 0)
        except (TypeError, ValueError):
            return 0

    def last_played(self, path: str) -> float:
        entry = self.stats.get(os.path.abspath(path)) or {}
        try:
            return float(entry.get("last_played") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def scan_root(
        self,
        root: str,
        *,
        extensions: Sequence[str] = DEFAULT_EXTS,
        walker: Optional[Callable[[str], List[str]]] = None,
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Incremental scan of ``root``.

        Returns ``(all_current, added_or_changed, removed)``.
        """
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            prev = set((self.roots.get(root) or {}).keys())
            self.roots.pop(root, None)
            return [], [], sorted(prev)

        if walker is not None:
            found = walker(root) or []
        else:
            found = scan_media_dir(root, extensions)
            if found is None:
                found = []
                for dirpath, _dirs, files in os.walk(root):
                    for name in files:
                        path = os.path.join(dirpath, name)
                        ext = os.path.splitext(name)[1].lower()
                        if ext in extensions or ext in {e.lower() for e in extensions}:
                            found.append(path)

        prev_map = dict(self.roots.get(root) or {})
        new_map: Dict[str, Dict[str, int]] = {}
        added_or_changed: List[str] = []
        current: List[str] = []

        for path in found:
            if not path:
                continue
            abs_path = os.path.abspath(path)
            fp = _file_fingerprint(abs_path)
            if not fp:
                continue
            current.append(abs_path)
            new_map[abs_path] = fp
            old = prev_map.get(abs_path)
            if old is None or old.get("mtime") != fp["mtime"] or old.get("size") != fp["size"]:
                added_or_changed.append(abs_path)

        removed = sorted(set(prev_map.keys()) - set(new_map.keys()))
        self.roots[root] = new_map
        return current, added_or_changed, removed

    def forget_paths(self, paths: Iterable[str]) -> None:
        drop = {os.path.abspath(p) for p in paths if p}
        for root, files in list(self.roots.items()):
            for p in list(files.keys()):
                if p in drop:
                    del files[p]
            if not files:
                self.roots.pop(root, None)
