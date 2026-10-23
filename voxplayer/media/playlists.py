"""Local playlist persistence (Favorites + user playlists) by absolute file paths."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional


def _store_root() -> str:
    root = os.path.join(os.path.expanduser("~"), ".local", "share", "voxplayer", "playlists")
    os.makedirs(root, exist_ok=True)
    return root


def _index_path() -> str:
    return os.path.join(_store_root(), "index.json")


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", " ") else "_" for ch in (name or "").strip())
    cleaned = cleaned.strip() or "Playlist"
    return cleaned[:80]


class PlaylistStore:
    """JSON-backed playlists keyed by display name; entries are absolute paths."""

    FAVORITES = "Favorites"

    def __init__(self):
        self._data: Dict[str, List[str]] = {}
        self.load()

    def load(self) -> None:
        path = _index_path()
        if not os.path.isfile(path):
            self._data = {self.FAVORITES: []}
            self.save()
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict):
                self._data = {
                    str(k): [p for p in (v or []) if isinstance(p, str)]
                    for k, v in raw.items()
                }
            else:
                self._data = {self.FAVORITES: []}
        except (OSError, json.JSONDecodeError, TypeError):
            self._data = {self.FAVORITES: []}
        self._data.setdefault(self.FAVORITES, [])

    def save(self) -> None:
        path = _index_path()
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def names(self) -> List[str]:
        names = list(self._data.keys())
        if self.FAVORITES in names:
            names.remove(self.FAVORITES)
            names.sort(key=str.lower)
            return [self.FAVORITES] + names
        names.sort(key=str.lower)
        return names

    def get(self, name: str) -> List[str]:
        return list(self._data.get(name, []))

    def create(self, name: str) -> str:
        key = _safe_name(name)
        if key not in self._data:
            self._data[key] = []
            self.save()
        return key

    def delete(self, name: str) -> bool:
        if name == self.FAVORITES or name not in self._data:
            return False
        del self._data[name]
        self.save()
        return True

    def add(self, name: str, path: str) -> bool:
        if not path:
            return False
        key = name if name in self._data else self.create(name)
        abspath = os.path.abspath(path)
        entries = self._data.setdefault(key, [])
        if abspath in entries:
            return False
        entries.append(abspath)
        self.save()
        return True

    def remove(self, name: str, path: str) -> bool:
        if name not in self._data:
            return False
        abspath = os.path.abspath(path)
        entries = self._data[name]
        if abspath not in entries:
            return False
        entries.remove(abspath)
        self.save()
        return True

    def clear(self, name: str) -> None:
        if name in self._data:
            self._data[name] = []
            self.save()
